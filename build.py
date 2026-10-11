#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["langcodes", "language_data"]
# ///
"""Build the OMW pronoun wordnet as a wn collection of WN-LMF 1.4 packages.

The design follows the KinDiv wordnet:

- ``omw-pronoun`` (language ``mul``) holds the concepts: one unlexicalized synset
  per concept code (``data/concepts.tsv``), with its definition, an ILI proposal
  when some language has a word for it, and the hypernym hierarchy, computed
  from the features (``1e;Du`` is under ``1;Du`` and ``1e;Pl``). Its lemmas are
  the codes, as unlexicalized senses.
- ``omw-pronoun-<tag>`` holds one language's words and no relations; the
  hierarchy is reached through the ILI once CILI accepts the proposals.

Case is inflection: case forms are ``<Form>`` variants tagged with their case,
never separate concepts. Bound forms (affixes) are variants of the free pronoun
with the same cells, or entries of their own. Every lemma and form records its
Unicode script (ISO 15924); forms from a transcribed source also get a
``<Pronunciation>``.

Word sources, in order: NTUMC (orthographic, the synsets still in its current
database), ``data/extra-lemmas.tsv`` (curated), Parabank Pronoun (languages NTUMC
lacks, or where Parabank's forms are orthographic), and TUFS, whose forms are
used only when they confirm a word already found (``data/tufs-candidates.tsv``
lists the rest for curation).

Usage: uv run build.py
"""

from __future__ import annotations

import csv
import json
import logging
import re
import shutil
import tarfile
import unicodedata
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import langcodes

import concepts as concept_table

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
#: the hierarchy browser, docs/hierarchy/index.html, and the data it shows
BROWSER = HERE / "docs" / "hierarchy"
BASE = "omw-pronoun"
VERSION = "0.1"
EMAIL = "bond@ieee.org"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
URL = "https://github.com/fcbond/omw-pronoun"
CITATION = (
    "Yu Jie Seah and Francis Bond (2014) Annotation of Pronouns in a Multilingual "
    "Corpus of Mandarin Chinese, English and Japanese. ISA-10."
)
DOCTYPE = (
    "<!DOCTYPE LexicalResource SYSTEM "
    '"http://globalwordnet.github.io/schemas/WN-LMF-1.4.dtd">'
)
DC_NAMESPACE = "https://globalwordnet.github.io/schemas/dc/"

#: NTUMC language columns -> BCP 47 tag and name
NTUMC_LANGUAGES = {
    "eng": ("en", "English"),
    "cmn": ("cmn", "Mandarin Chinese"),
    "jpn": ("ja", "Japanese"),
    "ind": ("id", "Indonesian"),
    "zsm": ("zsm", "Malay"),
    "ces": ("cs", "Czech"),
    "ita": ("it", "Italian"),
    "mya": ("my", "Burmese"),
    "qcn": ("cmn-Hant", "Mandarin Chinese (traditional)"),
}
#: individual-language codes whose macrolanguage tag is used instead
MACRO = {
    "arb": "ar",
    "zsm": "zsm",
    "cmn": "cmn",
    "hbs": "sh",
    "pes": "fa",
    "swh": "sw",
    "tgl": "tl",  # langcodes would make this fil
}

#: Unicode name prefix -> ISO 15924 script
SCRIPTS = {
    "LATIN": "Latn",
    "CYRILLIC": "Cyrl",
    "GREEK": "Grek",
    "ARABIC": "Arab",
    "HEBREW": "Hebr",
    "DEVANAGARI": "Deva",
    "BENGALI": "Beng",
    "GURMUKHI": "Guru",
    "GUJARATI": "Gujr",
    "TAMIL": "Taml",
    "TELUGU": "Telu",
    "KANNADA": "Knda",
    "MALAYALAM": "Mlym",
    "SINHALA": "Sinh",
    "THAI": "Thai",
    "LAO": "Laoo",
    "KHMER": "Khmr",
    "MYANMAR": "Mymr",
    "TIBETAN": "Tibt",
    "GEORGIAN": "Geor",
    "ARMENIAN": "Armn",
    "ETHIOPIC": "Ethi",
    "HANGUL": "Hang",
    "CJK": "Hani",
    "HIRAGANA": "Hira",
    "KATAKANA": "Kana",
    "MONGOLIAN": "Mong",
}
#: letters and marks only IPA uses, marking a form as a transcription
IPA = re.compile(r"[ɐ-ʯːˈˌʰʲʷɪʊəɛɔæðθŋʃʒɲɨʉɯɤɑɒ]")


def script_of(form: str) -> str:
    """The ISO 15924 script of a form; Japanese kana with kanji is ``Jpan``.

    >>> script_of("我们"), script_of("わたし"), script_of("私たち"), script_of("my")
    ('Hani', 'Hira', 'Jpan', 'Latn')
    """
    found = set()
    for ch in form:
        if not ch.isalpha():
            continue
        name = unicodedata.name(ch, "")
        found |= {s for prefix, s in SCRIPTS.items() if name.startswith(prefix)}
    if (
        {"Hani", "Hira"} <= found
        or {"Hani", "Kana"} <= found
        or {"Hira", "Kana"} <= found
    ):
        return "Jpan"
    return found.pop() if len(found) == 1 else ""


