"""
email_automata.py - Module 3: practical e-mail format, built as a real NFA.

Language (practical subset of RFC 5322):
    local  = alnum+ ( [._-] alnum+ )*
    '@'    exactly one
    domain = label ( '.' label )* '.' tld
    label  = alnum ( [alnum-]* alnum )?          (letters, digits, INTERNAL hyphens)
    tld    = letter{2,}                           (at least two letters)
alnum = ASCII letter or digit.

Input classes (the alphabet of the NFA):
    L letter   D digit   '.'   '_'   '-'   '@'   O any other character

The NFA "guesses" at every dot in the domain whether the next label is an ordinary
label or the final TLD - that is the non-determinism (done with two ε-moves).
The pipeline is  NFA -> subset construction -> remove unreachable -> minimise.
"""
from __future__ import annotations

import string
from dataclasses import dataclass
from functools import lru_cache

from .dfa import DFA, display_char
from .minimization import MinimizationResult, minimize, remove_unreachable
from .nfa import EPSILON, NFA
from .subset_construction import SubsetResult, subset_construction

EMAIL_ALPHABET = ["L", "D", ".", "_", "-", "@", "O"]


def classify_email_char(ch: str) -> str:
    if ch in string.ascii_letters:
        return "L"
    if ch in string.digits:
        return "D"
    if ch in "._-@":
        return ch
    return "O"


# --------------------------------------------------------------- the NFA ---
# (source, symbol, target).  `EPSILON` = move without reading input.
_TRANSITIONS = [
    # local part:  alnum+ ([._-] alnum+)*
    ("q0", "L", "q1"), ("q0", "D", "q1"),
    ("q1", "L", "q1"), ("q1", "D", "q1"),
    ("q1", ".", "q2"), ("q1", "_", "q2"), ("q1", "-", "q2"),
    ("q2", "L", "q1"), ("q2", "D", "q1"),
    ("q1", "@", "q3"),
    # domain labels:  alnum ([alnum-]* alnum)?
    ("q3", "L", "q4"), ("q3", "D", "q4"),
    ("q4", "L", "q4"), ("q4", "D", "q4"),
    ("q4", "-", "q5"),
    ("q5", "L", "q4"), ("q5", "D", "q4"), ("q5", "-", "q5"),
    # a dot after a label: GUESS - ordinary label (q3) or the TLD (q7)?
    ("q4", ".", "q6"),
    ("q6", EPSILON, "q3"),
    ("q6", EPSILON, "q7"),
    # TLD: at least two letters
    ("q7", "L", "q8"), ("q8", "L", "q9"), ("q9", "L", "q9"),
]

NFA_STATE_MEANING = {
    "q0": "start: nothing read",
    "q1": "inside local part (last char is a letter/digit)",
    "q2": "just read a separator . _ - in the local part",
    "q3": "just read '@' or a domain dot: a label must start",
    "q4": "inside a domain label (last char is a letter/digit)",
    "q5": "inside a domain label, last char is a hyphen",
    "q6": "just read a dot in the domain (the guess happens here)",
    "q7": "guess: next label is the TLD (needs letters)",
    "q8": "one TLD letter read",
    "q9": "TLD has two or more letters (accepting)",
}


def build_email_nfa() -> NFA:
    delta: dict = {}
    for src, sym, dst in _TRANSITIONS:
        delta.setdefault((src, sym), set()).add(dst)
    states = [f"q{i}" for i in range(10)]
    return NFA(states, EMAIL_ALPHABET, delta, "q0", ["q9"], name="E-mail NFA", details=NFA_STATE_MEANING)


# ------------------------------------------------------------- pipeline ---
@dataclass
class EmailSystem:
    nfa: NFA
    subset: SubsetResult                 # subset construction (DFA states = sets of NFA states)
    subset_pruned: DFA                   # after removing unreachable states
    unreachable_removed: list
    minimal: MinimizationResult

    @property
    def stage_counts(self) -> dict:
        trap = lambda d: len(d.dead_states())
        return {
            "nfa_states": len(self.nfa.states),
            "subset_dfa_states": len(self.subset_pruned.states),
            "subset_dfa_states_excluding_trap": len(self.subset_pruned.states) - trap(self.subset_pruned),
            "minimal_dfa_states": len(self.minimal.dfa.states),
            "minimal_dfa_states_excluding_trap": len(self.minimal.dfa.states) - trap(self.minimal.dfa),
            "powerset_size": 2 ** len(self.nfa.states),
        }


def build_email_system() -> EmailSystem:
    nfa = build_email_nfa()
    subset = subset_construction(nfa)
    pruned, removed = remove_unreachable(subset.dfa)
    minimal = minimize(pruned, name="E-mail minimal DFA")
    return EmailSystem(nfa, subset, pruned, removed, minimal)


@lru_cache(maxsize=None)
def get_email_system() -> EmailSystem:
    return build_email_system()


# ------------------------------------------------------------ validation ---
@dataclass
class EmailResult:
    accepted: bool               # verdict of the NFA
    accepted_subset_dfa: bool
    accepted_minimal_dfa: bool
    classes: list[str]
    nfa_trace: list[dict]
    subset_end_state: str
    minimal_end_state: str
    reason: str

    @property
    def consistent(self) -> bool:
        return self.accepted == self.accepted_subset_dfa == self.accepted_minimal_dfa


def validate_email(text: str, system: EmailSystem | None = None) -> EmailResult:
    system = system or get_email_system()
    classes = [classify_email_char(c) for c in text]
    nfa_rows = system.nfa.trace(classes)
    final_set = nfa_rows[-1]["after"] if nfa_rows else system.nfa.start_set()
    accepted = bool(final_set & system.nfa.accepting)

    subset_final = system.subset_pruned.run(classes)
    min_final = system.minimal.state_map[subset_final]
    acc_subset = subset_final in system.subset_pruned.accepting
    acc_min = system.minimal.dfa.accepts(classes)

    if accepted:
        reason = "At least one NFA path ends in the accepting state q9 (valid TLD of 2+ letters)."
    else:
        dead_at = next((r for r in nfa_rows if not r["after"]), None)
        if dead_at:
            ch = text[dead_at["index"] - 1]
            reason = (f"All NFA paths died at character #{dead_at['index']} ({display_char(ch)!r}, class "
                      f"{dead_at['symbol']}): no transition allows it here.")
        else:
            reason = ("The whole input was read but no active state is accepting "
                      "(the address is incomplete, e.g. missing '@', domain or a TLD of 2+ letters).")
    return EmailResult(accepted, acc_subset, acc_min, classes, nfa_rows,
                       system.subset_pruned.label(subset_final), min_final, reason)
