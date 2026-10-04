"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Randwerte, Würfel-Knopf, Permalink, Abschnitte, Exakt-Tab, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import trs_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def _has_metric(at, label):
    return any(m.label == label for m in at.metric)


OPT = "Optimum: Gesamtverspätung"


def test_default_run_has_no_exception_and_shows_the_main_metrics():
    at = _run()
    _ok(at)
    for label in (OPT, "Erstanmelder (FCFS)", "Reihenfolge verbessert", "Fair (Min-Max, dann Summe)"):
        assert _has_metric(at, label), label
    assert at.session_state["trains_select"] == C.DEFAULT_TRAINS and at.session_state["seed_input"] == C.DEFAULT_SEED
    assert any("Fairness kostet" in s.value for s in list(at.success) + list(at.info))
    assert any("Vorrang für Operator A" in i.value for i in at.info)


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_button_runs_and_sets_the_controls(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["trains_select"] == p["trains"] and at.session_state["clear_select"] == p["clear"] and at.session_state["share_select"] == p["share"]
    assert at.session_state["favoured_select"] == p["favoured"] and at.session_state["seed_input"] == p["seed"] and _has_metric(at, OPT)


@pytest.mark.parametrize("kw", [dict(trains_select=6), dict(trains_select=10), dict(clear_select=1), dict(clear_select=3), dict(share_select=30), dict(share_select=70),
                                 dict(favoured_select=1), dict(favoured_select=2), dict(seed_input=C.SEED_MIN), dict(seed_input=C.SEED_MAX),
                                 dict(view_select="opt"), dict(view_select="fair"), dict(view_select="search")])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_more_trains_and_other_favoured_operator_change_the_result():
    std = _run()
    assert _metric(std, OPT) != _metric(_run(trains_select=6), OPT)
    a, b = _run(favoured_select=0), _run(favoured_select=1)
    text_a = next(i.value for i in a.info if "Vorrang für Operator" in i.value)
    text_b = next(i.value for i in b.info if "Vorrang für Operator" in i.value)
    assert "Operator A" in text_a and "Operator B" in text_b and text_a != text_b


def test_dice_button_changes_the_seed_and_the_network():
    at = _run()
    old_seed, old = at.session_state["seed_input"], _metric(at, OPT)
    next(b for b in at.button if b.label == "🎲 Neues Netz würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old_seed and _metric(at, OPT) != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["trains"] = "9"
    at.query_params["clear"] = "5"
    at.query_params["share"] = "65"
    at.query_params["view"] = "opt"
    at.query_params["seed"] = "99999"
    at.run()
    _ok(at)
    s = at.session_state
    assert s["trains_select"] == 8 and s["clear_select"] == 3 and s["share_select"] == 60 and s["view_select"] == "opt" and s["seed_input"] == C.SEED_MAX


def test_permalink_ignores_garbage_and_roundtrips():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["trains"] = "viele"
    at.query_params["view"] = "unbekannt"
    at.run()
    _ok(at)
    assert at.session_state["trains_select"] == C.DEFAULT_TRAINS and at.session_state["view_select"] == C.DEFAULT_VIEW
    next(b for b in at.button if b.key == "preset_Dominanter Operator").click().run()
    qp = at.query_params
    at2 = AppTest.from_file(APP, default_timeout=300)
    for k in ("trains", "clear", "share", "fav", "seed", "view"):
        at2.query_params[k] = qp[k]
    at2.run()
    _ok(at2)
    p = C.PRESETS["Dominanter Operator"]
    assert at2.session_state["share_select"] == p["share"] and at2.session_state["favoured_select"] == p["favoured"]


def test_sections_expanders_and_charts_are_present():
    at = _run()
    _ok(at)
    headers = [s.value for s in at.subheader] + [m.value for m in at.markdown]
    assert any("Was die Messreihe zeigt" in h for h in headers) and any("Was kostet die Regel" in h for h in headers) and any("Bildfahrplan" in h for h in headers)
    titles = [e.label for e in at.expander]
    assert "🔧 Wie wir das erreichen – vollständiger Methodenvergleich" in titles and "Wie funktioniert diese Demo?" in titles and "📐 Mathematische Formulierung" in titles
    assert [t.label for t in at.tabs] == ["🚂 Regeln", "🧮 Exakt (OR-Tools)", "📈 Messreihe"]
    assert len(at.get("plotly_chart")) == 5          # Balken je Operator, Streudiagramm, Bildfahrplan, zwei Messreihen-Diagramme


def test_exact_tab_runs_cpsat_on_the_current_network():
    at = _run(trains_select=6)
    _ok(at)
    next(b for b in at.button if b.key == "exact_button").click().run()
    _ok(at)
    assert _has_metric(at, "Gesamtverspätung") and _has_metric(at, "Schranke") and _has_metric(at, "Status")
    assert _metric(at, "Status") == "bewiesen optimal"
    at.select_slider(key="trains_select").set_value(8).run()
    assert not _has_metric(at, "Schranke") and any("erneut lösen" in c.value for c in at.caption)


def test_seed_control_uses_the_portfolio_wording():
    assert [n.label for n in _run().number_input] == ["Zufalls-Seed"]


def test_related_demos_are_linked_and_footer_is_present():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("taktfahrplan-demo", "crew-pairing-demo", "job-shop-demo"):
        assert name in text
    assert "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in text
    assert "geplant" not in text and "noch nicht" not in text
