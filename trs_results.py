"""Vorgerechnete Messreihe (data/trs_results.json, erzeugt mit tools/sweep.py): Auswertung je Variante. Die App rechnet sie nie live."""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import trs_constants as C

ROOT = Path(__file__).resolve().parent
METHODS = C.METHODS


def load_results(path=None) -> dict:
    return json.loads(Path(path or ROOT / C.RESULTS_FILE).read_text(encoding="utf-8"))


def mean_se(xs) -> tuple:
    xs = list(xs)
    return st.mean(xs), (st.stdev(xs) / len(xs) ** 0.5 if len(xs) > 1 else float("nan"))


def rows_of(res: dict, variant: str) -> list:
    return [r for r in res["rows"] if r["variant"] == variant]


def proven(row: dict) -> bool:
    """Optimum UND faire Lösung bewiesen (sonst sind Abstände zum „Optimum“ nur Abstände zur besten gefundenen Lösung)."""
    return row["methods"]["opt"]["status"] == "OPTIMAL" and row["methods"]["fair"]["status"] == "OPTIMAL"


def summary(res: dict, variant: str, only_proven: bool = True) -> dict:
    rows = rows_of(res, variant)
    use = [r for r in rows if proven(r)] if only_proven else rows
    out = {"n": len(rows), "n_used": len(use), "proven": sum(1 for r in rows if proven(r)), "trains": st.mean(r["n"] for r in rows)}
    over = {k: [100 * (r["methods"][k]["total"] / r["methods"]["opt"]["total"] - 1) for r in use] for k in ("fcfs", "prio", "search", "fair")}
    for k, xs in over.items():
        out[f"over_{k}"], out[f"over_{k}_se"] = mean_se(xs)
        out[f"over_{k}_max"] = max(xs)
    out["fair_cheaper_than_5pct"] = sum(1 for x in over["fair"] if x < 5.0)
    for k in METHODS:
        out[f"total_{k}"] = st.mean(r["methods"][k]["total"] for r in use)
        out[f"spread_{k}"], out[f"spread_{k}_se"] = mean_se(r["methods"][k]["spread"] for r in use)
        out[f"maxavg_{k}"] = st.mean(r["methods"][k]["max_avg"] for r in use)
        out[f"jain_{k}"] = st.mean(r["methods"][k]["jain"] for r in use)
    out["time_median"] = st.median(r["methods"]["opt"]["time"] + r["methods"]["fair"]["time"] for r in rows)
    return out


def all_variants(res: dict) -> list:
    return [{"name": name, **summary(res, name)} for name in res["meta"]["variants"]]


def variant_name(settings: dict) -> str | None:
    """Welche Messreihen-Variante entspricht den Reglern genau? None, wenn keine."""
    key = (settings["trains"], settings["clear"], settings["share"], settings["favoured"])
    return {(n, cl, sh, fav): name for name, n, cl, sh, fav in C.SWEEP_VARIANTS}.get(key)
