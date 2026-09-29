#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build the pronoun concept inventory, ``data/concepts.tsv``.

Concepts come from two places:

- **NTUMC**: every pronoun synset still in the current NTUMC database (synsets
  dropped from it since the April 2026 XML export are ignored). Case is
  inflection, not meaning, so the case slot is removed from the code and
  synsets that differ only in case fold together: *I*, *me*, *my* and *mine* are
  all ``1;Sg``.
- **Parabank**: codes of Parabank lexemes that NTUMC lacks (dual, greater plural,
  clusivity in the dual, ...), admitted by the rule used for KinDiv: attested in
  at least ``MIN_FAMILIES`` families in ``MIN_AREAS`` macroareas.

Each concept gets an English label and definition composed from its code.

Usage: uv run concepts.py [path/to/wn-ntumc.db]
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import ntumc_pronouns

HERE = Path(__file__).resolve().parent
MIN_FAMILIES = 5
MIN_AREAS = 3
#: Haspelmath's sample is almost all Eurasian, so the macroarea test cannot be
#: met; indefinite series are admitted on families alone
MIN_FAMILIES_SERIES = 5
FUNCTIONS = {"SK", "SU", "IRR", "Q", "COND", "INEG", "DNEG", "COMP", "FC"}

CASES = {"Subj", "Obj", "Poss"}

PERSON = {
    "1": "first person",
    "1i": "first person inclusive",
    "1e": "first person exclusive",
    "2": "second person",
    "3": "third person",
}
WORDS = {
    "Sg": "singular",
    "Du": "dual",
    "Tr": "trial",
    "Pl": "plural",
    "Gpl": "greater plural",
    "M": "masculine",
    "F": "feminine",
    "N": "neuter",
    "Pers": "person",
    "Thng": "thing",
    "Ent": "entity",
    "Plc": "place",
    "Tim": "time",
    "Mnr": "manner",
    "Rsn": "reason",
    "Knd": "kind",
    "Dur": "duration",
    "Dx": "deictic",
    "Qnt": "quantity",
    "Det": "determiner",
    "NStd": "non-standard",
    "Asrt": "assertive existential",
    "Elec": "elective existential",
    "Neg": "negative",
    "Univ": "universal",
    "Int": "interrogative",
    "Refl": "reflexive",
    "Recp": "reciprocal",
    "Oth": "other",
    "SK": "specific known",
    "SU": "specific unknown",
    "IRR": "irrealis non-specific",
    "Q": "question",
    "COND": "conditional",
    "INEG": "indirect negation",
    "DNEG": "direct negation",
    "COMP": "comparative",
    "FC": "free choice",
    "Fml": "formal",
    "Infml": "informal",
    "Pol": "polite",
    "Hon": "honorific",
    "NHon": "non-honorific",
    "Prox": "proximal",
    "Med": "medial",
    "Dist": "distal",
    "Rem": "remote",
    "Men": "men's speech",
    "Wom": "women's speech",
    "Arch": "archaic",
}
#: who a personal pronoun refers to, for definitions
REFERENTS = {
    "1": "the speaker",
    "1i": "the speaker and the addressee",
    "1e": "the speaker and others, not the addressee",
    "2": "the addressee",
    "3": "someone or something other than speaker and addressee",
}
NUMBERS = {
    "Sg": "one",
    "Du": "two",
    "Tr": "three",
    "Pl": "more than one",
    "Gpl": "more than two (where a dual contrasts)",
}


def caseless(code: str) -> str:
    """Drop the case slot from a code: ``3;Sg;F;Poss+Subj`` -> ``3;Sg;F``."""
    return ";".join(p for p in code.split(";") if not set(p.split("+")) <= CASES)


def label(code: str) -> str:
    """An English label: ``1i;Du`` -> "first person inclusive dual".

    Alternatives in a slot read as "or": ``Plc;Prox+Dist`` -> "place proximal or
    distal pronoun".
    """
    words = []
    for part in code.split(";"):
        words.append(
            " or ".join(PERSON.get(v) or WORDS.get(v, v) for v in part.split("+"))
        )
    return " ".join(words) + (" pronoun" if code else "")


