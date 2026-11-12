"""Tests for Module 3: e-mail NFA, subset construction, minimal DFA."""
import random
from itertools import product

import pytest

from automata.dfa import equivalent
from automata.email_automata import (build_email_nfa, classify_email_char, get_email_system, validate_email)
from automata.nfa import EPSILON
from validation import cases as C
from validation.reference import ref_email, table_filling_class_count

SYSTEM = get_email_system()


@pytest.mark.parametrize("addr", C.EMAIL_REPORT_ACCEPT + C.EMAIL_BOUNDARY_ACCEPT)
def test_accepted(addr):
    res = validate_email(addr)
    assert res.accepted and res.consistent


@pytest.mark.parametrize("addr", C.EMAIL_REPORT_REJECT + C.EMAIL_BOUNDARY_REJECT)
def test_rejected(addr):
    res = validate_email(addr)
    assert not res.accepted and res.consistent


def test_both_spellings_of_the_leading_dot_typo_are_tested():
    assert ".hHarshini@gmail.com" in C.EMAIL_REPORT_REJECT and ".harshini@gmail.com" in C.EMAIL_REPORT_REJECT


def test_tld_length_boundaries():
    assert [validate_email(f"a@b.{t}").accepted for t in ("c", "cc", "ccc")] == [False, True, True]


def test_character_classes():
    assert [classify_email_char(c) for c in "aZ5._-@é +"] == ["L", "L", "D", ".", "_", "-", "@", "O", "O", "O"]


def test_nfa_is_really_nondeterministic_and_has_epsilon_moves():
    nfa = build_email_nfa()
    assert nfa.epsilon_transitions() == [("q6", "q3"), ("q6", "q7")]
    assert nfa.epsilon_closure({"q6"}) == {"q3", "q6", "q7"}
    assert nfa.start_set() == {"q0"}
    # after "a@b." the NFA is in three states at once
    assert validate_email("a@b.").nfa_trace[-1]["after"] == {"q3", "q6", "q7"}


def test_nfa_trace_for_a_valid_address():
    trace = validate_email("x@y.io").nfa_trace
    assert [sorted(r["after"]) for r in trace] == [["q1"], ["q3"], ["q4"], ["q3", "q6", "q7"], ["q4", "q8"], ["q4", "q9"]]


def test_subset_dfa_structure():
    sub = SYSTEM.subset.dfa
    assert sub.start == frozenset({"q0"})
    assert frozenset() in sub.states and frozenset() in sub.dead_states()           # empty set = trap
    assert all((s in sub.accepting) == bool(s & {"q9"}) for s in sub.states)       # accepting iff contains q9
    assert not SYSTEM.unreachable_removed


def test_stage_counts_follow_the_pipeline():
    c = SYSTEM.stage_counts
    assert c["nfa_states"] == len(SYSTEM.nfa.states) == 10
    assert c["minimal_dfa_states"] <= c["subset_dfa_states"]
    assert c["minimal_dfa_states"] == c["subset_dfa_states"] - sum(len(g) - 1 for _, g in SYSTEM.minimal.merged_groups)


def test_minimisation_merges_s0_and_s2():
    """{q0} (start) and {q2} (after a separator) both need exactly one alnum first, so they are equivalent."""
    assert SYSTEM.minimal.merged_groups == [("M0", ["S0", "S2"])]


def test_minimal_dfa_equivalent_and_minimal():
    same, witness = equivalent(SYSTEM.subset_pruned, SYSTEM.minimal.dfa)
    assert same, witness
    assert table_filling_class_count(SYSTEM.subset_pruned) == len(SYSTEM.minimal.dfa.states)


def test_dfa_equivalence_checker_detects_a_difference():
    from automata.dfa import DFA
    broken_delta = dict(SYSTEM.minimal.dfa.delta)
    m = SYSTEM.minimal.dfa
    broken = DFA(m.states, m.alphabet, broken_delta, m.start, set(), name="broken")   # accepts nothing
    same, witness = equivalent(m, broken)
    assert not same and m.accepts(witness)


def test_exhaustive_all_three_machines_agree_with_reference():
    chars = ["a", "1", ".", "-", "_", "@", "!"]
    for n in range(6):
        for tup in product(chars, repeat=n):
            s = "".join(tup)
            res = validate_email(s)
            assert (res.accepted, res.accepted_subset_dfa, res.accepted_minimal_dfa) == (ref_email(s),) * 3, s


def test_random_addresses_fixed_seed():
    rng = random.Random(2026)
    pieces = ["a", "b1", "x-y", ".", "_", "-", "@", ".com", ".io", "co", "é", " "]
    for _ in range(5000):
        s = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 9)))
        assert validate_email(s).accepted == ref_email(s), s
