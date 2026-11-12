"""
dfa.py - A small, generic Deterministic Finite Automaton (DFA) class.

A DFA is a 5-tuple  M = (Q, Sigma, delta, q0, F):
    Q      - finite set of states
    Sigma  - input alphabet (here: *classes* of characters such as D, O, U, L ...)
    delta  - transition function  Q x Sigma -> Q   (must be TOTAL: no missing entries)
    q0     - start state
    F      - set of accepting states

The same class is used for every deterministic machine in the project
(PIN, card lock, password components, product DFA, subset DFA, minimal DFA).
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from math import prod
from typing import Any, Hashable, Iterable, Sequence

import pandas as pd


class AutomatonError(ValueError):
    """Raised when an automaton is built or used incorrectly."""


# --------------------------------------------------------------------------
# Small helpers shared by all modules
# --------------------------------------------------------------------------
def _natural_key(text: str):
    """Sort 'q2' before 'q10' (natural order)."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def format_state(state: Any) -> str:
    """Readable text for a state: sets look like {q1,q2}, tuples like (3,1,0)."""
    if isinstance(state, frozenset):
        if not state:
            return "∅"
        return "{" + ",".join(sorted((format_state(s) for s in state), key=_natural_key)) + "}"
    if isinstance(state, tuple):
        return "(" + ",".join(format_state(s) for s in state) + ")"
    return str(state)


def display_char(ch: str) -> str:
    """Make invisible characters visible in tables (space -> '␠')."""
    if ch == " ":
        return "␠"
    if ch == "\t":
        return "⇥"
    if ch.isprintable():
        return ch
    return repr(ch)[1:-1]


@dataclass(frozen=True)
class Step:
    """One move of a DFA: read `symbol` in `source` and arrive in `target`."""

    index: int          # 1-based position in the input
    symbol: str
    source: Hashable
    target: Hashable


