"""Tests for the OMW pronoun wordnet builders.

Run with: uv run --with pytest --with langcodes --with language_data pytest
"""

from __future__ import annotations

import pytest

import build
import concepts
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


def test_case_is_not_part_of_a_concept() -> None:
    assert concepts.caseless("1;Sg;Poss") == "1;Sg"
    assert concepts.caseless("3;Sg;F;Poss+Subj") == "3;Sg;F"


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
