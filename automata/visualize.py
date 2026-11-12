"""
visualize.py - Turn the REAL automaton objects into Graphviz DOT text.

Nothing here is drawn by hand: every node and edge comes from `dfa.delta` / `nfa.delta`,
so a diagram can never disagree with the implemented machine.

Conventions used in every diagram
  * an arrow from nowhere ("start") enters the start state
  * accepting states are DOUBLE circles
  * dead / trap states (no accepting state reachable) are dashed and grey/red
  * parallel edges are merged:  "D, O" on one arrow;  Σ means "every symbol"
"""
from __future__ import annotations

import shutil
from typing import Callable, Iterable

import graphviz

from .dfa import DFA, format_state
from .nfa import EPSILON, NFA

THEMES = {
    "light": dict(bg="white", fill="#eef4ff", line="#1e3a8a", font="#0f172a", edge="#334155",
                  acc_fill="#dcfce7", acc_line="#166534", dead_fill="#fee2e2", dead_line="#991b1b",
                  hi_fill="#fef08a", hi_line="#a16207"),
    "dark": dict(bg="#0b1220", fill="#16264a", line="#60a5fa", font="#e6edf7", edge="#93c5fd",
                 acc_fill="#14532d", acc_line="#4ade80", dead_fill="#4c1d2b", dead_line="#f87171",
                 hi_fill="#713f12", hi_line="#facc15"),
}


