import pandas as pd
import streamlit as st

from automata.dfa import display_char, format_state
from automata.email_automata import get_email_system, validate_email
from automata.visualize import dfa_to_dot
from ui.common import show_diagram, show_table, verdict


def counts_table(system) -> pd.DataFrame:
    c = system.stage_counts
    return pd.DataFrame([
        {"Stage": "NFA", "States": c["nfa_states"], "Comment": f"{len(system.nfa.epsilon_transitions())} ε-transitions (the dot-guess)"},
        {"Stage": "Subset DFA (reachable)", "States": c["subset_dfa_states"],
         "Comment": f"{c['subset_dfa_states_excluding_trap']} + trap ∅; naive power set would have {c['powerset_size']}"},
        {"Stage": "Minimal DFA", "States": c["minimal_dfa_states"],
         "Comment": f"{c['minimal_dfa_states_excluding_trap']} + trap; " + (
             "; ".join(f"{m} = {' ≡ '.join(g)}" for m, g in system.minimal.merged_groups) or "nothing merged")},
    ])


def render() -> None:
    st.title("E-mail Validator")
    st.caption("local = alnum+([._-]alnum+)*  ·  exactly one @  ·  dot-separated labels (letters, digits, internal hyphens)  ·  final TLD of ≥ 2 letters")
    system = get_email_system()
    addr = st.text_input("Enter an e-mail address", max_chars=120)
    if st.button("Validate", type="primary"):
        res = validate_email(addr, system)
        verdict(res.accepted)
        st.write(res.reason)
        c1, c2, c3 = st.columns(3)
        c1.metric("NFA", "accepts" if res.accepted else "rejects")
        c2.metric("Subset DFA", "accepts" if res.accepted_subset_dfa else "rejects", help=f"ends in {res.subset_end_state}")
        c3.metric("Minimal DFA", "accepts" if res.accepted_minimal_dfa else "rejects", help=f"ends in {res.minimal_end_state}")
        st.caption(f"All three machines agree: {'yes' if res.consistent else 'NO'}.  Subset DFA ends in {res.subset_end_state}; "
                   f"minimal DFA ends in {res.minimal_end_state}.")
        st.subheader("NFA transition trace (set of active states)")
        rows = [{"Step": 0, "Character": "—", "Class": "—", "After move": "—", "After ε-closure": format_state(system.nfa.start_set())}]
        rows += [{"Step": r["index"], "Character": display_char(addr[r["index"] - 1]), "Class": r["symbol"],
                  "After move": format_state(r["moved"]), "After ε-closure": format_state(r["after"])} for r in res.nfa_trace]
        show_table(pd.DataFrame(rows))

    st.subheader("State count comparison")
    show_table(counts_table(system))

    with st.expander("Subset construction details", expanded=False):
        st.markdown("Start state = ε-closure({q0}). Each row: from DFA state S on symbol a go to **ε-closure(move(S, a))**. "
                    "The empty set ∅ is the trap state; a set accepts if it contains q9.")
        show_table(pd.DataFrame([{"DFA state": n, "NFA states in the set": format_state(s)} for s, n in system.subset.names.items()]))
        show_table(pd.DataFrame(system.subset.rows))
    with st.expander("Minimisation: which states were merged?", expanded=True):
        mr = system.minimal
        st.write(f"Partition refinement: blocks after each round = {mr.round_block_counts}. "
                 f"Unreachable states removed: {len(mr.unreachable_removed)}.")
        for m, g in mr.merged_groups:
            st.markdown(f"* **{m}** = {' ≡ '.join(g)} → {', '.join(format_state(s) for s in system.subset.dfa.states if system.subset.names[s] in g)}. "
                        "No string tells these apart: both need exactly one letter/digit next, then behave identically.")
        if not mr.merged_groups:
            st.write("No two states were equivalent: the subset DFA was already minimal.")
    st.subheader("Minimal DFA")
    d = system.minimal.dfa
    show_diagram(dfa_to_dot(d, theme="dark", show_details=True), dfa_to_dot(d, theme="light", show_details=True), key="email_min")
    with st.expander("Minimal DFA transition table"):
        show_table(d.transition_table())