# --------------------------------------------------------------------------
# The DFA class
# --------------------------------------------------------------------------
class DFA:
    def __init__(
        self,
        states: Iterable[Hashable],
        alphabet: Sequence[str],
        delta: dict,
        start: Hashable,
        accepting: Iterable[Hashable],
        name: str = "DFA",
        labels: dict | None = None,
        details: dict | None = None,
    ):
        self.states = list(states)
        self.alphabet = list(alphabet)
        self.delta = dict(delta)
        self.start = start
        self.accepting = set(accepting)
        self.name = name
        self.labels = dict(labels or {})     # state -> short display name
        self.details = dict(details or {})   # state -> longer explanation
        self.meta: dict = {}                 # free-form extra facts (e.g. cartesian size)
        self._validate()

    # ---- construction check ---------------------------------------------
    def _validate(self) -> None:
        if len(set(self.states)) != len(self.states):
            raise AutomatonError(f"{self.name}: duplicate states")
        known = set(self.states)
        if self.start not in known:
            raise AutomatonError(f"{self.name}: start state not in Q")
        if not self.accepting <= known:
            raise AutomatonError(f"{self.name}: accepting states not in Q")
        for q in self.states:
            for a in self.alphabet:
                if (q, a) not in self.delta:
                    raise AutomatonError(f"{self.name}: missing transition ({format_state(q)}, {a})")
                if self.delta[(q, a)] not in known:
                    raise AutomatonError(f"{self.name}: transition leaves Q")

    # ---- naming -----------------------------------------------------------
    def label(self, state: Hashable) -> str:
        return self.labels.get(state, format_state(state))

    def detail(self, state: Hashable) -> str:
        return self.details.get(state, "")

    # ---- running ----------------------------------------------------------
    def step(self, state: Hashable, symbol: str) -> Hashable:
        if symbol not in self.alphabet:
            raise AutomatonError(f"{self.name}: symbol {symbol!r} is not in the alphabet {self.alphabet}")
        return self.delta[(state, symbol)]

    def trace(self, symbols: Iterable[str]) -> list[Step]:
        """Return every transition taken while reading `symbols`."""
        steps, state = [], self.start
        for i, sym in enumerate(symbols, start=1):
            nxt = self.step(state, sym)
            steps.append(Step(i, sym, state, nxt))
            state = nxt
        return steps

    def run(self, symbols: Iterable[str]) -> Hashable:
        state = self.start
        for sym in symbols:
            state = self.step(state, sym)
        return state

    def accepts(self, symbols: Iterable[str]) -> bool:
        return self.run(symbols) in self.accepting

    # ---- graph facts --------------------------------------------------------
    def reachable_states(self) -> list:
        """States reachable from the start state (breadth-first order)."""
        seen, order, queue = {self.start}, [self.start], deque([self.start])
        while queue:
            q = queue.popleft()
            for a in self.alphabet:
                t = self.delta[(q, a)]
                if t not in seen:
                    seen.add(t)
                    order.append(t)
                    queue.append(t)
        return order

    def dead_states(self) -> set:
        """Trap / dead states: from them no accepting state can ever be reached."""
        reverse: dict = {q: set() for q in self.states}
        for (q, _a), t in self.delta.items():
            reverse[t].add(q)
        alive, queue = set(self.accepting), deque(self.accepting)
        while queue:
            t = queue.popleft()
            for q in reverse[t]:
                if q not in alive:
                    alive.add(q)
                    queue.append(q)
        return set(self.states) - alive

    # ---- tables --------------------------------------------------------------
    def transition_table(self) -> pd.DataFrame:
        rows = []
        for q in self.states:
            marks = ("→" if q == self.start else "") + ("*" if q in self.accepting else "")
            row = {"State": self.label(q), "Start/Accept": marks}
            for a in self.alphabet:
                row[f"on {a}"] = self.label(self.delta[(q, a)])
            if self.detail(q):
                row["Meaning"] = self.detail(q)
            rows.append(row)
        return pd.DataFrame(rows)

    # ---- product construction -------------------------------------------------
    @classmethod
    def product(cls, dfas: Sequence["DFA"], rule: str = "all", name: str = "Product DFA") -> "DFA":
        """
        Product construction.  A product state is a tuple (q1, q2, ..., qk) holding the
        current state of every component.  Only states REACHABLE from the start tuple are
        created (breadth-first exploration).

        rule="all" -> accept when EVERY component accepts  (intersection of languages)
        rule="any" -> accept when SOME component accepts   (union of languages)
        """
        if rule not in ("all", "any"):
            raise AutomatonError("rule must be 'all' or 'any'")
        alphabet = dfas[0].alphabet
        for d in dfas:
            if set(d.alphabet) != set(alphabet):
                raise AutomatonError("all component DFAs must share one alphabet")
        start = tuple(d.start for d in dfas)
        order, seen, queue, delta = [start], {start}, deque([start]), {}
        while queue:
            s = queue.popleft()
            for a in alphabet:
                t = tuple(d.delta[(c, a)] for d, c in zip(dfas, s))
                delta[(s, a)] = t
                if t not in seen:
                    seen.add(t)
                    order.append(t)
                    queue.append(t)
        check = all if rule == "all" else any
        accepting = [s for s in order if check(c in d.accepting for d, c in zip(dfas, s))]
        result = cls(order, alphabet, delta, start, accepting, name=name)
        result.meta["cartesian_size"] = prod(len(d.states) for d in dfas)
        result.meta["component_sizes"] = [len(d.states) for d in dfas]
        return result


# --------------------------------------------------------------------------
# Equivalence of two DFAs (used by the tests and the "equivalence" checks)
# --------------------------------------------------------------------------
def equivalent(a: DFA, b: DFA) -> tuple[bool, list[str] | None]:
    """
    Decide whether two DFAs accept exactly the same language.
    Explore pairs of states (p, q) together; if some reachable pair has one
    accepting and one rejecting component, the languages differ and the path
    to that pair is a counter-example string.
    Returns (True, None) or (False, counter_example_symbols).
    """
    if set(a.alphabet) != set(b.alphabet):
        raise AutomatonError("alphabets differ")
    start = (a.start, b.start)
    seen, queue = {start: []}, deque([start])
    while queue:
        p, q = queue.popleft()
        if (p in a.accepting) != (q in b.accepting):
            return False, seen[(p, q)]
        for sym in a.alphabet:
            nxt = (a.delta[(p, sym)], b.delta[(q, sym)])
            if nxt not in seen:
                seen[nxt] = seen[(p, q)] + [sym]
                queue.append(nxt)
    return True, None
