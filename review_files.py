#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["langcodes", "language_data"]  # via build.py
# ///
"""Write the curated TUFS pro-forms of some languages as TOML for human review.

One file per language in ``review/``, one table per concept, with the lemmas,
the concept's English lemmas (from the built English lexicon, so run build.py
first), its label and definition, what TUFS listed them under, and the status
(built, or held back and why). Each table ends with an empty ``comment`` for
the reviewer.

Usage: uv run review_files.py [tufs_lang ...]   (default: en zh ja id)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

from build import (
    NTUMC_LANGUAGES,
    feature_links,
    hypernyms,
    ntumc_lemmas,
    read_features,
    subsumes,
)

HERE = Path(__file__).resolve().parent
#: header lines explaining the hierarchy fields
HIERARCHY_NOTE = (
    "# hypernyms: direct hypernyms in the shared (mul) hierarchy; ancestors: all of"
    " them, nearest first.\n# Nodes with no word here are included where the"
    " hierarchy needs them (status `unlexicalized`)."
)
NAMES = {
    "en": "English",
    "zh": "Mandarin Chinese",
    "ja": "Japanese",
    "id": "Indonesian",
}


#: TUFS language code -> NTUMC language column
TUFS_NTUMC = {"en": "eng", "zh": "cmn", "ja": "jpn", "id": "ind"}
#: lexicon tag -> NTUMC language column (``cs`` -> ``ces``)
TAG_NTUMC = {tag: column for column, (tag, _) in NTUMC_LANGUAGES.items()}


def ntumc_for(column: str | None, codes: set[str]) -> dict[str, list[str]]:
    """Concept code -> NTUMC lemmas of one language, as ``"lemma <- synset"``."""
    found: dict[str, list[str]] = defaultdict(list)
    if column:
        for code, col, lemma, synset in ntumc_lemmas(codes):
            if col == column:
                found[code].append(f"{lemma} <- {synset}")
    return {code: list(dict.fromkeys(items)) for code, items in found.items()}


def ntumc_line(code: str, ntumc: dict[str, list[str]]) -> list[str]:
    """The ``ntumc`` line of a concept table, if NTUMC has lemmas for it."""
    if code not in ntumc:
        return []
    return [f"ntumc = [{', '.join(toml_string(x) for x in ntumc[code])}]"]


def ntumc_definitions(concepts: dict[str, dict]) -> dict[str, list[str]]:
    """Concept code -> the definitions of its NTUMC synsets, as ``"synset: text"``.

    A concept folded from several synsets (*my* and *mine*) lists each one.
    """
    with (HERE / "data" / "ntumc-pronouns.tsv").open(encoding="utf8") as handle:
        text = {
            row["synset"]: row["definition"]
            for row in csv.DictReader(handle, delimiter="\t")
        }
    return {
        code: [f"{s}: {text[s]}" for s in row["ntumc"].split() if text.get(s)]
        for code, row in concepts.items()
        if row.get("ntumc")
    }


def definition_lines(concept: dict, ntumc_defs: list[str]) -> list[str]:
    """The generated definition, then NTUMC's own definitions if it has any."""
    lines = [f"definition = {toml_string(concept.get('definition', ''))}"]
    if ntumc_defs:
        lines.append(
            f"ntumc_definitions = [{', '.join(toml_string(d) for d in ntumc_defs)}]"
        )
    return lines


def hierarchy(concepts: dict[str, dict]) -> dict[str, set[str]]:
    """Code -> its direct hypernyms in the shared (mul) lexicon.

    As in the build, these are the closest broader concepts of the same part of
    speech, plus the head's feature synset (*who* is a kind of person), written
    ``feature:Pers``.
    """
    pos = {code: row["pos"] for code, row in concepts.items()}
    parents = hypernyms(list(concepts), pos)
    table = read_features()
    for code in concepts:
        parents[code] |= {
            f"feature:{abbr}"
            for rel, abbr in feature_links(code, table)
            if rel == "hypernym"
        }
    return parents


