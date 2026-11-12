"""Tests for Module 2: password policy (component DFAs, product, minimisation)."""
import random
import string
from itertools import product

import pytest

from automata.dfa import equivalent
from automata.password_automata import (PasswordPolicy, build_length_dfa, build_password_system,
                                        build_presence_dfa, classify_password_char,
                                        get_password_system, validate_password)
from validation import cases as C
from validation.reference import ref_password, table_filling_class_count

SYSTEM = get_password_system()


@pytest.mark.parametrize("pw", C.PW_REPORT_ACCEPT)
def test_report_accepted(pw):
    assert validate_password(pw).accepted


@pytest.mark.parametrize("pw", C.PW_REPORT_REJECT)
def test_report_rejected(pw):
    assert not validate_password(pw).accepted


@pytest.mark.parametrize("pw,expected,why", C.PW_EXTRA)
def test_extra_boundaries(pw, expected, why):
    assert validate_password(pw).accepted == expected, why


@pytest.mark.parametrize("pw,expected,why", C.password_boundary_cases())
def test_lengths_7_8_16_17_with_each_class_missing(pw, expected, why):
    assert validate_password(pw).accepted == expected, why
    assert ref_password(pw) == expected


def test_boundary_generator_really_builds_the_lengths_and_missing_classes():
    for pw, _exp, why in C.password_boundary_cases():
        classes = {classify_password_char(c) for c in pw}
        assert len(pw) == int(why.split()[1].rstrip(","))
        if "missing" in why:
            assert why.split(", ")[1][0] not in classes


def test_character_classes():
    assert [classify_password_char(c) for c in "aZ5! é"] == ["L", "U", "D", "S", "O", "O"]
    assert all(classify_password_char(c) == "S" for c in string.punctuation)
    assert len(string.punctuation) == 32


def test_presence_dfa_is_two_states_and_sticky():
    d = build_presence_dfa("U")
    assert len(d.states) == 2 and d.accepts("LDU") and not d.accepts("LDSO") and d.accepts("UUUL")


def test_length_dfa_counts_zero_to_sixteen_and_rejects_seventeenth():
    d = build_length_dfa(8, 16)
    assert len(d.states) == 18                      # n0..n16 plus the overflow trap
    assert [d.accepts("L" * n) for n in (0, 7, 8, 16, 17, 40)] == [False, False, True, True, False, False]


def test_product_state_is_the_tuple_from_the_report():
    res = validate_password("Srm@2026")
    assert res.final_state == (8, 1, 1, 1, 1) and res.final_state in SYSTEM.product.accepting
    assert validate_password("A").final_state == (1, 1, 0, 0, 0)


def test_product_accepting_states_follow_the_rule():
    for state in SYSTEM.product.states:
        rule = 8 <= state[0] <= 16 and all(state[1:])
        assert (state in SYSTEM.product.accepting) == rule


def test_state_counts_are_computed_from_the_machines():
    table = SYSTEM.design_table()
    assert table["States"].tolist() == [sum(len(d.states) for d in SYSTEM.components),
                                        len(SYSTEM.product.states), len(SYSTEM.minimal.dfa.states)]
    assert table["States"].iloc[0] > 0
    assert len(SYSTEM.product.states) <= SYSTEM.product.meta["cartesian_size"]
    assert len(SYSTEM.minimal.dfa.states) < len(SYSTEM.product.states)


def test_minimal_dfa_is_equivalent_and_really_minimal():
    same, witness = equivalent(SYSTEM.product, SYSTEM.minimal.dfa)
    assert same, witness
    assert table_filling_class_count(SYSTEM.product) == len(SYSTEM.minimal.dfa.states)


def test_all_overflow_states_merge_into_one():
    over = [s for s in SYSTEM.product.states if s[0] == 17]
    assert len(over) == 16 and len({SYSTEM.minimal.state_map[s] for s in over}) == 1


def test_changing_the_policy_changes_the_machines():
    small = build_password_system(PasswordPolicy(min_len=2, max_len=3, required=("U", "D")))
    assert len(small.product.states) < len(SYSTEM.product.states)
    assert small.product.accepts(list("UD")) and not small.product.accepts(list("UUU")) and not small.product.accepts(list("UDLS"))


def test_exhaustive_class_strings_up_to_length_7():
    rep = {"U": "A", "L": "a", "D": "1", "S": "!", "O": " "}
    for n in range(8):
        for tup in product("ULDSO", repeat=n):
            s = "".join(rep[c] for c in tup)
            assert SYSTEM.product.accepts(tup) == SYSTEM.minimal.dfa.accepts(tup) == ref_password(s)


def test_random_passwords_fixed_seed():
    rng = random.Random(2026)
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, string.punctuation, " é"]
    for _ in range(5000):
        chosen = [p for p in pools if rng.random() < 0.7] or [pools[0]]
        s = "".join(rng.choice(rng.choice(chosen)) for _ in range(rng.randint(0, 20)))
        res = validate_password(s)
        assert res.accepted == ref_password(s) and res.consistent


def test_missing_requirements_are_reported():
    res = validate_password("srm@2026")
    assert [name for name, ok in res.requirements if not ok] == ["At least one uppercase letter (U)"]
    assert validate_password("Sr@1").missing[0].startswith("Length 8–16")
