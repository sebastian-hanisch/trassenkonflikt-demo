"""Permalink-Einrasten, Presets und Konstanten-Konsistenz."""
import trs_constants as C
import trs_presets as PR
import trs_results as R


def test_snap_rounds_to_the_nearest_step_and_prefers_the_smaller_on_ties():
    assert PR.snap(C.TRAINS_OPTIONS, 7) == 6 and PR.snap(C.TRAINS_OPTIONS, 9) == 8 and PR.snap(C.TRAINS_OPTIONS, 99) == 10 and PR.snap(C.TRAINS_OPTIONS, 0) == 6
    assert PR.snap(C.SHARE_OPTIONS, 40) == 40 and PR.snap(C.SHARE_OPTIONS, 65) == 60 and PR.snap(C.SHARE_OPTIONS, 99) == 70 and PR.snap(C.CLEAR_OPTIONS, 5) == 3


def test_every_preset_sets_every_control_with_valid_values():
    assert set(C.PRESET_ORDER) == set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESET_ORDER) == 5
    for name, p in C.PRESETS.items():
        assert set(p) == set(PR.PRESET_KEYS)
        assert p["trains"] in C.TRAINS_OPTIONS and p["clear"] in C.CLEAR_OPTIONS and p["share"] in C.SHARE_OPTIONS and p["favoured"] in C.FAVOURED_OPTIONS
        assert C.SEED_MIN <= p["seed"] <= C.SEED_MAX and not (C.SWEEP_SEEDS.start <= p["seed"] < C.SWEEP_SEEDS.stop), name


def test_each_non_standard_preset_changes_the_levers_it_is_named_for():
    std = C.PRESETS["Standard"]
    changed = {n: sorted(k for k in std if k != "seed" and C.PRESETS[n][k] != std[k]) for n in C.PRESET_ORDER if n != "Standard"}
    assert changed == {"Dichter Verkehr": ["trains"], "Dünner Verkehr": ["trains"], "Dominanter Operator": ["favoured", "share"], "Enge Räumzeit": ["clear"]}
    assert len({p["seed"] for p in C.PRESETS.values()}) == 1 and std["seed"] == C.DEFAULT_SEED


def test_presets_with_a_sweep_variant_match_it():
    names = {n: R.variant_name({k: C.PRESETS[n][k] for k in ("trains", "clear", "share", "favoured")}) for n in C.PRESET_ORDER}
    assert names["Standard"] == "Standard (8 Züge)" and names["Dichter Verkehr"] == "10 Züge" and names["Dünner Verkehr"] == "6 Züge" and names["Enge Räumzeit"] == "Räumzeit 3 min"
    assert names["Dominanter Operator"] is None                                   # Anteil 70 % mit Vorrang B ist eine Kombination ohne eigene Messreihen-Zeile


def test_view_options_are_the_methods_and_settings_convert():
    assert tuple(C.VIEW_OPTIONS) == tuple(C.METHODS) and set(C.METHOD_LABELS) == set(C.METHODS) == set(C.METHOD_COLORS)
    s = PR.settings_from_state({"trains_select": 8, "clear_select": 2, "share_select": 50, "favoured_select": 1, "seed_input": 500.0})
    assert s == {"trains": 8, "clear": 2, "share": 50, "favoured": 1, "seed": 500}
