"""Tests for the OMW pronoun wordnet builders.

Run with: uv run --with pytest --with langcodes --with language_data pytest
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import build
import concepts
import facts
import ntumc_pronouns
import parabank_words


def test_code_follows_the_papers_order() -> None:
    features = {
        "person": {"1"},
        "number": {"sg"},
        "formality": {"formal"},
        "politeness": {"polite"},
        "head": {"person"},
    }
    assert ntumc_pronouns.code(features) == "1;Sg;Fml;Pol"


def test_case_is_not_part_of_a_concept_but_the_possessive_is() -> None:
    assert concepts.caseless("1;Sg;Obj") == "1;Sg"
    assert concepts.caseless("1;Sg;Poss") == "1;Sg;Poss"
    assert concepts.caseless("3;Sg;F;Poss+Subj") == "3;Sg;F;Poss"


def test_possessive_cells_are_lexemes_of_their_own() -> None:
    # Czech: on/jeho (3sg m) and ono/jej (3sg n) differ, but share possessive jeho
    cells = {
        ("3", "sg", "m"): {"s": {"on"}, "o": {"jeho"}, "p": {"jeho"}},
        ("3", "sg", "n"): {"s": {"ono"}, "o": {"jej"}, "p": {"jeho"}},
    }
    core = parabank_words.lexemes(cells)
    possessive = parabank_words.lexemes(cells, parabank_words.POSSESSIVE)
    assert len(core) == 2
    assert all("p" not in forms for _, forms in core)
    assert possessive == [(frozenset(cells), {"p": {"jeho"}})]


def test_a_possessive_is_not_a_kind_of_its_pronoun() -> None:
    assert not build.subsumes("1;Sg", "1;Sg;Poss")
    assert not build.subsumes("1;Sg;Poss", "1;Sg")
    assert build.subsumes("3;Sg;Poss", "3;Sg;F;Poss")


def test_possessives_link_to_their_pronouns() -> None:
    codes = {"1;Sg", "1;Sg;Poss", "Ent;1;Sg;Poss", "Int", "Poss;Int"}
    assert build.possessive_links("1;Sg;Poss", codes) == [("possessor", "1;Sg")]
    assert build.possessive_links("Ent;1;Sg;Poss", codes) == [("possessor", "1;Sg")]
    assert build.possessive_links("1;Sg", codes) == [
        ("possessive", "1;Sg;Poss"),
        ("possessive", "Ent;1;Sg;Poss"),
    ]
    assert build.possessive_links("Poss;Int", codes) == []


def test_possessive_determinative_and_pronoun_are_separate_concepts() -> None:
    my = {"code": "1;Sg;Poss", "synset": "77000107-a"}
    mine = {"code": "1;Sg;Poss", "synset": "77000107-n"}
    assert concepts.concept_code(my) == "1;Sg;Poss"
    assert concepts.concept_code(mine) == "Ent;1;Sg;Poss"
    assert concepts.label("1;Sg;Poss").endswith("determinative")
    assert concepts.label("Sg;Prox", "a") == "singular proximal determinative"
    pos = {"1;Sg;Poss": "a", "Ent;1;Sg;Poss": "n"}
    assert build.determinative_links("1;Sg;Poss", pos) == [("pronoun", "Ent;1;Sg;Poss")]
    assert concepts.label("Ent;1;Sg;Poss") == "first person singular possessive pronoun"


def test_hypernymy_stays_within_a_part_of_speech() -> None:
    pos = {"Sg;Prox": "a", "Ent;Sg;Prox": "n", "1;Sg;Poss": "a", "Ent;1;Sg;Poss": "n"}
    parents = build.hypernyms(list(pos), pos)
    assert parents["Ent;Sg;Prox"] == set()
    assert parents["Ent;1;Sg;Poss"] == set()


def test_a_place_code_is_a_noun_and_a_pro_adposition() -> None:
    pos = {
        "Plc;Prox": "n",
        "Plc;Prox;Dir": "p",
        "Plc;Prox;Loc+Goal": "p",
        "Plc;Prox;Loc": "p",
        "Plc;Prox;Goal": "p",
        "Plc;Prox;Src": "p",
    }
    parents = build.hypernyms(list(pos), pos)
    assert parents["Plc;Prox;Loc+Goal"] == {"Plc;Prox;Dir"}
    assert parents["Plc;Prox;Loc"] == parents["Plc;Prox;Goal"] == {"Plc;Prox;Loc+Goal"}
    # hence is not a kind of here: English here does not cover "from"
    assert parents["Plc;Prox;Src"] == {"Plc;Prox;Dir"}
    # the noun lacks the relation, so it is not above the adposition
    assert parents["Plc;Prox"] == parents["Plc;Prox;Dir"] == set()
    assert concepts.label("Plc;Prox;Loc+Goal", "p") == (
        "place proximal adposition (at or to)"
    )
    assert concepts.define("Tim;Int;Dir", "p") == (
        "an adposition: at, until or since a time (interrogative)"
    )
    assert build.feature_links("Plc;Prox;Dir", build.read_features(), "p") == [
        ("attribute", "Plc"),
        ("exemplifies", "Prox"),
        ("exemplifies", "Dir"),
    ]
    used = ["Loc", "Goal", "Src", "Dir", "Tmp", "Role"]
    assert ("hypernym", "Role") in build.feature_hierarchy("Dir", used)
    assert ("hypernym", "Dir") in build.feature_hierarchy("Tmp", used)
    assert build.direction_links("Plc;Prox", pos) == [("adposition", "Plc;Prox;Dir")]


def test_words_take_their_languages_part_of_speech_and_direction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        build,
        "POS",
        {"Plc;Prox": "n", "Plc;Prox;Dir": "p", "Plc;Prox;Loc+Goal": "p"},
    )
    languages = {tag: build.Language(tag, tag) for tag in ("en", "ja", "it")}
    for tag, lemma in (("en", "here"), ("ja", "ここ"), ("it", "qui")):
        languages[tag].entry(lemma, "Plc;Prox").senses["Plc;Prox"].add("test")
    build.place_pro_forms(languages)

    def senses(tag: str) -> list[tuple[str, str]]:
        return sorted(
            (e.pos, code) for e in languages[tag].entries.values() for code in e.senses
        )

    assert senses("en") == [("n", "Plc;Prox"), ("p", "Plc;Prox;Loc+Goal")]
    assert senses("ja") == [("n", "Plc;Prox")]
    assert senses("it") == [("p", "Plc;Prox;Dir")]


def test_remapped_sense_moves_to_an_entry_of_its_part_of_speech(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "remap.tsv").write_text(
        "lang\tlemma\tfrom_code\tto_code\tnote\ncs\tkam\tPlc;Int\tPlc;Int;Goal\t\n",
        encoding="utf8",
    )
    monkeypatch.setattr(build, "DATA", tmp_path)
    monkeypatch.setattr(build, "POS", {"Plc;Int": "n", "Plc;Int;Goal": "p"})
    czech = build.Language("cs", "Czech")
    czech.entry("kam", "Plc;Int").senses["Plc;Int"].add("test")
    build.remap({"cs": czech})
    assert [(e.lemma, e.pos, set(e.senses)) for e in czech.entries.values()] == [
        ("kam", "p", {"Plc;Int;Goal"})
    ]


def test_derivation_links_one_lemma_across_parts_of_speech() -> None:
    senses = [
        ("here", "n", "Plc;Prox", "here-n"),
        ("here", "p", "Plc;Prox;Loc+Goal", "here-p"),
        ("this", "a", "Sg;Prox", "this-a"),
        ("this", "n", "Ent;Sg;Prox", "this-n"),
        ("that", "a", "Sg;Dist", "that-a"),
    ]
    assert build.derivations(senses) == {
        "here-n": ["here-p"],
        "here-p": ["here-n"],
        "this-a": ["this-n"],
        "this-n": ["this-a"],
    }


@pytest.mark.parametrize(
    ("numbers", "elicited", "expected"),
    [
        ({"du", "pl"}, {"sg", "du", "pl"}, "Pl"),  # English "we": non-singular
        ({"pl"}, {"sg", "du", "pl"}, "Gpl"),  # plural where a dual contrasts
        ({"du"}, {"sg", "du", "pl"}, "Du"),
    ],
)
def test_number(numbers: set[str], elicited: set[str], expected: str) -> None:
    assert parabank_words.render_number(numbers, elicited) == expected


def test_singular_first_person_has_no_clusivity() -> None:
    atoms = frozenset({("1e", "sg", "")})
    elicited = {("1e", "sg", ""), ("1e", "pl", ""), ("1i", "pl", "")}
    assert parabank_words.code(atoms, elicited, gender_trusted=True) == "1;Sg"


def test_a_form_for_every_number_leaves_number_unmarked() -> None:
    atoms = frozenset({("2", "sg", ""), ("2", "du", ""), ("2", "pl", "")})
    assert parabank_words.code(atoms, set(atoms), gender_trusted=True) == "2"


def test_untrusted_gender_gets_no_code() -> None:
    elicited = {("3", "sg", "m"), ("3", "sg", "n")}
    she = frozenset({("3", "sg", "n")})
    assert parabank_words.code(she, elicited, gender_trusted=False) == ""


@pytest.mark.parametrize(
    ("general", "specific"),
    [
        ("1;Du", "1e;Du"),
        ("1e;Pl", "1e;Du"),
        ("2;Sg", "2;Sg;Infml"),
        ("Pers;Int", "Pers;Int;Pol"),
    ],
)
def test_hierarchy(general: str, specific: str) -> None:
    assert build.subsumes(general, specific)
    assert not build.subsumes(specific, general)


def test_closest_hypernyms_only() -> None:
    parents = build.hypernyms(["1;Pl", "1e;Pl", "1e;Du", "1;Du"])
    assert parents["1e;Du"] == {"1;Du", "1e;Pl"}


@pytest.mark.parametrize(
    ("form", "script"),
    [
        ("我们", "Hani"),
        ("わたし", "Hira"),
        ("私たち", "Jpan"),
        ("она", "Cyrl"),
        ("we", "Latn"),
    ],
)
def test_script(form: str, script: str) -> None:
    assert build.script_of(form) == script


def test_english_indefinite_types_are_unions_of_haspelmaths_functions() -> None:
    # someone (Pers;Sg;Asrt) falls under any series covering all of some-'s uses
    assert build.subsumes("SK+SU+IRR+Q+COND", "Pers;Sg;Asrt")
    assert not build.subsumes("SK+SU", "Pers;Sg;Asrt")
    assert build.subsumes("SK+SU+IRR+Q+COND+INEG", "SK+SU")
    assert build.expand(frozenset({"Asrt"})) == {"SK", "SU", "IRR", "Q", "COND"}


def test_series_definition_lists_its_functions() -> None:
    assert concepts.define("SK+SU") == (
        "an indefinite pronoun series used for: specific known, specific unknown"
        " (Haspelmath's functions)"
    )


def test_genderless_cells_do_not_override_explicit_gender() -> None:
    # Parabank Spanish has 3pl_f ellas and also a genderless 3p-s ellos
    _, paradigms = parabank_words.read(parabank_words.DEFAULT)
    cells = next(c for (lang, _), c in paradigms.items() if lang == "spanish")
    assert cells[("3", "pl", "f")]["s"] == {"ellas"}
    assert cells[("3", "pl", "m")]["s"] == {"ellos"}


def test_first_person_is_exclusive_only_where_an_inclusive_contrasts() -> None:
    no_inclusive = {("1e", "sg", ""), ("1e", "pl", "")}  # Mandarin: only 1pl wǒmen
    assert (
        parabank_words.code(frozenset({("1e", "pl", "")}), no_inclusive, True) == "1;Pl"
    )
    with_inclusive = no_inclusive | {("1i", "pl", "")}
    assert (
        parabank_words.code(frozenset({("1e", "pl", "")}), with_inclusive, True)
        == "1e;Pl"
    )


def test_subsumes_is_containment_of_feature_assignments() -> None:
    # FEATURES.md: a code denotes the assignments that agree with its features;
    # an unfilled slot allows any value or none, except case (non-possessive) and
    # direction (a noun, not an adposition), which mean the relation is absent
    with (build.DATA / "concepts.tsv").open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    codes = [r["code"] for r in rows]
    slots = {**build.SLOTS, **build.CATEGORIES}
    domain = {
        s: set().union(*(build.expand(frozenset({v})) for v in vs))
        for s, vs in slots.items()
    }

    def denotation(code: str) -> dict[str, frozenset[str]]:
        found = build.features(code)
        unfilled = {
            "case": frozenset({"non-possessive"}),
            "direction": frozenset({"none"}),
        }
        return {
            s: frozenset(build.expand(found[s]))
            if s in found
            else unfilled.get(s, frozenset(domain[s] | {"none"}))
            for s in slots
        }

    meaning = {code: denotation(code) for code in codes}
    for general in codes:
        for specific in codes:
            contained = all(meaning[specific][s] <= meaning[general][s] for s in slots)
            assert contained == build.subsumes(general, specific), (general, specific)


def test_ili_links_name_concepts_and_are_unique() -> None:
    with (build.DATA / "concepts.tsv").open(encoding="utf8") as handle:
        codes = {row["code"] for row in csv.DictReader(handle, delimiter="\t")}
    linked = build.read_concept_ili()
    assert set(linked) <= codes
    assert linked["Tim;Prox"] == "i116653"  # now: the momentary present
    features = {row["ili"] for row in build.read_features().values() if row["ili"]}
    ilis = list(linked.values())
    assert len(ilis) == len(set(ilis))
    assert not set(ilis) & features


def test_extra_ntumc_synsets_have_a_valid_code_or_are_skipped() -> None:
    for synset, row in ntumc_pronouns.extra().items():
        if row["code"]:
            assert row["pos"] in ("n", "a", "r"), synset
            assert not any(s.startswith("?") for s in build.features(row["code"]))
        else:
            assert row["note"].startswith("skip:"), synset


def test_wordnet_words_are_for_linked_concepts() -> None:
    linked = build.read_concept_ili()
    with (build.DATA / "wordnet-words.tsv").open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows
    assert all(linked.get(r["concept"]) == r["ili"] for r in rows)
    assert not any(r["source"].startswith("tufs-") for r in rows)


def test_facts_are_current() -> None:
    # the gender figure is read from the Parabank clone (../parabank-pronouns);
    # without it, compute() leaves it out, and so does the comparison
    committed = json.loads((build.DATA / "facts.json").read_text(encoding="utf8"))
    found = facts.compute()
    if "gender_untrusted" not in found["parabank"]:
        committed["parabank"].pop("gender_untrusted", None)
    assert found == committed, "data/facts.json is stale: run uv run facts.py"


#: the slots in FEATURES.md's order
SLOT_ORDER = [
    "head",
    "person",
    "number",
    "domain",
    "gender",
    "case",
    "type",
    "formality",
    "politeness",
    "proximity",
    "direction",
    "register",
]


def test_concept_codes_follow_the_slot_order() -> None:
    with (build.DATA / "concepts.tsv").open(encoding="utf8") as handle:
        codes = [r["code"] for r in csv.DictReader(handle, delimiter="\t")]
    disordered = set()
    for code in codes:
        slots = [SLOT_ORDER.index(s) for s in build.features(code)]
        if slots != sorted(slots):
            disordered.add(code)
    assert not disordered
