#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Extract the NTUMC pronoun inventory as a table of feature bundles.

NTUMC's pronoun synsets (ids ``770xxxxx``) come from the componential analysis of
Seah & Bond (2014), "Annotation of Pronouns in a Multilingual Corpus of Mandarin
Chinese, English and Japanese" (ISA-10). Each is a bundle of features:

    head        person, thing, entity, place, time, manner, reason, quantifier
    person      1, 2, 3 (1 split into inclusive/exclusive)
    number      singular, dual, plural
    gender      masculine, feminine, neuter
    case        subjective, objective, possessive
    type        assertive, elective, negative, universal, interrogative,
                reflexive, reciprocal, other
    formality   formal, informal
    politeness  polite (NTUMC adds honorific, non-honorific)
    proximity   proximal, medial, distal (NTUMC adds remote)

In the wordnet the head is the synset's hypernym and most other features are
``dmnu`` (domain of usage) links to feature synsets; the rest are only in the
definition text, so both are read. Codes the NTUMC analysis gets wrong are
corrected from ``data/ntumc-fixes.tsv`` (Japanese *are* is remote, not distal
and remote); the feature columns keep NTUMC's analysis.

Writes ``data/ntumc-pronouns.tsv``.

Usage: uv run ntumc_pronouns.py [path/to/wn-ntumc.db]
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_DB = Path.home() / "git" / "NTUMC" / "build" / "wn-ntumc.db"

FEATURES = [
    "head",
    "class",
    "person",
    "number",
    "gender",
    "case",
    "type",
    "formality",
    "politeness",
    "proximity",
    "register",
]

#: a feature synset's English name, or a phrase in a definition -> (feature, value)
VALUES = {
    "first person": ("person", "1"),
    "1st person": ("person", "1"),
    "second person": ("person", "2"),
    "2nd person": ("person", "2"),
    "third person": ("person", "3"),
    "3rd person": ("person", "3"),
    "3nd person": ("person", "3"),  # sic, in one NTUMC definition
    "inclusive": ("person", "1i"),
    "exclusive": ("person", "1e"),
    "singular": ("number", "sg"),
    "plural": ("number", "pl"),
    "dual": ("number", "du"),
    "masculine": ("gender", "m"),
    "feminine": ("gender", "f"),
    "neuter": ("gender", "n"),
    "subjective": ("case", "subj"),
    "objective": ("case", "obj"),
    "possessive": ("case", "poss"),
    "assertive existential": ("type", "assertive"),
    "elective existential": ("type", "elective"),
    "negative": ("type", "negative"),
    "universal": ("type", "universal"),
    "interrogative": ("type", "interrogative"),
    "reflexive": ("type", "reflexive"),
    "reciprocal": ("type", "reciprocal"),
    "other": ("type", "other"),
    "formal": ("formality", "formal"),
    "informal": ("formality", "informal"),
    "polite": ("politeness", "polite"),
    "honorific": ("politeness", "honorific"),
    "non-honorific": ("politeness", "non-honorific"),
    "proximal": ("proximity", "proximal"),
    "medial": ("proximity", "medial"),
    "distal": ("proximity", "distal"),
    "remote": ("proximity", "remote"),
    "men's speech": ("register", "men"),
    "women's speech": ("register", "women"),
    "archaic": ("register", "archaic"),
    "personal pronoun": ("class", "personal"),
    "demonstrative pronoun": ("class", "demonstrative"),
    "demonstrative determiner": ("class", "demonstrative determiner"),
    "possessive pronoun": ("case", "poss"),  # the paper's case: Possessive
    "possessive determiner": ("case", "poss"),
    "duration": ("head", "duration"),
    "interrogative pronoun": ("type", "interrogative"),  # the paper's type
    "interrogative determiner": ("type", "interrogative"),
}
#: an English lemma of the hypernym -> head value
HEADS = {
    "person": "person",
    "entity": "entity",
    "thing": "thing",
    "place": "place",
    "time": "time",
    "manner": "manner",
    "deictic": "deictic",
    "determiner": "determiner",
    "non-standard speech": "non-standard",
    "reason": "reason",
    "kind": "kind",
}
#: longest phrases first, so "elective existential" beats "existential"; a hyphen
#: counts as part of a word, so "honorific" does not match inside "non-honorific"
PHRASES = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(p) for p in sorted(VALUES, key=len, reverse=True))
    + r")(?![\w-])"
)

#: code abbreviations per feature, in the paper's order (register is NTUMC's)
ABBREVIATIONS = {
    "head": {
        "person": "Pers",
        "thing": "Thng",
        "entity": "Ent",
        "place": "Plc",
        "time": "Tim",
        "manner": "Mnr",
        "reason": "Rsn",
        "kind": "Knd",
        "duration": "Dur",
        "deictic": "Dx",
        "determiner": "Det",
        "quantity": "Qnt",
        "non-standard": "NStd",
    },
    "person": {"1": "1", "1i": "1i", "1e": "1e", "2": "2", "3": "3"},
    "number": {"sg": "Sg", "du": "Du", "pl": "Pl"},
    "gender": {"m": "M", "f": "F", "n": "N"},
    "case": {"subj": "Subj", "obj": "Obj", "poss": "Poss"},
    "type": {
        "assertive": "Asrt",
        "elective": "Elec",
        "negative": "Neg",
        "universal": "Univ",
        "interrogative": "Int",
        "reflexive": "Refl",
        "reciprocal": "Recp",
        "other": "Oth",
    },
    "formality": {"formal": "Fml", "informal": "Infml"},
    "politeness": {"polite": "Pol", "honorific": "Hon", "non-honorific": "NHon"},
    "proximity": {
        "proximal": "Prox",
        "medial": "Med",
        "distal": "Dist",
        "remote": "Rem",
    },
    "register": {"men": "Men", "women": "Wom", "archaic": "Arch"},
}


