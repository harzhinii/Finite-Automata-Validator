"""
nfa.py - A Nondeterministic Finite Automaton with epsilon (ε) transitions.

delta maps (state, symbol) -> SET of next states.  The special symbol EPSILON
means "move without reading any input".  A string is accepted if at least one
path ends in an accepting state after the whole input has been read.
"""
from __future__ import annotations

from typing import Hashable, Iterable, Sequence

import pandas as pd

from .dfa import AutomatonError, format_state

EPSILON = "ε"


class NFA:
    def __init__(
        self,
        states: Iterable[Hashable],
        alphabet: Sequence[str],
        delta: dict,
        start: Hashable,
        accepting: Iterable[Hashable],
        name: str = "NFA",
        details: dict | None = None,
    ):
        self.states = list(states)
        self.alphabet = list(alphabet)          # never contains EPSILON
        self.delta = {k: frozenset(v) for k, v in delta.items()}
        self.start = start
        self.accepting = set(accepting)
        self.name = name
        self.details = dict(details or {})
        self._validate()

    def _validate(self) -> None:
        known = set(self.states)
        if EPSILON in self.alphabet:
            raise AutomatonError("EPSILON must not be part of the alphabet")
        if self.start not in known or not self.accepting <= known:
            raise AutomatonError(f"{self.name}: start/accepting states must belong to Q")
        for (q, a), targets in self.delta.items():
            if q not in known or not targets <= known:
                raise AutomatonError(f"{self.name}: transition uses an unknown state")
            if a != EPSILON and a not in self.alphabet:
                raise AutomatonError(f"{self.name}: symbol {a!r} not in alphabet")

    # ---- the two basic operations -------------------------------------------
    def epsilon_closure(self, states: Iterable[Hashable]) -> frozenset:
        """All states reachable from `states` using only ε-moves (including themselves)."""
        closure, stack = set(states), list(states)
        while stack:
            q = stack.pop()
            for t in self.delta.get((q, EPSILON), ()):
                if t not in closure:
                    closure.add(t)
                    stack.append(t)
        return frozenset(closure)

    def move(self, states: Iterable[Hashable], symbol: str) -> frozenset:
        """States reachable by reading exactly one `symbol` (before taking ε-closure)."""
        out: set = set()
        for q in states:
            out |= self.delta.get((q, symbol), frozenset())
        return frozenset(out)

    def next_set(self, states: Iterable[Hashable], symbol: str) -> frozenset:
        return self.epsilon_closure(self.move(states, symbol))

    def start_set(self) -> frozenset:
        return self.epsilon_closure({self.start})

    # ---- running ----------------------------------------------------------
    def trace(self, symbols: Iterable[str]) -> list[dict]:
        """Set-of-active-states after every symbol (shows the 'guessing' of the NFA)."""
        current, rows = self.start_set(), []
        for i, sym in enumerate(symbols, start=1):
            if sym not in self.alphabet:
                raise AutomatonError(f"{self.name}: symbol {sym!r} is not in the alphabet")
            moved = self.move(current, sym)
            closed = self.epsilon_closure(moved)
            rows.append({"index": i, "symbol": sym, "before": current, "moved": moved, "after": closed})
            current = closed
        return rows

    def run(self, symbols: Iterable[str]) -> frozenset:
        current = self.start_set()
        for sym in symbols:
            if sym not in self.alphabet:
                raise AutomatonError(f"{self.name}: symbol {sym!r} is not in the alphabet")
            current = self.next_set(current, sym)
        return current

    def accepts(self, symbols: Iterable[str]) -> bool:
        return bool(self.run(symbols) & self.accepting)

    # ---- facts / tables -------------------------------------------------------
    def epsilon_transitions(self) -> list[tuple]:
        return sorted(
            ((q, t) for (q, a), ts in self.delta.items() if a == EPSILON for t in ts),
            key=lambda x: (format_state(x[0]), format_state(x[1])),
        )

    def transition_table(self) -> pd.DataFrame:
        rows = []
        for q in self.states:
            marks = ("→" if q == self.start else "") + ("*" if q in self.accepting else "")
            row = {"State": format_state(q), "Start/Accept": marks}
            for a in self.alphabet + [EPSILON]:
                targets = self.delta.get((q, a), frozenset())
                row[f"on {a}"] = format_state(targets) if targets else "–"
            if q in self.details:
                row["Meaning"] = self.details[q]
            rows.append(row)
        return pd.DataFrame(rows)
