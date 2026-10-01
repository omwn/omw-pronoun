#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Turn Parabank Pronoun paradigms into lexemes with concept codes.

The Parabank Pronoun Dataset (Greenhill et al., CC BY 4.0,
github.com/SimonGreenhill/pronouns) records, per language and paradigm, the form
in each cell of a person x number x gender x case grid: ``1sg_s``, ``12du_a``,
``3sg_f_o``. ``1`` is the exclusive first person and ``12`` the inclusive.

Case is inflection, not meaning, so a **lexeme** is a set of cells that share one
row of case forms (A, S, O): English *I/me* is one lexeme for 1sg, and *we/us*
one lexeme for 1du, 1pl, 12du and 12pl. The lemma is the S form (else A); the
other case forms are variants. The possessive (P) is not a case form: *my* adds
a relation to *I*, and Czech *můj* "my" inflects for case itself. Each P form is
a lexeme of its own, with the cells that share it, and its code ends in ``Poss``
(``1;Sg;Poss``).

The lexeme's cells give its **concept code**, in the order of Seah & Bond (2014):
person, number, gender.

- Person: ``1`` when both exclusive and inclusive are covered, else ``1e`` or
  ``1i``; ``2``; ``3``.
- Number: ``Pl`` is non-singular, as in the paper (English *we* fills the dual
  and plural cells); where a dual (or trial) contrasts, the plural alone is
  ``Gpl``, greater plural.
- Gender: Parabank's gender slots are positional. With only ``m`` and ``n``
  filled, ``n`` usually holds the feminine (English *she*, Arabic *hiya*) and in
  Hindi the slots hold proximal/distal forms, so gender is trusted only when the
  ``f`` slot is used. A lexeme split across untrusted slots gets no code.

Free and bound paradigms are both read; the ``analect`` column says which. A bound
lexeme is an affix: it becomes a variant of a free lexeme with the same cells,
or an entry of its own when its syncretisms differ. Writes
``data/parabank-lexemes.tsv``.

