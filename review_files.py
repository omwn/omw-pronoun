#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
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

from build import subsumes

HERE = Path(__file__).resolve().parent
NAMES = {
    "en": "English",
    "zh": "Mandarin Chinese",
    "ja": "Japanese",
    "id": "Indonesian",
}


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
) -> Path:
    """Write review/tufs-<lang>.toml and return its path."""
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_code[row["code"] or "(none)"].append(row)
    lines = [
        f"# TUFS pro-forms for {NAMES.get(lang, lang)}, as curated for the OMW pronoun wordnet.",
        "# One table per concept. Edit `comment`; leave the rest as generated.",
        "# status: built = in the wordnet; held = kept out (substitute, not-proform, low confidence)",
        "",
    ]
    for code in sorted(by_code, key=lambda c: (c == "(none)", c)):
        group = by_code[code]
        concept = concepts.get(code, {})
        lines.append(f"[{toml_string(code)}]")
        # one TUFS word can appear under several headings (谁 under だれ, だれか and
        # どなた): list each lemma once, with all its headings
        headings: dict[str, dict[str, None]] = defaultdict(dict)
        for r in group:
            headings[r["form"]][f"{r['heading']} ({r['confidence']})"] = None
        lines.append(f"lemmas = [{', '.join(toml_string(f) for f in headings)}]")
        if lang != "en":
            lines += english_lines(code, english)
        lines.append(f"label = {toml_string(concept.get('label', ''))}")
        lines.append(f"definition = {toml_string(concept.get('definition', ''))}")
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
    path = HERE / "review" / f"tufs-{lang}.toml"
    path.write_text("\n".join(lines), encoding="utf8")
    return path


def write_lexicon(
    tag: str, concepts: dict[str, dict], english: dict[str, list[str]]
) -> Path:
    """Write review/<tag>.toml from a built language lexicon, for languages TUFS lacks.

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
    lines = [
        f"# Pronouns for {name}, from the built OMW pronoun lexicon {lexicon}.",
        "# One table per concept. Edit `comment`; leave the rest as generated.",
        "",
    ]
    for code in sorted(by_code):
        concept = concepts.get(code, {})
        lemmas = by_code[code]
        lines.append(f"[{toml_string(code)}]")
        lines.append(f"lemmas = [{', '.join(toml_string(w) for w in lemmas)}]")
        lines += english_lines(code, english)
        lines.append(f"label = {toml_string(concept.get('label', ''))}")
        lines.append(f"definition = {toml_string(concept.get('definition', ''))}")
        forms = [f"{w}: {'; '.join(fs)}" for w, (fs, _) in lemmas.items() if fs]
        if forms:
            lines.append(f"forms = [{', '.join(toml_string(f) for f in forms)}]")
        sources = [f"{w} <- {', '.join(sorted(src))}" for w, (_, src) in lemmas.items()]
        lines.append(f"sources = [{', '.join(toml_string(s) for s in sources)}]")
        lines.append('comment = ""')
        lines.append("")
    out = HERE / "review" / f"{tag}.toml"
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
            path = write_lexicon(tag, concepts, english_lemmas())
            print(path.relative_to(HERE), file=sys.stderr)
        return
    langs = sys.argv[1:] or ["en", "zh", "ja", "id"]
    with (HERE / "data" / "concepts.tsv").open(encoding="utf8") as handle:
        concepts = {row["code"]: row for row in csv.DictReader(handle, delimiter="\t")}
    with (HERE / "data" / "tufs-curation.tsv").open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    (HERE / "review").mkdir(exist_ok=True)
    english = english_lemmas()
    for lang in langs:
        rows_for = [r for r in rows if r["tufs_lang"] == lang]
        path = write(lang, rows_for, concepts, english)
        print(path.relative_to(HERE), file=sys.stderr)


if __name__ == "__main__":
    main()
