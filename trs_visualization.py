"""Plotly-Figuren der Trassenkonflikt-Demo. Alle Achsen fest (fixedrange), damit Touch-Scrollen nicht am Chart hängen bleibt."""
from __future__ import annotations

import plotly.graph_objects as go

import trs_constants as C
from trs_evaluation import segment_intervals


POSITIONS = {"fcfs": "top center", "prio": "top center", "search": "top center", "opt": "top center", "fair": "bottom center"}


def _lock(fig, height=360, **layout):
    fig.update_layout(height=height, margin=dict(l=50, r=20, t=40, b=55), font=dict(size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0), **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def build_timetable(trains: list, starts: dict, clear: int) -> go.Figure:
    """Bildfahrplan: Zeit waagerecht, Station senkrecht; jeder Zug eine Linie in der Farbe seines Operators (Schnellzug durchgezogen, langsamer gestrichelt);
    waagerechte Stücke sind Wartezeit in einer Station, die Raute die Wunschabfahrt."""
    fig = go.Figure()
    shown = set()
    for tr in segment_intervals(trains, starts, clear):
        op = tr["op"]
        xs = [p[0] for p in tr["points"]]
        ys = [p[1] for p in tr["points"]]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.OP_COLORS[op], width=2.5, dash="solid" if tr["fast"] else "dash"),
                                 name=f"Operator {C.op_name(op)}", legendgroup=f"op{op}", showlegend=op not in shown,
                                 hovertemplate=f"Zug {tr['train'] + 1} (Operator {C.op_name(op)}, {'schnell' if tr['fast'] else 'langsam'})<extra></extra>"))
        shown.add(op)
        fig.add_trace(go.Scatter(x=[tr["request"]], y=[ys[0]], mode="markers", marker=dict(symbol="diamond", size=7, color=C.OP_COLORS[op]), legendgroup=f"op{op}",
                                 showlegend=False, hovertemplate=f"Wunschabfahrt Zug {tr['train'] + 1}<extra></extra>"))
    fig.update_xaxes(title_text="Zeit (min)")
    fig.update_yaxes(tickvals=list(range(C.N_SEG + 1)), ticktext=[f"Station {s}" for s in range(C.N_SEG + 1)], autorange="reversed")
    return _lock(fig, 420)


def build_operator_bars(run: dict) -> go.Figure:
    """Mittlere Verspätung je Operator und Verfahren."""
    present = [o for o in range(C.N_OPS) if any(t.op == o for t in run["trains"])]
    fig = go.Figure()
    for key in C.METHODS:
        avg = run["results"][key]["metrics"]["avg"]
        fig.add_trace(go.Bar(x=[f"Operator {C.op_name(o)}" for o in present], y=[avg[o] for o in present], name=C.METHOD_LABELS[key], marker_color=C.METHOD_COLORS[key],
                             hovertemplate="%{x}: %{y:.1f} min<extra>" + C.METHOD_LABELS[key] + "</extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="mittlere Verspätung (min)", rangemode="tozero")
    return _lock(fig, 360)


def build_method_scatter(run: dict) -> go.Figure:
    """Je Verfahren ein Punkt: Gesamtverspätung gegen Spreizung zwischen den Operatoren (links unten ist gut)."""
    fig = go.Figure()
    for key in C.METHODS:
        m = run["results"][key]["metrics"]
        fig.add_trace(go.Scatter(x=[m["total"]], y=[m["spread"]], mode="markers+text", text=[C.METHOD_LABELS[key]], textposition=POSITIONS[key], marker=dict(size=14, color=C.METHOD_COLORS[key]),
                                 name=C.METHOD_LABELS[key], showlegend=False, hovertemplate=f"{C.METHOD_LABELS[key]}: %{{x}} min gesamt, Spreizung %{{y:.0f}} min<extra></extra>"))
    top = max(run["results"][k]["metrics"]["total"] for k in C.METHODS)
    fig.update_xaxes(title_text="Gesamtverspätung aller Züge (min)", range=[-0.12 * top, 1.2 * top])
    fig.update_yaxes(title_text="Spreizung der mittleren Verspätung (min)", rangemode="tozero")
    return _lock(fig, 340)


def build_sweep_bars(rows: list) -> go.Figure:
    """Messreihe: Gesamtverspätung über dem Optimum (%) je Variante für Erstanmelder, Vorrang, verbesserte Reihenfolge und fair (Mittel ± Standardfehler)."""
    fig = go.Figure()
    names = [r["name"] for r in rows]
    for key, label in (("fcfs", C.METHOD_LABELS["fcfs"]), ("prio", C.METHOD_LABELS["prio"]), ("search", C.METHOD_LABELS["search"]), ("fair", C.METHOD_LABELS["fair"])):
        fig.add_trace(go.Bar(x=names, y=[r[f"over_{key}"] for r in rows], name=label, marker_color=C.METHOD_COLORS[key],
                             error_y=dict(type="data", array=[r[f"over_{key}_se"] for r in rows], visible=True)))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Gesamtverspätung über dem Optimum (%)", rangemode="tozero")
    return _lock(fig, 380)


def build_spread_bars(rows: list) -> go.Figure:
    """Messreihe: Spreizung der mittleren Verspätung zwischen den Operatoren (min) je Variante und Verfahren."""
    fig = go.Figure()
    names = [r["name"] for r in rows]
    for key in C.METHODS:
        fig.add_trace(go.Bar(x=names, y=[r[f"spread_{key}"] for r in rows], name=C.METHOD_LABELS[key], marker_color=C.METHOD_COLORS[key],
                             error_y=dict(type="data", array=[r[f"spread_{key}_se"] for r in rows], visible=True)))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Spreizung der mittleren Verspätung (min)", rangemode="tozero")
    return _lock(fig, 380)
