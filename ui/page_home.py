import streamlit as st

from ui.common import card, hero


def render() -> None:
    hero("FINITE AUTOMATA VALIDATOR",
         "Finite Automata for Real-Time Validation — ATM PIN & Card Lock • Password Policy • E-mail Format")
    st.write("This prototype shows three everyday input checks modelled as **real finite automata** "
             "(no regular expressions, no `if` chains). Every machine is a Python object; every state count, "
             "diagram and test result you see is computed from those objects when the app runs.")
    c1, c2, c3 = st.columns(3)
    with c1:
        card("1 · ATM PIN & Card Lock", "A 6-state DFA accepts exactly four digits (qD is the trap). A second DFA "
             "(s0, s1, s2, LOCK) locks the card after three consecutive wrong attempts.")
    with c2:
        card("2 · Password Policy", "Five small DFAs (4 presence + length 0–16) are combined by the PRODUCT "
             "construction (intersection) and then minimised by partition refinement.")
    with c3:
        card("3 · E-mail Format", "An NFA with ε-moves guesses where the TLD starts. Subset construction gives a DFA, "
             "unreachable states are removed and equivalent states merged.")
    st.write("")
    a, b = st.columns(2)
    with a:
        st.subheader("DFA vs NFA in one minute")
        st.markdown("""
* **DFA** – exactly one next state for every (state, symbol). Reading a string is one pass with constant memory,
  ideal for as-you-type validation.
* **NFA** – may have several next states (and ε-moves). A string is accepted if **some** path ends in an accepting state.
* **Subset construction** turns an NFA into a DFA whose states are *sets* of NFA states.
* **Minimisation** merges states no string can tell apart (partition refinement).
* **Product construction** runs several DFAs in lock-step; accepting when *all* accept ⇒ intersection of languages.
""")
    with b:
        st.subheader("Technology stack")
        st.markdown("""
| Tool | Used for |
|---|---|
| Python 3 | all automata algorithms |
| Streamlit | this web interface |
| Graphviz | state diagrams (from the real objects) |
| Pandas | transition tables and test results |
| Pytest | automated test suite |
""")
    st.info("Automata check **syntax only**. Whether a PIN is the card's PIN, a password was leaked, or a mailbox exists "
            "needs outside data and is not something a finite automaton can decide.")