def _q(text: str) -> str:
    """Quote text for DOT."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _edge_label(symbols: list[str], alphabet: list[str]) -> str:
    syms = [s for s in alphabet if s in symbols]
    if len(syms) == len(alphabet):
        return "Σ"
    if len(alphabet) >= 5 and len(syms) >= len(alphabet) - 2:
        return "Σ∖{" + ",".join(s for s in alphabet if s not in syms) + "}"
    return ", ".join(syms)


def _header(theme: dict, title: str | None, rankdir: str, dpi: int | None) -> list[str]:
    graph = f'graph [rankdir={rankdir}, bgcolor={_q(theme["bg"])}, pad=0.3, nodesep=0.45, ranksep=0.7, ' \
            f'fontname="Helvetica", fontsize=20, fontcolor={_q(theme["font"])}'
    if dpi:
        graph += f", dpi={dpi}"
    if title:
        graph += f", labelloc=t, label={_q(title)}"
    graph += "];"
    return [
        "digraph G {",
        graph,
        f'node [shape=circle, style=filled, fillcolor={_q(theme["fill"])}, color={_q(theme["line"])}, '
        f'fontcolor={_q(theme["font"])}, fontname="Helvetica", fontsize=13, penwidth=1.6, margin=0.04];',
        f'edge [color={_q(theme["edge"])}, fontcolor={_q(theme["font"])}, fontname="Helvetica", fontsize=12, arrowsize=0.8];',
    ]


def _dfa_body(dfa: DFA, prefix: str, theme: dict, *, label_fn: Callable | None, highlight: Iterable,
              current, show_details: bool, rank_fn: Callable | None) -> list[str]:
    ids = {q: f"{prefix}n{i}" for i, q in enumerate(dfa.states)}
    dead, highlight = dfa.dead_states(), set(highlight or [])
    lines = []
    for q in dfa.states:
        if label_fn:
            text = label_fn(q)
        else:
            text = dfa.label(q)
            if show_details and dfa.detail(q) and dfa.detail(q) != text:
                text += "\n" + dfa.detail(q)
        attrs = [f"label={_q(text)}"]
        if q in dfa.accepting:
            attrs += ["shape=doublecircle", f'fillcolor={_q(theme["acc_fill"])}', f'color={_q(theme["acc_line"])}']
        if q in dead and q not in dfa.accepting:
            attrs += ["style=\"filled,dashed\"", f'fillcolor={_q(theme["dead_fill"])}', f'color={_q(theme["dead_line"])}']
        if q in highlight:
            attrs += [f'fillcolor={_q(theme["hi_fill"])}', f'color={_q(theme["hi_line"])}']
            attrs += ['fontcolor="#111827"'] if theme["bg"] == "white" else ['fontcolor="#fef9c3"']
        if q == current:
            attrs += ["penwidth=4"]
        lines.append(f"{ids[q]} [{', '.join(attrs)}];")

    start_id = f"{prefix}start"
    lines.append(f'{start_id} [shape=none, label="start", width=0, height=0, fontsize=11, style=""];')
    lines.append(f"{start_id} -> {ids[dfa.start]};")

    merged: dict = {}
    for q in dfa.states:
        for a in dfa.alphabet:
            merged.setdefault((q, dfa.delta[(q, a)]), []).append(a)
    for (src, dst), syms in merged.items():
        lines.append(f"{ids[src]} -> {ids[dst]} [label={_q(_edge_label(syms, dfa.alphabet))}];")

    if rank_fn:
        layers: dict = {}
        for q in dfa.states:
            layers.setdefault(rank_fn(q), []).append(ids[q])
        for members in layers.values():
            lines.append("{rank=same; " + "; ".join(members) + ";}")
    return lines


def dfa_to_dot(dfa: DFA, *, theme: str = "light", title: str | None = None, rankdir: str = "LR",
               label_fn: Callable | None = None, highlight: Iterable = (), current=None,
               show_details: bool = False, rank_fn: Callable | None = None, dpi: int | None = None) -> str:
    t = THEMES[theme]
    lines = _header(t, title, rankdir, dpi)
    lines += _dfa_body(dfa, "", t, label_fn=label_fn, highlight=highlight, current=current,
                       show_details=show_details, rank_fn=rank_fn)
    lines.append("}")
    return "\n".join(lines)


def multi_dfa_to_dot(dfas: list[DFA], *, theme: str = "light", title: str | None = None,
                     dpi: int | None = None) -> str:
    """Several DFAs in one picture (one labelled box each) - 'run side by side'."""
    t = THEMES[theme]
    lines = _header(t, title, "LR", dpi)
    for i, d in enumerate(dfas):
        lines.append(f"subgraph cluster_{i} {{")
        lines.append(f'label={_q(d.name)}; style="rounded"; color={_q(t["line"])}; fontcolor={_q(t["font"])}; fontsize=15;')
        lines += _dfa_body(d, f"c{i}_", t, label_fn=None, highlight=(), current=None, show_details=False, rank_fn=None)
        lines.append("}")
    lines.append("}")
    return "\n".join(lines)


def nfa_to_dot(nfa: NFA, *, theme: str = "light", title: str | None = None, rankdir: str = "LR",
               highlight: Iterable = (), dpi: int | None = None) -> str:
    t = THEMES[theme]
    highlight = set(highlight or [])
    ids = {q: f"n{i}" for i, q in enumerate(nfa.states)}
    lines = _header(t, title, rankdir, dpi)
    for q in nfa.states:
        attrs = [f"label={_q(format_state(q))}"]
        if q in nfa.accepting:
            attrs += ["shape=doublecircle", f'fillcolor={_q(t["acc_fill"])}', f'color={_q(t["acc_line"])}']
        if q in highlight:
            attrs += [f'fillcolor={_q(t["hi_fill"])}', f'color={_q(t["hi_line"])}']
            attrs += ['fontcolor="#111827"'] if t["bg"] == "white" else ['fontcolor="#fef9c3"']
        lines.append(f"{ids[q]} [{', '.join(attrs)}];")
    lines.append('start [shape=none, label="start", width=0, height=0, fontsize=11, style=""];')
    lines.append(f"start -> {ids[nfa.start]};")

    merged: dict = {}
    for (q, a), targets in nfa.delta.items():
        for tgt in targets:
            merged.setdefault((q, tgt), []).append(a)
    order = nfa.alphabet + [EPSILON]
    for (src, dst), syms in merged.items():
        syms = [s for s in order if s in syms]
        style = ", style=dashed" if syms == [EPSILON] else ""
        lines.append(f"{ids[src]} -> {ids[dst]} [label={_q(', '.join(syms))}{style}];")
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------- rendering ---
def graphviz_available() -> bool:
    return shutil.which("dot") is not None


def render_bytes(dot: str, fmt: str = "png") -> bytes:
    """Render DOT text to PNG/SVG bytes using the Graphviz `dot` program."""
    return graphviz.Source(dot).pipe(format=fmt)
