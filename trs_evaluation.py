"""Live-Rechnung: ein Netz von Zügen auf der eingleisigen Strecke unter vier Verfahren (Erstanmelder, Vorrang, Optimum, fair), Kennzahlen und Meldungen."""
from __future__ import annotations

import time

import trs_constants as C
import trs_exact as X
import trs_model as M


def settings_trains(s: dict) -> list:
    return M.generate(s["trains"], C.N_OPS, C.N_SEG, C.WINDOW, s["seed"], C.shares_for(s["share"]), C.FAST_PCT)


def solve_all(trains: list, clear: int, favoured: int, cp_limit: float = C.CP_TIME_LIMIT) -> dict:
    """Alle fünf Verfahren auf denselben Zügen. Rückgabe {Verfahren: {starts, metrics, status, valid}}."""
    out = {}
    fc = M.dispatch(trains, C.N_SEG, clear, M.order_fcfs(trains))
    pr = M.dispatch(trains, C.N_SEG, clear, M.order_priority(trains, favoured))
    out["fcfs"] = {"starts": fc, "status": "Regel"}
    out["prio"] = {"starts": pr, "status": "Regel"}
    out["search"] = {"starts": M.dispatch(trains, C.N_SEG, clear, M.improve_order(trains, C.N_SEG, clear, M.order_fcfs(trains), C.N_OPS)), "status": "Lokalsuche"}
    for key, obj in (("opt", "total"), ("fair", "fair_total")):
        r = X.solve(trains, C.N_SEG, clear, obj, cp_limit)
        if "starts" in r:
            out[key] = {"starts": r["starts"], "status": r["status"], "time": r["time"], "bound": r.get("bound")}
        else:       # Zeitlimit ohne jede Lösung: die verbesserte Reihenfolge steht stellvertretend da, Status zeigt es
            out[key] = {"starts": out["search"]["starts"], "status": f"{r['status']} (keine Lösung im Zeitlimit; Ersatz: verbesserte Reihenfolge)", "time": r["time"], "bound": None}
    for v in out.values():
        v["metrics"] = M.metrics(trains, C.N_SEG, v["starts"], C.N_OPS)
        v["valid"] = M.valid_schedule(trains, C.N_SEG, clear, v["starts"])
    return out


def run_live(settings: dict, cp_limit: float = C.CP_TIME_LIMIT) -> dict:
    t0 = time.perf_counter()
    trains = settings_trains(settings)
    res = solve_all(trains, settings["clear"], settings["favoured"], cp_limit)
    return {"trains": trains, "results": res, "seconds": time.perf_counter() - t0, "proven": res["opt"]["status"] == "OPTIMAL" and res["fair"]["status"] == "OPTIMAL"}


def over_opt_pct(run: dict, key: str) -> float:
    """Gesamtverspätung des Verfahrens über dem Optimum in Prozent (Basis = Optimum)."""
    return 100 * (run["results"][key]["metrics"]["total"] / run["results"]["opt"]["metrics"]["total"] - 1)


def fairness_price(run: dict) -> dict:
    """Was kostet die Fairness gegenüber dem Optimum der Gesamtverspätung? (Minuten und Prozent des Optimums)"""
    o, f = run["results"]["opt"]["metrics"], run["results"]["fair"]["metrics"]
    return {"minutes": f["total"] - o["total"], "pct": 100 * (f["total"] / o["total"] - 1) if o["total"] else 0.0, "spread_opt": o["spread"], "spread_fair": f["spread"]}


def fairness_message(run: dict):
    """Drei Zustände: Zeitlimit (Optimum nicht bewiesen) / Fairness fast umsonst / Fairness kostet spürbar."""
    p = fairness_price(run)
    if not run["proven"]:
        return "unproven", (f"Das CP-SAT-Zeitlimit ({C.CP_TIME_LIMIT:.0f} s) wurde erreicht: Optimum und faire Lösung sind die besten gefundenen, nicht bewiesen. "
                            f"Der Vergleich ({p['pct']:+.1f} %) gilt für diese Lösungen.")
    if p["pct"] < C.FAIR_SMALL_PCT:
        return "cheap", (f"Fairness kostet auf diesem Netz nur {p['minutes']:.0f} min Gesamtverspätung ({p['pct']:+.1f} %) und senkt die Spreizung zwischen den Operatoren von "
                         f"{p['spread_opt']:.0f} auf {p['spread_fair']:.0f} min.")
    return "costly", (f"Auf diesem Netz kostet Fairness {p['minutes']:.0f} min Gesamtverspätung ({p['pct']:+.1f} %): die Spreizung sinkt von {p['spread_opt']:.0f} auf "
                      f"{p['spread_fair']:.0f} min.")


def priority_message(run: dict, favoured: int) -> str:
    r = run["results"]
    avg = r["prio"]["metrics"]["avg"]
    present = [i for i in range(C.N_OPS) if any(t.op == i for t in run["trains"])]
    worst = max(present, key=lambda i: avg[i])
    return (f"Mit Vorrang für Operator {C.op_name(favoured)} wartet {C.op_name(worst)} im Mittel {avg[worst]:.0f} min, {C.op_name(favoured)} dagegen "
            f"{avg[favoured]:.0f} min; die Gesamtverspätung liegt {over_opt_pct(run, 'prio'):+.0f} % über dem Optimum.")


def segment_intervals(trains: list, starts: dict, clear: int) -> list:
    """Für den Bildfahrplan: je Zug die Folge (Zeit, Station) der Fahrt: Einfahrt in jeden Abschnitt und Ankunft, Wartezeiten in Stationen als waagerechte Stücke."""
    out = []
    for t in trains:
        pts = []
        rt = M.run_time(t.fast)
        for j in M.route(t, C.N_SEG):
            s0, s1 = (j, j + 1) if t.up else (j + 1, j)
            pts.append((starts[t.idx][j], s0))
            pts.append((starts[t.idx][j] + rt, s1))
        out.append({"train": t.idx, "op": t.op, "fast": t.fast, "points": pts, "request": t.request})
    return out
