"""Abnahmekriterien der Presets: jedes Preset erzählt eine Geschichte, die am gezeigten Netz UND an der Messreihe überprüfbar ist.

Reine Funktionen einfacher Zahlen (`facts`), damit Tests sie mit künstlichen Werten einzeln an ihrer Schwelle kippen können; `facts_for` baut die Zahlen aus einer Live-Rechnung,
dem Standard-Lauf auf demselben Seed und der Ergebnisdatei. `tools/preset_search.py` sucht damit einen Seed außerhalb der Messreihen-Seeds, bei dem alle Kriterien aller Presets gelten.
"""
from __future__ import annotations

import trs_evaluation as E
import trs_results as R

CRITERIA = {
    "Standard": [
        ("proven", "Optimum und faire Lösung bewiesen", lambda f: f["proven"]),
        ("rule_costs", "Erstanmelder liegt mindestens 20 % über dem Optimum", lambda f: f["over_fcfs"] >= 20.0),
        ("fair_cheap", "Fairness kostet weniger als 10 % des Optimums", lambda f: f["fair_pct"] < 10.0),
        ("sweep_rule_costs", "Messreihe: Erstanmelder im Mittel mindestens 40 % über dem Optimum", lambda f: f["sweep_over_fcfs"] >= 40.0),
        ("sweep_fair_cheap", "Messreihe: Fairness im Mittel unter 6 % über dem Optimum", lambda f: f["sweep_over_fair"] < 6.0),
    ],
    "Dichter Verkehr": [
        ("proven", "Optimum und faire Lösung bewiesen", lambda f: f["proven"]),
        ("ten_trains", "das Netz hat 10 Züge", lambda f: f["n_trains"] == 10),
        ("more_delay", "Optimum verspätet mehr als im Standardfall", lambda f: f["opt_total"] > f["ref_opt_total"]),
        ("sweep_grows", "Messreihe: Verspätung des Optimums wächst von 6 über 8 auf 10 Züge", lambda f: f["sweep_total_opt_6"] < f["sweep_total_opt_8"] < f["sweep_total_opt_10"]),
    ],
    "Dünner Verkehr": [
        ("proven", "Optimum und faire Lösung bewiesen", lambda f: f["proven"]),
        ("six_trains", "das Netz hat 6 Züge", lambda f: f["n_trains"] == 6),
        ("less_delay", "Optimum verspätet weniger als im Standardfall", lambda f: f["opt_total"] < f["ref_opt_total"]),
        ("sweep_smaller", "Messreihe: Verspätung des Optimums bei 6 Zügen unter der bei 8", lambda f: f["sweep_total_opt_6"] < f["sweep_total_opt_8"]),
    ],
    "Dominanter Operator": [
        ("proven", "Optimum und faire Lösung bewiesen", lambda f: f["proven"]),
        ("prio_unfair", "Vorrang spreizt die Operatoren um mindestens 15 min", lambda f: f["spread_prio"] >= 15.0),
        ("fair_narrow", "die faire Lösung spreizt höchstens halb so stark wie Vorrang", lambda f: f["spread_fair"] <= 0.5 * f["spread_prio"]),
        ("sweep_unfair", "Messreihe (Anteil A 70 %): Vorrang spreizt mindestens dreimal so stark wie fair", lambda f: f["sweep_spread_prio_70"] >= 3 * f["sweep_spread_fair_70"]),
    ],
    "Enge Räumzeit": [
        ("proven", "Optimum und faire Lösung bewiesen", lambda f: f["proven"]),
        ("more_delay", "Optimum verspätet mehr als im Standardfall (2 min Räumzeit)", lambda f: f["opt_total"] > f["ref_opt_total"]),
        ("sweep_grows", "Messreihe: Verspätung des Optimums bei 3 min Räumzeit über der bei 2 min", lambda f: f["sweep_total_opt_clear3"] > f["sweep_total_opt_8"]),
    ],
}


def sweep_facts(res: dict) -> dict:
    v = {x["name"]: x for x in R.all_variants(res)}
    return {"sweep_over_fcfs": v["Standard (8 Züge)"]["over_fcfs"], "sweep_over_fair": v["Standard (8 Züge)"]["over_fair"],
            "sweep_total_opt_6": v["6 Züge"]["total_opt"], "sweep_total_opt_8": v["Standard (8 Züge)"]["total_opt"], "sweep_total_opt_10": v["10 Züge"]["total_opt"],
            "sweep_spread_prio_70": v["Anteil A 70 %"]["spread_prio"], "sweep_spread_fair_70": v["Anteil A 70 %"]["spread_fair"],
            "sweep_total_opt_clear3": v["Räumzeit 3 min"]["total_opt"]}


def facts_for(run: dict, ref_run: dict, res: dict) -> dict:
    """Zahlen des Live-Laufs, des Standard-Laufs auf demselben Seed (`ref_run`) und der Messreihe."""
    r = run["results"]
    return {**sweep_facts(res), "proven": run["proven"], "n_trains": len(run["trains"]), "over_fcfs": E.over_opt_pct(run, "fcfs"), "fair_pct": E.fairness_price(run)["pct"],
            "opt_total": r["opt"]["metrics"]["total"], "ref_opt_total": ref_run["results"]["opt"]["metrics"]["total"], "spread_prio": r["prio"]["metrics"]["spread"],
            "spread_fair": r["fair"]["metrics"]["spread"]}


def check(name: str, facts: dict) -> list:
    """[(Kennung, Text, erfüllt)] aller Kriterien des Presets."""
    return [(cid, text, bool(fn(facts))) for cid, text, fn in CRITERIA[name]]
