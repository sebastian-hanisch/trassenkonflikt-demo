"""Trassenkonflikt: Wer bekommt die Strecke? - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Dritter Baustein der Reihe Bahn/Schienenverkehr: Auf einer eingleisigen Strecke wollen Züge mehrerer Bahnunternehmen im selben Zeitfenster fahren; jeder Abschnitt trägt
immer nur einen Zug. Die Demo vergleicht Regeln der Trassenvergabe (Erstanmelder, Vorrang), eine verbesserte Reihenfolge und die exakte Lösung mit CP-SAT - und fragt,
was Fairness zwischen den Unternehmen kostet.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import trs_constants as C
import trs_exact as X
import trs_model as M
import trs_results as R
from trs_evaluation import (fairness_message, fairness_price, over_opt_pct, priority_message, run_live)
from trs_pdf_export import generate_plan_pdf
from trs_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, settings_from_state,
                         sync_query_params)
from trs_visualization import build_method_scatter, build_operator_bars, build_spread_bars, build_sweep_bars, build_timetable

st.set_page_config(page_title="Trassenkonflikt – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _results():
    return R.load_results()


@st.cache_data(show_spinner=False)
def _live(trains, clear, share, favoured, seed):
    return run_live({"trains": trains, "clear": clear, "share": share, "favoured": favoured, "seed": seed})


st.title("🚦 Trassenkonflikt: Wer bekommt die Strecke?")
st.markdown(
    """
