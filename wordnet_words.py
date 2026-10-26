#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["langcodes", "language_data", "wn>=1.1"]
# ///
"""Collect words for the ILI-linked pronoun concepts from existing wordnets.

A concept with an exact counterpart in CILI (``data/concept-ili.tsv``) can take
its words from any wordnet with a synset for that ILI: Czech *teď* for *now*
(``Tim;Prox``). The wordnets are the ones Cygnet is built from (see
`cygnet_wordnets.py`), except the TUFS lexicons, which are a source of their own,
and the NTU wordnets in ``../NTUMC``, reached through the ILI's Princeton 3.0
synset. Nobody has checked these words as pronouns.

Writes ``data/wordnet-words.tsv``: one row per (language, concept, word), with
the wordnet it came from, in that wordnet's order.

Usage: uv run wordnet_words.py
"""

from __future__ import annotations

import csv
import logging
import sqlite3
import tomllib
from pathlib import Path

import wn

import build
import cygnet_wordnets
from ntumc_pronouns import DEFAULT_DB

logger = logging.getLogger(__name__)

#: lexicons left out: TUFS is read directly (`tufs_pronouns.py`), and this
#: wordnet itself, which Cygnet now includes
SKIP_PREFIXES = ("tufs-", "omw-pronoun")
#: ILI -> Princeton 3.0 synset, as NTUMC's synsets are identified
ILI_MAP = DEFAULT_DB.parent / "ili-map-pwn30.tab"


def cygnet_rows(linked: dict[str, str]) -> list[tuple[str, str, str, str, str]]:
    """(tag, concept, word, source, ili) from Cygnet's wordnets."""
    with (cygnet_wordnets.CYGNET / "wordnets.toml").open("rb") as handle:
        keys = list(tomllib.load(handle))
    rows = []
    for key in keys:
        try:
            wordnets = cygnet_wordnets.wordnets(key)
        # a source Wn cannot read, or one with a malformed lexicon (an empty version)
        except (wn.Error, KeyError) as error:
            logger.warning("%s: skipped: %s: %s", key, type(error).__name__, error)
            continue
        for wordnet in wordnets:
            lexicon = wordnet.lexicons()[0]
            if lexicon.id.startswith(SKIP_PREFIXES):
                continue
            source = f"{lexicon.id}:{lexicon.version}"
            for code, ili in linked.items():
                for synset in wordnet.synsets(ili=ili):
                    for lemma in synset.lemmas():
                        rows.append((build.bcp47(key), code, lemma, source, ili))
    return rows


def ntumc_rows(linked: dict[str, str]) -> list[tuple[str, str, str, str, str]]:
    """(tag, concept, word, source, ili) from the NTU wordnets."""
    with ILI_MAP.open(encoding="utf8") as handle:
        pwn30 = dict(line.split()[:2] for line in handle if line.strip())
    con = sqlite3.connect(DEFAULT_DB)
    rows = []
    for code, ili in linked.items():
        synset = pwn30.get(ili)
        if not synset:
            continue
        for lang, lemma in con.execute(
            "SELECT w.lang, w.lemma FROM sense s JOIN word w USING (wordid)"
            " WHERE s.synset = ? ORDER BY s.freq DESC",
            (synset,),
        ):
            if lang in build.NTUMC_LANGUAGES:
                tag = build.NTUMC_LANGUAGES[lang][0]
                rows.append((tag, code, lemma, f"NTUMC wordnet {synset}", ili))
    return rows


def main() -> None:
    """Write data/wordnet-words.tsv."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    linked = build.read_concept_ili()
    rows = dict.fromkeys(ntumc_rows(linked) + cygnet_rows(linked))
    out = build.DATA / "wordnet-words.tsv"
    with out.open("w", encoding="utf8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["tag", "concept", "word", "source", "ili"])
        # a stable sort: each wordnet's own order within a language and concept
        writer.writerows(sorted(rows, key=lambda r: (r[0], r[1])))
    logger.info("wrote %d rows to %s", len(rows), Path(out).relative_to(build.HERE))


if __name__ == "__main__":
    main()
