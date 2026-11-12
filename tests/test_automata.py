"""Tests for the generic machinery: DFA, NFA, product, subset construction, minimisation."""
from itertools import product

import pytest

from automata.dfa import DFA, AutomatonError, equivalent
from automata.minimization import minimize, remove_unreachable
from automata.nfa import EPSILON, NFA
from automata.subset_construction import full_powerset_dfa, subset_construction
from validation.reference import table_filling_class_count


def ends_with_01_nfa() -> NFA:
    """Classic textbook NFA: strings over {0,1} ending in 01."""
    return NFA(["a", "b", "c"], ["0", "1"],
               {("a", "0"): {"a", "b"}, ("a", "1"): {"a"}, ("b", "1"): {"c"}}, "a", ["c"], name="ends-01")


def parity_dfa(copies: int = 1) -> DFA:
    """Even number of 1s, deliberately bloated: state (parity, copy) - all copies are equivalent."""
    states = [(p, k) for p in (0, 1) for k in range(copies)]
    delta = {((p, k), "0"): (p, (k + 1) % copies) for p, k in states}
    delta.update({((p, k), "1"): (1 - p, (k + 1) % copies) for p, k in states})
    return DFA(states, ["0", "1"], delta, (0, 0), [(0, k) for k in range(copies)], name="parity")


# --------------------------------------------------------------------- DFA ---
def test_dfa_rejects_incomplete_transition_function():
    with pytest.raises(AutomatonError):
        DFA(["a"], ["0", "1"], {("a", "0"): "a"}, "a", ["a"])


def test_dfa_rejects_transition_to_unknown_state():
    with pytest.raises(AutomatonError):
        DFA(["a"], ["0"], {("a", "0"): "z"}, "a", ["a"])


def test_dfa_trace_and_dead_states():
    d = DFA(["s", "t", "x"], ["a", "b"], {("s", "a"): "t", ("s", "b"): "x", ("t", "a"): "t", ("t", "b"): "t",
                                          ("x", "a"): "x", ("x", "b"): "x"}, "s", ["t"])
    assert [(s.source, s.symbol, s.target) for s in d.trace("ab")] == [("s", "a", "t"), ("t", "b", "t")]
    assert d.dead_states() == {"x"}


def test_product_intersection_and_union():
    even = parity_dfa()
    ends0 = DFA(["n", "z"], ["0", "1"], {("n", "0"): "z", ("n", "1"): "n", ("z", "0"): "z", ("z", "1"): "n"}, "n", ["z"])
    both, either = DFA.product([even, ends0], "all"), DFA.product([even, ends0], "any")
    for n in range(8):
        for t in product("01", repeat=n):
            w = "".join(t)
            e, z = w.count("1") % 2 == 0, w.endswith("0")
            assert both.accepts(w) == (e and z) and either.accepts(w) == (e or z)


# --------------------------------------------------------------------- NFA ---
def test_epsilon_closure_follows_chains():
    nfa = NFA(["p", "q", "r", "s"], ["a"], {("p", EPSILON): {"q"}, ("q", EPSILON): {"r"}, ("r", "a"): {"s"}}, "p", ["s"])
    assert nfa.epsilon_closure({"p"}) == {"p", "q", "r"}
    assert nfa.accepts("a") and not nfa.accepts("") and not nfa.accepts("aa")


def test_nfa_accepts_when_some_path_accepts():
    nfa = ends_with_01_nfa()
    assert nfa.accepts("1101") and not nfa.accepts("0110") and not nfa.accepts("")


def test_nfa_rejects_symbol_outside_alphabet():
    with pytest.raises(AutomatonError):
        ends_with_01_nfa().accepts("012")


# ------------------------------------------------------- subset construction ---
def test_subset_construction_equivalent_to_nfa_exhaustively():
    nfa = ends_with_01_nfa()
    dfa = subset_construction(nfa).dfa
    for n in range(11):
        for t in product("01", repeat=n):
            assert dfa.accepts(t) == nfa.accepts(t)


def test_subset_construction_with_epsilon_moves():
    nfa = NFA(["p", "q", "r"], ["a", "b"], {("p", EPSILON): {"q"}, ("q", "a"): {"r"}, ("r", "b"): {"q"}}, "p", ["r"])
    res = subset_construction(nfa)
    assert res.start_closure == {"p", "q"}
    for n in range(9):
        for t in product("ab", repeat=n):
            assert res.dfa.accepts(t) == nfa.accepts(t)


def test_empty_set_is_the_trap_state():
    nfa = NFA(["p", "q"], ["a", "b"], {("p", "a"): {"q"}}, "p", ["q"])
    d2 = subset_construction(nfa).dfa
    assert frozenset() in d2.states and d2.dead_states() == {frozenset()}


def test_powerset_minus_unreachable_equals_bfs_construction():
    nfa = ends_with_01_nfa()
    full = full_powerset_dfa(nfa)
    assert len(full.states) == 2 ** len(nfa.states)
    pruned, removed = remove_unreachable(full)
    assert set(pruned.states) == set(subset_construction(nfa).dfa.states) and removed


# ------------------------------------------------------------ minimisation ---
def test_remove_unreachable_states():
    d = DFA(["a", "b", "orphan"], ["x"], {("a", "x"): "b", ("b", "x"): "a", ("orphan", "x"): "a"}, "a", ["b"])
    smaller, removed = remove_unreachable(d)
    assert removed == ["orphan"] and smaller.states == ["a", "b"]


@pytest.mark.parametrize("copies", [1, 2, 3, 5])
def test_minimisation_collapses_bloated_dfa(copies):
    big = parity_dfa(copies)
    res = minimize(big)
    assert len(res.dfa.states) == 2 and len(big.states) == 2 * copies
    assert equivalent(big, res.dfa)[0]
    assert table_filling_class_count(big) == 2


def test_minimisation_keeps_a_minimal_dfa_unchanged():
    d = minimize(parity_dfa()).dfa
    assert len(minimize(d).dfa.states) == len(d.states)


def test_minimisation_records_merged_groups():
    res = minimize(parity_dfa(3))
    assert len(res.merged_groups) == 2 and all(len(members) == 3 for _, members in res.merged_groups)
    assert res.round_block_counts[0] == 2


def test_minimal_dfa_of_subset_dfa_is_equivalent_to_nfa():
    nfa = ends_with_01_nfa()
    mini = minimize(subset_construction(nfa).dfa).dfa
    assert len(mini.states) == 3
    for n in range(10):
        for t in product("01", repeat=n):
            assert mini.accepts(t) == nfa.accepts(t)


def test_equivalent_returns_counter_example():
    a, b = parity_dfa(), DFA(["s"], ["0", "1"], {("s", "0"): "s", ("s", "1"): "s"}, "s", ["s"])
    same, witness = equivalent(a, b)
    assert not same and a.accepts(witness) != b.accepts(witness)
