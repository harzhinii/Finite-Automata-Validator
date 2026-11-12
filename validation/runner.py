"""
runner.py - Executes every test against the REAL automata and builds the result tables.

Nothing is hard-coded: each row is produced by running the implementation, and the totals
are sums over those rows.  Random tests use a FIXED seed so results are reproducible.
"""
from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import pandas as pd

from automata.dfa import equivalent
from automata.email_automata import get_email_system, validate_email
from automata.minimization import minimize, remove_unreachable
from automata.password_automata import get_password_system, validate_password
from automata.pin_automata import (CardLock, build_card_lock_dfa, build_pin_dfa, card_usable,
                                   run_card_events, validate_pin)
from automata.stats import collect_state_counts
from automata.subset_construction import full_powerset_dfa
from validation import cases as C
from validation.reference import (ref_card_state, ref_email, ref_password, ref_pin,
                                  table_filling_class_count)

SEED = 2026
GROUPS = ["PIN validator", "Card-lock DFA", "Password validator", "E-mail validator",
          "Construction (NFA→DFA, minimisation)"]
COLUMNS = ["ID", "Group", "Category", "Input", "Expected", "Automaton", "Reference",
           "Checks", "Passed", "Failed", "Result", "Note"]


@dataclass
class TestReport:
    details: pd.DataFrame
    summary: pd.DataFrame
    totals: dict
    seed: int = SEED


# ------------------------------------------------------------- row builders ---
class _Rows:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def case(self, group, category, shown, expected, automaton, reference=None, note="",
             names=("ACCEPT", "REJECT"), extra_ok=True):
        ok = automaton == expected and (reference is None or reference == expected) and extra_ok
        self._add(group, category, shown, names[0 if expected else 1], names[0 if automaton else 1],
                  "" if reference is None else names[0 if reference else 1], 1, int(ok), note)

    def suite(self, group, category, description, checks, failures, note=""):
        self._add(group, category, description, "all agree", "all agree" if not failures else f"{failures} differ",
                  "", checks, checks - failures, note)

    def _add(self, group, category, shown, expected, automaton, reference, checks, passed, note):
        self.rows.append({
            "ID": len(self.rows) + 1, "Group": group, "Category": category, "Input": shown,
            "Expected": expected, "Automaton": automaton, "Reference": reference,
            "Checks": checks, "Passed": passed, "Failed": checks - passed,
            "Result": "PASS" if passed == checks else "FAIL", "Note": note,
        })


def _shown(text: str) -> str:
    """How an input appears in tables ('ε' for the empty string)."""
    if text == "":
        return "ε (empty)"
    return "".join("␠" if c == " " else (c if c.isprintable() else repr(c)[1:-1]) for c in text)


# ----------------------------------------------------------------- groups ---
def _run_pin(r: _Rows) -> None:
    g = "PIN validator"
    dfa = build_pin_dfa()
    for cat, items, exp in (("Report case", C.PIN_REPORT_ACCEPT, True), ("Report case", C.PIN_REPORT_REJECT, False),
                            ("Boundary", C.PIN_BOUNDARY_ACCEPT, True), ("Boundary", C.PIN_BOUNDARY_REJECT, False)):
        for s in items:
            res = validate_pin(s, dfa)
            r.case(g, cat, _shown(s), exp, res.accepted, ref_pin(s), note=res.reason)

    bad = sum(dfa.delta.get(k) != v for k, v in C.PIN_TABLE_FROM_REPORT.items()) + \
        (len(dfa.delta) != len(C.PIN_TABLE_FROM_REPORT))
    r.suite(g, "State transition", "All 12 transitions equal Table 1 of the report",
            len(C.PIN_TABLE_FROM_REPORT), bad)

    chars = ["0", "7", "a", "-", " ", "٣"]                     # digits, letter, symbol, space, non-ASCII digit
    total = failures = 0
    for n in range(0, 7):
        for tup in product(chars, repeat=n):
            s = "".join(tup)
            total += 1
            failures += validate_pin(s, dfa).accepted != ref_pin(s)
    r.suite(g, "Exhaustive", f"every string of length 0–6 over {len(chars)} characters {chars}", total, failures)