def slug(code: str) -> str:
    """An XML-safe id fragment for a code: ``1i;Du`` -> ``1i-Du``."""
    return code.replace(";", "-").replace("+", "_")


#: concept code -> part of speech (n pronoun, a determiner, r pro-adverb), filled
#: from data/concepts.tsv by `main`
POS: dict[str, str] = {}
#: lexicographer file per part of speech: pro-forms cut across parts of speech
LEXFILES = {"n": "noun.pronoun", "a": "adj.pronoun", "r": "adv.pronoun"}


# --- the concept hierarchy ---------------------------------------------------

SLOTS = {
    "person": {"1", "1e", "1i", "2", "3"},
    "number": {"Sg", "Du", "Tr", "Pl", "Gpl"},
    "gender": {"M", "F", "N"},
}
EXPAND = {
    # an entity is a person or a thing: English *which* covers *who* and *what*
    "Ent": {"Pers", "Thng"},
    "1": {"1e", "1i"},
    "Pl": {"Du", "Tr", "Gpl"},
    # distal is not proximal: English *that* covers Japanese *sore* and *are*
    "Dist": {"Med", "Rem"},
    # the English-based indefinite types are unions of Haspelmath's functions,
    # as his English data shows: some-, any- (with ever-). The negative (no-) is
    # not one: *nobody* is used in direct negation, as *anybody* is, but carries
    # the negation itself, so it is not a kind of *anybody*
    "Asrt": {"SK", "SU", "IRR", "Q", "COND"},
    "Elec": {"Q", "COND", "INEG", "DNEG", "COMP", "FC"},
}


def features(code: str) -> dict[str, frozenset[str]]:
    """A code's features, slot -> values; unnamed slots are keyed by position.

    >>> features("1e;Du") == {"person": {"1e"}, "number": {"Du"}}
    True
    """
    found: dict[str, frozenset[str]] = {}
    for part in code.split(";") if code else []:
        values = frozenset(part.split("+"))
        slot = next((s for s, vs in SLOTS.items() if values <= vs), None)
        found[slot or category_of(values)] = values
    return found


#: the paper's other slots, by value
CATEGORIES = {
    "head": {
        "Pers",
        "Thng",
        "Ent",
        "Plc",
        "Tim",
        "Mnr",
        "Rsn",
        "Knd",
        "Dur",
        "Qnt",
        "Dx",
        "Det",
        "NStd",
    },
    "type": {
        "Asrt",
        "Elec",
        "Neg",
        "Univ",
        "Int",
        "Refl",
        "Recp",
        "Oth",
        "SK",
        "SU",
        "IRR",
        "Q",
        "COND",
        "INEG",
        "DNEG",
        "COMP",
        "FC",
    },
    "case": {"Poss"},
    "formality": {"Fml", "Infml"},
    "politeness": {"Pol", "Hon", "NHon"},
    "proximity": {"Prox", "Med", "Dist", "Rem"},
    "direction": {"Loc", "Goal", "Src"},
    "register": {"Men", "Wom", "Arch"},
}


def category_of(values: frozenset[str]) -> str:
    """The slot a set of values belongs to (by its first value)."""
    value = next(iter(values))
    return next((c for c, vs in CATEGORIES.items() if value in vs), f"?{value}")


def expand(values: frozenset[str]) -> set[str]:
    """Unmarked values stand for their marked ones: 1 = 1e + 1i, Dist = Med + Rem."""
    out = set()
    for v in values:
        out |= EXPAND.get(v, {v})
    return out


def subsumes(general: str, specific: str) -> bool:
    """True if every feature of `general` is implied by `specific`.

    A possessive is not a kind of its pronoun (*my* is not a kind of *I*), so
    possessives and non-possessives never subsume each other.

    >>> subsumes("1;Sg", "1;Sg;Poss"), subsumes("1;Poss", "1;Sg;Poss")
    (False, True)
    >>> subsumes("Ent;Sg;Dist", "Ent;Sg;Rem"), subsumes("Pers;Sg;Elec", "Pers;Sg;Neg")
    (True, False)
    >>> subsumes("Plc;Int", "Plc;Goal;Int"), subsumes("Plc;Loc;Int", "Plc;Goal;Int")
    (True, False)
    >>> subsumes("Ent;Int", "Thng;Int"), subsumes("Thng;Int", "Ent;Int")
    (True, False)
    """
    g, s = features(general), features(specific)
    if ("case" in g) != ("case" in s):
        return False
    return all(
        slot in s and expand(vals) >= expand(s[slot]) for slot, vals in g.items()
    )


