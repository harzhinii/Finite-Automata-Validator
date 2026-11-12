"""
pin_automata.py - Module 1: ATM PIN DFA and Card-Lock DFA.

PIN DFA      alphabet {D, O}: D = ASCII digit 0-9, O = any other character.
             L_PIN = { w in D* : |w| = 4 }
Card-lock    alphabet {C, W}: C = correct PIN attempt, W = wrong PIN attempt.
"""
from __future__ import annotations

from dataclasses import dataclass

from .dfa import DFA, Step, display_char

PIN_ALPHABET = ["D", "O"]
CARD_ALPHABET = ["C", "W"]
PIN_LENGTH = 4


# ---------------------------------------------------------------- PIN DFA ---
def classify_pin_char(ch: str) -> str:
    """D for the ten ASCII digits, O for everything else (letters, spaces, '-', '٣' ...)."""
    return "D" if ch in "0123456789" else "O"


def build_pin_dfa() -> DFA:
    states = [f"q{i}" for i in range(PIN_LENGTH + 1)] + ["qD"]
    delta = {}
    for i in range(PIN_LENGTH + 1):
        q = f"q{i}"
        delta[(q, "D")] = f"q{i + 1}" if i < PIN_LENGTH else "qD"   # a 5th digit -> trap
        delta[(q, "O")] = "qD"                                       # non-digit  -> trap
    delta[("qD", "D")] = "qD"
    delta[("qD", "O")] = "qD"
    details = {
        "q0": "No digits read (start)",
        "q1": "One digit read",
        "q2": "Two digits read",
        "q3": "Three digits read",
        "q4": "Exactly four digits (accepting)",
        "qD": "Invalid input (trap)",
    }
    return DFA(states, PIN_ALPHABET, delta, "q0", ["q4"], name="PIN DFA",
               labels={s: s for s in states}, details=details)


@dataclass
class PinResult:
    accepted: bool
    final_state: str
    length: int
    reason: str
    steps: list[dict]        # rows for the transition trace


def validate_pin(text: str, dfa: DFA | None = None) -> PinResult:
    """Run the PIN DFA over `text` and explain the result from the recorded trace."""
    dfa = dfa or build_pin_dfa()
    symbols = [classify_pin_char(c) for c in text]
    trace: list[Step] = dfa.trace(symbols)
    final = trace[-1].target if trace else dfa.start
    rows = [{
        "Step": s.index, "Character": display_char(text[s.index - 1]), "Class": s.symbol,
        "From": s.source, "To": s.target,
    } for s in trace]

    accepted = final in dfa.accepting
    if accepted:
        reason = "Exactly four digits were read."
    elif final == "qD":
        first_trap = next(s for s in trace if s.target == "qD")
        if first_trap.symbol == "O":
            reason = f"Character #{first_trap.index} is not a digit, so the DFA entered the trap state qD."
        else:
            reason = f"A fifth digit (character #{first_trap.index}) was read, so the DFA entered the trap state qD."
    elif not text:
        reason = "The input is empty: the DFA stays in q0 (no digits read)."
    else:
        reason = f"Only {len(text)} digit(s) were read; exactly four are required."
    return PinResult(accepted, final, len(text), reason, rows)


# -------------------------------------------------------------- Card lock ---
def build_card_lock_dfa() -> DFA:
    """
    s_i = i consecutive wrong attempts.  C resets to s0, W advances, third W -> LOCK.
    LOCK is absorbing.  'Accepting' = the card is still usable (not locked), as in Table 3
    of the report.  The external reset is NOT an input symbol of this DFA.
    """
    states = ["s0", "s1", "s2", "LOCK"]
    delta = {
        ("s0", "C"): "s0", ("s0", "W"): "s1",
        ("s1", "C"): "s0", ("s1", "W"): "s2",
        ("s2", "C"): "s0", ("s2", "W"): "LOCK",
        ("LOCK", "C"): "LOCK", ("LOCK", "W"): "LOCK",
    }
    details = {
        "s0": "0 consecutive wrong attempts",
        "s1": "1 consecutive wrong attempt",
        "s2": "2 consecutive wrong attempts",
        "LOCK": "Card locked (needs external reset)",
    }
    return DFA(states, CARD_ALPHABET, delta, "s0", ["s0", "s1", "s2"], name="Card-lock DFA",
               labels={s: s for s in states}, details=details)


class CardLock:
    """A card whose behaviour is driven by the card-lock DFA, plus the external reset."""

    def __init__(self) -> None:
        self.dfa = build_card_lock_dfa()
        self.state = self.dfa.start
        self.history: list[dict] = []

    @property
    def locked(self) -> bool:
        return self.state not in self.dfa.accepting

    def apply(self, event: str) -> str:
        """Feed one event ('C' or 'W') and return the new state."""
        before = self.state
        self.state = self.dfa.step(before, event)
        self.history.append({
            "#": len(self.history) + 1, "Event": event, "From": before, "To": self.state,
            "Card": "LOCKED" if self.locked else "usable",
        })
        return self.state

    def reset(self) -> None:
        """External unlock/reset (an administrative operation, not a DFA input)."""
        before = self.state
        self.state = self.dfa.start
        self.history.append({
            "#": len(self.history) + 1, "Event": "RESET (external)", "From": before,
            "To": self.state, "Card": "usable",
        })


def run_card_events(events: str | list[str]) -> list[str]:
    """States visited while reading the events, starting with the start state."""
    dfa = build_card_lock_dfa()
    states = [dfa.start]
    for e in events:
        states.append(dfa.step(states[-1], e))
    return states


def card_usable(events: str | list[str]) -> bool:
    return run_card_events(events)[-1] != "LOCK"
