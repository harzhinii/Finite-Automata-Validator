"""Shared look-and-feel helpers for the Streamlit pages."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from automata.visualize import graphviz_available, render_bytes

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
h1, h2, h3 {letter-spacing: .2px;}
.fa-hero {background: linear-gradient(135deg,#0f2147 0%,#16336b 100%); border:1px solid #1e3a8a;
          border-radius: 14px; padding: 28px 32px; margin-bottom: 18px;}
.fa-hero h1 {margin:0 0 6px 0; font-size: 2.1rem; color:#fff;}
.fa-hero p {margin:0; color:#bcd0f5; font-size: 1.02rem;}
.fa-card {background:#111c33; border:1px solid #223559; border-radius:12px; padding:18px 20px; height:100%;}
.fa-card h4 {margin:0 0 6px 0; color:#7fb0ff;}
.fa-card p {margin:0; color:#c8d6f0; font-size:.93rem;}
.fa-badge {display:inline-block; padding:6px 16px; border-radius:999px; font-weight:700; font-size:1.05rem;}
.fa-ok {background:#0f3d28; color:#6ee7a8; border:1px solid #1f7a4d;}
.fa-bad {background:#4a1626; color:#fda4af; border:1px solid #9f2a45;}
.fa-state {display:inline-block; padding:4px 12px; border-radius:8px; background:#16264a; border:1px solid #3b82f6;
           font-family: monospace; font-size:1.05rem; color:#e6edf7;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="fa-hero"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def card(title: str, body: str) -> None:
    st.markdown(f'<div class="fa-card"><h4>{html.escape(title)}</h4><p>{html.escape(body)}</p></div>',
                unsafe_allow_html=True)


def verdict(accepted: bool, ok_text: str = "ACCEPTED", bad_text: str = "REJECTED") -> None:
    cls, text, icon = ("fa-ok", ok_text, "✔") if accepted else ("fa-bad", bad_text, "✘")
    st.markdown(f'<span class="fa-badge {cls}">{icon} {html.escape(text)}</span>', unsafe_allow_html=True)


def state_chip(text: str) -> None:
    st.markdown(f'<span class="fa-state">{html.escape(str(text))}</span>', unsafe_allow_html=True)


def show_table(df: pd.DataFrame, **kw) -> None:
    st.dataframe(df, hide_index=True, width="stretch", **kw)


def show_diagram(dot_dark: str, dot_light: str | None = None, key: str = "diagram", downloads: bool = True) -> None:
    """Interactive (browser-rendered) diagram + optional PNG/SVG download of the white-background version."""
    st.graphviz_chart(dot_dark, width="stretch")
    if downloads and dot_light and graphviz_available():
        c1, c2, _ = st.columns([1, 1, 4])
        c1.download_button("⬇ PNG (for Word)", render_bytes(dot_light.replace("graph [", "graph [dpi=200, ", 1), "png"),
                           file_name=f"{key}.png", mime="image/png", key=f"{key}_png")
        c2.download_button("⬇ SVG", render_bytes(dot_light, "svg"), file_name=f"{key}.svg",
                           mime="image/svg+xml", key=f"{key}_svg")
