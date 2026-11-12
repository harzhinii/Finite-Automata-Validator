import streamlit as st

from automata.catalog import REDUCED_POLICY
from automata.password_automata import get_password_system, validate_password
from automata.visualize import dfa_to_dot, multi_dfa_to_dot
from ui.common import show_diagram, show_table, verdict


def render() -> None:
    st.title("Password Validator")
    st.caption("Policy: 8–16 characters with at least one uppercase, lowercase, digit and special character. "
               "L = L_U ∩ L_L ∩ L_D ∩ L_S ∩ L_len.  🔒 Passwords are processed in memory only – never stored, logged or written to disk.")
    system = get_password_system()

    pw = st.text_input("Enter a password", type="password", max_chars=64)
    if st.button("Validate", type="primary"):
        res = validate_password(pw, system)
        verdict(res.accepted)
        c1, c2, c3 = st.columns(3)
        c1.metric("Character count", res.length, help="Policy: 8 to 16")
        c2.metric("Product DFA state (n,u,l,d,s)", system.product.label(res.final_state))
        c3.metric("Minimal DFA state", res.minimal_state)
        l, r = st.columns(2)
        with l:
            st.subheader("Satisfied")
            for name, ok in res.requirements:
                if ok:
                    st.markdown(f"✅ {name}")
        with r:
            st.subheader("Missing")
            if not res.missing:
                st.markdown("_Nothing – all requirements met._")
            for m in res.missing:
                st.markdown(f"❌ {m}")
        st.caption("Requirement flags are read from the final product state: n = characters read (capped at 17), "
                   "u/l/d/s = 1 if that class has been seen. Accepting ⇔ 8 ≤ n ≤ 16 and u = l = d = s = 1."
                   f" Product and minimal DFA agree: {'yes' if res.consistent else 'NO'}.")
        with st.expander("Per-character trace (shows character classes, not the characters)"):
            show_table(__import__("pandas").DataFrame(res.steps))

    st.subheader("State count comparison")
    show_table(system.design_table())
    p, m = system.product, system.minimal
    st.markdown(
        f"* **Product states** are tuples (n, u, l, d, s). Only **{len(p.states)}** of the **{p.meta['cartesian_size']}** "
        f"tuples in the full Cartesian product are reachable (a string of n characters can have set at most min(n,4) flags).\n"
        f"* A product state accepts exactly when *every* component accepts: n in 8…16 and all four flags set "
        f"→ **{len(p.accepting)}** accepting product states.\n"
        f"* Minimisation (partition refinement) needed **{len(m.round_block_counts)}** rounds "
        f"(blocks per round: {m.round_block_counts}) and merged {len(p.states) - len(m.dfa.states)} states away.")
    with st.expander("Which states were merged?"):
        over = [s for s in p.states if s[0] > system.policy.max_len]
        st.write(f"All {len(over)} 'too long' states (n ≥ 17, whatever flags) merge into one dead state; the same happens to "
                 "states that can no longer reach acceptance (not enough characters left for the missing classes).")
        import pandas as pd
        show_table(pd.DataFrame([{"Minimal state": k, "Product states merged": len(v), "Examples": ", ".join(system.product.label(s) for s in v[:5])}
                                 for k, v in m.blocks.items() if len(v) > 1]).sort_values("Product states merged", ascending=False))

    st.subheader("Password DFA diagrams")
    t1, t2, t3 = st.tabs(["Five component DFAs", "Product DFA (small teaching instance)", "Full product / minimal DFA"])
    with t1:
        show_diagram(multi_dfa_to_dot(system.components, theme="dark"), multi_dfa_to_dot(system.components, theme="light"), key="pw_components")
    with t2:
        small = get_password_system(REDUCED_POLICY)
        kw = dict(label_fn=small.node_label, rank_fn=lambda s: s[0])
        st.caption("Same code, reduced policy (length 2–3, classes U and D) so the product is readable. Label = n and classes seen.")
        show_diagram(dfa_to_dot(small.product, theme="dark", **kw), dfa_to_dot(small.product, theme="light", **kw), key="pw_reduced")
    with t3:
        st.write(f"The full machines have {len(p.states)} and {len(m.dfa.states)} states – too large for a screen. "
                 "Open `diagrams/07_password_product_dfa_reachable.svg` and `diagrams/08_password_product_dfa_minimal.svg` "
                 "in a browser and zoom (run `python generate_assets.py` if they are missing).")
