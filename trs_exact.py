"""Exakte Trassenvergabe mit OR-Tools CP-SAT: Intervallmodell (je Zug und Abschnitt ein Intervall der Länge Fahrzeit + Räumzeit, je Abschnitt NoOverlap),
Ziele Gesamtverspätung, Min-Max der mittleren Verspätung je Operator, und Min-Max gefolgt von der kleinsten Gesamtverspätung bei gehaltener Fairness."""
from __future__ import annotations

import os

from ortools.sat.python import cp_model

from trs_model import free_run, route, run_time

OBJECTIVES = ("total", "minmax", "fair_total")


def build_model(trains: list, n_seg: int, clear: int, m_cap: int | None = None) -> dict:
    """Modell ohne Ziel. Rückgabe: model, starts, arrival, delay, sums, cnt, maxavg (nur wenn gewünscht), horizon."""
    model = cp_model.CpModel()
    horizon = max(t.request for t in trains) + 200 + 40 * len(trains)
    starts, arrival, per_seg = {}, {}, [[] for _ in range(n_seg)]
    for t in trains:
        prev_end = None
        starts[t.idx] = {}
        for j in route(t, n_seg):
            rt = run_time(t.fast)
            s = model.NewIntVar(0, horizon, f"s_{t.idx}_{j}")
            per_seg[j].append(model.NewFixedSizeIntervalVar(s, rt + clear, f"iv_{t.idx}_{j}"))
            model.Add(s >= (t.request if prev_end is None else prev_end))
            starts[t.idx][j] = s
            prev_end = s + rt
        arrival[t.idx] = prev_end
    for ivs in per_seg:
        model.AddNoOverlap(ivs)
    delay = {t.idx: model.NewIntVar(0, horizon, f"d_{t.idx}") for t in trains}
    for t in trains:
        model.Add(delay[t.idx] == arrival[t.idx] - (t.request + free_run(t, n_seg)))
    ops = sorted({t.op for t in trains})
    sums = {o: sum(delay[t.idx] for t in trains if t.op == o) for o in ops}
    cnt = {o: sum(1 for t in trains if t.op == o) for o in ops}
    maxavg = model.NewIntVar(0, horizon if m_cap is None else m_cap, "maxavg")
    for o in ops:
        model.Add(maxavg * cnt[o] >= sums[o])           # maxavg ist eine ganze Zahl: die kleinste ganze Zahl >= größte mittlere Verspätung
    return {"model": model, "starts": starts, "arrival": arrival, "delay": delay, "maxavg": maxavg, "horizon": horizon}


def _solve(model, time_limit: float, workers: int):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = 1
    return solver, solver.Solve(model)


def solve(trains: list, n_seg: int, clear: int, objective: str, time_limit: float = 20.0) -> dict:
    """Rückgabe: status ('OPTIMAL', 'FEASIBLE', ...), time, starts {Zug: {Abschnitt: Einfahrt}}, bound (Schranke des Ziels der letzten Stufe), obj."""
    if objective not in OBJECTIVES:
        raise ValueError(objective)
    workers = max(1, min(8, os.cpu_count() or 1))
    m = build_model(trains, n_seg, clear)
    total = sum(m["delay"].values())
    if objective == "total":
        m["model"].Minimize(total)
    else:
        m["model"].Minimize(m["maxavg"])
    solver, st = _solve(m["model"], time_limit, workers)
    status, t_used = solver.StatusName(st), solver.WallTime()
    if objective == "fair_total" and st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        m_star = int(round(solver.ObjectiveValue()))
        stage1 = status
        m = build_model(trains, n_seg, clear, m_cap=m_star)
        m["model"].Minimize(sum(m["delay"].values()))
        solver, st = _solve(m["model"], time_limit, workers)
        status = solver.StatusName(st) if stage1 == "OPTIMAL" else f"{solver.StatusName(st)} (Fairness nicht bewiesen)"
        t_used += solver.WallTime()
    out = {"status": status, "time": t_used}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        out.update({"starts": {i: {j: solver.Value(v) for j, v in sj.items()} for i, sj in m["starts"].items()}, "bound": solver.BestObjectiveBound(), "obj": solver.ObjectiveValue()})
    return out