Usage: uv run parabank_words.py [path/to/parabank-pronouns]
"""

from __future__ import annotations

import csv
import itertools
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = Path.home() / "git" / "parabank-pronouns"

CELL = re.compile(r"(12|1|2|3)(sg|du|tr|pl)(?:_([mfn]))?_([asop])")
UNGENDERED = re.compile(r"3([dp])-([asop])(?:_([mf]))?")
PERSONS = {"1": "1e", "12": "1i", "2": "2", "3": "3"}
CORE = "sao"  # citation order: S first, then A
#: the possessive is a word of its own (Czech *můj* "my" inflects for case
#: itself), so the ``p`` cells make separate lexemes, of possessive concepts
POSSESSIVE = "p"

#: an atom is (person, number, gender); gender only for the 3rd person
Atom = tuple[str, str, str]


def parse_cell(cell: str) -> tuple[list[Atom], str] | None:
    """Return the atoms a Parabank cell covers, and its case.

    >>> parse_cell("12du_a")
    ([('1i', 'du', '')], 'a')
    >>> parse_cell("3sg_f_o")
    ([('3', 'sg', 'f')], 'o')
    >>> parse_cell("3p-s")   # 3rd plural, gender not distinguished
    ([('3', 'pl', 'f'), ('3', 'pl', 'm'), ('3', 'pl', 'n')], 's')
    """
    if match := CELL.fullmatch(cell):
        person, number, gender, case = match.groups()
        return [(PERSONS[person], number, gender or "")], case
    if match := UNGENDERED.fullmatch(cell):
        number, case, gender = match.groups()
        number = {"d": "du", "p": "pl"}[number]
        genders = [gender] if gender else ["f", "m", "n"]
        return [("3", number, g) for g in genders], case
    return None


def read(root: Path) -> tuple[dict, dict]:
    """Return languages by id, and cells -> case -> forms per (language, paradigm)."""
    cldf = root / "cldf"
    with (cldf / "languages.csv").open(encoding="utf8") as handle:
        languages = {row["ID"]: row for row in csv.DictReader(handle)}
    paradigms: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    # a genderless 3rd dual/plural cell (``3p-s``) fills only the genders the
    # paradigm does not give explicitly: Spanish has 3pl_f ellas and also 3p-s
    # ellos, which must not make ellos feminine
    genderless: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    with (cldf / "forms.csv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle):
            if not row["Form"]:
                continue
            parsed = parse_cell(row["Parameter_ID"])
            if not parsed:
                continue
            atoms, case = parsed
            target = (
                genderless if UNGENDERED.fullmatch(row["Parameter_ID"]) else paradigms
            )
            for atom in atoms:
                target[row["Language_ID"], row["Paradigm_ID"]][atom][case].add(
                    row["Form"]
                )
    for key, cells in genderless.items():
        explicit = paradigms[key]
        for (person, number, gender), cases in cells.items():
            if not any(p == person and n == number and g for p, n, g in explicit):
                for case, forms in cases.items():
                    explicit[person, number, gender][case] |= forms
    return languages, paradigms


def lexemes(
    cells: dict, cases: str = CORE
) -> list[tuple[frozenset, dict[str, set[str]]]]:
    """Group a paradigm's atoms by identical rows of the given cases.

    Atoms with no form in any of the cases are left out.
    """
    by_row: dict = defaultdict(set)
    for atom, forms in cells.items():
        row = tuple((case, frozenset(forms.get(case, ()))) for case in cases)
        if any(f for _, f in row):
            by_row[row].add(atom)
    return [
        (frozenset(atoms), {case: set(forms) for case, forms in row if forms})
        for row, atoms in by_row.items()
    ]


def render_number(numbers: set[str], elicited: set[str]) -> str:
    """Name a set of numbers, with Pl as non-singular and Gpl as greater plural.

    >>> render_number({"du", "pl"}, {"sg", "du", "pl"})
    'Pl'
    >>> render_number({"pl"}, {"sg", "du", "pl"})
    'Gpl'
    >>> render_number({"du"}, {"sg", "du", "pl"})
    'Du'
    """
    nonsingular = elicited - {"sg"}
    if numbers == {"sg"}:
        return "Sg"
    if numbers and numbers == nonsingular:
        return "Pl"
    names = {"sg": "Sg", "du": "Du", "tr": "Tr", "pl": "Gpl"}
    return "+".join(names[n] for n in ("sg", "du", "tr", "pl") if n in numbers)


def render_person(persons: set[str]) -> str:
    """``1`` for exclusive + inclusive, else the persons joined with ``+``."""
    if {"1e", "1i"} <= persons:
        persons = (persons - {"1e", "1i"}) | {"1"}
    return "+".join(sorted(persons))


def code(atoms: frozenset, elicited: set[Atom], gender_trusted: bool) -> str:
    """The concept code of a lexeme's atoms, or '' if it cannot be stated.

    The atoms must form a product (persons x numbers x genders), with gender
    only in the 3rd person.
    """
    persons = {p for p, _, _ in atoms}
    numbers = {n for _, n, _ in atoms}
    elicited_numbers = {n for _, n, _ in elicited}
    third = {g for p, _, g in atoms if p == "3"}
    genders = third or {""}
    product = {
        (p, n, g if p == "3" else "")
        for p, n, g in itertools.product(persons, numbers, genders)
    }
    if product != set(atoms):
        return ""
    # Parabank's "1" is exclusive only where the paradigm also has inclusive ("12")
    # cells; without them (Mandarin has only 1pl wǒmen) it is plain first person.
    # Clusivity is also no property of the singular.
    has_inclusive = any(p == "1i" for p, _, _ in elicited)
    if numbers == {"sg"} or not has_inclusive:
        persons = {"1" if p == "1e" else p for p in persons}
    parts = [render_person(persons)]
    if numbers != elicited_numbers:  # a form for every number leaves it unmarked
        parts.append(render_number(numbers, elicited_numbers))
    if third:
        all_genders = {g for p, n, g in elicited if p == "3" and n in numbers}
        if third != all_genders:
            if not gender_trusted:
                return ""
            parts.append("+".join(g.upper() for g in sorted(third)))
    return ";".join(parts)


def gender_uncertain(cells: dict) -> bool:
    """True if 3rd-person forms differ by gender slot but no slot is feminine.

    Parabank's gender slots are positional: with only ``m`` and ``n`` used, ``n``
    may hold the feminine (English *she*) or even a distal form (Hindi *vah*).
    Their gender-split lexemes are left uncoded rather than given wrong genders.
    """
    third = [(n, g) for p, n, g in cells if p == "3"]
    # only singular cells are always explicitly gendered; the ungendered dual and
    # plural cells are expanded to all three genders, so they cannot vouch
    if any(g == "f" for n, g in third if n == "sg"):
        return False
    for number in {n for n, _ in third}:
        rows = {
            tuple(sorted((c, frozenset(f)) for c, f in cells[("3", number, g)].items()))
            for n, g in third
            if n == number
        }
        if len(rows) > 1:
            return True
    return False


def main() -> None:
    """Write data/parabank-lexemes.tsv."""
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    languages, paradigms = read(root)
    rows = []
    dropped = set()
    for (language_id, paradigm), cells in paradigms.items():
        # an uncertain language keeps everything but its gender-split lexemes,
        # which get no code (see `code`)
        gender_trusted = not gender_uncertain(cells)
        if not gender_trusted:
            dropped.add(language_id)
        elicited = set(cells)
        language = languages[language_id]
        common = (
            language_id,
            language["Glottocode"],
            language["ISO639P3code"],
            language["Name"],
            language["Family"],
            language["Macroarea"],
            paradigm,
            language["Analect"].lower(),
        )
        for atoms, cases in lexemes(cells):
            citation = next(iter(sorted(cases.get("s") or cases.get("a") or [""])))
            variants = "; ".join(
                f"{case}:{form}"
                for case in CORE
                for form in sorted(cases.get(case, ()))
                if form != citation
            )
            concept = code(atoms, elicited, gender_trusted)
            rows.append((concept, *common, citation, variants, str(len(atoms))))
        # possessives: one lexeme per form (English *my* and *mine*), coded over
        # the cells that have a possessive
        owned = {atom for atom, forms in cells.items() if forms.get(POSSESSIVE)}
        for atoms, cases in lexemes(cells, POSSESSIVE):
            concept = code(atoms, owned, gender_trusted)
            concept = f"{concept};Poss" if concept else ""
            for form in sorted(cases[POSSESSIVE]):
                rows.append((concept, *common, form, "", str(len(atoms))))
    columns = [
        "code",
        "language_id",
        "glottocode",
        "iso639_3",
        "language",
        "family",
        "macroarea",
        "paradigm",
        "analect",
        "lemma",
        "variants",
        "atoms",
    ]
    with (HERE / "data" / "parabank-lexemes.tsv").open("w", encoding="utf8") as out:
        out.write("\t".join(columns) + "\n")
        for row in sorted(rows):
            out.write("\t".join(row) + "\n")
    coded = [r for r in rows if r[0]]
    print(
        f"{len(rows)} lexemes in {len(paradigms)} paradigms;"
        f" {len(coded)} coded; {len(dropped)} languages lose gendered 3rd person",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
