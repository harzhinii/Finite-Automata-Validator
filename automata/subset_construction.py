"""
subset_construction.py - Convert an NFA into an equivalent DFA.

Rules (as in the report):
  * the DFA start state is the ε-closure of the NFA start state;
  * every DFA state is a SET of NFA states;
  * on symbol a, a set S goes to  ε-closure( move(S, a) );
  * the empty set ∅ becomes the (rejecting) trap state;
  * a set is accepting if it contains an accepting NFA state.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import chain, combinations

from .dfa import DFA, format_state
from .nfa import NFA


@dataclass
class SubsetResult:
    dfa: DFA
    rows: list[dict]          # one row per (DFA state, symbol): move, closure, target
    names: dict               # frozenset -> "S0", "S1", ...
    start_closure: frozenset


def subset_construction(nfa: NFA, name: str | None = None) -> SubsetResult:
    """Breadth-first subset construction; only reachable subsets are created."""
    start = nfa.start_set()
    names: dict = {start: "S0"}
    order, queue = [start], deque([start])
    delta, rows = {}, []
    counter = 1

    while queue:
        subset = queue.popleft()
        for a in nfa.alphabet:
            moved = nfa.move(subset, a)
            target = nfa.epsilon_closure(moved)
            if target not in names:
                if target:
                    names[target] = f"S{counter}"
                    counter += 1
                else:
                    names[target] = "∅"
                order.append(target)
                queue.append(target)
            delta[(subset, a)] = target
            rows.append({
                "DFA state": names[subset],
                "NFA subset": format_state(subset),
                "Symbol": a,
                "move(S, a)": format_state(moved),
                "ε-closure": format_state(target),
                "Goes to": names[target],
            })

    accepting = [s for s in order if s & nfa.accepting]
    details = {s: format_state(s) + (" (trap)" if not s else "") for s in order}
    dfa = DFA(order, nfa.alphabet, delta, start, accepting,
              name=name or f"Subset DFA of {nfa.name}", labels=names, details=details)
    return SubsetResult(dfa=dfa, rows=rows, names=names, start_closure=start)


def full_powerset_dfa(nfa: NFA) -> DFA:
    """
    The NAIVE construction: one DFA state for each of the 2^n subsets of NFA states
    (reachable or not).  Used to show how many states `remove_unreachable` discards.
    """
    n = len(nfa.states)
    subsets = [frozenset(c) for c in chain.from_iterable(combinations(nfa.states, k) for k in range(n + 1))]
    delta = {(s, a): nfa.epsilon_closure(nfa.move(s, a)) for s in subsets for a in nfa.alphabet}
    # In the naive version the start state is the ε-closure of the start state.
    # Non-ε-closed subsets can still appear in the list; they are simply unreachable.
    accepting = [s for s in subsets if s & nfa.accepting]
    return DFA(subsets, nfa.alphabet, delta, nfa.start_set(), accepting, name=f"Power-set DFA of {nfa.name}")