Auf einer **eingleisigen Strecke** wollen Züge mehrerer **Bahnunternehmen** im selben Zeitfenster fahren; ein Abschnitt trägt immer nur **einen** Zug, begegnen und überholen geht nur in den
Stationen. Wer fährt wann? Die Demo vergleicht **Regeln der Trassenvergabe** (der Erstanmelder fährt zuerst, oder ein Unternehmen hat Vorrang), eine **verbesserte Reihenfolge** und die **exakte Lösung**
(OR-Tools CP-SAT) und beantwortet zwei Fragen: **Was kostet die Regel gegenüber dem Optimum?** und **Was kostet Fairness zwischen den Unternehmen?**
"""
)
st.caption(
    "Dritter Baustein der Reihe Bahn/Schienenverkehr nach [Taktfahrplan](https://sebastianhanisch-taktfahrplan-demo.streamlit.app/) (dort stand die Mindest-Zugfolge nur als Vorgriff) und "
    "[Crew Pairing](https://sebastianhanisch-crew-pairing-demo.streamlit.app/). Strukturell ein Job-Shop mit Routen wie in "
    "[job-shop-demo](https://sebastianhanisch-job-shop-demo.streamlit.app/); neu ist die Frage nach der Fairness zwischen den Unternehmen."
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(3)
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i % 3]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.select_slider("Züge", options=C.TRAINS_OPTIONS, key="trains_select",
                     help=f"Zahl der Züge im Zeitfenster von {C.WINDOW} min auf der Strecke mit {C.N_SEG} Abschnitten (Stationen 0 bis {C.N_SEG}). Mit mehr Zügen nehmen die Konflikte stark zu.")
    st.select_slider("Räumzeit je Abschnitt", options=C.CLEAR_OPTIONS, key="clear_select", format_func=lambda m: f"{m} min",
                     help="Zeit nach dem Verlassen eines Abschnitts, in der kein anderer Zug (gleich welcher Richtung) einfahren darf.")
    st.slider("Anteil der Züge von Operator A (%)", C.SHARE_OPTIONS[0], C.SHARE_OPTIONS[-1], step=C.SHARE_OPTIONS[1] - C.SHARE_OPTIONS[0], key="share_select",
                     help="Operator A stellt diesen Anteil der Züge (mit mehr Schnellzügen); B und C teilen den Rest im Verhältnis 3 zu 2.")
    st.select_slider("Vorrang für Operator", options=C.FAVOURED_OPTIONS, key="favoured_select", format_func=C.op_name,
                     help="Bei der Vorrangregel werden zuerst alle Züge dieses Operators eingeplant, danach die übrigen nach Wunschabfahrt.")
    st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1], step=1, key="seed_input",
                    help="Bestimmt Operator, Richtung, Klasse und Wunschabfahrt jedes Zuges.")
    st.button("🎲 Neues Netz würfeln", on_click=randomize_seed)

values = {k: st.session_state[k] for k in ("trains_select", "clear_select", "share_select", "favoured_select", "seed_input", "view_select")}
sync_query_params(values)
settings = settings_from_state(values)

res = _results()
with st.spinner(f"Rechne die fünf Verfahren (CP-SAT bis {C.CP_TIME_LIMIT:.0f} s je Lauf) …"):
    run = _live(settings["trains"], settings["clear"], settings["share"], settings["favoured"], settings["seed"])
trains, results = run["trains"], run["results"]
counts = [sum(1 for t in trains if t.op == o) for o in range(C.N_OPS)]
vname = R.variant_name(settings)
st.caption(
    f"{len(trains)} Züge (Operator A {counts[0]}, B {counts[1]}, C {counts[2]}), {sum(t.fast for t in trains)} Schnellzüge, {sum(t.up for t in trains)} aufwärts. "
    f"Rechenzeit dieses Laufs {run['seconds']:.1f} s (beim ersten Aufruf; danach aus dem Zwischenspeicher)."
)

st.markdown("---")
st.markdown("## 🚦 Was kostet die Regel – und was kostet Fairness?")
opt = results["opt"]["metrics"]
price = fairness_price(run)
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)
m1.metric("Optimum: Gesamtverspätung", f"{opt['total']} min", delta=None if run["proven"] else "nicht bewiesen", delta_color="off",
          help="Kleinste Summe der Verspätungen aller Züge (CP-SAT). Verspätung = Ankunft am Ziel minus Wunschabfahrt minus ungestörte Fahrzeit.")
m2.metric("Erstanmelder (FCFS)", f"{results['fcfs']['metrics']['total']} min", delta=f"{over_opt_pct(run, 'fcfs'):+.0f} % gegen Optimum", delta_color="inverse",
          help="Die Trassenvergabe in der Reihenfolge der Anmeldung (Wunschabfahrt); jeder Zug nimmt auf jedem Abschnitt die früheste freie Lage.")
m3.metric("Reihenfolge verbessert", f"{results['search']['metrics']['total']} min", delta=f"{over_opt_pct(run, 'search'):+.0f} % gegen Optimum", delta_color="inverse",
          help="Lokalsuche über die Reihenfolge der Serienplanung, Start bei Erstanmelder.")
m4.metric("Fair (Min-Max, dann Summe)", f"{results['fair']['metrics']['total']} min", delta=f"{price['pct']:+.1f} % gegen Optimum", delta_color="inverse",
          help="Erst die größte mittlere Verspätung eines Operators minimieren, dann bei gehaltener Fairness die Gesamtverspätung.")

state, text = fairness_message(run)
(st.success if state == "cheap" else st.warning if state == "unproven" else st.info)(f"💡 {text}")
st.info("⚖️ " + priority_message(run, settings["favoured"]))

rows = []
for key in C.METHODS:
    m = results[key]["metrics"]
    rows.append({"Verfahren": C.METHOD_LABELS[key] + (f" ({C.op_name(settings['favoured'])})" if key == "prio" else ""), "Gesamtverspätung (min)": m["total"],
                 **{f"Ø Operator {C.op_name(o)}": round(m["avg"][o], 1) if counts[o] else "–" for o in range(C.N_OPS)}, "Spreizung (min)": round(m["spread"], 1),
                 "Jain-Index": round(m["jain"], 3), "längste Verspätung": m["max_delay"], "Status": results[key]["status"]})
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
st.caption("Spreizung = größte minus kleinste mittlere Verspätung der Operatoren; Jain-Index 1 = alle Operatoren gleich verspätet. Die Verfahren sehen dieselben Züge; jedes Ergebnis ist ein zulässiger Fahrplan (geprüft).")
if not all(v["valid"] for v in results.values()):
    st.error("Interner Fehler: ein Fahrplan verletzt die Strecke.")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Wer wartet wie lange?**")
    st.plotly_chart(build_operator_bars(run), width="stretch", key=f"opbars_{settings}")
with c2:
    st.markdown("**Gesamtverspätung gegen Fairness** (links unten ist gut)")
    st.plotly_chart(build_method_scatter(run), width="stretch", key=f"scatter_{settings}")

st.markdown("### Der Bildfahrplan")
view = st.radio("Verfahren anzeigen", C.VIEW_OPTIONS, key="view_select", horizontal=True, format_func=lambda k: C.METHOD_LABELS[k] + (f" ({C.op_name(settings['favoured'])})" if k == "prio" else ""),
                help="Reine Anzeigewahl: welches Verfahren als Bildfahrplan gezeigt wird (keine Einstellung der Rechnung).")
st.plotly_chart(build_timetable(trains, results[view]["starts"], settings["clear"]), width="stretch", key=f"timetable_{settings}_{view}")
st.caption("Zeit waagerecht, Station senkrecht. Farbe = Operator, durchgezogen = Schnellzug, gestrichelt = langsamer Zug, Raute = Wunschabfahrt; waagerechte Stücke sind Wartezeit in einer Station.")
summary_lines = [f"{len(trains)} Züge, Räumzeit {settings['clear']} min, Verfahren: {C.METHOD_LABELS[view]}",
                 f"Gesamtverspätung {results[view]['metrics']['total']} min, Spreizung der Operatoren {results[view]['metrics']['spread']:.1f} min."]
st.download_button("📄 Trassenplan als PDF herunterladen", data=generate_plan_pdf(trains, results[view]["starts"], "Trassenplan", summary_lines), file_name="trassenplan.pdf",
                   mime="application/pdf", key="pdf_download")

# ------------------------------------------------------------------ Kernabschnitt: Messreihe
st.markdown("---")
st.subheader("📐 Was die Messreihe zeigt")
variants = R.all_variants(res)
names = [v["name"] for v in variants]
st.caption(f"Vorgerechnet (tools/sweep.py): {len(R.rows_of(res, names[0]))} Netze je Variante, alle Verfahren; Abstände zum Optimum nur über Netze mit bewiesenem Optimum (Zahl je Variante in der Tabelle).")
std = next(v for v in variants if v["name"] == "Standard (8 Züge)")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Erstanmelder über Optimum", f"{std['over_fcfs']:.0f} ± {std['over_fcfs_se']:.0f} %", help="Standardfall, 8 Züge: Mittel ± Standardfehler der Gesamtverspätung gegen das Optimum.")
d2.metric("Vorrang über Optimum", f"{std['over_prio']:.0f} ± {std['over_prio_se']:.0f} %")
d3.metric("Reihenfolge verbessert", f"{std['over_search']:.0f} ± {std['over_search_se']:.0f} %")
d4.metric("Fair über Optimum", f"{std['over_fair']:.1f} ± {std['over_fair_se']:.1f} %", help="Der Preis der Fairness: Gesamtverspätung der fairen Lösung gegen das Optimum.")
st.plotly_chart(build_sweep_bars(variants), width="stretch", key="sweep_cost")
st.plotly_chart(build_spread_bars(variants), width="stretch", key="sweep_spread")
st.dataframe(pd.DataFrame([{"Variante": v["name"], "Optimum bewiesen": f"{v['proven']}/{v['n']}", "Erstanmelder über Opt.": f"{v['over_fcfs']:.0f} ± {v['over_fcfs_se']:.0f} %",
                            "Vorrang über Opt.": f"{v['over_prio']:.0f} ± {v['over_prio_se']:.0f} %", "verbessert über Opt.": f"{v['over_search']:.0f} ± {v['over_search_se']:.0f} %",
                            "fair über Opt.": f"{v['over_fair']:.1f} ± {v['over_fair_se']:.1f} %", "Spreizung Vorrang (min)": round(v["spread_prio"], 1),
                            "Spreizung fair (min)": round(v["spread_fair"], 1)} for v in variants]), width="stretch", hide_index=True)
if vname:
    cur = next(v for v in variants if v["name"] == vname)
    st.caption(f"Die gewählten Einstellungen entsprechen der Messreihen-Variante „{vname}“: Erstanmelder {cur['over_fcfs']:+.0f} %, Vorrang {cur['over_prio']:+.0f} %, verbessert {cur['over_search']:+.0f} %, fair {cur['over_fair']:+.1f} % gegen das Optimum.")
else:
    st.caption("Für diese Kombination der Regler gibt es keine Messreihen-Variante; die Tabelle zeigt die gemessenen Fälle.")

# ------------------------------------------------------------------ Methodenvergleich
st.markdown("---")
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["🚂 Regeln", "🧮 Exakt (OR-Tools)", "📈 Messreihe"])

    with tabs[0]:
        st.markdown(
            "**Serienplanung:** Die Züge werden in einer Reihenfolge nacheinander eingeplant; jeder nimmt auf jedem Abschnitt die früheste freie Lage (mit Räumzeit), in Stationen darf er warten. "
            "*Erstanmelder:* Reihenfolge nach Wunschabfahrt. *Vorrang:* erst alle Züge des bevorzugten Operators. *Reihenfolge verbessert:* Lokalsuche, die einzelne Züge in der Reihenfolge "
            "verschiebt, solange die Gesamtverspätung sinkt. Alle drei sind schnell und nachvollziehbar, vergeben die Trasse aber Zug für Zug und ganz; das Optimum darf Züge abschnittsweise verzahnen (ein Zug wartet in einer Station, bis ein Gegenzug vorbei ist, obwohl er schon weiterfahren könnte). Auf manchen Netzen ist das Optimum deshalb besser als jede Zug-Reihenfolge."
        )
        st.dataframe(pd.DataFrame([{"Zug": t.idx + 1, "Operator": C.op_name(t.op), "Richtung": "aufwärts" if t.up else "abwärts", "Klasse": "schnell" if t.fast else "langsam",
                                    "Wunschabfahrt": t.request, "Verspätung FCFS": results["fcfs"]["metrics"]["delays"][t.idx], "Verspätung Vorrang": results["prio"]["metrics"]["delays"][t.idx],
                                    "Verspätung verbessert": results["search"]["metrics"]["delays"][t.idx], "Verspätung Optimum": results["opt"]["metrics"]["delays"][t.idx],
                                    "Verspätung fair": results["fair"]["metrics"]["delays"][t.idx]} for t in trains]), width="stretch", hide_index=True)

    with tabs[1]:
        st.caption(f"Das exakte Modell: je Zug und Abschnitt ein Intervall der Länge Fahrzeit + Räumzeit, je Abschnitt eine NoOverlap-Bedingung, Warten nur zwischen Abschnitten. Live {C.CP_TIME_LIMIT:.0f} s Zeitlimit; hier {C.CP_TIME_LIMIT_BUTTON:.0f} s.")
        key = (tuple(sorted(settings.items())),)
        if st.button("🧮 Optimum mit längerem Zeitlimit lösen", key="exact_button"):
            with st.spinner(f"CP-SAT rechnet (bis zu {C.CP_TIME_LIMIT_BUTTON:.0f} s) …"):
                r = X.solve(trains, C.N_SEG, settings["clear"], "total", C.CP_TIME_LIMIT_BUTTON)
                st.session_state["exact_result"] = {"key": key, "res": r, "total": M.metrics(trains, C.N_SEG, r["starts"], C.N_OPS)["total"] if "starts" in r else None}
        ex = st.session_state.get("exact_result")
        if ex and ex["key"] == key:
            r = ex["res"]
            if "starts" not in r:
                st.warning(f"CP-SAT hat im Zeitlimit keine Lösung gefunden (Status {r['status']}).")
            else:
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Gesamtverspätung", f"{ex['total']} min")
                e2.metric("Schranke", f"{r['bound']:.0f} min", help="Bessere Fahrpläne als dieser Wert gibt es nicht.")
                e3.metric("Status", "bewiesen optimal" if r["status"] == "OPTIMAL" else "Zeitlimit")
                e4.metric("Rechenzeit", f"{r['time']:.1f} s")
                if r["status"] != "OPTIMAL":
                    st.info("Das Optimum ist nicht bewiesen: ab etwa 10 bis 12 Zügen im Zeitfenster wächst die Rechenzeit stark. Die Lösung ist die beste gefundene, die Schranke zeigt, wie weit sie höchstens vom Optimum entfernt ist.")
        elif ex:
            st.caption("Die Einstellungen haben sich seit dem letzten Lauf geändert - bitte erneut lösen.")
        st.caption("Das Optimum der fairen Lösung wird in zwei Stufen gerechnet: erst die kleinste größte mittlere Verspätung (ganzzahlig aufgerundet), dann die kleinste Summe unter dieser Grenze.")

    with tabs[2]:
        st.caption("Alle Varianten der Messreihe: mittlere Gesamtverspätung je Verfahren (min) und mittlere Rechenzeit der beiden CP-SAT-Läufe.")
        st.dataframe(pd.DataFrame([{"Variante": v["name"], "Züge Ø": round(v["trains"], 1), "FCFS": round(v["total_fcfs"]), "Vorrang": round(v["total_prio"]), "verbessert": round(v["total_search"]),
                                    "Optimum": round(v["total_opt"]), "fair": round(v["total_fair"]), "CP-SAT-Zeit Median (s)": round(v["time_median"], 1)} for v in variants]),
                     width="stretch", hide_index=True)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Strecke.** {C.N_SEG} Abschnitte zwischen {C.N_SEG + 1} Stationen, ein Gleis je Abschnitt (absoluter Blockabstand): Ein Zug belegt einen Abschnitt für seine Fahrzeit plus die Räumzeit. Schnellzüge brauchen {M.FAST_MIN} min je
Abschnitt, langsame Züge {M.SLOW_MIN} min. In Stationen kann beliebig gewartet werden (Ausweichgleise), dort begegnen und überholen sich Züge.

**Züge.** Drei Bahnunternehmen A, B, C; jeder Zug fährt die ganze Strecke in eine Richtung und hat eine Wunschabfahrt am Start (die ersten {C.WINDOW} min). Operator A fährt mehr Schnellzüge. **Verspätung** = Ankunft am Ziel minus
Wunschabfahrt minus ungestörte Fahrzeit.

**Verfahren.** *Erstanmelder* und *Vorrang* sind Regeln der Trassenvergabe in Form einer Serienplanung. *Reihenfolge verbessert* verschiebt Züge in der Reihenfolge, solange die Gesamtverspätung sinkt. *Optimum* löst das
Modell exakt in CP-SAT. *Fair* minimiert zuerst die größte mittlere Verspätung eines Operators und dann die Gesamtverspätung.

**Fairness.** Gemessen wird die Spreizung der mittleren Verspätung zwischen den Operatoren und der Jain-Index. Der **Preis der Fairness** ist die Mehrverspätung der fairen Lösung gegenüber dem Optimum.

**Grenzen.** Synthetische Strecke, nur eine Richtung je Zug über die ganze Länge, Wunschabfahrten fest, unbegrenzte Ausweichgleise, gleiche Verspätungskosten je Minute für alle Operatoren, keine Fahrzeitreserven (die verteilt die Demo [Fahrzeitreserve](https://sebastianhanisch-fahrzeitreserve-demo.streamlit.app/)). Die Zahlen belegen
Größenordnungen auf diesen Netzen, keine Trassenpreise oder Rechtslage.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Zug $i$ hat die Route $j_1, \dots, j_S$ (Abschnitte in Fahrtrichtung), Fahrzeit $p_i$ je Abschnitt, Wunschabfahrt $r_i$. Variablen $s_{ij}$ = Einfahrt in Abschnitt $j$:
$s_{i j_1} \ge r_i$, $s_{i j_{k+1}} \ge s_{i j_k} + p_i$ (Warten in der Station erlaubt). Auf jedem Abschnitt $j$ dürfen sich die Intervalle $[s_{ij},\, s_{ij} + p_i + c)$ aller Züge nicht überschneiden ($c$ = Räumzeit).

**Verspätung.** $d_i = s_{i j_S} + p_i - (r_i + S\,p_i)$. **Optimum:** $\min \sum_i d_i$. **Fairness:** $\min m$ mit $m \cdot n_o \ge \sum_{i \in o} d_i$ für jeden Operator $o$ ($n_o$ = Zahl seiner Züge), danach
$\min \sum_i d_i$ unter $m \le m^*$.

**Serienplanung.** Für eine Reihenfolge $\pi$ wird Zug $\pi_1$ zuerst eingeplant, jeder weitere nimmt auf jedem Abschnitt die früheste Lage, die kein bereits belegtes Intervall schneidet. Die Lokalsuche verschiebt einen Zug in der
Reihenfolge, solange $\sum d_i$ sinkt.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html)."
)