def hypernyms(
    codes: list[str], pos: dict[str, str] | None = None
) -> dict[str, set[str]]:
    """Each concept's closest strict generalizations among `codes`.

    Hypernymy stays within a part of speech: the pronoun *this* (``Ent;Sg;Prox``)
    is not a kind of the determiner *this* (``Sg;Prox``), nor *mine* of *my*.
    """
    pos = pos or {}
    found = {}
    for code in codes:
        above = [
            c
            for c in codes
            if c != code
            and pos.get(c, "n") == pos.get(code, "n")
            and subsumes(c, code)
            and not subsumes(code, c)
        ]
        found[code] = {
            c for c in above if not any(c != d and subsumes(c, d) for d in above)
        }
    return found


# --- words -------------------------------------------------------------------


@dataclass
class Entry:
    """A lemma, its variant forms and the concepts it lexicalizes."""

    lemma: str
    tags: list[tuple[str, str]] = field(default_factory=list)  # e.g. ("morph", "bound")
    forms: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    senses: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    transcribed: bool = False
    pos: str = "n"


@dataclass
class Language:
    """The entries for one language tag."""

    tag: str
    name: str
    entries: dict[tuple[str, str, str], Entry] = field(default_factory=dict)

    def entry(self, lemma: str, code: str, bound: bool = False) -> Entry:
        """The entry for `lemma` as a word for `code`.

        An entry has one part of speech, taken from the concept, so *this* the
        determiner and *this* the pronoun are separate entries; a bound form is a
        separate entry too.
        """
        pos = POS.get(code, "n")
        key = (lemma, "bound" if bound else "", pos)
        if key not in self.entries:
            self.entries[key] = Entry(
                lemma, [("morph", "bound")] if bound else [], pos=pos
            )
        return self.entries[key]

    def has(self, form: str) -> dict[str, set[str]]:
        """Concepts of any entry whose lemma or variant is `form`."""
        found: dict[str, set[str]] = defaultdict(set)
        for entry in self.entries.values():
            if entry.lemma == form or form in entry.forms:
                for code, sources in entry.senses.items():
                    found[code] |= sources
        return found


