"""Preset-Kriterien mit künstlichen Werten: jedes Kriterium kippt einzeln an seiner Schwelle."""
import pytest

import trs_constants as C
import trs_stories as S

GOOD = {"proven": True, "over_fcfs": 50.0, "fair_pct": 3.0, "sweep_over_fcfs": 58.0, "sweep_over_fair": 3.3, "n_trains": 8, "opt_total": 130, "ref_opt_total": 100,
        "sweep_total_opt_6": 60, "sweep_total_opt_8": 90, "sweep_total_opt_10": 150, "sweep_total_opt_clear3": 100, "spread_prio": 40.0, "spread_fair": 5.0,
        "sweep_spread_prio_70": 33.0, "sweep_spread_fair_70": 4.0}
# Kennung -> (Schlüssel, falscher Wert, richtiger Wert); Kriterien mit mehreren Ausprägungen (sweep_grows) stehen im eigenen Test
FLIPS = {
    "proven": ("proven", False, True), "rule_costs": ("over_fcfs", 19.9, 20.0), "fair_cheap": ("fair_pct", 10.0, 9.9), "sweep_rule_costs": ("sweep_over_fcfs", 39.9, 40.0),
    "sweep_fair_cheap": ("sweep_over_fair", 6.0, 5.9), "ten_trains": ("n_trains", 9, 10), "more_delay": ("opt_total", 100, 101), "sweep_grows": None,
    "six_trains": ("n_trains", 7, 6), "less_delay": ("opt_total", 100, 99), "sweep_smaller": ("sweep_total_opt_6", 90, 89), "prio_unfair": ("spread_prio", 14.9, 15.0),
    "fair_narrow": ("spread_fair", 20.1, 20.0), "sweep_unfair": ("sweep_spread_fair_70", 11.1, 11.0),
}
PRESET_FACTS = {"Standard": {}, "Dichter Verkehr": {"n_trains": 10}, "Dünner Verkehr": {"n_trains": 6, "opt_total": 70}, "Dominanter Operator": {}, "Enge Räumzeit": {}}


def facts(name):
    return {**GOOD, **PRESET_FACTS[name]}


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_good_facts_satisfy_every_criterion_of_the_preset(name):
    assert all(ok for _, _, ok in S.check(name, facts(name)))


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_each_criterion_flips_alone_at_its_threshold(name):
    for cid, _, _ in S.check(name, facts(name)):
        flip = FLIPS[cid]
        if flip is None:
            continue
        key, bad, good = flip
        for value, expect in ((bad, False), (good, True)):
            f = {**facts(name), key: value}
            if name == "Dünner Verkehr" and key == "opt_total":
                f["ref_opt_total"] = 100
            outcome = {c: ok for c, _, ok in S.check(name, f)}
            assert outcome[cid] is expect, (name, cid, key, value)
            assert all(ok for c, ok in outcome.items() if c != cid), (name, cid)


def test_sweep_growth_criteria_flip_on_each_ordering():
    ok = lambda name, **kw: dict((c, o) for c, _, o in S.check(name, {**facts(name), **kw}))["sweep_grows"]
    assert ok("Dichter Verkehr") and not ok("Dichter Verkehr", sweep_total_opt_10=90) and not ok("Dichter Verkehr", sweep_total_opt_6=90)
    assert not ok("Enge Räumzeit", sweep_total_opt_clear3=90) and ok("Enge Räumzeit", sweep_total_opt_clear3=91)


def test_every_criterion_has_a_readable_text_and_a_flip():
    ids = {cid for crit in S.CRITERIA.values() for cid, _, _ in crit}
    assert ids == set(FLIPS) and all(len(text) > 15 for crit in S.CRITERIA.values() for _, text, _ in crit)
