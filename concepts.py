#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Build the pronoun concept inventory, ``data/concepts.tsv``.

Concepts come from two places:

- **NTUMC**: every pronoun synset still in the current NTUMC database (synsets
  dropped from it since the April 2026 XML export are ignored). Case is
  inflection, not meaning, so subjective and objective are removed from the
  code and synsets that differ only in them fold together: *I* and *me* are
  both ``1;Sg``. The possessive stays: *my* and *mine* are ``1;Sg;Poss``, a
  concept of its own.
- **Parabank**: codes of Parabank lexemes that NTUMC lacks (dual, plural beside a dual,
  clusivity in the dual, ...), admitted by the rule used for KinDiv: attested in
  at least ``MIN_FAMILIES`` families in ``MIN_AREAS`` macroareas.

Each concept gets an English label and definition composed from its code.

A place or time pro-form can be a noun or an adposition, an intransitive
preposition in the sense of Huddleston and Pullum (2002): English *here* is both,
Japanese *koko* only a noun, *hither* only an adposition
(``data/pro-form-pos.tsv``). The adposition is the noun plus an unspecified
relation to it, the ERG's ``loc_nonsp``: its code adds the direction ``Dir``
(at, to or from), so *here* the noun is ``Plc;Prox`` and the adposition
``Plc;Prox;Dir``. Words whose direction is known get a narrower code
(``data/word-direction.tsv``): English *here* is ``Plc;Prox;Loc+Goal``, since
"from here" needs a preposition. Manner, reason and duration pro-forms are
adverbs (``r``).

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

#: the unmarked direction: at, to or from a place; at, until or since a time
DIRECTION = "Dir"
#: what each direction means, by head
RELATIONS = {
    "Plc": {"Loc": "at", "Goal": "to", "Src": "from"},
    "Tim": {"Loc": "at", "Goal": "until", "Src": "since"},
}

#: cases that are inflection; the possessive (``Poss``) is part of the meaning
CASES = {"Subj", "Obj"}

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
    "Gpl": "plural (beyond the dual)",
    "Two": "of two",
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
    "Det": "determinative",
    "NStd": "non-standard",
    "Asrt": "assertive existential",
    "Elec": "elective existential",
    "Neg": "negative",
    "Univ": "universal",
    "Int": "interrogative",
    "Refl": "reflexive",
    "Recp": "reciprocal",
    "Oth": "other",
    "Poss": "possessive",
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
    "Loc": "locative",
    "Goal": "goal",
    "Src": "source",
    "Dir": "non-specific direction",
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
    """Drop the inflectional cases from a code, keeping the possessive.

    >>> caseless("3;Sg;F;Subj+Obj")
    '3;Sg;F'
    >>> caseless("3;Sg;F;Poss+Subj")
    '3;Sg;F;Poss'
    """
    parts = (
        "+".join(v for v in p.split("+") if v not in CASES) for p in code.split(";")
    )
    return ";".join(p for p in parts if p)


def concept_code(row: dict[str, str]) -> str:
    """The concept code of an NTUMC synset row.

    Case is dropped, keeping the possessive. NTUMC gives the possessive determiner
    (*my*, ``-a``) and the possessive pronoun (*mine*, ``-n``) the same features;
    the pronoun stands for a person or thing, so it gets the head ``Ent``, as the
    demonstrative pronoun *this* (``Ent;Sg;Prox``) does beside the determiner
    (``Sg;Prox``).

    >>> concept_code({"code": "1;Sg;Poss", "synset": "77000107-n"})
    'Ent;1;Sg;Poss'
    >>> concept_code({"code": "1;Sg;Poss", "synset": "77000107-a"})
    '1;Sg;Poss'
    """
    code = caseless(row["code"])
    parts = code.split(";")
    if "Poss" in parts and parts[0] in PERSON and row["synset"].endswith("-n"):
        return f"Ent;{code}"
    return code


