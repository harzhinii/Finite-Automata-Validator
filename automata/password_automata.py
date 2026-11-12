"""
password_automata.py - Module 2: password policy as an INTERSECTION of regular languages.

Alphabet  Sigma = {U, L, D, S, O}
    U upper-case ASCII letter      L lower-case ASCII letter      D ASCII digit
    S printable ASCII punctuation  O anything else (space, non-ASCII, control ...)

    L(policy) = L_U ∩ L_L ∩ L_D ∩ L_S ∩ L_len

Five small component DFAs (four 2-state "presence" machines + one length counter) are
combined by the PRODUCT construction into one DFA whose states are tuples
(n, u, l, d, s):   n = characters read so far (capped at max+1),  u,l,d,s = class seen?
The product is then minimised by partition refinement.
Every number shown in the application is computed from these objects.
"""
from __future__ import annotations

import string
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from .dfa import DFA
from .minimization import MinimizationResult, minimize

PW_ALPHABET = ["U", "L", "D", "S", "O"]
CLASS_NAMES = {"U": "uppercase letter", "L": "lowercase letter", "D": "digit", "S": "special character"}


def classify_password_char(ch: str) -> str:
    if "A" <= ch <= "Z":
        return "U"
    if "a" <= ch <= "z":
        return "L"
    if "0" <= ch <= "9":
        return "D"
    if ch in string.punctuation:          # the 32 printable ASCII punctuation marks
        return "S"
    return "O"


@dataclass(frozen=True)
class PasswordPolicy:
    min_len: int = 8
    max_len: int = 16
    required: tuple = ("U", "L", "D", "S")      # classes that must each appear at least once


# ------------------------------------------------------------ components ---
def build_presence_dfa(cls: str) -> DFA:
    """Two states: 0 = class not seen yet, 1 = seen (absorbing).  Accepting: 1."""
    low = cls.lower()
    delta = {}
    for a in PW_ALPHABET:
        delta[(0, a)] = 1 if a == cls else 0
        delta[(1, a)] = 1
    return DFA([0, 1], PW_ALPHABET, delta, 0, [1], name=f"Has {CLASS_NAMES[cls]} ({cls})",
               labels={0: f"{low}0", 1: f"{low}1"},
               details={0: f"no {cls} yet", 1: f"{cls} seen"})


def build_length_dfa(min_len: int, max_len: int) -> DFA:
    """Counts 0..max_len; the (max_len+1)-th character moves to the overflow trap."""
    states = list(range(max_len + 2))
    overflow = max_len + 1
    delta = {(n, a): min(n + 1, overflow) for n in states for a in PW_ALPHABET}
    labels = {n: f"n{n}" for n in states}
    labels[overflow] = f"n{overflow}+"
    details = {n: f"{n} character(s) read" for n in states}
    details[overflow] = f"more than {max_len} characters (trap)"
    return DFA(states, PW_ALPHABET, delta, 0, range(min_len, max_len + 1),
               name=f"Length {min_len}–{max_len}", labels=labels, details=details)


# ---------------------------------------------------------------- system ---
@dataclass
class PasswordSystem:
    policy: PasswordPolicy
    components: list[DFA]            # [length, then one presence DFA per required class]
    product: DFA                     # reachable part of the product construction
    minimal: MinimizationResult
    required: tuple = field(default_factory=tuple)

    # ---- state counts (always computed from the real objects) --------------
    @property
    def component_total(self) -> int:
        return sum(len(d.states) for d in self.components)

    def design_table(self) -> pd.DataFrame:
        sizes = " + ".join(str(len(d.states)) for d in self.components)
        cart = self.product.meta["cartesian_size"]
        rows = [
            {"Design": "Five component DFAs side by side" if len(self.components) == 5
             else f"{len(self.components)} component DFAs side by side",
             "States": self.component_total,
             "Comment": f"{sizes} states; one rule = one machine, easy to change"},
            {"Design": "Product DFA (reachable part)",
             "States": len(self.product.states),
             "Comment": f"{len(self.product.states)} of {cart} possible tuples are reachable; the single machine the theory promises"},
            {"Design": "Product DFA after minimisation",
             "States": len(self.minimal.dfa.states),
             "Comment": f"Equivalent states merged ({len(self.product.states) - len(self.minimal.dfa.states)} fewer states)"},
        ]
        return pd.DataFrame(rows)

    def node_label(self, state: tuple) -> str:
        """Compact diagram label for a product state, e.g. '3\\nU·D·'."""
        n, flags = state[0], state[1:]
        suffix = "+" if n > self.policy.max_len else ""
        letters = "".join(c if f else "·" for c, f in zip(self.required, flags))
        return f"{n}{suffix}\n{letters}"

    def describe_state(self, state: tuple) -> dict:
        n, flags = state[0], state[1:]
        return {
            "length n": f"{n}" + ("+ (too long)" if n > self.policy.max_len else ""),
            **{f"{c} seen ({CLASS_NAMES[c]})": bool(f) for c, f in zip(self.required, flags)},
            "accepting": state in self.product.accepting,
        }


def build_password_system(policy: PasswordPolicy = PasswordPolicy()) -> PasswordSystem:
    components = [build_length_dfa(policy.min_len, policy.max_len)] + [build_presence_dfa(c) for c in policy.required]
    product = DFA.product(components, rule="all", name="Password product DFA")
    minimal = minimize(product, name="Password product DFA (minimal)")
    return PasswordSystem(policy, components, product, minimal, tuple(policy.required))


@lru_cache(maxsize=None)
def get_password_system(policy: PasswordPolicy = PasswordPolicy()) -> PasswordSystem:
    return build_password_system(policy)


# ------------------------------------------------------------ validation ---
@dataclass
class PasswordResult:
    accepted: bool
    length: int
    classes: list[str]
    final_state: tuple
    minimal_state: str
    requirements: list[tuple]    # (description, satisfied)
    missing: list[str]
    steps: list[dict]
    consistent: bool             # product DFA and minimal DFA agree


def validate_password(text: str, system: PasswordSystem | None = None) -> PasswordResult:
    """Run the product DFA over `text`.  Requirement flags are read from the FINAL product state."""
    system = system or get_password_system()
    pol = system.policy
    classes = [classify_password_char(c) for c in text]
    trace = system.product.trace(classes)
    final = trace[-1].target if trace else system.product.start

    n, flags = final[0], final[1:]
    requirements, missing = [], []
    len_ok = pol.min_len <= n <= pol.max_len
    len_text = f"Length {pol.min_len}–{pol.max_len} characters"
    requirements.append((len_text, len_ok))
    if not len_ok:
        missing.append(f"{len_text} (currently {len(text)})")
    for c, f in zip(system.required, flags):
        requirements.append((f"At least one {CLASS_NAMES[c]} ({c})", bool(f)))
        if not f:
            missing.append(f"At least one {CLASS_NAMES[c]} ({c})")

    steps = [{"Step": s.index, "Class": s.symbol, "Product state (n,u,l,d,s)": system.product.label(s.target),
              "Minimal DFA state": system.minimal.state_map[s.target]} for s in trace]
    accepted = final in system.product.accepting
    min_accept = system.minimal.dfa.accepts(classes)
    return PasswordResult(accepted, len(text), classes, final, system.minimal.state_map[final],
                          requirements, missing, steps, accepted == min_accept)
