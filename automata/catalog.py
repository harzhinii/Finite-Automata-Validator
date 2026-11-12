"""
catalog.py - The list of every diagram in the project.

Both the Streamlit "Automata Visualizer" page and generate_assets.py (which writes the
PNG/SVG files for Microsoft Word) read this list, so the pictures are identical.
Each diagram is built from the real DFA/NFA objects - never drawn by hand.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .email_automata import get_email_system
from .password_automata import PasswordPolicy, get_password_system
from .pin_automata import build_card_lock_dfa, build_pin_dfa
from .visualize import dfa_to_dot, multi_dfa_to_dot, nfa_to_dot

REDUCED_POLICY = PasswordPolicy(min_len=2, max_len=3, required=("U", "D"))


@dataclass
class Diagram:
    key: str                         # file name stem
    title: str
    caption: str
    build: Callable[..., str]        # build(theme="light", dpi=None) -> DOT text
    table: Callable | None = None    # optional function returning a DataFrame (transition table)
    large: bool = False              # True for diagrams with hundreds of states


def get_catalog() -> list[Diagram]:
    pin, card = build_pin_dfa(), build_card_lock_dfa()
    pw, em = get_password_system(), get_email_system()
    small = get_password_system(REDUCED_POLICY)
    rep_n = {m: members[0][0] for m, members in pw.minimal.blocks.items()}

    items = [
        Diagram("01_pin_dfa", "PIN DFA (Σ = {D, O})",
                "Counts digits q0…q4; q4 accepts exactly four digits; qD is the rejecting trap.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(pin, theme=theme, dpi=dpi, title="PIN DFA   Σ = {D, O}", **k),
                pin.transition_table),
        Diagram("02_card_lock_dfa", "Card-lock DFA (events C, W)",
                "s_i = i consecutive wrong attempts. Accepting = card still usable; LOCK is absorbing.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(card, theme=theme, dpi=dpi, title="Card-lock DFA   events C / W", **k),
                card.transition_table),
        Diagram("03_password_component_dfas", "Password: five component DFAs side by side",
                "Four 2-state presence machines (U, L, D, S) and the length counter 0…16 with an overflow trap.",
                lambda theme="light", dpi=None, **k: multi_dfa_to_dot(pw.components, theme=theme, dpi=dpi,
                                                                     title="Password policy – five component DFAs")),
    ]
    for comp in pw.components[1:]:
        key = "password_" + comp.name.split("(")[1][0] .lower()
        items.append(Diagram(f"04_{key}_presence_dfa", comp.name,
                             "Two states: class not seen yet / seen. 'seen' is absorbing and accepting.",
                             (lambda c: lambda theme="light", dpi=None, **k: dfa_to_dot(c, theme=theme, dpi=dpi, title=c.name, show_details=True, **k))(comp),
                             comp.transition_table))
    items += [
        Diagram("05_password_length_dfa", pw.components[0].name,
                "Counts characters 0…16; the 17th character enters the overflow trap n17+.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(pw.components[0], theme=theme, dpi=dpi, title=pw.components[0].name, **k),
                pw.components[0].transition_table),
        Diagram("06_password_reduced_product_demo", "Password product DFA – small teaching instance",
                "SAME code with a reduced policy (length 2–3, classes U and D only) so the product is readable. "
                "Node label = length n and the classes seen (· = not yet).",
                lambda theme="light", dpi=None, **k: dfa_to_dot(small.product, theme=theme, dpi=dpi, label_fn=small.node_label,
                                                                rank_fn=lambda s: s[0], title="Product DFA – reduced policy (length 2–3, U and D)", **k)),
        Diagram("07_password_product_dfa_reachable", f"Password product DFA – reachable part ({len(pw.product.states)} states)",
                "Full policy. Node label = length n and the classes seen (U L D S, · = not yet). Grey dashed = can never accept.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(pw.product, theme=theme, dpi=dpi, label_fn=pw.node_label, rank_fn=lambda s: s[0],
                                                                title=f"Password product DFA – reachable part ({len(pw.product.states)} states)", **k),
                pw.product.transition_table, large=True),
        Diagram("08_password_product_dfa_minimal", f"Password product DFA after minimisation ({len(pw.minimal.dfa.states)} states)",
                "Equivalent product states merged by partition refinement. Mi = merged block (see the merge table).",
                lambda theme="light", dpi=None, **k: dfa_to_dot(pw.minimal.dfa, theme=theme, dpi=dpi, label_fn=lambda m: m, rank_fn=lambda m: rep_n[m],
                                                                title=f"Password product DFA – minimal ({len(pw.minimal.dfa.states)} states)", **k),
                pw.minimal.dfa.transition_table, large=True),
        Diagram("09_email_nfa", f"E-mail NFA ({len(em.nfa.states)} states)",
                "Dashed ε-edges leave q6: after a dot in the domain the NFA guesses 'ordinary label' (q3) or 'TLD' (q7).",
                lambda theme="light", dpi=None, **k: nfa_to_dot(em.nfa, theme=theme, dpi=dpi, title=f"E-mail NFA ({len(em.nfa.states)} states)", **k),
                em.nfa.transition_table),
        Diagram("10_email_subset_dfa", f"E-mail subset-construction DFA ({len(em.subset_pruned.states)} states)",
                "Each state is a set of NFA states. ∅ is the trap state.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(em.subset_pruned, theme=theme, dpi=dpi, show_details=True,
                                                                title=f"E-mail subset DFA ({len(em.subset_pruned.states)} states)", **k),
                em.subset_pruned.transition_table),
        Diagram("11_email_minimal_dfa", f"E-mail minimal DFA ({len(em.minimal.dfa.states)} states)",
                "After partition refinement. M0 merges the subset states listed in the table below the diagram.",
                lambda theme="light", dpi=None, **k: dfa_to_dot(em.minimal.dfa, theme=theme, dpi=dpi, show_details=True,
                                                                title=f"E-mail minimal DFA ({len(em.minimal.dfa.states)} states)", **k),
                em.minimal.dfa.transition_table),
    ]
    return items
