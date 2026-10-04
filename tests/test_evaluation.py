"""Live-Rechnung auf echten Netzen: alle Verfahren gültig, Ordnungen, Fairness-Preis, drei Meldungszustände, Bildfahrplan-Daten."""
import pytest

import trs_constants as C
import trs_evaluation as E
import trs_model as M

S = {"trains": 6, "clear": 2, "share": 50, "favoured": 0, "seed": 500}


@pytest.fixture(scope="module")
def run():
    return E.run_live(S)


def test_all_five_methods_are_valid_and_ordered(run):
    r = run["results"]
    assert tuple(r) == C.METHODS and run["proven"] and len(run["trains"]) == 6
    assert all(v["valid"] for v in r.values())
    tot = {k: v["metrics"]["total"] for k, v in r.items()}
    assert tot["opt"] <= tot["fair"] and tot["opt"] <= tot["search"] <= tot["fcfs"] and tot["opt"] <= tot["prio"]
    assert r["fair"]["metrics"]["max_avg"] <= r["opt"]["metrics"]["max_avg"] + 1e-9           # fair: nie ungleicher als das Optimum der Summe
    assert r["fcfs"]["status"] == "Regel" and r["opt"]["status"] == "OPTIMAL"


def test_run_is_deterministic(run):
    again = E.run_live(S)
    assert {k: v["metrics"]["total"] for k, v in again["results"].items()} == {k: v["metrics"]["total"] for k, v in run["results"].items()}


def test_percentages_use_the_optimum_as_base(run):
    r = run["results"]
    assert abs(E.over_opt_pct(run, "fcfs") - 100 * (r["fcfs"]["metrics"]["total"] / r["opt"]["metrics"]["total"] - 1)) < 1e-12
    p = E.fairness_price(run)
    assert p["minutes"] == r["fair"]["metrics"]["total"] - r["opt"]["metrics"]["total"] and p["minutes"] >= 0
    assert p["spread_fair"] <= p["spread_opt"] + 1.0 and E.over_opt_pct(run, "opt") == 0.0


def test_priority_favours_the_chosen_operator():
    a = E.run_live({**S, "favoured": 0})
    b = E.run_live({**S, "favoured": 1})
    present = [o for o in range(3) if any(t.op == o for t in a["trains"])]
    assert 0 in present and 1 in present
    assert a["results"]["prio"]["metrics"]["avg"][0] <= b["results"]["prio"]["metrics"]["avg"][0] + 1e-9
    assert b["results"]["prio"]["metrics"]["avg"][1] <= a["results"]["prio"]["metrics"]["avg"][1] + 1e-9
    assert a["results"]["fcfs"]["metrics"]["total"] == b["results"]["fcfs"]["metrics"]["total"]          # FCFS hängt nicht vom Vorrang ab


def test_three_message_states(run):
    state, text = E.fairness_message(run)
    assert state in ("cheap", "costly") and "Spreizung" in text
    cheap = {**run, "results": {**run["results"], "fair": {**run["results"]["fair"], "metrics": {**run["results"]["fair"]["metrics"], "total": run["results"]["opt"]["metrics"]["total"] * 1.05}}}}
    assert E.fairness_message(cheap)[0] == "cheap"
    costly = {**cheap, "results": {**cheap["results"], "fair": {**cheap["results"]["fair"], "metrics": {**cheap["results"]["fair"]["metrics"], "total": run["results"]["opt"]["metrics"]["total"] * 1.20}}}}
    assert E.fairness_message(costly)[0] == "costly"
    assert E.fairness_message({**costly, "proven": False})[0] == "unproven" and "Zeitlimit" in E.fairness_message({**costly, "proven": False})[1]
    boundary = {**cheap, "results": {**cheap["results"], "fair": {**cheap["results"]["fair"], "metrics": {**cheap["results"]["fair"]["metrics"], "total": run["results"]["opt"]["metrics"]["total"] * (1 + C.FAIR_SMALL_PCT / 100)}}}}
    assert E.fairness_message(boundary)[0] == "costly"                          # genau auf der Schwelle gilt nicht mehr als „fast umsonst“


def test_priority_message_names_the_worst_operator(run):
    text = E.priority_message(run, 0)
    assert "Vorrang für Operator A" in text and "über dem Optimum" in text


def test_timetable_points_follow_the_route_and_the_schedule(run):
    st = run["results"]["opt"]["starts"]
    segs = E.segment_intervals(run["trains"], st, S["clear"])
    assert len(segs) == len(run["trains"])
    for tr, t in zip(segs, run["trains"]):
        assert len(tr["points"]) == 2 * C.N_SEG and tr["points"][0][1] == (0 if t.up else C.N_SEG) and tr["points"][-1][1] == (C.N_SEG if t.up else 0)
        times = [p[0] for p in tr["points"]]
        assert times == sorted(times) and times[0] >= t.request
        assert tr["points"][-1][0] == M.arrivals(run["trains"], C.N_SEG, st)[t.idx]


def test_shares_for_sum_to_one_hundred():
    for a in C.SHARE_OPTIONS:
        s = C.shares_for(a)
        assert sum(s) == 100 and s[0] == a and s[1] > s[2] > 0