def ancestors(code: str, parents: dict[str, set[str]]) -> list[str]:
    """Every node above `code` in the shared hierarchy, nearest first.

    A concept can have several hypernyms (``1e;Du`` is under ``1;Du`` and
    ``1e;Pl``), so this is the union of all the chains up to the roots.
    """
    found: list[str] = []
    layer = sorted(parents.get(code, ()))
    while layer:
        layer = [c for c in dict.fromkeys(layer) if c not in found]
        found += layer
        layer = sorted({p for c in layer for p in parents.get(c, ())})
    return found


def hierarchy_lines(code: str, parents: dict[str, set[str]]) -> list[str]:
    """The ``hypernyms`` (direct) and ``ancestors`` (all, nearest first) lines."""
    direct = sorted(parents.get(code, ()))
    return [
        f"hypernyms = [{', '.join(toml_string(c) for c in direct)}]",
        f"ancestors = [{', '.join(toml_string(c) for c in ancestors(code, parents))}]",
    ]


def hierarchy_only(codes: set[str], parents: dict[str, set[str]]) -> set[str]:
    """The ancestors of `codes` that have no table of their own yet."""
    return {a for c in codes for a in ancestors(c, parents)} - codes


def unlexicalized_table(code: str, lang: str, context: dict) -> list[str]:
    """A table for a node the hierarchy needs but the language has no word for.

    `context` holds ``concepts``, ``english``, ``defs`` and ``parents``.
    """
    lines = [f"[{toml_string(code)}]", "lemmas = []"]
    if code.startswith("feature:"):
        row = read_features()[code.removeprefix("feature:")]
        lines.append(
            'status = "unlexicalized: feature synset, no words in any language"'
        )
        lines.append(f"label = {toml_string(row['label'])}")
        lines.append(f"definition = {toml_string(row['definition'])}")
    else:
        concept = context["concepts"][code]
        lines.append(
            f'status = "unlexicalized: no {lang} word; included for the hierarchy"'
        )
        if lang != "en":
            lines += english_lines(code, context["english"])
        lines.append(f"label = {toml_string(concept['label'])}")
        lines += definition_lines(concept, context["defs"].get(code, []))
    lines += hierarchy_lines(code, context["parents"])
    return lines + ['comment = ""', ""]


def status(row: dict[str, str], codes: set[str]) -> str:
    """Whether the build uses a curated row, and if not, why not."""
    if row["kind"] != "pronoun":
        return f"held: {row['kind']}"
    if row["confidence"] == "low":
        return "held: low confidence"
    if row["code"] not in codes:
        return "held: no such concept"
    return "built"


def toml_string(value: str) -> str:
    """A TOML basic string (JSON escaping is valid TOML for these strings)."""
    return json.dumps(value, ensure_ascii=False)


def english_lemmas() -> dict[str, list[str]]:
    """Concept code -> English lemmas, from the built English lexicon."""
    path = (
        HERE
        / "release"
        / "omw-pronoun-0.1"
        / "omw-pronoun-en"
        / "omw-pronoun-en-0.1.xml"
    )
    root = ElementTree.parse(path).getroot()
    dc = "{https://globalwordnet.github.io/schemas/dc/}identifier"
    code_of = {
        s.get("id"): s.get(dc).removeprefix("pronoun:") for s in root.iter("Synset")
    }
    found: dict[str, list[str]] = defaultdict(list)
    for entry in root.iter("LexicalEntry"):
        lemma = entry.find("Lemma").get("writtenForm")
        for sense in entry.iter("Sense"):
            if sense.get("lexicalized") != "false":
                found[code_of[sense.get("synset")]].append(lemma)
    return {code: list(dict.fromkeys(lemmas)) for code, lemmas in found.items()}


def english_lines(code: str, english: dict[str, list[str]]) -> list[str]:
    """The English lemmas of a concept, or of its closest broader concept.

    English *you* is number-neutral (``2``), so Czech *ty* (``2;Sg``) shows it with
    ``english_via = "2"``.
    """
    if english.get(code):
        return [f"english = [{', '.join(toml_string(w) for w in english[code])}]"]
    broader = [c for c in english if c != code and subsumes(c, code)]
    closest = [
        c for c in broader if not any(subsumes(c, d) and c != d for d in broader)
    ]
    if not closest:
        return []
    via = min(closest)
    return [
        f"english = [{', '.join(toml_string(w) for w in english[via])}]",
        f"english_via = {toml_string(via)}",
    ]


