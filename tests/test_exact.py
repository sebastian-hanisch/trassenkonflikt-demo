"""CP-SAT gegen Vollaufzählung aller Reihenfolgen der Serienplanung (für reguläre Ziele liefert sie ein Optimum) und Eigenschaften der fairen Lösung."""
import itertools
import math

import pytest

import trs_exact as X
import trs_model as M


def small(n, seed, seg=2):
    return M.generate(n, 3, seg, 40, seed, [40, 35, 25]), seg


def operation_orders(n_trains, n_seg):
    """Alle Reihenfolgen der Operationen (Zug, k-ter Abschnitt seiner Route), in denen jeder Zug seine Abschnitte nacheinander abarbeitet."""
    def rec(counts, seq):
        if all(c == n_seg for c in counts):
            yield list(seq)
            return
        for i, c in enumerate(counts):
            if c < n_seg:
                counts[i] += 1
                seq.append((i, c))
                yield from rec(counts, seq)
                seq.pop()
                counts[i] -= 1
    yield from rec([0] * n_trains, [])


def schedule_by_operations(tr, seg, clear, ops):
    """Unabhängige Referenz: Operationen in der gegebenen Reihenfolge jeweils frühestmöglich (mit Lückenfüllen) einplanen."""
    occ = [[] for _ in range(seg)]
    starts = {t.idx: {} for t in tr}
    ready = {t.idx: t.request for t in tr}
    for i, k in ops:
        t = tr[i]
        j = M.route(t, seg)[k]
        rt = M.run_time(t.fast)
        s = M.free_slot(occ[j], ready[i], rt + clear)
        occ[j].append((s, s + rt + clear))
        occ[j].sort()
        starts[i][j] = s
        ready[i] = s + rt
    return starts


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_total_delay_optimum_equals_the_best_operation_order(seed):
    tr, seg = small(4, seed)
    best = min(M.metrics(tr, seg, schedule_by_operations(tr, seg, 2, ops), 3)["total"] for ops in operation_orders(len(tr), seg))
    r = X.solve(tr, seg, 2, "total", 20.0)
    assert r["status"] == "OPTIMAL" and M.valid_schedule(tr, seg, 2, r["starts"])
    assert M.metrics(tr, seg, r["starts"], 3)["total"] == best


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_minmax_optimum_equals_the_best_operation_order_and_fair_total_keeps_it(seed):
    tr, seg = small(4, seed)
    best = min(math.ceil(M.metrics(tr, seg, schedule_by_operations(tr, seg, 2, ops), 3)["max_avg"] - 1e-9) for ops in operation_orders(len(tr), seg))
    mm = X.solve(tr, seg, 2, "minmax", 20.0)
    assert mm["status"] == "OPTIMAL" and int(round(mm["obj"])) == best
    ft = X.solve(tr, seg, 2, "fair_total", 20.0)
    assert ft["status"] == "OPTIMAL" and M.valid_schedule(tr, seg, 2, ft["starts"])
    m_ft = M.metrics(tr, seg, ft["starts"], 3)
    assert math.ceil(m_ft["max_avg"] - 1e-9) <= best                           # Fairness gehalten
    opt = M.metrics(tr, seg, X.solve(tr, seg, 2, "total", 20.0)["starts"], 3)
    assert m_ft["total"] >= opt["total"]                                       # Fairness kostet nie weniger als das Optimum


def test_train_by_train_rules_can_miss_the_optimum_because_they_cannot_interleave_trains():
    """Die Regeln planen Zug für Zug (ganze Trasse); das Optimum darf Züge in einzelnen Abschnitten verzahnen. Auf mindestens einem kleinen Netz ist das Optimum
    strikt besser als jede Zug-Reihenfolge - sonst wäre der Abstand der Regeln nur eine Frage der Reihenfolge."""
    strictly = 0
    for seed in range(1, 15):
        tr, seg = M.generate(5, 3, 3, 60, seed, [40, 35, 25]), 3
        best_order = min(M.metrics(tr, seg, M.dispatch(tr, seg, 2, list(p)), 3)["total"] for p in itertools.permutations(range(5)))
        opt = M.metrics(tr, seg, X.solve(tr, seg, 2, "total", 20.0)["starts"], 3)["total"]
        assert opt <= best_order
        strictly += opt < best_order
    assert strictly >= 1


def test_objectives_and_errors():
    tr, seg = small(4, 1)
    assert set(X.OBJECTIVES) == {"total", "minmax", "fair_total"}
    with pytest.raises(ValueError):
        X.solve(tr, seg, 2, "unbekannt")


def test_every_heuristic_is_never_better_than_the_optimum():
    for seed in (5, 6, 7):
        tr, seg = M.generate(6, 3, 4, 60, seed, [40, 35, 25]), 4
        opt = X.solve(tr, seg, 2, "total", 20.0)
        o = M.metrics(tr, seg, opt["starts"], 3)["total"]
        for order in (M.order_fcfs(tr), M.order_priority(tr, 0), M.improve_order(tr, seg, 2, M.order_fcfs(tr), 3)):
            assert M.metrics(tr, seg, M.dispatch(tr, seg, 2, order), 3)["total"] >= o
        assert opt["bound"] <= o + 1e-6
