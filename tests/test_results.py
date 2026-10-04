"""Statistik der Messreihe an einer von Hand gerechneten Mini-Ergebnisdatei."""
import math

import pytest

import trs_results as R


def method(total, spread, status="OPTIMAL", avg=(10.0, 20.0, 30.0)):
    return {"total": total, "avg": list(avg), "max_avg": max(avg), "spread": spread, "jain": 0.9, "max_delay": 50, "status": status, "time": 1.0, "valid": True}


def row(variant, opt, fcfs, prio, search, fair, status="OPTIMAL", n=8, fair_status=None):
    return {"variant": variant, "seed": 1, "n": n, "ops": [3, 3, 2], "methods": {"fcfs": method(fcfs, 12), "prio": method(prio, 40), "search": method(search, 14), "opt": method(opt, 10, status),
                                                                       "fair": method(fair, 4, fair_status or status)}}


@pytest.fixture
def res():
    rows = [row("V", 100, 150, 180, 120, 104), row("V", 200, 300, 400, 240, 210), row("V", 50, 500, 500, 500, 500, status="FEASIBLE"), row("W", 100, 110, 120, 105, 101),
            row("W", 100, 110, 120, 105, 101, fair_status="FEASIBLE")]
    return {"meta": {"variants": ["V", "W"]}, "rows": rows}


def test_mean_se():
    m, se = R.mean_se([2.0, 4.0, 6.0])
    assert m == 4.0 and abs(se - 2.0 / math.sqrt(3)) < 1e-12 and math.isnan(R.mean_se([5.0])[1])


def test_proven_requires_optimum_and_fair_solution(res):
    assert [R.proven(r) for r in res["rows"]] == [True, True, False, True, False]        # letzte Zeile: Optimum bewiesen, faire Lösung nicht


def test_summary_uses_only_proven_rows_and_the_optimum_as_base(res):
    s = R.summary(res, "V")
    assert s["n"] == 3 and s["n_used"] == 2 and s["proven"] == 2
    # FCFS: 150/100 = +50 %, 300/200 = +50 %; Vorrang +80 % / +100 %; verbessert +20 % / +20 %; fair +4 % / +5 %
    assert abs(s["over_fcfs"] - 50.0) < 1e-9 and abs(s["over_prio"] - 90.0) < 1e-9 and abs(s["over_search"] - 20.0) < 1e-9 and abs(s["over_fair"] - 4.5) < 1e-9
    assert abs(s["over_prio_max"] - 100.0) < 1e-9 and s["fair_cheaper_than_5pct"] == 1      # +4 % zählt, +5 % genau auf der Schwelle nicht
    assert s["total_opt"] == 150 and s["spread_prio"] == 40 and s["spread_fair"] == 4 and s["time_median"] == 2.0 and s["trains"] == 8
    assert R.summary(res, "V", only_proven=False)["n_used"] == 3


def test_all_variants_and_variant_name(res):
    assert [v["name"] for v in R.all_variants(res)] == ["V", "W"]
    assert R.variant_name({"trains": 8, "clear": 2, "share": 50, "favoured": 0}) == "Standard (8 Züge)"
    assert R.variant_name({"trains": 8, "clear": 3, "share": 50, "favoured": 0}) == "Räumzeit 3 min" and R.variant_name({"trains": 8, "clear": 1, "share": 70, "favoured": 0}) is None
    assert R.variant_name({"trains": 8, "clear": 2, "share": 50, "favoured": 2}) == "Vorrang für C"