def write(
    lang: str,
    rows: list[dict[str, str]],
    concepts: dict[str, dict],
    english: dict[str, list[str]],
    parents: dict[str, set[str]],
) -> Path:
    """Write review/pronoun-<lang>.toml and return its path.

    Concepts with NTUMC lemmas for the language list them as ``ntumc``; those
    TUFS lacks get a table of their own (status ``built (NTUMC only)``). Every
    node above them in the shared hierarchy that has no table gets one, marked
    unlexicalized.
    """
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_code[row["code"] or "(none)"].append(row)
    ntumc = ntumc_for(TUFS_NTUMC.get(lang), set(concepts))
    defs = ntumc_definitions(concepts)
    for code in ntumc:
        by_code.setdefault(code, [])
    extra = hierarchy_only(set(by_code) - {"(none)"}, parents)
    context = {
        "concepts": concepts,
        "english": english,
        "defs": defs,
        "parents": parents,
    }
    lines = [
        f"# TUFS pro-forms for {NAMES.get(lang, lang)}, as curated for the OMW pronoun wordnet.",
        "# One table per concept. Edit `comment`; leave the rest as generated.",
        "# status: built = in the wordnet; held = kept out (substitute, not-proform, low confidence)",
        "# ntumc: the concept's lemmas in the NTUMC wordnet, with their synsets",
        "# definition: generated from the code; ntumc_definitions: NTUMC's own",
        HIERARCHY_NOTE,
        "",
    ]
    for code in sorted(set(by_code) | extra, key=lambda c: (c == "(none)", c)):
        if code in extra:
            lines += unlexicalized_table(code, lang, context)
            continue
        group = by_code[code]
        concept = concepts.get(code, {})
        lines.append(f"[{toml_string(code)}]")
        if not group:  # NTUMC only
            lines += ntumc_line(code, ntumc)
            if lang != "en":
                lines += english_lines(code, english)
            lines.append(f"label = {toml_string(concept.get('label', ''))}")
            lines += definition_lines(concept, defs.get(code, []))
            lines += hierarchy_lines(code, parents)
            lines.append('status = "built (NTUMC only)"')
            lines.append('comment = ""')
            lines.append("")
            continue
        # one TUFS word can appear under several headings (谁 under だれ, だれか and
        # どなた): list each lemma once, with all its headings
        headings: dict[str, dict[str, None]] = defaultdict(dict)
        for r in group:
            headings[r["form"]][f"{r['heading']} ({r['confidence']})"] = None
        lines.append(f"lemmas = [{', '.join(toml_string(f) for f in headings)}]")
        lines += ntumc_line(code, ntumc)
        if lang != "en":
            lines += english_lines(code, english)
        lines.append(f"label = {toml_string(concept.get('label', ''))}")
        lines += definition_lines(concept, defs.get(code, []))
        if code != "(none)":
            lines += hierarchy_lines(code, parents)
        lines.append(
            "tufs = ["
            + ", ".join(
                toml_string(f"{form} <- {', '.join(hs)}")
                for form, hs in headings.items()
            )
            + "]"
        )
        notes = list(dict.fromkeys(r["note"] for r in group if r["note"]))
        if notes:
            lines.append(
                f"curator_notes = [{', '.join(toml_string(n) for n in notes)}]"
            )
        lines.append(
            f"status = {toml_string('; '.join(sorted({status(r, set(concepts)) for r in group})))}"
        )
        lines.append('comment = ""')
        lines.append("")
    path = HERE / "review" / f"pronoun-{lang}.toml"
    path.write_text("\n".join(lines), encoding="utf8")
    return path