def directions(code: str) -> list[str]:
    """The direction values of a code, unmarked ``Dir`` expanded.

    >>> directions("Plc;Prox;Loc+Goal"), directions("Tim;Int;Dir"), directions("Plc")
    (['Loc', 'Goal'], ['Loc', 'Goal', 'Src'], [])
    """
    for part in code.split(";"):
        values = part.split("+")
        if DIRECTION in values:
            return ["Loc", "Goal", "Src"]
        if set(values) <= {"Loc", "Goal", "Src"}:
            return values
    return []


def without_direction(code: str) -> str:
    """The code with its direction slot removed: the noun of an adposition.

    >>> without_direction("Plc;Prox;Loc+Goal"), without_direction("Ent;Sg;Prox")
    ('Plc;Prox', 'Ent;Sg;Prox')
    """
    return ";".join(
        p
        for p in code.split(";")
        if not set(p.split("+")) & {*RELATIONS["Plc"], DIRECTION}
    )


def label(code: str, pos: str = "n") -> str:
    """An English label: ``1i;Du`` -> "first person inclusive dual".

    Alternatives in a slot read as "or": ``Plc;Prox+Dist`` -> "place proximal or
    distal pronoun". Choice from two comes last: ``Sg;Two;Univ`` -> "singular
    universal pronoun of two". An adverb (``Mnr;Int`` with `pos` ``r``) is "manner interrogative
    adverb", and an adposition says its
    relation unless it is unmarked: ``Plc;Prox;Loc+Goal`` -> "place proximal
    adposition (at or to)".
    """
    if pos == "p":
        head = code.split(";")[0]
        rel = (
            ""
            if DIRECTION in code.split(";")[-1].split("+")
            else " ("
            + " or ".join(
                RELATIONS.get(head, RELATIONS["Plc"])[d] for d in directions(code)
            )
            + ")"
        )
        return (
            label(without_direction(code)).removesuffix(" pronoun")
            + " adposition"
            + rel
        )
    parts = code.split(";")
    two = " of two" if "Two" in parts else ""
    parts = [p for p in parts if p != "Two"]
    kind = " pronoun"
    if pos == "r":
        kind = " adverb"
    elif pos == "a" or ("Poss" in parts and parts[0] != "Ent"):
        # the category, after Huddleston and Pullum (2002); determiner is the
        # function: this, which, my
        kind = " determinative"
    elif "Poss" in parts:
        parts = parts[1:]  # mine: "first person singular possessive pronoun"
    words = [
        " or ".join(PERSON.get(v) or WORDS.get(v, v) for v in part.split("+"))
        for part in parts
    ]
    return " ".join(words) + (kind if code else "") + two


def define(code: str, pos: str = "n") -> str:
    """A definition; personal pronouns say who they refer to and how many.

    An adposition says its relation to a place or time:
    ``Plc;Int;Loc+Goal`` -> "an adposition: at or to a place (interrogative)".
    """
    if pos == "p":
        head, *rest = without_direction(code).split(";")
        relation = RELATIONS.get(head, RELATIONS["Plc"])
        rel = ", ".join(relation[d] for d in directions(code))
        rel = " or ".join(rel.rsplit(", ", 1))
        noun = {"Plc": "place", "Tim": "time"}.get(head, WORDS.get(head, head))
        text = f"an adposition: {rel} a {noun}"
        if rest:
            text += (
                " ("
                + ", ".join(
                    " or ".join(WORDS.get(v, v) for v in p.split("+")) for p in rest
                )
                + ")"
            )
        return text
    parts = code.split(";")
    if set(code.split("+")) <= FUNCTIONS:
        uses = ", ".join(WORDS[f] for f in code.split("+"))
        return f"an indefinite pronoun series used for: {uses} (Haspelmath's functions)"
    independent = parts[0] == "Ent" and "Poss" in parts
    if independent:
        parts = parts[1:]
    if parts and parts[0] in REFERENTS:
        possessive = "Poss" in parts
        parts = [p for p in parts if p != "Poss"]
        whose = REFERENTS[parts[0]]
        text = f"a pronoun referring to {whose}"
        if independent:
            text = f"a possessive pronoun: someone or something belonging to {whose}"
        elif possessive:
            text = f"a possessive determinative: of or belonging to {whose}"
        rest = parts[1:]
        if rest and rest[0] in NUMBERS:
            count = NUMBERS[rest[0]]
            text += f", {count} {'possessor' if possessive else 'in all'}"
            rest = rest[1:]
        if rest:
            text += (
                " ("
                + ", ".join(
                    " or ".join(WORDS.get(v, v) for v in p.split("+")) for p in rest
                )
                + ")"
            )
        return text
    text = label(code, pos)
    vowel = text[0] in "aeiou" and not text.startswith("uni")
    return f"{'an' if vowel else 'a'} {text}"


