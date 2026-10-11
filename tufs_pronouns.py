#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Extract TUFS Basic Vocabulary pronouns, with a default concept per heading.

TUFS words are translations of Japanese headwords. Pro-forms are filed under
several Bunrui Goihyō classes: persons (1.20), things (1.101), places (1.17),
times (1.1611), quantities (1.196), reasons (4.118), universals (1.194) and
determiners and manner (3.1010). Each heading gets the concept its translations most
likely express (``HEADINGS``). This is a default, not a checked mapping: French
*vous* under あなた is not ``2;Sg``. Rows are marked ``default`` so that a
curation step can override them, as for KinDiv's TUFS words.

Japanese is included so it can be checked against NTUMC's Japanese lemmas.

Writes ``data/tufs-pronouns.tsv``.

Usage: uv run tufs_pronouns.py [path/to/tufs]
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = Path.home() / "git" / "tufs"

#: Bunrui heading (midasi) -> default concept code
HEADINGS = {
    # personal (Bunrui 1.201-1.202)
    "私（わたし）": "1;Sg",
    "私（わたくし）": "1;Sg",
    "私たち": "1;Pl",
    "あなた": "2;Sg",
    "君（きみ）": "2;Sg;Infml",
    "あなた方": "2;Pl",
    "彼（かれ）": "3;Sg;M",
    "彼女": "3;Sg;F",
    "彼ら": "3;Pl",
    "だれ": "Pers;Int",
    "どなた": "Pers;Int;Pol",
    "だれか": "Pers;Sg;Asrt",
    "自分": "Pers;Refl",
    # universal (1.194)
    "みんな": "Pers;Univ",
    "皆さん": "Pers;Univ;Pol",
    "全部": "Thng;Sg;Univ",
    # things (1.101): Japanese has three degrees of distance
    "これ": "Ent;Sg;Prox",
    "それ": "Ent;Sg;Med",
    "あれ": "Ent;Sg;Rem",
    "どれ": "Ent;Int",
    "どっち": "Ent;Two;Int;Infml",
    "何（なに・なん）": "Thng;Int",
    # places and directions (1.17, 1.173)
    "ここ": "Plc;Prox",
    "そこ": "Plc;Med",
    "あそこ": "Plc;Rem",
    "どこ": "Plc;Int",
    "こちら": "Plc;Prox",
    "そちら": "Plc;Med",
    "あちら": "Plc;Rem",
    "どちら": "Plc;Int",
    "こっち": "Plc;Prox",
    "そっち": "Plc;Med",
    "あっち": "Plc;Rem",
    # time, quantity, reason (1.1611, 1.196, 4.118)
    "いつ": "Tim;Int",
    "いくつ": "Qnt;Int",
    "いくら": "Qnt;Int",
    "なぜ": "Rsn;Int",
    "どうして": "Rsn;Int",
    # determiners and manner (3.1010)
    "この": "Prox",
    "その": "Med",
    "あの": "Rem",
    "どの": "Int",
    "こんな": "Knd;Prox",
    "どんな": "Knd;Int",
    "そう": "Mnr;Med",
    "どう": "Mnr;Int",
}
#: TUFS language codes that differ from ISO 639-3 (TUFS `as` is Syrian Arabic)
TUFS_ISO = {
    "ar": "arb",
    "as": "apc",
    "de": "deu",
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "id": "ind",
    "km": "khm",
    "ko": "kor",
    "lo": "lao",
    "mn": "khk",
    "ms": "zsm",
    "my": "mya",
    "pb": "por",
    "pt": "por",
    "ru": "rus",
    "th": "tha",
    "tl": "tgl",
    "tr": "tur",
    "ur": "urd",
    "vi": "vie",
    "zh": "cmn",
}
DUMP = re.compile(r"vmod_([a-z]+)\.sql")
COPY = re.compile(r"COPY (\w+) \(([^)]*)\) FROM stdin;")
ANNOTATION = re.compile(r"\((?:orth|morph):[^)]*\)|（[^）]*）|\([^)]*\)")
PINYIN = re.compile(r"\s+[a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]+$")


def forms_of(lemma: str, lang: str) -> list[str]:
    """Split a TUFS lemma cell into NFC word forms, without annotations.

    >>> forms_of("(သူတစ်ပါးရဲ့)အစ်ကို; ကိုကို", "my")
    ['အစ်ကို', 'ကိုကို']
    >>> forms_of("你 nǐ", "zh")
    ['你']
    """
    parts = (
        ANNOTATION.sub("", p) for p in re.split(r"[;；/]", lemma.replace("\\n", " "))
    )
    cleaned = [" ".join(p.split()).rstrip("\u200f") for p in parts]
    if lang == "zh":  # the raw dumps append pinyin
        cleaned = [PINYIN.sub("", f) for f in cleaned]
    return [unicodedata.normalize("NFC", f) for f in cleaned if f]


def read_dump(path: Path) -> dict[str, list[dict[str, str]]]:
    """Read the COPY blocks of a PostgreSQL dump into rows keyed by table."""
    tables: dict[str, list[dict[str, str]]] = {}
    columns: list[str] = []
    table = ""
    with path.open(encoding="utf8") as handle:
        for line in handle:
            if match := COPY.match(line):
                table, columns = match[1], [c.strip() for c in match[2].split(",")]
                tables[table] = []
            elif table and line.startswith("\\."):
                table = ""
            elif table:
                tables[table].append(dict(zip(columns, line.rstrip("\n").split("\t"))))
    return tables


def main() -> None:
    """Write data/tufs-pronouns.tsv."""
    tufs = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    rows = set()
    for path in sorted((tufs / "tufsdata").glob("vmod_*.sql")):
        match = DUMP.fullmatch(path.name)
        if not match:
            continue
        lang = match[1]
        tables = read_dump(path)
        words = {w["id"]: w["basic"] for w in tables["t_word"]}
        word_of = {u["usage_id"]: u["word_id"] for u in tables["t_usage"]}
        for row in tables["t_usage_classified_rel"]:
            if (
                row["midasi"] in HEADINGS
                and row["usage_id"] in word_of
                and not row["bunrui_no"].startswith("4.3")  # あの(2) is a filler
            ):
                wid = word_of[row["usage_id"]]
                for form in forms_of(words.get(wid, ""), lang):
                    rows.add(
                        (
                            HEADINGS[row["midasi"]],
                            lang,
                            TUFS_ISO.get(lang, lang),
                            wid,
                            row["midasi"],
                            form,
                        )
                    )
    with (HERE / "data" / "tufs-pronouns.tsv").open("w", encoding="utf8") as out:
        out.write("code\ttufs_lang\tiso639_3\ttufs_wid\theading\tform\tmethod\n")
        for row in sorted(rows):
            out.write("\t".join(row) + "\tdefault\n")
    print(f"{len(rows)} TUFS pronoun forms", file=sys.stderr)


if __name__ == "__main__":
    main()
