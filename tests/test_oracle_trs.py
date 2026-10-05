"""Orakel-Tests: Serienplanung gegen eine Minutenraster-Simulation; CP-SAT gegen die Vollaufzählung aller Zugreihenfolgen je Abschnitt (disjunktiver Graph, längster Weg); Kennzahlen von Hand."""
import itertools
import math

import numpy as np
import pytest

import trs_constants as C
import trs_exact as X
import trs_model as M


def grid_dispatch(trains, n_seg, clear, order):
    """Belegung je Abschnitt als Minutenraster; Start = kleinste Minute, ab der Fahrzeit + Räumzeit am Stück frei sind."""
    occ = np.zeros((n_seg, 3000), dtype=bool)
    starts = {}
    for i in order:
        t = trains[i]
        now, rt, starts[i] = t.request, (6 if t.fast else 10), {}
        for j in (range(n_seg) if t.up else range(n_seg - 1, -1, -1)):
            s = now
            while occ[j, s:s + rt + clear].any():
                s += 1
            occ[j, s:s + rt + clear] = True
            starts[i][j] = s
            now = s + rt
    return starts


def earliest_by_orders(trains, n_seg, clear, perms):
    """Frühestmögliche Starts bei gegebener Zugreihenfolge je Abschnitt (längster Weg im disjunktiven Graphen); None bei Zyklus."""
    nT = len(trains)
    rt = [6 if t.fast else 10 for t in trains]
    route = [list(range(n_seg)) if t.up else list(range(n_seg - 1, -1, -1)) for t in trains]
    s = {(i, j): trains[i].request for i in range(nT) for j in range(n_seg)}
    for _ in range(nT * n_seg + 2):
        changed = False
        for i in range(nT):
            for a, b in zip(route[i], route[i][1:]):
                if s[(i, b)] < s[(i, a)] + rt[i]:
                    s[(i, b)] = s[(i, a)] + rt[i]
                    changed = True
        for j in range(n_seg):
            for a, b in zip(perms[j], perms[j][1:]):
                if s[(b, j)] < s[(a, j)] + rt[a] + clear:
                    s[(b, j)] = s[(a, j)] + rt[a] + clear
                    changed = True
        if not changed:
            return {i: {j: s[(i, j)] for j in range(n_seg)} for i in range(nT)}
    return None


def delays_of(trains, n_seg, starts):
    out = []
    for i, t in enumerate(trains):
        rt = 6 if t.fast else 10
        out.append(starts[i][(n_seg - 1) if t.up else 0] + rt - (t.request + rt * n_seg))
    return out


@pytest.mark.parametrize("seed", range(12))
def test_serial_dispatch_equals_the_minute_grid_simulation(seed):
    rng = np.random.default_rng(seed)
    n, seg, clear = int(rng.integers(3, 12)), int(rng.choice([2, 3, 5])), int(rng.integers(1, 4))
    tr = M.generate(n, 3, seg, int(rng.choice([30, 120])), seed * 7 + 1, C.shares_for(50), C.FAST_PCT)
    order = [int(x) for x in rng.permutation(n)]
    a = M.dispatch(tr, seg, clear, order)
    assert a == grid_dispatch(tr, seg, clear, order) and M.valid_schedule(tr, seg, clear, a)
    d = delays_of(tr, seg, a)
    m = M.metrics(tr, seg, a, 3)
    assert m["total"] == sum(d) and [m["delays"][i] for i in range(n)] == d
    avg = [np.mean([d[i] for i in range(n) if tr[i].op == o]) for o in range(3) if any(t.op == o for t in tr)]
    assert m["spread"] == pytest.approx(max(avg) - min(avg)) and m["jain"] == pytest.approx(sum(avg) ** 2 / (len(avg) * sum(a * a for a in avg)))


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_cp_sat_objectives_equal_the_enumeration_of_all_train_orders_per_section(seed):
    rng = np.random.default_rng(seed)
    n, seg, clear = 3, 3, int(rng.integers(1, 4))
    tr = M.generate(n, 3, seg, 20, int(rng.integers(0, 10**6)), C.shares_for(50), C.FAST_PCT)
    rows = []
    for combo in itertools.product(list(itertools.permutations(range(n))), repeat=seg):
        s = earliest_by_orders(tr, seg, clear, combo)
        if s is None:
            continue
        mm = M.metrics(tr, seg, s, 3)
        rows.append((sum(delays_of(tr, seg, s)), math.ceil(mm["max_avg"] - 1e-9)))
    best_total, best_mm = min(r[0] for r in rows), min(r[1] for r in rows)
    best_fair_total = min(r[0] for r in rows if r[1] <= best_mm)
    r1, r2, r3 = (X.solve(tr, seg, clear, o, 20.0) for o in ("total", "minmax", "fair_total"))
    assert r1["status"] == r2["status"] == r3["status"] == "OPTIMAL"
    assert M.metrics(tr, seg, r1["starts"], 3)["total"] == best_total
    assert round(r2["obj"]) == best_mm
    m3 = M.metrics(tr, seg, r3["starts"], 3)
    assert m3["total"] == best_fair_total and math.ceil(m3["max_avg"] - 1e-9) == best_mm
