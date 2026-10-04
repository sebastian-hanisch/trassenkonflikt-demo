"""Gezielte Tests für Stellen, die der Fehler-Einbau-Test (tools/mutation_check.py) zuerst nicht fand: Grenzen des Prüfers, eingefrorene Züge, Meldung auf der Schwelle,
Zeitlimit-Pfad (nicht bewiesen), Bildfahrplan-Zeitpunkte, Nennung des am stärksten verspäteten Operators."""
import pytest

import trs_constants as C
import trs_evaluation as E
import trs_exact as X
import trs_model as M
from trs_model import Train


def mini():
    return [Train(0, 0, True, True, 0), Train(1, 1, False, False, 0), Train(2, 0, True, False, 5)]


def test_validator_rejects_a_start_one_minute_before_the_train_left_the_previous_section():
    tr = mini()
    ok = M.dispatch(tr, 2, 2, [0, 1, 2])
    early = {i: dict(v) for i, v in ok.items()}
    early[0][1] = 5                                   # Zug 0 verlässt Abschnitt 0 erst bei 6
    assert not M.valid_schedule(tr, 2, 2, early)
    exact = {i: dict(v) for i, v in ok.items()}
    exact[0][1] = 6
    assert M.valid_schedule(tr, 2, 2, exact)


def test_validator_counts_the_clearance_time_on_both_sides():
    tr = [Train(0, 0, True, True, 0), Train(1, 0, True, True, 0)]
    one_apart = {0: {0: 0}, 1: {0: 7}}              # Zug 0 belegt [0, 8): Start 7 überschneidet sich um 1 min
    assert not M.valid_schedule(tr, 1, 2, one_apart)
    assert M.valid_schedule(tr, 1, 2, {0: {0: 0}, 1: {0: 8}})


def test_generator_is_frozen_down_to_direction_and_class():
    tr = M.generate(8, 3, 5, 120, 100, [50, 30, 20])
    assert [(t.op, t.up, t.fast, t.request) for t in tr] == [(1, True, True, 60), (0, True, True, 65), (2, False, False, 70), (0, True, False, 80), (0, True, False, 90),
                                                            (2, True, False, 95), (0, True, True, 100), (0, True, True, 110)]
    big = M.generate(3000, 3, 5, 120, 7, [50, 30, 20])
    assert abs(sum(t.up for t in big) / 3000 - 0.5) < 0.03
    fast = [sum(t.fast for t in big if t.op == o) / max(1, sum(1 for t in big if t.op == o)) for o in range(3)]
    assert all(abs(f - e) < 0.05 for f, e in zip(fast, (0.6, 0.3, 0.3)))


def run_with(**over):
    run = E.run_live({"trains": 6, "clear": 2, "share": 50, "favoured": 0, "seed": 500})
    return {**run, **over}


def test_fairness_message_exactly_on_the_threshold_is_costly(monkeypatch):
    run = run_with()
    monkeypatch.setattr(C, "FAIR_SMALL_PCT", 0.0)
    same = {**run, "results": {**run["results"], "fair": {**run["results"]["fair"], "metrics": run["results"]["opt"]["metrics"]}}}
    assert E.fairness_price(same)["pct"] == 0.0 and E.fairness_message(same)[0] == "costly"
    monkeypatch.setattr(C, "FAIR_SMALL_PCT", 1e-9)
    assert E.fairness_message(same)[0] == "cheap"


def test_priority_message_names_the_operator_with_the_longest_average_delay():
    run = run_with()
    avg = run["results"]["prio"]["metrics"]["avg"]
    present = [o for o in range(3) if any(t.op == o for t in run["trains"])]
    worst = max(present, key=lambda o: avg[o])
    assert f"wartet {C.op_name(worst)} im Mittel {avg[worst]:.0f} min" in E.priority_message(run, 0)


def test_time_limit_path_reports_unproven_results_and_keeps_the_status():
    run = E.run_live({"trains": 10, "clear": 2, "share": 50, "favoured": 0, "seed": 506}, cp_limit=0.02)
    assert not run["proven"] and E.fairness_message(run)[0] == "unproven"
    assert any(run["results"][k]["status"] != "OPTIMAL" for k in ("opt", "fair")) and all(v["valid"] for v in run["results"].values())


def test_fair_solution_never_costs_more_than_minmax_alone_and_sometimes_strictly_less():
    strictly = 0
    for seed in range(1, 12):
        tr = M.generate(5, 3, 3, 60, seed, [40, 35, 25])
        fair = M.metrics(tr, 3, X.solve(tr, 3, 2, "fair_total", 20.0)["starts"], 3)["total"]
        mm = M.metrics(tr, 3, X.solve(tr, 3, 2, "minmax", 20.0)["starts"], 3)["total"]
        assert fair <= mm
        strictly += fair < mm
    assert strictly >= 1


def test_every_diagram_point_starts_at_the_scheduled_entry_time():
    run = run_with()
    starts = run["results"]["fcfs"]["starts"]
    for tr, t in zip(E.segment_intervals(run["trains"], starts, 2), run["trains"]):
        entries = [starts[t.idx][j] for j in M.route(t, C.N_SEG)]
        assert [p[0] for p in tr["points"][0::2]] == entries
        assert [p[0] for p in tr["points"][1::2]] == [e + M.run_time(t.fast) for e in entries]


def test_fast_class_probability_has_exact_bounds():
    assert not any(t.fast for t in M.generate(3000, 3, 5, 120, 7, [50, 30, 20], fast_pct=(0, 0, 0)))
    assert all(t.fast for t in M.generate(3000, 3, 5, 120, 7, [50, 30, 20], fast_pct=(100, 100, 100)))


def test_fair_solution_holds_the_minmax_bound_on_eight_train_nets():
    import math
    for seed in range(100, 104):
        tr = M.generate(8, 3, 5, 120, seed, [50, 30, 20])
        mm = X.solve(tr, 5, 2, "minmax", 20.0)
        ft = X.solve(tr, 5, 2, "fair_total", 20.0)
        assert mm["status"] == ft["status"].split(" ")[0] == "OPTIMAL"
        assert math.ceil(M.metrics(tr, 5, ft["starts"], 3)["max_avg"] - 1e-9) <= int(round(mm["obj"]))


def test_live_fair_method_is_the_two_stage_solution_not_minmax_alone():
    strictly = 0
    for seed in range(500, 508):
        run = E.run_live({"trains": 6, "clear": 2, "share": 50, "favoured": 0, "seed": seed})
        tr = run["trains"]
        mm_total = M.metrics(tr, C.N_SEG, X.solve(tr, C.N_SEG, 2, "minmax", 20.0)["starts"], C.N_OPS)["total"]
        assert run["results"]["fair"]["metrics"]["total"] <= mm_total
        strictly += run["results"]["fair"]["metrics"]["total"] < mm_total
    assert strictly >= 1