def write_lexicon(
    tag: str,
    concepts: dict[str, dict],
    english: dict[str, list[str]],
    parents: dict[str, set[str]],
) -> Path:
    """Write review/pronoun-<tag>.toml from a built language lexicon, for languages TUFS lacks.

    Each concept lists its lemmas, their case and bound forms, and where each
    lemma comes from (NTUMC, Parabank, ...).
    """
    lexicon = f"omw-pronoun-{tag}"
    path = HERE / "release" / "omw-pronoun-0.1" / lexicon / f"{lexicon}-0.1.xml"
    root = ElementTree.parse(path).getroot()
    dc = "{https://globalwordnet.github.io/schemas/dc/}"
    code_of = {
        s.get("id"): s.get(dc + "identifier").removeprefix("pronoun:")
        for s in root.iter("Synset")
    }
    by_code: dict[str, dict[str, tuple[list[str], set[str]]]] = defaultdict(dict)
    for entry in root.iter("LexicalEntry"):
        lemma = entry.find("Lemma").get("writtenForm")
        forms = [
            f"{f.get('writtenForm')} ({', '.join(t.text for t in f.iter('Tag'))})"
            for f in entry.iter("Form")
        ]
        for sense in entry.iter("Sense"):
            sources = {
                s.split()[0] for s in (sense.get(dc + "source") or "").split("; ") if s
            }
            by_code[code_of[sense.get("synset")]][lemma] = (forms, sources)
    name = root.find("Lexicon").get("label").removeprefix("OMW pronouns: ")
    ntumc = ntumc_for(TAG_NTUMC.get(tag), set(concepts))
    defs = ntumc_definitions(concepts)
    lines = [
        f"# Pronouns for {name}, from the built OMW pronoun lexicon {lexicon}.",
        "# One table per concept. Edit `comment`; leave the rest as generated.",
        "# definition: generated from the code; ntumc_definitions: NTUMC's own",
        HIERARCHY_NOTE,
        "",
    ]
    extra = hierarchy_only(set(by_code), parents)
    context = {
        "concepts": concepts,
        "english": english,
        "defs": defs,
        "parents": parents,
    }
    for code in sorted(set(by_code) | extra):
        if code in extra:
            lines += unlexicalized_table(code, tag, context)
            continue
        concept = concepts.get(code, {})
        lemmas = by_code[code]
        lines.append(f"[{toml_string(code)}]")
        lines.append(f"lemmas = [{', '.join(toml_string(w) for w in lemmas)}]")
        lines += ntumc_line(code, ntumc)
        lines += english_lines(code, english)
        lines.append(f"label = {toml_string(concept.get('label', ''))}")
        lines += definition_lines(concept, defs.get(code, []))
        lines += hierarchy_lines(code, parents)
        forms = [f"{w}: {'; '.join(fs)}" for w, (fs, _) in lemmas.items() if fs]
        if forms:
            lines.append(f"forms = [{', '.join(toml_string(f) for f in forms)}]")
        sources = [f"{w} <- {', '.join(sorted(src))}" for w, (_, src) in lemmas.items()]
        lines.append(f"sources = [{', '.join(toml_string(s) for s in sources)}]")
        lines.append('comment = ""')
        lines.append("")
    out = HERE / "review" / f"pronoun-{tag}.toml"
    out.write_text("\n".join(lines), encoding="utf8")
    return out


def main() -> None:
    """Write the review files.

    Arguments are TUFS language codes (default: en zh ja id); ``--lexicon TAG``
    instead writes a review of a built lexicon, for languages TUFS lacks.
    """
    if sys.argv[1:2] == ["--lexicon"]:
        with (HERE / "data" / "concepts.tsv").open(encoding="utf8") as handle:
            concepts = {
                row["code"]: row for row in csv.DictReader(handle, delimiter="\t")
            }
        for tag in sys.argv[2:]:
            path = write_lexicon(tag, concepts, english_lemmas(), hierarchy(concepts))
            print(path.relative_to(HERE), file=sys.stderr)
        return
    langs = sys.argv[1:] or ["en", "zh", "ja", "id"]
    with (HERE / "data" / "concepts.tsv").open(encoding="utf8") as handle:
        concepts = {row["code"]: row for row in csv.DictReader(handle, delimiter="\t")}
    with (HERE / "data" / "tufs-curation.tsv").open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    (HERE / "review").mkdir(exist_ok=True)
    english = english_lemmas()
    parents = hierarchy(concepts)
    for lang in langs:
        rows_for = [r for r in rows if r["tufs_lang"] == lang]
        path = write(lang, rows_for, concepts, english, parents)
        print(path.relative_to(HERE), file=sys.stderr)


if __name__ == "__main__":
    main()