def ntumc_lemmas(codes: set[str]) -> Iterator[tuple[str, str, str, str]]:
    """Yield (concept code, NTUMC language column, lemma, synset) for NTUMC lemmas.

    Only synsets still in the current NTUMC database, and only concepts in
    ``codes`` (NTUMC codes are made caseless: *we* and *us* are both ``1;Pl``).
    """
    current = {
        s
        for synsets in concept_table.ntumc_concepts(
            concept_table.ntumc_pronouns.DEFAULT_DB
        ).values()
        for s in synsets
    }
    with (DATA / "ntumc-pronouns.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            code = concept_table.concept_code(row)
            if row["synset"] not in current or code not in codes:
                continue
            for column in NTUMC_LANGUAGES:
                for lemma in filter(None, (x.strip() for x in row[column].split(";"))):
                    yield code, column, lemma, row["synset"]


def add_ntumc(languages: dict[str, Language], codes: set[str]) -> None:
    """Add NTUMC lemmas, with English case forms as variants of their lemma."""
    # English case form -> (lemma, case); keyed by form alone, since NTUMC may
    # file a form under a narrower concept than its lemma. Possessives are words
    # of their own: *her* the possessive is not a form of *she*
    with (DATA / "eng-paradigms.tsv").open(encoding="utf8") as handle:
        paradigms = {
            row["form"]: (row["lemma"], row["case"])
            for row in csv.DictReader(handle, delimiter="\t")
        }
    for tag, name in NTUMC_LANGUAGES.values():
        languages.setdefault(tag, Language(tag, name))
    for code, column, lemma, synset in ntumc_lemmas(codes):
        tag = NTUMC_LANGUAGES[column][0]
        language = languages[tag]
        # a Princeton synset NTUMC tags as a pronoun (here, all) carries the
        # wordnet's words for it, which nobody has checked as pronouns
        kind = (
            "NTUMC"
            if concept_table.ntumc_pronouns.is_inventory(synset)
            else "NTUMC wordnet"
        )
        source = f"{kind} {synset}"
        if tag == "en" and lemma in paradigms and "Poss" not in code:
            head, case = paradigms[lemma]
            entry = language.entry(head, code)
            entry.forms.setdefault(lemma, []).append(("case", case))
            entry.senses[code].add(source)
        else:
            language.entry(lemma, code).senses[code].add(source)


def add_extra(languages: dict[str, Language], codes: set[str]) -> None:
    """Add the curated lemmas of data/extra-lemmas.tsv, to existing lexicons."""
    tags = {c: t for c, (t, _) in NTUMC_LANGUAGES.items()}
    with (DATA / "extra-lemmas.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            tag = tags.get(row["lang"], row["lang"])
            if tag not in languages:
                logger.warning("extra lemma %s: no %s lexicon", row["form"], tag)
            elif row["code"] in codes:
                entry = languages[tag].entry(row["form"], row["code"])
                entry.senses[row["code"]].add(row["source"])


def add_wordnets(languages: dict[str, Language], codes: set[str]) -> None:
    """Add words for the ILI-linked concepts from existing wordnets.

    `wordnet_words.py` collects them in data/wordnet-words.tsv; nobody has
    checked them as pronouns, so the browser shows them only on request. Only
    languages that already have a lexicon get them.
    """
    with (DATA / "wordnet-words.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["tag"] in languages and row["concept"] in codes:
                entry = languages[row["tag"]].entry(row["word"], row["concept"])
                entry.senses[row["concept"]].add(row["source"])


def unchecked_sources() -> set[str]:
    """Sources of words nobody has checked as pronouns: existing wordnets."""
    with (DATA / "wordnet-words.tsv").open(encoding="utf8") as handle:
        return {row["source"] for row in csv.DictReader(handle, delimiter="\t")}


def is_unchecked(source: str, wordnets: set[str]) -> bool:
    """Whether a word's source is an existing wordnet, not a pronoun analysis."""
    return source in wordnets or source.startswith("NTUMC wordnet ")


def bcp47(iso: str) -> str:
    """The tag for an ISO 639-3 code, preferring NTUMC's tags."""
    ours = {
        "eng": "en",
        "jpn": "ja",
        "ind": "id",
        "ces": "cs",
        "ita": "it",
        "mya": "my",
    }
    return ours.get(iso) or MACRO.get(iso) or langcodes.standardize_tag(iso)


def add_parabank(languages: dict[str, Language], codes: set[str]) -> None:
    """Add Parabank lexemes: case and bound forms as variants.

    A language NTUMC already covers keeps only Parabank's orthographic forms; one
    whose Parabank forms are transcriptions (English ``aj``, ``ðɛj``) is skipped.
    """
    with (DATA / "parabank-lexemes.tsv").open(encoding="utf8") as handle:
        rows = [r for r in csv.DictReader(handle, delimiter="\t") if r["iso639_3"]]
    transcribed = defaultdict(bool)
    for row in rows:
        if IPA.search(row["lemma"] + row["variants"]) or ":" in row["lemma"]:
            transcribed[row["iso639_3"]] = True
    ntumc_tags = {t for t, _ in NTUMC_LANGUAGES.values()}
    free = {(r["language_id"], r["code"]): r for r in rows if r["analect"] == "free"}
    for row in rows:
        code = row["code"]
        if code not in codes:
            continue
        tag = bcp47(row["iso639_3"])
        if tag in ntumc_tags and transcribed[row["iso639_3"]]:
            continue
        language = languages.setdefault(tag, Language(tag, row["language"]))
        source = f"Parabank {row['language_id']}"
        bound = row["analect"] == "bound"
        host = (
            free.get((row["language_id"].removesuffix("_b"), code)) if bound else None
        )
        if host:  # a bound form with the free pronoun's cells is its variant
            entry = language.entry(host["lemma"], code)
            entry.forms.setdefault(row["lemma"], []).append(("morph", "bound"))
        else:
            entry = language.entry(row["lemma"], code, bound=bound)
        entry.transcribed |= transcribed[row["iso639_3"]]
        entry.senses[code].add(source)
        for variant in filter(None, row["variants"].split("; ")):
            case, form = variant.split(":", 1)
            tags = [("case", case)] + ([("morph", "bound")] if bound else [])
            entry.forms.setdefault(form, []).extend(tags)


def add_haspelmath(languages: dict[str, Language], codes: set[str]) -> None:
    """Add Haspelmath's indefinite series markers for the admitted series concepts.

    A marker (German *irgend-*) is not a whole word, so its entry is tagged
    ``morph=series``.
    """
    with (DATA / "haspelmath-series.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["code"] not in codes or not row["iso639_3"]:
                continue
            tag = bcp47(row["iso639_3"])
            language = languages.setdefault(tag, Language(tag, row["language"]))
            entry = language.entry(row["marker"], row["code"])
            if ("morph", "series") not in entry.tags:
                entry.tags.append(("morph", "series"))
            entry.senses[row["code"]].add(f"Haspelmath 1997 {row['construction']}")


def add_tufs(languages: dict[str, Language], codes: set[str]) -> None:
    """Add the curated TUFS pro-forms (data/tufs-curation.tsv).

    Each TUFS word was mapped by its own meaning, not by the Japanese headword it
    translates (French *vous* under あなた is 2;Pl and 2;Sg;Fml;Pol). Only rows of
    kind ``pronoun`` with at least medium confidence and a known concept are used;
    pronoun substitutes (Vietnamese kin terms used as "you") and rows proposing a
    NEW concept stay in the table for later.
    """
    iso = {}
    with (DATA / "tufs-pronouns.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            iso[row["tufs_lang"]] = row["iso639_3"]
    added = held = 0
    with (DATA / "tufs-curation.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            usable = (
                row["kind"] == "pronoun"
                and row["confidence"] in ("high", "medium")
                and row["code"] in codes
            )
            if not usable:
                held += 1
                continue
            tag = bcp47(iso[row["tufs_lang"]])
            language = languages.setdefault(
                tag, Language(tag, TUFS_NAMES.get(tag, tag))
            )
            entry = language.entry(row["form"], row["code"])
            entry.senses[row["code"]].add(f"TUFS {row['tufs_lang']} {row['tufs_wid']}")
            added += 1
    logger.info("TUFS: %d senses added, %d rows held back", added, held)


#: names for languages that only TUFS contributes
TUFS_NAMES = {
    "th": "Thai",
    "lo": "Lao",
    "km": "Khmer",
    "vi": "Vietnamese",
    "tl": "Tagalog",
    "ko": "Korean",
    "mn": "Mongolian",
    "khk": "Mongolian",
    "apc": "Syrian Arabic",
    "ur": "Urdu",
    "ar": "Arabic",
    "ms": "Malay",
    "zsm": "Malay",
    "tr": "Turkish",
}


def remap(languages: dict[str, Language]) -> None:
    """Apply data/remap.tsv: move a lemma's sense from one concept to another.

    Used where a source's analysis is wrong for a language: NTUMC splits English
    *you* into 2;Sg and 2;Pl, but it does not mark number, so it is ``2``.
    """
    with (DATA / "remap.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            language = languages.get(row["lang"])
            for entry in language.entries.values() if language else []:
                if entry.lemma == row["lemma"] and row["from_code"] in entry.senses:
                    sources = entry.senses.pop(row["from_code"])
                    entry.senses[row["to_code"]] |= sources


# --- writing -----------------------------------------------------------------


def attrs(pairs: list[tuple[str, str]]) -> str:
    """Render optional attributes, dropping empty ones."""
    return "".join(f" {name}={quoteattr(value)}" for name, value in pairs if value)


def lexicon_open(lexicon_id: str, label: str, tag: str) -> str:
    """The opening tag of a Lexicon."""
    return (
        f'  <Lexicon id="{lexicon_id}" label={quoteattr(label)} language="{tag}"'
        f' email="{EMAIL}" license="{LICENSE}" version="{VERSION}" url="{URL}"'
        f" citation={quoteattr(CITATION)}>"
    )


def written(
    element: str, form: str, transcribed: bool, tags: list, extra: str = ""
) -> list[str]:
    """A Lemma or Form element with script, transcription and tags."""
    script = script_of(form)
    head = f"<{element}{extra} writtenForm={quoteattr(form)}" + attrs(
        [("script", script)]
    )
    inner = []
    if transcribed:
        inner.append(
            f'<Pronunciation notation="source-transcription">{escape(form)}'
            "</Pronunciation>"
        )
    inner += [f'<Tag category="{c}">{escape(v)}</Tag>' for c, v in dict.fromkeys(tags)]
    if not inner:
        return [head + "/>"]
    return [head + ">", *(f"  {x}" for x in inner), f"</{element}>"]


def write_base(concepts: list[dict[str, str]], attested: set[str]) -> list[str]:
    """The shared concept lexicon, with the feature values as synsets too."""
    feature_table = read_features()
    codes = [c["code"] for c in concepts]
    parents = hypernyms(codes, {c["code"]: c["pos"] for c in concepts})
    children: dict[str, set[str]] = defaultdict(set)
    for code, above in parents.items():
        for parent in above:
            children[parent].add(code)
    linked = read_concept_ili()
    lines = [lexicon_open(BASE, "OMW pronoun concepts", "mul")]
    for c in concepts:
        eid = f"{BASE}-e-{slug(c['code'])}"
        lines += [
            f'    <LexicalEntry id="{eid}">',
            f'      <Lemma writtenForm={quoteattr(c["code"])} partOfSpeech="{c["pos"]}"/>',
            (
                f'      <Sense id="{eid}-1" synset="{BASE}-{slug(c["code"])}"'
                ' lexicalized="false"/>'
            ),
            "    </LexicalEntry>",
        ]
    # WN-LMF wants every entry before any synset
    feature_entries, feature_synsets = write_features(concepts, attested, feature_table)
    lines += feature_entries
    for c in concepts:
        code = c["code"]
        # an existing ILI where CILI has the concept, else a proposal
        ili = linked.get(code) or ("in" if code in attested else "")
        lines.append(
            f'    <Synset id="{BASE}-{slug(code)}" ili="{ili}" partOfSpeech="{c["pos"]}"'
            f' lexicalized="false" lexfile="{LEXFILES[c["pos"]]}"'
            + attrs(
                [
                    ("dc:identifier", f"pronoun:{code}"),
                    ("dc:description", c["label"]),
                    ("dc:source", c["source"]),
                ]
            )
            + ">"
        )
        lines.append(
            f'      <Definition language="en">{escape(c["definition"])}</Definition>'
        )
        if ili == "in":
            lines.append(
                f"      <ILIDefinition>{escape(c['definition'])}</ILIDefinition>"
            )
        for rel, targets in (("hypernym", parents[code]), ("hyponym", children[code])):
            for t in sorted(targets):
                lines.append(
                    f'      <SynsetRelation relType="{rel}" target="{BASE}-{slug(t)}"/>'
                )
        for rel, abbr in feature_links(code, feature_table, c["pos"]):
            lines.append(
                f'      <SynsetRelation relType="{rel}" target="{feature_id(abbr)}"/>'
            )
        for rel, other in possessive_links(code, set(codes)):
            lines.append(
                f'      <SynsetRelation relType="other" dc:type="{rel}"'
                f' target="{BASE}-{slug(other)}"/>'
            )
        lines.append("    </Synset>")
    lines += feature_synsets
    lines.append("  </Lexicon>")
    return lines


def possessive_links(code: str, codes: set[str]) -> list[tuple[str, str]]:
    """Link a possessive to its pronoun and back.

    WN-LMF has no synset relation for this, so it is ``other`` with a
    ``dc:type``: ``possessor`` from the possessive, ``possessive`` from the
    pronoun. Both possessives of *I* point to it: *my* (``1;Sg;Poss``) and
    *mine* (``Ent;1;Sg;Poss``).

    >>> possessive_links("Ent;1;Sg;Poss", {"1;Sg", "Ent;1;Sg;Poss"})
    [('possessor', '1;Sg')]
    """
    if "Poss" in code.split(";"):
        pronoun = possessor(code)
        return [("possessor", pronoun)] if pronoun in codes else []
    owned = sorted(c for c in codes if "Poss" in c.split(";") and possessor(c) == code)
    return [("possessive", c) for c in owned]


def possessor(code: str) -> str:
    """The personal pronoun a possessive belongs to, or '' (whose: ``Poss;Int``).

    >>> possessor("1;Sg;Poss"), possessor("Ent;1;Sg;Poss"), possessor("Poss;Int")
    ('1;Sg', '1;Sg', '')
    """
    parts = [p for p in code.split(";") if p not in ("Poss", "Ent")]
    return ";".join(parts) if parts and parts[0] in SLOTS["person"] else ""


def feature_id(abbr: str) -> str:
    """The synset id of a feature value: ``Du`` -> ``omw-pronoun-feature-Du``."""
    return f"{BASE}-feature-{slug(abbr)}"


def read_features() -> dict[str, dict[str, str]]:
    """The feature values, from data/features.tsv, by abbreviation."""
    with (DATA / "features.tsv").open(encoding="utf8") as handle:
        return {row["abbr"]: row for row in csv.DictReader(handle, delimiter="\t")}


#: the inverse of each concept-to-feature relation, for the feature synsets
INVERSE = {
    "hypernym": "hyponym",
    "attribute": "attribute",
    "exemplifies": "is_exemplified_by",
}


def feature_links(
    code: str, table: dict[str, dict[str, str]], pos: str = "n"
) -> list[tuple[str, str]]:
    """Relations from a concept to its feature synsets.

    The head of a pronoun is its hypernym, as in NTUMC (*who* is a kind of
    person). A determiner or pro-adverb is not a kind of the noun that heads it
    (*such* is not a kind of kind), so its head is linked by ``attribute``, as
    NTUMC links kind and manner. Every other feature is linked by
    ``exemplifies``, NTUMC's usage-domain link.

    >>> feature_links("Pers;Int;Pol", read_features())
    [('hypernym', 'Pers'), ('exemplifies', 'Int'), ('exemplifies', 'Pol')]
    >>> feature_links("Mnr;Prox", read_features(), "r")
    [('attribute', 'Mnr'), ('exemplifies', 'Prox')]
    """
    head = "hypernym" if pos == "n" else "attribute"
    links = []
    for slot, values in features(code).items():
        for value in sorted(values):
            if value in table:
                links.append((head if slot == "head" else "exemplifies", value))
    return links


def feature_hierarchy(abbr: str, used: list[str]) -> list[tuple[str, str]]:
    """Hypernymy among feature values, from the values they stand for.

    >>> feature_hierarchy("Dist", ["Prox", "Med", "Dist", "Rem"])
    [('hyponym', 'Med'), ('hyponym', 'Rem')]
    >>> feature_hierarchy("Rem", ["Prox", "Med", "Dist", "Rem"])
    [('hypernym', 'Dist')]
    """
    links = [("hypernym", v) for v in used if abbr in EXPAND.get(v, set())]
    return links + [("hyponym", v) for v in used if v in EXPAND.get(abbr, set())]


def write_features(
    concepts: list[dict[str, str]], attested: set[str], table: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    """Entries and synsets for the feature values the concepts use.

    A feature keeps its Princeton ILI (``status`` pwn); NTUMC's own features and
    new ones are proposed to CILI; features marked ``check`` point at a doubtful
    Princeton sense and get no ILI until it is resolved.
    """
    back: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for c in concepts:
        for rel, abbr in feature_links(c["code"], table, c["pos"]):
            inverse = INVERSE[rel]
            back[abbr].append((inverse, c["code"]))
    used = [a for a in table if a in back]
    entries: list[str] = []
    lines: list[str] = []
    for abbr in used:
        row = table[abbr]
        eid = f"{BASE}-e-feature-{slug(abbr)}"
        entries += [
            f'    <LexicalEntry id="{eid}">',
            (
                f"      <Lemma writtenForm={quoteattr(row['slot'] + ':' + abbr)}"
                ' partOfSpeech="n"/>'
            ),
            f'      <Sense id="{eid}-1" synset="{feature_id(abbr)}" lexicalized="false"/>',
            "    </LexicalEntry>",
        ]
    for abbr in used:
        row = table[abbr]
        proposed = row["status"] in ("ntumc", "new") and any(
            code in attested for _, code in back[abbr]
        )
        ili = row["ili"] if row["status"] == "pwn" else "in" if proposed else ""
        lines.append(
            f'    <Synset id="{feature_id(abbr)}" ili="{ili}" partOfSpeech="n"'
            ' lexicalized="false"'
            + attrs(
                [
                    ("dc:identifier", f"feature:{row['slot']}:{abbr}"),
                    ("dc:description", row["label"]),
                    ("dc:source", "NTUMC " + row["ntumc"] if row["ntumc"] else ""),
                    ("dc:relation", "UD:" + row["ud"] if row["ud"] else ""),
                    (
                        "note",
                        "check the Princeton sense" if row["status"] == "check" else "",
                    ),
                ]
            )
            + ">"
        )
        definition = escape(row["definition"])
        lines.append(f'      <Definition language="en">{definition}</Definition>')
        if ili == "in":
            lines.append(f"      <ILIDefinition>{definition}</ILIDefinition>")
        for rel, code in sorted(back[abbr]):
            lines.append(
                f'      <SynsetRelation relType="{rel}" target="{BASE}-{slug(code)}"/>'
            )
        for rel, other in feature_hierarchy(abbr, used):
            lines.append(
                f'      <SynsetRelation relType="{rel}" target="{feature_id(other)}"/>'
            )
        lines.append("    </Synset>")
    return entries, lines


def write_language(language: Language, definitions: dict[str, str]) -> list[str]:
    """One language's standalone lexicon of words."""
    lid = f"{BASE}-{language.tag}"
    linked = read_concept_ili()
    lines = [lexicon_open(lid, f"OMW pronouns: {language.name}", language.tag)]
    used = set()
    for index, entry in enumerate(
        sorted(language.entries.values(), key=lambda e: (e.lemma, e.tags)), 1
    ):
        eid = f"{lid}-e{index:04d}"
        lines.append(f'    <LexicalEntry id="{eid}">')
        lines += [
            "      " + x
            for x in written(
                "Lemma",
                entry.lemma,
                entry.transcribed,
                entry.tags,
                f' partOfSpeech="{entry.pos}"',
            )
        ]
        for form, tags in sorted(entry.forms.items()):
            if form != entry.lemma:
                lines += [
                    "      " + x for x in written("Form", form, entry.transcribed, tags)
                ]
        for code, sources in sorted(entry.senses.items()):
            used.add(code)
            lines.append(
                f'      <Sense id="{eid}-{slug(code)}" synset="{lid}-{slug(code)}"'
                + attrs([("dc:source", "; ".join(sorted(sources)))])
                + "/>"
            )
        lines.append("    </LexicalEntry>")
    for code in sorted(used):
        lines.append(
            f'    <Synset id="{lid}-{slug(code)}" ili="{linked.get(code, "")}"'
            f' partOfSpeech="{POS[code]}"'
            f' lexfile="{LEXFILES[POS[code]]}"'
            + attrs([("dc:identifier", f"pronoun:{code}")])
            + ">"
        )
        lines.append(
            f'      <Definition language="en">{escape(definitions[code])}</Definition>'
        )
        lines.append("    </Synset>")
    lines.append("  </Lexicon>")
    return lines


def write_package(collection: Path, lexicon_id: str, body: list[str]) -> None:
    """One WN-LMF package: a directory with a single XML file."""
    package = collection / lexicon_id
    package.mkdir(parents=True, exist_ok=True)
    document = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        DOCTYPE,
        f'<LexicalResource xmlns:dc="{DC_NAMESPACE}">',
        *body,
        "</LexicalResource>",
    ]
    (package / f"{lexicon_id}-{VERSION}.xml").write_text(
        "\n".join(document) + "\n", encoding="utf8"
    )


def read_concept_ili() -> dict[str, str]:
    """Concepts with an exact counterpart in CILI (data/concept-ili.tsv) -> its ILI.

    Only ``exact`` rows link; ``related`` rows record near misses, such as
    OEWN's *someone*, which is *person* "a human being", not the pronoun.
    """
    with (DATA / "concept-ili.tsv").open(encoding="utf8") as handle:
        return {
            row["concept"]: row["ili"]
            for row in csv.DictReader(handle, delimiter="\t")
            if row["relation"] == "exact"
        }


#: parts of speech, as the browser names them
POS_NAMES = {"n": "pronoun", "a": "determiner", "r": "pro-adverb"}


def write_browser_data(
    concepts: list[dict[str, str]], languages: dict[str, Language]
) -> None:
    """Write the data for the hierarchy browser as a script, `window.PRONOUNS`.

    A script rather than JSON, so the page also works opened from disk. Each
    concept lists its nearest hypernyms (`hypernyms`); each feature its slot and
    label; each language its checked words, by concept (`words`), and the words
    found only in an existing wordnet, which nobody has checked (`wordnet`).
    """
    codes = [c["code"] for c in concepts]
    parents = hypernyms(codes, POS)
    wordnets = unchecked_sources()
    words: dict[str, dict[str, list[str]]] = {}
    unchecked: dict[str, dict[str, list[str]]] = {}
    for tag, language in languages.items():
        checked: dict[str, list[str]] = defaultdict(list)
        others: dict[str, list[str]] = defaultdict(list)
        for entry in language.entries.values():
            for code, sources in entry.senses.items():
                ok = not all(is_unchecked(s, wordnets) for s in sources)
                target = checked if ok else others
                if entry.lemma not in target[code]:
                    target[code].append(entry.lemma)
        words[tag] = dict(checked)
        unchecked[tag] = dict(others)
    speakers: dict[str, int] = defaultdict(int)
    for by_code in words.values():
        for code in by_code:
            speakers[code] += 1
    order = {code: i for i, code in enumerate(codes)}
    data = {
        "version": VERSION,
        "pos": POS_NAMES,
        "features": {
            abbr: {
                "slot": row["slot"],
                "label": row["label"],
                "ud": row["ud"],
                "definition": row["definition"],
            }
            for abbr, row in read_features().items()
        },
        # what each unmarked value stands for: the browser groups concepts by
        # head, and Pers and Thng under Ent
        "expand": {value: sorted(values) for value, values in EXPAND.items()},
        "concepts": {
            c["code"]: {
                "label": c["label"],
                "definition": c["definition"],
                "pos": c["pos"],
                "source": c["source"],
                "languages": speakers[c["code"]],
                "parents": sorted(parents[c["code"]], key=order.__getitem__),
            }
            for c in concepts
        },
        "languages": [
            {
                "name": languages[tag].name,
                "tag": tag,
                "words": words[tag],
                "wordnet": unchecked[tag],
            }
            for tag in sorted(languages, key=lambda t: languages[t].name)
        ],
    }
    BROWSER.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (BROWSER / "data.js").write_text(f"window.PRONOUNS = {text};\n", encoding="utf8")


def main() -> None:
    """Build the collection and data/lexicons.tsv."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with (DATA / "concepts.tsv").open(encoding="utf8") as handle:
        concepts = list(csv.DictReader(handle, delimiter="\t"))
    codes = {c["code"] for c in concepts}
    POS.update({c["code"]: c["pos"] for c in concepts})
    languages: dict[str, Language] = {}
    add_ntumc(languages, codes)
    add_parabank(languages, codes)
    add_haspelmath(languages, codes)
    add_tufs(languages, codes)
    add_extra(languages, codes)
    add_wordnets(languages, codes)
    remap(languages)
    languages = {t: lang for t, lang in languages.items() if lang.entries}
    attested = {
        code
        for lang in languages.values()
        for e in lang.entries.values()
        for code in e.senses
    }

    collection = HERE / "release" / f"{BASE}-{VERSION}"
    shutil.rmtree(collection, ignore_errors=True)
    write_package(collection, BASE, write_base(concepts, attested))
    definitions = {c["code"]: c["definition"] for c in concepts}
    with (DATA / "lexicons.tsv").open("w", encoding="utf8") as out:
        out.write("lexicon\tlanguage\tentries\tsenses\tconcepts\n")
        for tag, language in sorted(languages.items()):
            write_package(
                collection, f"{BASE}-{tag}", write_language(language, definitions)
            )
            senses = sum(len(e.senses) for e in language.entries.values())
            used = {c for e in language.entries.values() for c in e.senses}
            out.write(
                f"{BASE}-{tag}\t{language.name}\t{len(language.entries)}"
                f"\t{senses}\t{len(used)}\n"
            )
    with tarfile.open(collection.parent / f"{collection.name}.tar.xz", "w:xz") as tar:
        tar.add(collection, arcname=collection.name)
    write_browser_data(concepts, languages)
    logger.info(
        "%d concepts (%d attested), %d languages",
        len(codes),
        len(attested),
        len(languages),
    )


if __name__ == "__main__":
    main()