def define(code: str) -> str:
    """A definition; personal pronouns say who they refer to and how many."""
    parts = code.split(";")
    if set(code.split("+")) <= FUNCTIONS:
        uses = ", ".join(WORDS[f] for f in code.split("+"))
        return f"an indefinite pronoun series used for: {uses} (Haspelmath's functions)"
    if parts and parts[0] in REFERENTS:
        text = f"a pronoun referring to {REFERENTS[parts[0]]}"
        rest = parts[1:]
        if rest and rest[0] in NUMBERS:
            count = NUMBERS[rest[0]]
            text += f", {count} in all"
            rest = rest[1:]
        if rest:
            text += (
                " ("
                + ", ".join(WORDS.get(v, v) for p in rest for v in p.split("+"))
                + ")"
            )
        return text
    text = label(code)
    return f"{'an' if text[0] in 'aeiou' else 'a'} {text}"


def ntumc_concepts(db: Path) -> dict[str, list[str]]:
    """Caseless code -> NTUMC synsets, for synsets in the current database."""
    current = {
        synset
        for (synset,) in sqlite3.connect(db).execute(
            "SELECT synset FROM synset WHERE synset LIKE '7700%'"
        )
    }
    by_code: dict[str, list[str]] = defaultdict(list)
    for row in ntumc_pronouns.read(db):
        if row["synset"] in current and row["code"]:
            by_code[caseless(row["code"])].append(row["synset"])
    return by_code


def parabank_concepts() -> dict[str, tuple[set[str], set[str], int]]:
    """Code -> (families, macroareas, languages) over the Parabank lexemes."""
    found: dict = defaultdict(lambda: (set(), set(), set()))
    with (HERE / "data" / "parabank-lexemes.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["code"]:
                families, areas, languages = found[row["code"]]
                families.add(row["family"] or row["glottocode"])
                areas.add(row["macroarea"])
                languages.add(row["language_id"])
    return {c: (f, a, len(l)) for c, (f, a, l) in found.items()}


def pos_of(code: str, ntumc: dict[str, list[str]], extra_pos: dict[str, str]) -> str:
    """A concept's part of speech: pronoun ``n``, determiner ``a``, pro-adverb ``r``.

    These correspond to Universal Dependencies' PRON, DET and ADV. A concept folded
    from several NTUMC synsets takes the most nominal (*I* absorbs *my*).
    """
    found = {synset[-1] for synset in ntumc.get(code, [])}
    return next((p for p in "nar" if p in found), extra_pos.get(code) or "n")


def haspelmath_concepts() -> set[str]:
    """Indefinite series lexicalized in at least MIN_FAMILIES_SERIES families."""
    families: dict[str, set[str]] = defaultdict(set)
    with (HERE / "data" / "haspelmath-series.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            families[row["code"]].add(row["family"])
    return {c for c, f in families.items() if len(f) >= MIN_FAMILIES_SERIES}


def main() -> None:
    """Write data/concepts.tsv."""
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else ntumc_pronouns.DEFAULT_DB
    ntumc = ntumc_concepts(db)
    parabank = parabank_concepts()
    from_parabank = {
        c
        for c, (f, a, _) in parabank.items()
        if len(f) >= MIN_FAMILIES and len(a) >= MIN_AREAS
    } - set(ntumc)
    with (HERE / "data" / "extra-concepts.tsv").open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    extra = {row["code"]: row["source"] for row in rows}
    extra_pos = {row["code"]: row["pos"] for row in rows}
    from_haspelmath = haspelmath_concepts() - set(ntumc)
    codes = set(ntumc) | from_parabank | from_haspelmath | set(extra)
    with (HERE / "data" / "concepts.tsv").open("w", encoding="utf8") as out:
        out.write(
            "code\tpos\tlabel\tdefinition\tsource\tntumc\tparabank_languages"
            "\tparabank_families\tparabank_macroareas\n"
        )
        for c in sorted(codes):
            families, areas, languages = parabank.get(c, (set(), set(), 0))
            source = (
                "NTUMC"
                if c in ntumc
                else "Parabank"
                if c in from_parabank
                else "Haspelmath"
                if c in from_haspelmath
                else extra[c]
            )
            out.write(
                f"{c}\t{pos_of(c, ntumc, extra_pos)}\t{label(c)}\t{define(c)}\t{source}"
                f"\t{' '.join(ntumc.get(c, []))}\t{languages}\t{len(families)}"
                f"\t{len(areas)}\n"
            )
    print(
        f"{len(codes)} concepts: {len(ntumc)} from NTUMC, {len(from_parabank)} from"
        f" Parabank, {len(set(extra) - set(ntumc))} from extra-concepts.tsv",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
