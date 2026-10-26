#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["langcodes", "language_data"]
# ///
"""Collect pronouns for our concepts from Wikidata lexemes (CC0).

``data/concept-wikidata.tsv`` links concepts to Wikidata items: grammatical
categories such as *first-person singular* (Q51929218), and words such as *who*
(Q20656443). A lexeme whose sense has one of those items as "item for this
sense" (P5137) is a word for the concept, e.g. Tamil நான் for ``1;Sg``. A row's
``lexical_category`` restricts it to lexemes of that kind (``pronoun``,
``adverb``, ``determiner``): *now* is ``Tim;Prox`` as a pronoun but
``Tim;Prox;Loc`` as an adverb, and a possessive determiner whose sense is
*first-person singular* is not ``1;Sg``. A row with no category takes any.

Writes ``data/wikidata-words.tsv`` (tag, concept, word, source, category,
note): one row per word, with the lexeme sense it came from, its lexical
category and its language styles (P6191).

Usage: uv run wikidata_words.py
"""

from __future__ import annotations

import csv
import logging
import urllib.parse
import urllib.request
from pathlib import Path

import build

logger = logging.getLogger(__name__)

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = f"omw-pronoun/{build.VERSION} (https://github.com/omwn/omw-pronoun)"
QUERY = """
SELECT ?item ?sense ?lemma ?categoryLabel ?iso ?style WHERE {{
  VALUES ?item {{ {items} }}
  ?sense wdt:P5137 ?item .
  ?lexeme ontolex:sense ?sense ; wikibase:lemma ?lemma ;
          wikibase:lexicalCategory ?category ; dct:language ?language .
  ?language wdt:P220 ?iso .
  OPTIONAL {{ ?sense wdt:P6191/rdfs:label ?style FILTER(LANG(?style) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""


def kind(category: str) -> str:
    """Our kind for a Wikidata lexical category label, or '' if none applies.

    >>> kind("personal pronoun"), kind("adverb"), kind("possessive determiner")
    ('pronoun', 'adverb', '')
    >>> kind("demonstrative adjective")
    'determiner'
    """
    if "possessive" in category:
        return ""
    for word, ours in (
        ("pronoun", "pronoun"),
        ("adverb", "adverb"),
        ("determiner", "determiner"),
        ("adjective", "determiner"),
    ):
        if word in category:
            return ours
    return ""


def run(query: str) -> list[dict[str, str]]:
    """Run a SPARQL query on Wikidata and return its rows."""
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query})
    request = urllib.request.Request(
        url, headers={"Accept": "text/csv", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return list(csv.DictReader(response.read().decode("utf8").splitlines()))


def main() -> None:
    """Write data/wikidata-words.tsv."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with (build.DATA / "concept-wikidata.tsv").open(encoding="utf8") as handle:
        links = [
            r
            for r in csv.DictReader(handle, delimiter="\t")
            if r["relation"] == "exact"
        ]
    items = " ".join(sorted({f"wd:{r['wikidata']}" for r in links}))
    #: (tag, concept, word, source, category) -> the sense's styles
    rows: dict[tuple[str, ...], set[str]] = {}
    for row in run(QUERY.format(items=items)):
        item = row["item"].rsplit("/", 1)[1]
        category = row["categoryLabel"]
        ours = kind(category)
        for link in links:
            if link["wikidata"] != item:
                continue
            if link["lexical_category"] and link["lexical_category"] != ours:
                continue
            sense = row["sense"].rsplit("/", 1)[1]
            key = (
                build.bcp47(row["iso"]),
                link["concept"],
                row["lemma"],
                f"Wikidata {sense}",
                category,
            )
            rows.setdefault(key, set()).update({row["style"]} - {""})
    out = build.DATA / "wikidata-words.tsv"
    with out.open("w", encoding="utf8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["tag", "concept", "word", "source", "category", "note"])
        for key in sorted(rows):
            writer.writerow([*key, ", ".join(sorted(rows[key]))])
    logger.info(
        "wrote %d rows (%d languages) to %s",
        len(rows),
        len({k[0] for k in rows}),
        Path(out).relative_to(build.HERE),
    )


if __name__ == "__main__":
    main()