def _run_card(r: _Rows) -> None:
    g = "Card-lock DFA"
    for cat, items, exp in (("Report case", C.CARD_REPORT_USABLE, True), ("Report case", C.CARD_REPORT_LOCKED, False),
                            ("Extra", C.CARD_EXTRA_USABLE, True), ("Extra", C.CARD_EXTRA_LOCKED, False)):
        for s in items:
            states = run_card_events(s)
            ref_state = ref_card_state(s)
            shown = ",".join(s) if s else "ε (no events)"
            note = "→".join(states) + ("" if states[-1] == ref_state else f"  (reference final state: {ref_state})")
            r.case(g, cat, shown, exp, card_usable(s), ref_state != "LOCK", note=note,
                   names=("USABLE", "LOCKED"), extra_ok=states[-1] == ref_state)

    dfa = build_card_lock_dfa()
    bad = sum(dfa.delta.get(k) != v for k, v in C.CARD_TABLE_FROM_RULES.items())
    r.suite(g, "State transition", "All 8 transitions equal the rules in the task statement",
            len(C.CARD_TABLE_FROM_RULES), bad)

    # external reset behaviour
    card, bad = CardLock(), 0
    for e in "WWW":
        card.apply(e)
    bad += card.state != "LOCK"
    card.apply("C")
    bad += card.state != "LOCK"            # a correct PIN must not unlock
    card.apply("W")
    bad += card.state != "LOCK"
    card.reset()
    bad += card.state != "s0" or card.locked
    r.suite(g, "State transition", "LOCK ignores C and W; only the external reset unlocks (4 checks)", 4, bad)

    total = failures = 0
    for n in range(0, 13):
        for tup in product("CW", repeat=n):
            s = "".join(tup)
            total += 1
            failures += run_card_events(s)[-1] != ref_card_state(s)
    r.suite(g, "Exhaustive", "every event sequence of length 0–12 over {C, W}: final state vs independent rule",
            total, failures)


def _run_password(r: _Rows) -> None:
    g = "Password validator"
    system = get_password_system()
    for cat, items, exp in (("Report case", C.PW_REPORT_ACCEPT, True), ("Report case", C.PW_REPORT_REJECT, False)):
        for s in items:
            res = validate_password(s, system)
            note = "all requirements met" if res.accepted else "missing: " + "; ".join(res.missing)
            r.case(g, cat, s, exp, res.accepted and res.consistent, ref_password(s), note=note)
    for s, exp, why in C.PW_EXTRA:
        res = validate_password(s, system)
        r.case(g, "Boundary", _shown(s), exp, res.accepted and res.consistent, ref_password(s), note=why)
    for s, exp, why in C.password_boundary_cases():
        res = validate_password(s, system)
        r.case(g, "Boundary 7/8/16/17", s, exp, res.accepted and res.consistent, ref_password(s), note=why)

    rep = {"U": "A", "L": "a", "D": "1", "S": "!", "O": " "}
    total = failures = 0
    for n in range(0, 8):
        for tup in product("ULDSO", repeat=n):
            s = "".join(rep[c] for c in tup)
            total += 1
            expect = ref_password(s)
            failures += not (system.product.accepts(tup) == expect == system.minimal.dfa.accepts(tup))
    r.suite(g, "Exhaustive", "every class string of length 0–7 over {U,L,D,S,O}: product DFA and minimal DFA vs reference",
            total, failures)

    rng = random.Random(SEED)
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, string.punctuation, " é€\t"]
    total = failures = 0
    for _ in range(20000):
        chosen = [p for p in pools if rng.random() < 0.7] or [pools[0]]
        s = "".join(rng.choice(rng.choice(chosen)) for _ in range(rng.randint(0, 20)))
        total += 1
        res = validate_password(s, system)
        failures += not (res.accepted == ref_password(s) and res.consistent)
    r.suite(g, "Random (seed 2026)", "20,000 random passwords of length 0–20 (full characters, classified by the DFA front end)",
            total, failures)


def _email_all(system, s: str):
    res = validate_email(s, system)
    return res.accepted, res.accepted_subset_dfa, res.accepted_minimal_dfa


def _run_email(r: _Rows) -> None:
    g = "E-mail validator"
    system = get_email_system()
    for cat, items, exp in (("Report case", C.EMAIL_REPORT_ACCEPT, True), ("Report case", C.EMAIL_REPORT_REJECT, False),
                            ("Boundary", C.EMAIL_BOUNDARY_ACCEPT, True), ("Boundary", C.EMAIL_BOUNDARY_REJECT, False)):
        for s in items:
            res = validate_email(s, system)
            r.case(g, cat, _shown(s), exp, res.accepted and res.consistent, ref_email(s), note=res.reason)

    chars = ["a", "1", ".", "-", "_", "@", "!"]
    total = failures = 0
    for n in range(0, 7):
        for tup in product(chars, repeat=n):
            s = "".join(tup)
            total += 1
            expect = ref_email(s)
            failures += not (_email_all(system, s) == (expect, expect, expect))
    r.suite(g, "Exhaustive", f"every string of length 0–6 over {chars}: NFA, subset DFA and minimal DFA vs reference",
            total, failures)

    rng = random.Random(SEED)
    pieces = ["a", "b1", "x-y", "7", ".", "_", "-", "@", "@", "..", ".com", ".io", "co", "é", " ", "m.n", "-x", "y-", "srm"]
    valid = C.EMAIL_REPORT_ACCEPT + C.EMAIL_BOUNDARY_ACCEPT
    total = failures = 0
    for i in range(20000):
        if i % 2:
            s = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 9)))
        else:                                              # mutate a valid address: delete / insert / replace one char
            s = rng.choice(valid)
            k = rng.randrange(len(s) + 1)
            op = rng.choice("dir")
            ch = rng.choice("a1.-_@! ")
            if op == "d" and s:
                s = s[:k % len(s)] + s[k % len(s) + 1:]
            elif op == "i":
                s = s[:k] + ch + s[k:]
            elif s:
                s = s[:k % len(s)] + ch + s[k % len(s) + 1:]
        total += 1
        expect = ref_email(s)
        failures += not (_email_all(system, s) == (expect, expect, expect))
    r.suite(g, "Random (seed 2026)", "20,000 random / mutated addresses: NFA, subset DFA and minimal DFA vs reference",
            total, failures)


