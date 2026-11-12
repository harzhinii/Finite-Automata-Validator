"""
stats.py - Every state count shown anywhere in the project comes from this module,
which measures the real objects.  Nothing is typed in by hand.
"""
from __future__ import annotations

from .email_automata import get_email_system
from .password_automata import get_password_system
from .pin_automata import build_card_lock_dfa, build_pin_dfa


def collect_state_counts() -> dict:
    pin, card = build_pin_dfa(), build_card_lock_dfa()
    pw = get_password_system()
    em = get_email_system()
    ec = em.stage_counts
    return {
        "pin_dfa": {"states": len(pin.states), "accepting": sorted(pin.accepting),
                    "trap_states": sorted(map(str, pin.dead_states()))},
        "card_lock_dfa": {"states": len(card.states), "accepting_(card_usable)": sorted(card.accepting),
                          "trap_states": sorted(map(str, card.dead_states()))},
        "password": {
            "components": {d.name: len(d.states) for d in pw.components},
            "five_components_total": pw.component_total,
            "product_cartesian_size": pw.product.meta["cartesian_size"],
            "product_reachable": len(pw.product.states),
            "product_minimal": len(pw.minimal.dfa.states),
            "minimisation_rounds_block_counts": pw.minimal.round_block_counts,
            "merged_blocks": len(pw.minimal.merged_groups),
            "design_table": pw.design_table().to_dict(orient="records"),
        },
        "email": {
            "nfa_states": ec["nfa_states"],
            "nfa_epsilon_transitions": len(em.nfa.epsilon_transitions()),
            "naive_powerset_size": ec["powerset_size"],
            "unreachable_states_removed_after_bfs_construction": len(em.unreachable_removed),
            "subset_dfa_states_including_trap": ec["subset_dfa_states"],
            "subset_dfa_states_excluding_trap": ec["subset_dfa_states_excluding_trap"],
            "minimal_dfa_states_including_trap": ec["minimal_dfa_states"],
            "minimal_dfa_states_excluding_trap": ec["minimal_dfa_states_excluding_trap"],
            "minimisation_rounds_block_counts": em.minimal.round_block_counts,
            "merged_groups": [{"minimal_state": m, "merged_subset_dfa_states": g} for m, g in em.minimal.merged_groups],
            "subset_state_names": {em.subset.names[s]: sorted(s) for s in em.subset.dfa.states},
        },
    }
