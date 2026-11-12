import subprocess
import sys
from pathlib import Path

import streamlit as st

from ui.common import show_table
from validation.runner import run_all, write_results

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(show_spinner="Running every test against the real automata …")
def _report():
    return run_all()


def render() -> None:
    st.title("Testing and Results")
    st.caption("Every number below is produced by executing the implementation now – nothing is hard-coded. "
               "Inputs are compared with independently written reference validators; random tests use a fixed seed.")
    if st.button("🔄 Re-run all tests"):
        _report.clear()
    rep = _report()
    t = rep.totals
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tests run", f"{t['tests']:,}")
    c2.metric("Passed", f"{t['passed']:,}")
    c3.metric("Failed", f"{t['failed']:,}")
    c4.metric("Pass percentage", f"{t['pass_percent']}%")
    st.caption("A 'test' is one string / event sequence / check compared with its expected verdict. Individual report and boundary "
               "cases are one row each; exhaustive and random suites are one row each counting all strings they covered.")
    if t["failed"]:
        st.error("Some tests failed – see the table below.")
    else:
        st.success("All executed tests passed.")

    st.subheader("Summary by test group (Table 4 of the report)")
    show_table(rep.summary)

    st.subheader("Detailed results")
    df = rep.details
    f1, f2 = st.columns(2)
    group = f1.multiselect("Group", list(df["Group"].unique()))
    status = f2.multiselect("Result", ["PASS", "FAIL"])
    view = df
    if group:
        view = view[view["Group"].isin(group)]
    if status:
        view = view[view["Result"].isin(status)]
    show_table(view)
    d1, d2 = st.columns(2)
    d1.download_button("⬇ Download test_results.csv", df.to_csv(index=False).encode("utf-8-sig"), "test_results.csv", "text/csv")
    if d2.button("💾 Write results/ files (CSV + JSON)"):
        write_results(ROOT / "results", rep)
        st.success("results/test_results.csv, test_summary.csv and state_counts.json written.")

    st.subheader("Pytest")
    if st.button("▶ Run pytest now"):
        with st.spinner("Running pytest …"):
            p = subprocess.run([sys.executable, "-m", "pytest", "-v", "--tb=short"], cwd=ROOT, capture_output=True, text=True, timeout=600)
        (st.success if p.returncode == 0 else st.error)(f"pytest exit code {p.returncode}")
        st.code(p.stdout + p.stderr, language="text")
