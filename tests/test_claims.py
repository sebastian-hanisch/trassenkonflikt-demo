"""Jede Zahl aus dem README wird hier aus data/trs_results.json nachgerechnet; die formatierten Texte müssen im README stehen.

20 Netze je Variante (Seeds 100-119); Abstände zum Optimum nur über Netze, in denen Optimum und faire Lösung bewiesen sind. Das CP-SAT-Optimum der Gesamtverspätung ist eindeutig, die
Spreizung der einen zurückgegebenen Lösung nicht: die Zahlen stehen als Messung in der Ergebnisdatei.
"""
from pathlib import Path

import pytest

import trs_constants as C
import trs_evaluation as E
import trs_results as R
import trs_stories as S

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def res():
    return R.load_results()


@pytest.fixture(scope="module")
def v(res):
    return {x["name"]: x for x in R.all_variants(res)}


def pm(x, se, digits=0):
    return f"{x:.{digits}f} ± {se:.{digits}f} %"


def test_meta_and_counts(res):
    assert res["meta"]["seeds"] == [100, 120] and res["meta"]["variants"] == [x[0] for x in C.SWEEP_VARIANTS]
    for name in res["meta"]["variants"]:
        assert len(R.rows_of(res, name)) == 20
    assert all(m["valid"] for r in res["rows"] for m in r["methods"].values())                 # jeder Fahrplan der Messreihe ist zulässig
    assert "Port 8960" in README


def test_standard_costs_of_the_rules_in_the_readme(v):
    s = v["Standard (8 Züge)"]
    assert pm(s["over_fcfs"], s["over_fcfs_se"]) in README and pm(s["over_prio"], s["over_prio_se"]) in README and pm(s["over_search"], s["over_search_se"]) in README
    assert pm(v["Vorrang für B"]["over_prio"], v["Vorrang für B"]["over_prio_se"]) in README and pm(v["Vorrang für C"]["over_prio"], v["Vorrang für C"]["over_prio_se"]) in README
    assert pm(v["6 Züge"]["over_search"], v["6 Züge"]["over_search_se"]) in README and pm(v["10 Züge"]["over_search"], v["10 Züge"]["over_search_se"]) in README


def test_price_of_fairness_in_the_readme(v):
    s = v["Standard (8 Züge)"]
    assert pm(s["over_fair"], s["over_fair_se"], 1) in README and f"in {s['fair_cheaper_than_5pct']} von 20 Netzen unter 5 %" in README
    assert pm(v["6 Züge"]["over_fair"], v["6 Züge"]["over_fair_se"], 1) in README and pm(v["10 Züge"]["over_fair"], v["10 Züge"]["over_fair_se"], 1) in README
    assert all(x["over_fair"] < 10 for x in v.values())                                          # Fairness kostet in jeder Variante im Mittel unter 10 %


def test_the_rules_cost_far_more_than_fairness_in_every_variant(v):
    for name, x in v.items():
        assert x["over_fcfs"] > 40 and x["over_prio"] > 50 and x["over_search"] < x["over_fcfs"] / 2 and x["over_fair"] < x["over_search"], name


def test_spreads_in_the_readme(v):
    s = v["Standard (8 Züge)"]
    assert f"**{s['spread_prio']:.1f} min**" in README and f"**{s['spread_fair']:.1f} min**" in README
    assert f"Erstanmelder {s['spread_fcfs']:.1f} min" in README and f"Optimum {s['spread_opt']:.1f} min" in README
    for name, x in v.items():
        assert x["spread_prio"] > 1.5 * x["spread_fair"], name                               # Vorrang spreizt in jeder Variante deutlich stärker als fair


def test_size_and_clearance_effects_in_the_readme(v):
    assert " / ".join(f"{v[n]['total_opt']:.1f}" for n in ("6 Züge", "Standard (8 Züge)", "10 Züge")) + " min" in README
    assert " / ".join(f"{v[n]['over_fcfs']:.0f}" for n in ("6 Züge", "Standard (8 Züge)", "10 Züge")) + " %" in README
    assert " / ".join(f"{v[n]['total_opt']:.1f}" for n in ("Räumzeit 1 min", "Standard (8 Züge)", "Räumzeit 3 min")) + " min" in README
    assert " / ".join(f"{v[n]['over_fcfs']:.0f}" for n in ("Räumzeit 1 min", "Standard (8 Züge)", "Räumzeit 3 min")) + " %" in README
    assert v["6 Züge"]["total_opt"] < v["Standard (8 Züge)"]["total_opt"] < v["10 Züge"]["total_opt"] and v["Räumzeit 1 min"]["total_opt"] < v["Räumzeit 3 min"]["total_opt"]


def test_solver_times_and_proofs_in_the_readme(v):
    assert f"{v['6 Züge']['time_median']:.1f} s (6 Züge), {v['Standard (8 Züge)']['time_median']:.1f} s (8 Züge), {v['10 Züge']['time_median']:.1f} s (10 Züge)" in README
    assert f"nur {v['10 Züge']['proven']} von 20" in README and f"in {v['10 Züge']['proven']} von 20 Netzen bewiesen" in README
    assert all(v[n]["proven"] == 20 for n in v if n != "10 Züge")


def test_orderings_exact(res):
    for r in res["rows"]:
        if not R.proven(r):
            continue
        m = r["methods"]
        assert m["opt"]["total"] <= m["search"]["total"] <= m["fcfs"]["total"] and m["opt"]["total"] <= m["prio"]["total"] and m["opt"]["total"] <= m["fair"]["total"]
        assert m["fair"]["max_avg"] <= m["opt"]["max_avg"] + 1e-9


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_tells_its_story_on_the_shown_network(res, name):
    p = C.PRESETS[name]
    settings = {k: p[k] for k in ("trains", "clear", "share", "favoured", "seed")}
    ref = E.run_live({**{k: C.PRESETS["Standard"][k] for k in ("trains", "clear", "share", "favoured")}, "seed": p["seed"]})
    run = ref if name == "Standard" else E.run_live(settings)
    failed = [text for _, text, ok in S.check(name, S.facts_for(run, ref, res)) if not ok]
    assert not failed, (name, failed)
