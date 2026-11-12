# Finite Automata Validator

FLA (21CSC301T) CLA-2 Task 2 – *Finite Automata for Real-Time Validation*: ATM PIN & card lock (DFA),
password policy (DFA product + minimisation), e-mail format (NFA → subset construction → minimal DFA).

Every automaton is a real Python object (`automata/`). State counts, diagrams and test results are **computed
from those objects** – nothing is hard-coded and no regular expressions are used for validation.

## Install
```bash
cd finite_automata_validator
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Graphviz **program** (only needed for PNG/SVG files; the web app draws diagrams in the browser without it):
Windows `winget install Graphviz.Graphviz` (reopen the terminal) · macOS `brew install graphviz` · Ubuntu `sudo apt install graphviz`.

## Run
```bash
streamlit run app.py               # opens http://localhost:8501
python generate_assets.py          # writes diagrams/*.png|svg and results/*.csv|json|md  (+ pytest log)
pytest                             # 215 automated tests
```

## Folder map
| Path | What |
|---|---|
| `automata/dfa.py`, `nfa.py` | generic DFA (with product construction, equivalence check) and NFA (ε-closure) |
| `automata/subset_construction.py` | NFA → DFA |
| `automata/minimization.py` | remove unreachable states, partition refinement |
| `automata/pin_automata.py` | PIN DFA, card-lock DFA, `CardLock` with external reset |
| `automata/password_automata.py` | 4 presence DFAs + length DFA, product, minimisation |
| `automata/email_automata.py` | e-mail NFA and the whole pipeline |
| `automata/visualize.py`, `catalog.py` | DOT diagrams drawn from the real objects |
| `validation/` | independent reference validators, test cases, test runner |
| `tests/` | pytest suite |
| `ui/`, `app.py` | Streamlit pages |

## How each automaton works (simple version)
* **PIN DFA** – states q0…q4 count digits; a non-digit or a 5th digit goes to the trap qD; only q4 accepts.
* **Card lock** – s0, s1, s2 = 0/1/2 wrong attempts in a row; C resets to s0; third W → LOCK, which ignores everything.
  "Accepting" = card still usable. Unlocking is an external `reset()`, not an input symbol.
* **Password** – each character is first mapped to a class U/L/D/S/O. Four 2-state DFAs remember "class seen?"; a length DFA
  counts 0…16 (17th char → overflow trap). The product construction runs all five together: state = (n,u,l,d,s);
  accepting ⇔ 8 ≤ n ≤ 16 and u=l=d=s=1. Partition refinement then merges equivalent states.
* **E-mail** – characters map to L, D, `.`, `_`, `-`, `@`, O. The NFA (q0…q9) uses two ε-moves after a domain dot to *guess*
  "another label" or "the TLD". Subset construction builds a DFA of state-sets (∅ = trap); partition refinement merges S0 ≡ S2.

## Design decisions worth knowing
* A "digit" is an ASCII digit 0–9 (Arabic-Indic or full-width digits are class O).
* Password class **O** (space, non-ASCII) counts towards length but satisfies no requirement – exactly as in the report's Σ. So `Srm@ 2026` is accepted.
* Reported state counts **include** the trap state (e.g. subset DFA ∅); `results/state_counts.json` also gives the count without it.
* Length DFA has 18 states: n0…n16 plus the overflow trap n17+.

## Using the results in your Word report
See `results/report_tables.md` (Table 2, Table 4 numbers, e-mail counts) and `diagrams/` (Fig. 1–3 images). In Word: *Insert → Pictures*.
Use `01_pin_dfa.png`, `02_card_lock_dfa.png` for Fig. 1; `09_email_nfa.png` + the NFA table (app page *Automata Visualizer*, or
`state_counts.json`) for Fig. 2; `11_email_minimal_dfa.png` for Fig. 3. Replace `[insert your repository link here]` with your GitHub URL.
