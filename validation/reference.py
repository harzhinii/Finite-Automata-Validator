"""
reference.py - INDEPENDENT reference validators.

These functions do NOT use any automaton code.  They are plain Python written directly
from the written rules, and are used only to cross-check the automata
(a machine must not be tested only against itself).
"""
from __future__ import annotations

import string
from collections import deque

# ------------------------------------------------------------------ PIN ---
def ref_pin(text: str) -> bool:
    """Exactly four ASCII decimal digits."""
    return len(text) == 4 and text.isascii() and text.isdigit()


# ------------------------------------------------------------ card lock ---
def ref_card_state(events: str) -> str:
    """
    Closed-form rule: the card is locked iff the event sequence contains three W in a
    row ('WWW').  Otherwise the state is s<k>, k = length of the trailing run of W's.
    """
    events = "".join(events)
    if "WWW" in events:
        return "LOCK"
    trailing = len(events) - len(events.rstrip("W"))
    return f"s{trailing}"


# ------------------------------------------------------------- password ---
def ref_password(text: str) -> bool:
    """8..16 characters with at least one of each: A-Z, a-z, 0-9, ASCII punctuation."""
    if not 8 <= len(text) <= 16:
        return False
    return (any(c in string.ascii_uppercase for c in text)
            and any(c in string.ascii_lowercase for c in text)
            and any(c in string.digits for c in text)
            and any(c in string.punctuation for c in text))


# --------------------------------------------------------------- e-mail ---
_ALNUM = set(string.ascii_letters + string.digits)
_LETTERS = set(string.ascii_letters)


def _local_ok(local: str) -> bool:
    """alnum+ ( [._-] alnum+ )*  parsed run by run."""
    i, n = 0, len(local)
    while True:
        j = i
        while j < n and local[j] in _ALNUM:
            j += 1
        if j == i:                      # an alnum run must not be empty
            return False
        if j == n:
            return True
        if local[j] not in "._-":
            return False
        i = j + 1                       # a separator must be followed by another run


def _label_ok(label: str) -> bool:
    return (len(label) >= 1 and label[0] in _ALNUM and label[-1] in _ALNUM
            and all(c in _ALNUM or c == "-" for c in label))


def ref_email(text: str) -> bool:
    if text.count("@") != 1:
        return False
    local, domain = text.split("@")
    if not _local_ok(local):
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    *front, tld = labels
    return all(_label_ok(x) for x in front) and len(tld) >= 2 and all(c in _LETTERS for c in tld)


# --------------------------------------------- independent minimisation ---
def table_filling_class_count(dfa) -> int:
    """
    Number of equivalence classes of REACHABLE states, found with the classical
    table-filling (Myhill-Nerode) algorithm - a different method from partition
    refinement, used to double-check the size of every minimal DFA.
    """
    states = dfa.reachable_states()
    index = {q: i for i, q in enumerate(states)}
    n = len(states)
    marked = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(i):
            if (states[i] in dfa.accepting) != (states[j] in dfa.accepting):
                marked[i][j] = True
    changed = True
    while changed:
        changed = False
        for i in range(n):
            for j in range(i):
                if marked[i][j]:
                    continue
                for a in dfa.alphabet:
                    p, q = index[dfa.delta[(states[i], a)]], index[dfa.delta[(states[j], a)]]
                    if p != q and marked[max(p, q)][min(p, q)]:
                        marked[i][j] = changed = True
                        break
    # unmarked pairs = equivalent; count classes with a tiny union-find
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i):
            if not marked[i][j]:
                parent[find(i)] = find(j)
    return len({find(i) for i in range(n)})