def code(features: dict[str, set[str]]) -> str:
    """Compose a concept code from features, in the paper's order.

    For a personal pronoun the person stands in for the head (``1;Sg``, not
    ``Pers;1;Sg``); a feature with two values joins them with ``+``.

    >>> code({"head": {"person"}, "person": {"3"}, "number": {"sg"}, "gender": {"f"}})
    '3;Sg;F'
    >>> code({"head": {"thing"}, "type": {"interrogative"}})
    'Thng;Int'
    """
    parts = []
    for feature, abbreviations in ABBREVIATIONS.items():
        if feature == "head" and features.get("person"):
            continue
        values = features.get(feature, set())
        if values:
            parts.append("+".join(sorted(abbreviations.get(v, v) for v in values)))
    return ";".join(parts)


def fixes() -> dict[str, str]:
    """Corrected codes for NTUMC synsets, from data/ntumc-fixes.tsv."""
    with (HERE / "data" / "ntumc-fixes.tsv").open(encoding="utf8") as handle:
        return {r["synset"]: r["code"] for r in csv.DictReader(handle, delimiter="\t")}


def read(db: Path) -> list[dict[str, str]]:
    """Return one row per NTUMC pronoun synset, with its features and lemmas."""
    con = sqlite3.connect(db)
    names: dict[str, list[str]] = defaultdict(list)
    for synset, lemma in con.execute(
        "SELECT s.synset, w.lemma FROM sense s JOIN word w USING (wordid)"
        " WHERE w.lang = 'eng'"
    ):
        names[synset].append(lemma)
    # a synset may have several definitions; keep them all
    definitions = dict(
        con.execute(
            "SELECT synset, GROUP_CONCAT(def, '; ') FROM synset_def"
            " WHERE lang = 'eng' AND synset LIKE '770%' GROUP BY synset"
        )
    )
    links = defaultdict(list)
    for source, link, target in con.execute(
        "SELECT synset1, link, synset2 FROM synlink WHERE synset1 LIKE '770%'"
        " AND link IN ('hype', 'dmnu', 'attr')"
    ):
        links[source].append((link, target))
    lemmas: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for synset, lang, lemma in con.execute(
        "SELECT s.synset, w.lang, w.lemma FROM sense s JOIN word w USING (wordid)"
        " WHERE s.synset LIKE '770%' ORDER BY s.freq DESC"
    ):
        # four Japanese words (77000035-n 彼女たち ...) are filed under "jap"
        lemmas[synset]["jpn" if lang == "jap" else lang].append(lemma)

    fixed = fixes()
    rows = []
    for synset in sorted(set(definitions) | set(links)):
        if not synset.startswith("7700"):  # 7701xxxx are the feature synsets
            continue
        features: dict[str, set[str]] = defaultdict(set)
        for link, target in links[synset]:
            if link in ("hype", "attr"):  # attr: "such" is (kind, proximal)
                heads = [HEADS[n] for n in names.get(target, []) if n in HEADS]
                features["head"].add(heads[0] if heads else target)
            else:
                for name in names.get(target, []):
                    if name in VALUES:
                        feature, value = VALUES[name]
                        features[feature].add(value)
        for phrase in PHRASES.findall(definitions.get(synset, "")):
            feature, value = VALUES[phrase]
            features[feature].add(value)
        if {"1i", "1e"} & features["person"]:
            features["person"].discard("1")
        row = {
            "synset": synset,
            "pos": synset[-1],
            "code": fixed.get(synset) or code(features),
        }
        row |= {f: "+".join(sorted(features[f])) for f in FEATURES}
        row["definition"] = definitions.get(synset, "")
        row |= {lang: "; ".join(dict.fromkeys(lemmas[synset][lang])) for lang in LANGS}
        rows.append(row)
    return rows


LANGS = ["eng", "cmn", "jpn", "ind", "zsm", "ces", "ita", "mya", "qcn"]


def main() -> None:
    """Write data/ntumc-pronouns.tsv."""
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    rows = read(db)
    columns = ["synset", "pos", "code", *FEATURES, "definition", *LANGS]
    with (HERE / "data" / "ntumc-pronouns.tsv").open("w", encoding="utf8") as out:
        out.write("\t".join(columns) + "\n")
        for row in rows:
            out.write("\t".join(row[c].replace("\t", " ") for c in columns) + "\n")
    print(f"{len(rows)} pronoun synsets", file=sys.stderr)


if __name__ == "__main__":
    main()
