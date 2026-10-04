"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).
Alle Regler sind immer sichtbar mit festen Grenzen - kein ausblendbarer Regler, kein KEPT-Muster."""

import random
from dataclasses import dataclass

import streamlit as st

import trs_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    options: tuple | None = None
    lo: int | None = None
    hi: int | None = None


SETTING_SPECS = {
    "trains_select": SettingSpec("trains", int, C.DEFAULT_TRAINS, C.TRAINS_OPTIONS),
    "clear_select": SettingSpec("clear", int, C.DEFAULT_CLEAR, C.CLEAR_OPTIONS),
    "share_select": SettingSpec("share", int, C.DEFAULT_SHARE, C.SHARE_OPTIONS),
    "favoured_select": SettingSpec("fav", int, C.DEFAULT_FAVOURED, C.FAVOURED_OPTIONS),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, None, C.SEED_MIN, C.SEED_MAX),
    "view_select": SettingSpec("view", str, C.DEFAULT_VIEW, C.VIEW_OPTIONS),
}
PRESET_KEYS = {"trains": "trains_select", "clear": "clear_select", "share": "share_select", "favoured": "favoured_select", "seed": "seed_input"}


def snap(options, value):
    """Nächste Stufe (bei Gleichstand die kleinere)."""
    return min(options, key=lambda o: (abs(o - value), o))


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if spec.caster is str:
                    if value not in spec.options:
                        continue
                elif spec.options is not None:
                    value = snap(spec.options, value)
                else:
                    value = max(spec.lo, min(spec.hi, value))
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(C.SEED_MIN, C.SEED_MAX)


def settings_from_state(values: dict) -> dict:
    return {"trains": int(values["trains_select"]), "clear": int(values["clear_select"]), "share": int(values["share_select"]),
            "favoured": int(values["favoured_select"]), "seed": int(values["seed_input"])}
