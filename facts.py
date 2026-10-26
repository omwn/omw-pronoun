#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["langcodes", "language_data", "unidecode"]
# ///
"""Compute every pronoun figure the paper cites, and write them to data/facts.json.

One command, one file, so that any number in the paper can be checked against the
data without counting by hand; the paper reads the figures through macros
(``\\fact{pro.concepts.total}``) generated from this file. Keys are stable,
short, snake_case and grouped by topic; every leaf is a number. Run it after
``uv run build.py``: the hierarchy, the attested concepts and the words from
existing wordnets come from the browser data (``docs/hierarchy/data.js``), the
rest from the tables in ``data/``. The one figure that needs a source clone, the
languages whose third-person gender is not trusted, is read from
``../parabank-pronouns`` and left out when it is missing.

Usage: uv run facts.py [--out data/facts.json] [--parabank ../parabank-pronouns]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

import build
import concepts
import parabank_words

DATA = build.DATA
BROWSER_DATA = build.BROWSER / "data.js"
#: NTUMC's own pronoun synsets, from Seah & Bond (2014). The synsets that
#: ``data/ntumc-extra.tsv`` checks by hand are the rest NTUMC tags as pronouns:
#: its later additions (8000xxxx) and Princeton synsets (*here*, *all*)
INVENTORY_PREFIX = "7700"


class Facts(TypedDict):
    """The figures, by topic, as written to data/facts.json."""

    concepts: dict[str, int]
    languages: int
    ili: dict[str, int]
    hierarchy: dict[str, int]
    features: dict[str, int]
    ntumc: dict[str, int]
    parabank: dict[str, int]
    tufs: dict[str, int]
    haspelmath: dict[str, int]
    direction: dict[str, int]
    time: dict[str, int]
    wordnet_words: dict[str, int]
    transcriptions: dict[str, int]


def generated(code: str) -> bool:
    """True for an adposition made from a noun or base code by concepts.py.

    ``Plc;Prox;Dir``, and ``Plc;Prox;Loc+Goal`` from data/word-direction.tsv:
    counts by source count the codes the sources give, not these.
    """
    known = {
        f"{r['code']};{r['direction']}" for r in rows_of(DATA / "word-direction.tsv")
    }
    return code.endswith(";" + concepts.DIRECTION) or code in known


def rows_of(path: Path) -> list[dict[str, str]]:
    """Read a TSV with a header row."""
    with path.open(encoding="utf8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def browser_data(path: Path = BROWSER_DATA) -> dict:
    """The hierarchy browser's data, a JSON object assigned to ``window.PRONOUNS``."""
    text = path.read_text(encoding="utf8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def attested(browser: dict) -> set[str]:
    """Concepts some language has a word for, checked or not.

    This is the set the build proposes to CILI (``ili="in"``) when a concept has
    no existing ILI.
    """
    return {
        code
        for language in browser["languages"]
        for part in ("words", "wordnet")
        for code in language[part]
    }


def parabank_admitted(lexemes: list[dict[str, str]]) -> set[str]:
    """Codes lexicalized in enough families and macroareas to be admitted."""
    families: dict[str, set[str]] = defaultdict(set)
    areas: dict[str, set[str]] = defaultdict(set)
    for row in lexemes:
        if row["code"]:
            families[row["code"]].add(row["family"] or row["glottocode"])
            areas[row["code"]].add(row["macroarea"])
    return {
        code
        for code in families
        if len(families[code]) >= concepts.MIN_FAMILIES
        and len(areas[code]) >= concepts.MIN_AREAS
    }


def concept_facts(inventory: list[dict[str, str]]) -> dict[str, int]:
    """The concepts, by part of speech, and those with the domain Two.

    ``noun_and_adposition`` counts the nouns that also have an adposition
    (*here*: ``Plc;Prox`` and ``Plc;Prox;Dir``); ``adposition_known`` the
    adpositions narrower than ``Dir`` that some word is known to cover
    (English *here*, ``Plc;Prox;Loc+Goal``).
    """
    by_pos = {pos: sum(1 for c in inventory if c["pos"] == pos) for pos in "narp"}
    codes_in = {c["code"]: c["pos"] for c in inventory}

    def codes(source: str) -> int:
        return sum(
            1 for c in inventory if c["source"] == source and not generated(c["code"])
        )

    return {
        "total": len(inventory),
        **by_pos,
        "noun_and_adposition": sum(
            1
            for code, pos in codes_in.items()
            if pos == "n" and codes_in.get(concepts.with_direction(code)) == "p"
        ),
        "adposition_known": len(
            {
                f"{r['code']};{r['direction']}"
                for r in rows_of(DATA / "word-direction.tsv")
            }
            & set(codes_in)
        ),
        "two": sum(1 for c in inventory if "Two" in c["code"].split(";")),
        "haspelmath": codes("Haspelmath"),
        "direction": codes("direction"),
        "time": codes("time deixis"),
    }


def ili_facts(inventory: list[dict[str, str]], used: set[str]) -> dict[str, int]:
    """Concepts linked to an existing ILI, and those proposed as new ones.

    A concept with no word in any language is neither: it stays in the hierarchy
    but is not proposed.
    """
    codes = {c["code"] for c in inventory}
    linked = set(build.read_concept_ili()) & codes
    proposed = (used & codes) - linked
    return {
        "linked": len(linked),
        "proposed": len(proposed),
        "unattested": len(codes - linked - proposed),
    }


def hierarchy_facts(browser: dict) -> dict[str, int]:
    """Concepts with more than one hypernym, and concepts with none."""
    parents = [c["parents"] for c in browser["concepts"].values()]
    return {
        "multiple_hypernyms": sum(1 for p in parents if len(p) > 1),
        "tops": sum(1 for p in parents if not p),
    }


def new_concepts(
    given: set[str], inventory: set[str], others: set[str], key: str
) -> dict[str, int]:
    """The concepts a source adds to NTUMC's inventory, alone and shared.

    The one rule for NTUMC's extras and for TUFS: a concept a source gives is
    new when no NTUMC inventory synset gives it; it is the source's ``only``
    when no other source gives it either (Parabank's admission rule, Haspelmath,
    NTUMC's extras, another curated concept), and ``shared`` otherwise. The
    figures are keyed ``key``, ``key_only`` and ``key_shared``.
    """
    new = given - inventory
    return {
        key: len(new),
        f"{key}_only": len(new - others),
        f"{key}_shared": len(new & others),
    }


def ntumc_facts(inventory: list[dict[str, str]], others: set[str]) -> dict[str, int]:
    """NTUMC's pronoun synsets, and the synsets outside them it tags as pronouns.

    The concepts the hand-checked extras add are counted by ``new_concepts``;
    ``others`` is what the other sources give.
    """
    synsets = [s for c in inventory for s in c["ntumc"].split()]
    from_inventory = {
        concepts.without_direction(c["code"]) if generated(c["code"]) else c["code"]
        for c in inventory
        if any(s.startswith(INVENTORY_PREFIX) for s in c["ntumc"].split())
    }
    extra = rows_of(DATA / "ntumc-extra.tsv")
    kept = [r for r in extra if r["code"]]
    new = new_concepts({r["code"] for r in kept}, from_inventory, others, "extra_new")
    return {
        "synsets": len({s for s in synsets if s.startswith(INVENTORY_PREFIX)}),
        "inventory_concepts": len(from_inventory),
        "extra_synsets": len(extra),
        "extra_kept": len(kept),
        "extra_skipped": len(extra) - len(kept),
        **new,
    }


def gender_untrusted(source: Path) -> int | None:
    """Languages whose gender-split third-person forms are left unmapped.

    None when the Parabank clone is not there to read.
    """
    if not (source / "cldf" / "forms.csv").exists():
        return None
    _, paradigms = parabank_words.read(source)
    return len(
        {
            language
            for (language, _), cells in paradigms.items()
            if parabank_words.gender_uncertain(cells)
        }
    )


def parabank_facts(
    lexemes: list[dict[str, str]],
    admitted: set[str],
    from_inventory: set[str],
    codes: set[str],
    source: Path,
) -> dict[str, int]:
    """Parabank's varieties, the concepts it adds, and its bound forms.

    A bound form is counted as the build counts it: a lexeme of a concept in the
    inventory, in a language the build does not skip, which is a variant when
    the free paradigm has a lexeme with the same cells. A variant spelled like
    the free pronoun adds no form to its entry; ``bound_variant_forms`` counts
    the distinct forms the others add (language, concept, form).
    """
    added = admitted - from_inventory
    with_iso = [r for r in lexemes if r["iso639_3"]]
    ipa = build.ipa_languages(with_iso)
    free = {
        (r["language_id"], r["code"]): r["lemma"]
        for r in with_iso
        if r["analect"] == "free"
    }
    bound = [
        r
        for r in with_iso
        if r["analect"] == "bound"
        and r["code"] in codes
        and not build.skipped_parabank(r, ipa)
    ]
    # (bound lexeme, the free pronoun's lemma) for each variant
    variants = [
        (r, free[host])
        for r in bound
        if (host := (r["language_id"].removesuffix("_b"), r["code"])) in free
    ]
    differ = [r for r, lemma in variants if r["lemma"] != lemma]
    facts = {
        "varieties": len({r["language_id"] for r in lexemes}),
        "admitted": len(added),
        "admitted_possessive": sum(1 for c in added if "Poss" in c.split(";")),
        "bound": len(bound),
        "bound_variants": len(variants),
        "bound_variants_same_spelling": len(variants) - len(differ),
        "bound_variants_spelled_differently": len(differ),
        "bound_variant_forms": len(
            {
                (r["language_id"].removesuffix("_b"), r["code"], r["lemma"])
                for r in differ
            }
        ),
    }
    untrusted = gender_untrusted(source)
    if untrusted is not None:
        facts["gender_untrusted"] = untrusted
    return facts


def tufs_facts(
    codes: set[str],
    from_inventory: set[str],
    extra_concepts: list[dict[str, str]],
    others: set[str],
) -> dict[str, int]:
    """The TUFS forms, their curation, and what it adds.

    A curated row maps one TUFS form to one concept. It is used when it is a
    pronoun, of at least medium confidence, for a concept in the inventory (as
    ``build.add_tufs`` decides); the rest are held back (``held_back_rows``).
    ``held_back_forms`` counts the distinct (language, form) pairs of those rows,
    and ``held_back_forms_unused`` those of them no used row adds. The new
    concepts are the curated concepts sourced from TUFS, counted by
    ``new_concepts``; ``others`` is what the other sources give. Japanese pronouns missing from NTUMC are the curated
    Japanese lemmas that are not NTUMC spellings, leaving out *ima* "now", which
    is counted with time.
    """
    forms = rows_of(DATA / "tufs-pronouns.tsv")
    curation = rows_of(DATA / "tufs-curation.tsv")
    used = [
        r
        for r in curation
        if r["kind"] == "pronoun"
        and r["confidence"] in ("high", "medium")
        and r["code"] in codes
    ]
    held = [r for r in curation if r not in used]
    held_forms = {(r["tufs_lang"], r["form"]) for r in held}
    lemmas = rows_of(DATA / "extra-lemmas.tsv")
    new = new_concepts(
        {r["code"] for r in extra_concepts if r["source"].startswith("TUFS")},
        from_inventory,
        others,
        "new_concepts",
    )
    return {
        "languages": len({r["tufs_lang"] for r in forms} - {"ja"}),
        "forms": len(forms),
        "curated": len(curation),
        "senses": len(used),
        "held_back_rows": len(held),
        "held_back_forms": len(held_forms),
        "held_back_forms_unused": len(
            held_forms - {(r["tufs_lang"], r["form"]) for r in used}
        ),
        **new,
        "there_forms": sum(1 for r in used if r["code"] == "Plc;Dist"),
        "japanese_not_in_ntumc": sum(
            1
            for r in lemmas
            if r["lang"] == "jpn"
            and r["source"] == "TUFS"
            and r["code"] != "Tim;Prox"
            and "NTUMC" not in r["note"]
        ),
    }


def time_facts(lemmas: list[dict[str, str]]) -> dict[str, int]:
    """Languages with a word for *now* and *then*, from TUFS or curated."""

    def languages(code: str, source: str) -> int:
        return len(
            {r["lang"] for r in lemmas if r["code"] == code and r["source"] == source}
        )

    return {
        "now_tufs_languages": languages("Tim;Prox", "TUFS"),
        "now_curated_languages": languages("Tim;Prox", "curated"),
        "then_curated_languages": languages("Tim;Dist", "curated"),
    }


def feature_facts(inventory: list[dict[str, str]], used: set[str]) -> dict[str, int]:
    """The feature values in use, by how they reach the ILI, and their UD mapping.

    As ``build.write_features`` decides: a Princeton value keeps its ILI, an NTUMC
    or new value used by an attested concept is proposed, and a value pointing
    at a doubtful Princeton sense (``check``) is flagged. ``unused`` are values
    ``data/features.tsv`` defines that no concept has (trial ``Tr``); Haspelmath's
    functions are counted as defined and as used.
    """
    table = build.read_features()
    users: dict[str, set[str]] = defaultdict(set)
    for c in inventory:
        for _, abbr in build.feature_links(c["code"], table, c["pos"]):
            users[abbr].add(c["code"])
    rows = [table[a] for a in table if a in users]
    return {
        "used": len(rows),
        "ili": sum(1 for r in rows if r["status"] == "pwn"),
        "proposed": sum(
            1
            for r in rows
            if r["status"] in ("ntumc", "new") and users[r["abbr"]] & used
        ),
        "flagged": sum(1 for r in rows if r["status"] == "check"),
        "ud": sum(1 for r in rows if r["ud"]),
        "unused": len(table) - len(rows),
        "haspelmath_functions": len(concepts.FUNCTIONS),
        "haspelmath_functions_used": len(concepts.FUNCTIONS & set(users)),
    }


def wordnet_word_facts(browser: dict) -> dict[str, int]:
    """Words that only existing wordnets give, through the ILI, and their languages."""
    unchecked = {
        language["tag"]: sum(len(words) for words in language["wordnet"].values())
        for language in browser["languages"]
    }
    return {
        "words": sum(unchecked.values()),
        "languages": sum(1 for n in unchecked.values() if n),
    }


def transcription_facts(collection: Path | None = None) -> dict[str, int]:
    """Parabank transcriptions: attached to a spelled word, or left as lemmas.

    Read from the built collection: a lemma whose pronunciation differs from its
    spelling has a transcription attached (Swedish *jag*, pronounced *jɑːg*); a
    lemma pronounced as it is written is a transcription with no spelling found.
    """
    collection = collection or build.HERE / "release" / f"{build.BASE}-{build.VERSION}"
    lemma = re.compile(
        r'<Lemma [^>]*writtenForm="([^"]*)"[^>]*>(.*?)</Lemma>', re.DOTALL
    )
    sound = re.compile(r"<Pronunciation [^>]*>([^<]*)</Pronunciation>")
    attached = transcribed = wikidata = 0
    languages = set()
    for path in sorted(collection.glob(f"{build.BASE}-*/*.xml")):
        text = path.read_text(encoding="utf8")
        for written, inner in lemma.findall(text):
            sounds = sound.findall(inner)
            transcribed += written in sounds
            others = sum(1 for x in sounds if x != written)
            attached += others
            if others:
                languages.add(path.parent.name)
        wikidata += len(re.findall(r'dc:source="[^"]*Wikidata L', text))
    return {
        "pronunciations": attached,
        "pronunciation_languages": len(languages),
        "lemmas": transcribed,
        "wikidata_senses": wikidata,
    }


def compute(parabank_source: Path = parabank_words.DEFAULT) -> Facts:
    """Every figure, by topic.

    ``parabank.gender_untrusted`` is read from the Parabank clone at
    ``parabank_source``, and is left out when the clone is missing.
    """
    inventory = rows_of(DATA / "concepts.tsv")
    # build.py also accepts the bare code of an adposition, which it moves
    codes = {c["code"] for c in inventory} | {
        concepts.without_direction(c["code"]) for c in inventory if c["pos"] == "p"
    }
    browser = browser_data()
    used = attested(browser)
    lexemes = rows_of(DATA / "parabank-lexemes.tsv")
    admitted = parabank_admitted(lexemes)
    extra_concepts = rows_of(DATA / "extra-concepts.tsv")
    extra_lemmas = rows_of(DATA / "extra-lemmas.tsv")
    from_inventory = {
        concepts.without_direction(c["code"]) if generated(c["code"]) else c["code"]
        for c in inventory
        if any(s.startswith(INVENTORY_PREFIX) for s in c["ntumc"].split())
    }
    series = rows_of(DATA / "haspelmath-series.tsv")
    ntumc_extra = {r["code"] for r in rows_of(DATA / "ntumc-extra.tsv") if r["code"]}
    from_tufs = {r["code"] for r in extra_concepts if r["source"].startswith("TUFS")}
    curated = {r["code"] for r in extra_concepts if not r["source"].startswith("TUFS")}
    from_haspelmath = concepts.haspelmath_concepts()
    return {
        "concepts": concept_facts(inventory),
        "languages": len(rows_of(DATA / "lexicons.tsv")),
        "ili": ili_facts(inventory, used),
        "hierarchy": hierarchy_facts(browser),
        "features": feature_facts(inventory, used),
        "ntumc": ntumc_facts(
            inventory, admitted | from_haspelmath | from_tufs | curated
        ),
        "parabank": parabank_facts(
            lexemes, admitted, from_inventory, codes, parabank_source
        ),
        "tufs": tufs_facts(
            codes,
            from_inventory,
            extra_concepts,
            admitted | from_haspelmath | ntumc_extra | curated,
        ),
        "haspelmath": {"languages": len({r["glottocode"] for r in series})},
        "transcriptions": transcription_facts(),
        "direction": {
            "languages": len(
                {r["lang"] for r in extra_lemmas if r["note"] == "direction"}
            )
        },
        "time": time_facts(extra_lemmas),
        "wordnet_words": wordnet_word_facts(browser),
    }


def main() -> None:
    """Write data/facts.json."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DATA / "facts.json")
    parser.add_argument(
        "--parabank",
        type=Path,
        default=parabank_words.DEFAULT,
        help="the Parabank Pronoun clone, for the gender figure",
    )
    args = parser.parse_args()
    facts = compute(args.parabank)
    args.out.write_text(
        json.dumps(facts, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf8",
    )
    if "gender_untrusted" not in facts["parabank"]:
        print(f"{args.parabank}: not found, gender figure left out", file=sys.stderr)
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
