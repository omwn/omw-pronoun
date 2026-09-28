#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Read Haspelmath's indefinite pronoun series as function sets.

Haspelmath (1997), as the CLDF dataset ``cldf-datasets/haspelmathindefpro``
(CC BY 4.0), records for 40 languages each indefinite pronoun series (German
*etwas*, *irgend-*, *je-*, *n-*) and which of nine functions it covers:

    SK   specific known          COND  conditional
    SU   specific unknown        INEG  indirect negation
    IRR  irrealis non-specific   DNEG  direct negation
    Q    question                COMP  comparative
                                 FC    free choice

A series' meaning is its set of functions, just as a Parabank pronoun's meaning
is its set of cells, so its concept code is the function set in the order of
Haspelmath's implicational map: German *irgend-* is ``SU+IRR+Q+COND+INEG+COMP+FC``.

Writes ``data/haspelmath-series.tsv``.

Usage: uv run haspelmath_series.py [path/to/haspelmathindefpro]
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = Path.home() / "git" / "haspelmathindefpro"

#: Haspelmath's functions, in the order of the implicational map
FUNCTIONS = {
    "specific-known": "SK",
    "specific-unknown": "SU",
    "irrealis-nsp": "IRR",
    "question": "Q",
    "conditional": "COND",
    "indirect-negation": "INEG",
    "direct-negation": "DNEG",
    "comparative": "COMP",
    "free-choice": "FC",
}
#: families for the languages Kinbank and Parabank do not list
FAMILIES = {
    "Ancash Quechua": "Quechuan",
    "Lezgian": "Nakh-Daghestanian",
    "Maltese": "Afro-Asiatic",
    "Nanay": "Tungusic",
    "Georgian": "Kartvelian",
    "Japanese": "Japonic",
    "Yakut": "Turkic",
}


def code(functions: set[str]) -> str:
    """A function set as a code, in map order.

    >>> code({"question", "specific-known", "free-choice"})
    'SK+Q+FC'
    """
    return "+".join(abbr for name, abbr in FUNCTIONS.items() if name in functions)


def families() -> dict[str, str]:
    """Glottocode -> family, from the Kinbank and Parabank language tables."""
    found = {}
    for path in (
        Path.home() / "git" / "kinbank" / "kinbank" / "cldf" / "languages.csv",
        Path.home() / "git" / "parabank-pronouns" / "cldf" / "languages.csv",
    ):
        with path.open(encoding="utf8") as handle:
            for row in csv.DictReader(handle):
                if row["Glottocode"] and row.get("Family"):
                    found.setdefault(row["Glottocode"], row["Family"])
    return found


def main() -> None:
    """Write data/haspelmath-series.tsv."""
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    cldf = root / "cldf"
    with (cldf / "languages.csv").open(encoding="utf8") as handle:
        languages = {row["ID"]: row for row in csv.DictReader(handle)}
    with (cldf / "constructions.csv").open(encoding="utf8") as handle:
        constructions = {row["ID"]: row for row in csv.DictReader(handle)}
    functions: dict[str, set[str]] = defaultdict(set)
    with (cldf / "cvalues.csv").open(encoding="utf8") as handle:
        for row in csv.DictReader(handle):
            if row["Value"] == "yes":
                functions[row["Construction_ID"]].add(
                    row["Parameter_ID"].removeprefix("c-")
                )
    family_of = families()
    with (HERE / "data" / "haspelmath-series.tsv").open("w", encoding="utf8") as out:
        out.write(
            "code\tconstruction\tglottocode\tiso639_3\tlanguage\tfamily\tmacroarea"
            "\tmarker\n"
        )
        for cid, found in sorted(functions.items()):
            language = languages[constructions[cid]["Language_ID"]]
            family = family_of.get(language["Glottocode"]) or FAMILIES.get(
                language["Name"], ""
            )
            marker = constructions[cid]["Name"].removeprefix("Marker: ")
            out.write(
                f"{code(found)}\t{cid}\t{language['Glottocode']}\t{language['ISO639P3code']}"
                f"\t{language['Name']}\t{family}\t{language['Macroarea']}\t{marker}\n"
            )
    print(f"{len(functions)} series", file=sys.stderr)


if __name__ == "__main__":
    main()
