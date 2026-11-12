import pandas as pd
import streamlit as st

from automata.pin_automata import CardLock, build_card_lock_dfa, build_pin_dfa, validate_pin
from automata.visualize import dfa_to_dot
from ui.common import show_diagram, show_table, state_chip, verdict

DEMO_PIN = "4821"      # stands in for the bank's stored PIN (a semantic check, outside the automaton)


def _diagram(dfa, key, highlight=(), current=None):
    show_diagram(dfa_to_dot(dfa, theme="dark", highlight=highlight, current=current),
                 dfa_to_dot(dfa, theme="light", highlight=highlight, current=current), key=key)


def render() -> None:
    st.title("ATM PIN Validator")
    pin_dfa = build_pin_dfa()
    tab1, tab2 = st.tabs(["PIN format DFA", "Card-lock simulator"])

    with tab1:
        st.caption("Σ = {D, O}: D = any digit 0–9, O = any other character. L = { w ∈ D* : |w| = 4 }. "
                   "Demo only – please do not type a real PIN.")
        pin = st.text_input("Enter a PIN", key="pin_input", max_chars=40)
        if st.button("Validate", type="primary", key="pin_validate"):
            st.session_state["pin_result"] = (pin, validate_pin(pin, pin_dfa))
        if "pin_result" in st.session_state:
            text, res = st.session_state["pin_result"]
            verdict(res.accepted)
            st.write(res.reason)
            c1, c2 = st.columns(2)
            c1.metric("Characters read", res.length)
            c2.metric("Final state", res.final_state)
            st.subheader("State transition trace")
            trace = pd.DataFrame([{"Step": 0, "Character": "—", "Class": "—", "From": "—", "To": pin_dfa.start}] + res.steps)
            show_table(trace)
            visited = {pin_dfa.start} | {r["To"] for r in res.steps}
            _diagram(pin_dfa, "pin_dfa", highlight=visited, current=res.final_state)
            st.caption("Highlighted = states visited by your input; thick outline = final state.")
        else:
            _diagram(pin_dfa, "pin_dfa")
        with st.expander("Transition table"):
            show_table(pin_dfa.transition_table())

    with tab2:
        st.caption("Events: C = correct PIN, W = wrong PIN. Three consecutive W lock the card; only the external reset unlocks it.")
        if "card" not in st.session_state:
            st.session_state["card"] = CardLock()
        card: CardLock = st.session_state["card"]
        b1, b2, b3, _ = st.columns([1, 1, 1, 2])
        if b1.button("✔ Correct PIN (C)", width="stretch"):
            card.apply("C")
        if b2.button("✘ Wrong PIN (W)", width="stretch"):
            card.apply("W")
        if b3.button("🔓 Reset / unlock", width="stretch"):
            card.reset()
        c1, c2 = st.columns([1, 3])
        with c1:
            st.write("Current state")
            state_chip(card.state)
        with c2:
            verdict(not card.locked, "CARD USABLE", "CARD LOCKED")
        if card.history:
            st.subheader("State after every event")
            show_table(pd.DataFrame(card.history))
        _diagram(card.dfa, "card_lock_dfa", highlight={card.state}, current=card.state)

        with st.expander("Full ATM flow: PIN format check → card-lock event"):
            st.write(f"The automaton only checks the *format*. Comparing with the stored PIN (demo value **{DEMO_PIN}**) is ordinary code.")
            attempt = st.text_input("PIN attempt", key="atm_attempt", max_chars=40)
            if st.button("Submit attempt"):
                res = validate_pin(attempt, pin_dfa)
                if not res.accepted:
                    st.warning("Format rejected by the PIN DFA – no event is sent to the card-lock DFA. " + res.reason)
                else:
                    event = "C" if attempt == DEMO_PIN else "W"
                    card.apply(event)
                    st.success(f"Format OK → event {event} → card state {card.state}. (Refresh the tab to see the table.)")