def _run_construction(r: _Rows) -> None:
    g = "Construction (NFA→DFA, minimisation)"
    em, pw = get_email_system(), get_password_system()

    same, witness = equivalent(em.subset_pruned, em.minimal.dfa)
    r.suite(g, "Equivalence", "E-mail: subset DFA ≡ minimal DFA (product-graph search, all strings)", 1, int(not same),
            "" if same else f"counter-example {witness}")
    same, witness = equivalent(pw.product, pw.minimal.dfa)
    r.suite(g, "Equivalence", "Password: product DFA ≡ minimal DFA (product-graph search, all strings)", 1, int(not same),
            "" if same else f"counter-example {witness}")

    again = minimize(em.minimal.dfa)
    r.suite(g, "Minimality", "E-mail: minimising the minimal DFA again changes nothing", 1,
            int(len(again.dfa.states) != len(em.minimal.dfa.states)))
    again = minimize(pw.minimal.dfa)
    r.suite(g, "Minimality", "Password: minimising the minimal DFA again changes nothing", 1,
            int(len(again.dfa.states) != len(pw.minimal.dfa.states)))
    r.suite(g, "Minimality", "E-mail: table-filling algorithm finds the same number of classes as partition refinement", 1,
            int(table_filling_class_count(em.subset_pruned) != len(em.minimal.dfa.states)),
            f"{table_filling_class_count(em.subset_pruned)} vs {len(em.minimal.dfa.states)}")
    r.suite(g, "Minimality", "Password: table-filling algorithm finds the same number of classes as partition refinement", 1,
            int(table_filling_class_count(pw.product) != len(pw.minimal.dfa.states)),
            f"{table_filling_class_count(pw.product)} vs {len(pw.minimal.dfa.states)}")

    full = full_powerset_dfa(em.nfa)
    pruned, removed = remove_unreachable(full)
    r.suite(g, "Unreachable states", f"Naive power set ({len(full.states)} subsets) minus unreachable = BFS subset DFA",
            1, int(set(pruned.states) != set(em.subset.dfa.states)),
            f"{len(removed)} unreachable subsets removed, {len(pruned.states)} remain")

    closure = em.nfa.epsilon_closure({"q6"})
    r.suite(g, "ε-closure", "ε-closure({q6}) = {q3, q6, q7} (the dot-guess)", 1, int(closure != {"q3", "q6", "q7"}))


def run_all() -> TestReport:
    rows = _Rows()
    for fn in (_run_pin, _run_card, _run_password, _run_email, _run_construction):
        fn(rows)
    details = pd.DataFrame(rows.rows, columns=COLUMNS)
    grouped = details.groupby("Group", sort=False).agg(
        **{"Tests run": ("Checks", "sum"), "Passed": ("Passed", "sum"), "Failed": ("Failed", "sum"),
           "Individual cases": ("Category", lambda s: int(sum(c in ("Report case", "Boundary", "Extra", "Boundary 7/8/16/17") for c in s)))}
    ).reset_index().reindex(columns=["Group", "Tests run", "Passed", "Failed", "Individual cases"])
    grouped["Pass %"] = (100 * grouped["Passed"] / grouped["Tests run"]).round(2)
    total = int(details["Checks"].sum())
    passed = int(details["Passed"].sum())
    totals = {"tests": total, "passed": passed, "failed": total - passed,
              "pass_percent": round(100 * passed / total, 2) if total else 0.0,
              "rows": len(details), "seed": SEED}
    return TestReport(details, grouped, totals)


def write_results(results_dir: str | Path, report: TestReport | None = None) -> TestReport:
    """Write test_results.csv, test_summary.csv and state_counts.json."""
    report = report or run_all()
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    report.details.to_csv(out / "test_results.csv", index=False, encoding="utf-8-sig")
    report.summary.to_csv(out / "test_summary.csv", index=False, encoding="utf-8-sig")
    with open(out / "state_counts.json", "w", encoding="utf-8") as f:
        json.dump(collect_state_counts(), f, indent=2, ensure_ascii=False)
    return report
