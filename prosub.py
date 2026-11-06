"""Read ProSub's pronouns and demonstratives, for review only (never for the build).

ProSub (github.com/matbahasa/ProSub; Okano et al. 2022) asks, for eight Asian
languages, which words are used for its questionnaire items, and whether each
can refer to the speaker (``1st``), to the addressee (``2nd``), or serve as an
address term or a title. It is CC BY 4.0, but its words are not checked, so
they go only into the review files, as suggestions for a speaker to check. The
clone is expected at ``../ProSub``; without it the review files are written
without them.

Each item is a concept code. A word listed under several items gets the
narrowest concept that covers them all: Indonesian *itu* under both "that
(medial)" and "that (distal)" is ``Ent;Sg;Dist``.
"""

from __future__ import annotations

import csv
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import build

HERE = Path(__file__).resolve().parent
PROSUB = HERE.parent / "ProSub"
DATA = PROSUB / "data_all_v2.0.tsv"
#: TUFS language code -> ProSub's language code
LANGUAGES = {
    "ja": "jpn",
    "ko": "kor",
    "id": "ind",
    "ms": "zsm",
    "th": "tha",
    "vi": "vie",
    "my": "mya",
}
#: ProSub's pronoun and demonstrative items as codes (its NTU synsets name
#: several; this is the plain one)
ITEMS = {
    "104": "Pers;Univ",
    "107": "Ent;Prox",
    "108": "Ent;Pl;Prox",
    "109": "Ent;Sg;Med",
    "110": "Ent;Pl;Med",
    "111": "Ent;Sg;Rem",
    "112": "Ent;Pl;Dist",
    "113": "Plc;Prox",
    "114": "Plc;Med",
    "115": "Plc;Rem",
    "139": "1;Sg",
    "140": "1i;Pl",
    "141": "1e;Pl",
    "142": "2;Sg",
    "143": "2;Pl",
    "144": "3;Sg;M",
    "145": "3;Sg;F",
    "146": "3;Pl",
    "147": "3;Pl;F",
}
#: ProSub's uses, in the order we list them
USES = ("1st", "2nd", "address", "title")


@dataclass
class Word:
    """A ProSub word: the items it is listed under, its gloss and its uses."""

    form: str
    items: set[str] = field(default_factory=set)
    gloss: str = ""
    uses: set[str] = field(default_factory=set)


def version() -> str:
    """The ProSub commit the review files were written from, or ''."""
    try:
        return subprocess.run(
            ["git", "-C", str(PROSUB), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def read_words(lang: str) -> dict[str, Word]:
    """ProSub's words for the items in ITEMS, by form; empty without the clone.

    ProSub numbers homographs (*pak cik01*); the number is dropped. A use counts
    when any of the word's rows judges it ``yes``.
    """
    code = LANGUAGES.get(lang)
    if not code or not DATA.exists():
        return {}
    words: dict[str, Word] = {}
    with DATA.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            row = [cell.strip() for cell in row]
            if len(row) < 10 or row[0] != code or row[1] not in ITEMS or not row[5]:
                continue
            form = re.sub(r"\d+$", "", row[5]).strip()
            word = words.setdefault(form, Word(form))
            word.items.add(row[1])
            word.gloss = word.gloss or row[7]
            if row[9] == "yes":
                word.uses.add(row[8])
    return words


def codes_for(items: set[str], codes: set[str]) -> list[str]:
    """The codes suggested for a word listed under `items`.

    The narrowest codes in `codes` that subsume every item's code: Malay *awak*
    under "you" and "you (pl)" is number-neutral ``2``, Indonesian *itu* under
    "that (medial)" and "that (distal)" is ``Ent;Sg;Dist``. Failing one, each
    item's own code.

    >>> codes_for({"109", "111"}, {"Ent;Sg;Med", "Ent;Sg;Rem", "Ent;Sg;Dist", "Ent;Dist"})
    ['Ent;Sg;Dist']
    >>> codes_for({"139"}, {"1;Sg"})
    ['1;Sg']
    """
    wanted = {ITEMS[i] for i in items}
    if len(wanted) == 1:
        return sorted(wanted)
    covers = {c for c in codes if all(build.subsumes(c, w) for w in wanted)}
    narrowest = sorted(
        c for c in covers if not any(o != c and build.subsumes(c, o) for o in covers)
    )
    return narrowest or sorted(wanted, key=list(ITEMS.values()).index)


def suggestions(lang: str, codes: set[str]) -> dict[str, list[tuple[str, str]]]:
    """ProSub words by the code in `codes` suggested for them: (form, review line).

    Each line reads ``form "gloss" [items] uses``.
    """
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for word in read_words(lang).values():
        items = ",".join(sorted(word.items, key=int))
        uses = " ".join(u for u in USES if u in word.uses) or "no person use"
        gloss = f' "{word.gloss}"' if word.gloss else ""
        for code in codes_for(word.items, codes):
            found[code].append((word.form, f"{word.form}{gloss} [{items}] {uses}"))
    return found
