"""
minimization.py - Remove unreachable states and minimise a DFA by PARTITION REFINEMENT
(Moore's algorithm).

Idea: two states are *equivalent* if no input string can tell them apart (every string
leads both to accepting, or both to rejecting).  We start with two blocks
{accepting} and {non-accepting} and keep splitting a block whenever two of its states
send some symbol into different blocks.  When nothing splits any more, every block is a
set of equivalent states and becomes ONE state of the minimal DFA.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .dfa import DFA


@dataclass
class MinimizationResult:
    dfa: DFA                       # the minimal DFA (states M0, M1, ...)
    input_states: int              # states of the DFA given to `minimize`
    unreachable_removed: list      # states dropped because they cannot be reached
    reachable_states: int
    round_block_counts: list[int]  # number of blocks after round 0, 1, 2, ...
    blocks: dict                   # "M3" -> list of ORIGINAL states merged into it
    state_map: dict                # original state -> "M3"
    merged_groups: list[tuple]     # [(new_label, [original labels...])] for blocks with >1 state


def remove_unreachable(dfa: DFA) -> tuple[DFA, list]:
    """Return (smaller DFA, list_of_removed_states)."""
    keep = dfa.reachable_states()
    keep_set = set(keep)
    removed = [q for q in dfa.states if q not in keep_set]
    if not removed:
        return dfa, []
    delta = {(q, a): dfa.delta[(q, a)] for q in keep for a in dfa.alphabet}
    new = DFA(keep, dfa.alphabet, delta, dfa.start, dfa.accepting & keep_set, name=dfa.name,
              labels={q: dfa.labels[q] for q in keep if q in dfa.labels},
              details={q: dfa.details[q] for q in keep if q in dfa.details})
    new.meta = dict(dfa.meta)
    return new, removed


def _short(items: list[str], limit: int = 4) -> str:
    if len(items) <= limit:
        return " ≡ ".join(items)
    return " ≡ ".join(items[:limit - 1]) + f" ≡ … (+{len(items) - limit + 1} more)"


def minimize(dfa: DFA, name: str | None = None) -> MinimizationResult:
    reduced, removed = remove_unreachable(dfa)
    states, alphabet = reduced.states, reduced.alphabet

    # Round 0: split into accepting / non-accepting.
    block_of = {q: (0 if q in reduced.accepting else 1) for q in states}
    counts = [len(set(block_of.values()))]

    while True:
        # Signature = (my block, block reached on each symbol).  Same signature => not yet split.
        signature = {q: (block_of[q], tuple(block_of[reduced.delta[(q, a)]] for a in alphabet)) for q in states}
        numbering: dict = {}
        new_block = {}
        for q in states:
            new_block[q] = numbering.setdefault(signature[q], len(numbering))
        if len(numbering) == counts[-1]:       # nothing split -> stable
            block_of = new_block
            break
        block_of = new_block
        counts.append(len(numbering))

    # Name the blocks M0, M1, ... in breadth-first order from the start block.
    rep: dict = {}
    for q in states:
        rep.setdefault(block_of[q], q)
    names: dict = {block_of[reduced.start]: "M0"}
    queue = deque([block_of[reduced.start]])
    order = [block_of[reduced.start]]
    while queue:
        b = queue.popleft()
        for a in alphabet:
            nb = block_of[reduced.delta[(rep[b], a)]]
            if nb not in names:
                names[nb] = f"M{len(names)}"
                order.append(nb)
                queue.append(nb)

    members: dict = {names[b]: [] for b in order}
    for q in states:
        members[names[block_of[q]]].append(q)

    new_states = [names[b] for b in order]
    delta = {(names[b], a): names[block_of[reduced.delta[(rep[b], a)]]] for b in order for a in alphabet}
    accepting = [names[b] for b in order if rep[b] in reduced.accepting]
    details = {m: _short([reduced.label(q) for q in qs]) for m, qs in members.items()}
    min_dfa = DFA(new_states, alphabet, delta, "M0", accepting,
                  name=name or f"Minimal {dfa.name}", labels={m: m for m in new_states}, details=details)
    merged = [(m, [reduced.label(q) for q in qs]) for m, qs in members.items() if len(qs) > 1]
    return MinimizationResult(
        dfa=min_dfa,
        input_states=len(dfa.states),
        unreachable_removed=removed,
        reachable_states=len(reduced.states),
        round_block_counts=counts,
        blocks=members,
        state_map={q: names[block_of[q]] for q in states},
        merged_groups=merged,
    )