def ntumc_concepts(db: Path) -> dict[str, list[str]]:
    """Caseless code -> NTUMC synsets, for synsets in the current database."""
    extra = ntumc_pronouns.extra()
    current = {
        synset
        for (synset,) in sqlite3.connect(db).execute("SELECT synset FROM synset")
        if synset.startswith("7700") or (extra.get(synset) or {}).get("code")
    }
    by_code: dict[str, list[str]] = defaultdict(list)
    for row in ntumc_pronouns.read(db):
        if row["synset"] in current and row["code"]:
            by_code[concept_code(row)].append(row["synset"])
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
    """A concept's part of speech: pronoun ``n``, determinative ``a``, adverb
    ``r``, adposition ``p``.

    A code with a direction is an adposition. Universal Dependencies tags these
    words ADV; the others correspond to PRON, DET and ADV. A concept folded from
    several NTUMC synsets takes the most nominal. A possessive with no head is a
    determiner (*my*; Parabank's possessives are these).
    """
    if directions(code):
        return "p"
    extra = ntumc_pronouns.extra()
    # a curated synset's part of speech can differ from Princeton's: everywhere
    found = {
        (extra.get(synset) or {}).get("pos") or synset[-1]
        for synset in ntumc.get(code, [])
    }
    parts = code.split(";")
    default = "a" if "Poss" in parts and parts[0] != "Ent" else "n"
    return next((p for p in "nar" if p in found), extra_pos.get(code) or default)


def pro_form_pos() -> dict[str, list[str]]:
    """Place, time, manner, reason and duration code -> its parts of speech.

    From data/pro-form-pos.tsv: ``n p`` for a code that is a noun and, with a
    direction added, an adposition; ``p`` for one that is only a
    adposition; ``r`` for an adverb.
    """
    with (HERE / "data" / "pro-form-pos.tsv").open(encoding="utf8") as handle:
        return {
            row["code"]: row["pos"].split()
            for row in csv.DictReader(handle, delimiter="\t")
        }


def word_directions() -> dict[str, set[str]]:
    """Code -> the directions its words are known to cover (data/word-direction.tsv)."""
    found: dict[str, set[str]] = defaultdict(set)
    with (HERE / "data" / "word-direction.tsv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            found[row["code"]].add(row["direction"])
    return found


def with_direction(code: str, direction: str = DIRECTION) -> str:
    """The adposition of a code: ``Plc;Prox`` -> ``Plc;Prox;Dir``."""
    return f"{code};{direction}"


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
    forms = pro_form_pos()
    known = word_directions()
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
            rows = [(c, pos) for pos in forms.get(c, []) if pos in "nr"]
            if "p" in forms.get(c, []):
                rows += [(with_direction(c), "p")]
                rows += [(with_direction(c, d), "p") for d in sorted(known[c])]
            for key, pos in rows or [(c, pos_of(c, ntumc, extra_pos))]:
                out.write(
                    f"{key}\t{pos}\t{label(key, pos)}\t{define(key, pos)}\t{source}"
                    f"\t{' '.join(ntumc.get(c, []))}\t{languages}\t{len(families)}"
                    f"\t{len(areas)}\n"
                )
    print(
        f"{len(codes)} concepts: {len(ntumc)} from NTUMC, {len(from_parabank)} from"
        f" Parabank, {len(set(extra) - set(ntumc))} from extra-concepts.tsv;"
        f" {sum('p' in p for p in forms.values())} as adpositions",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
