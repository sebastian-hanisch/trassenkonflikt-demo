# Trassenkonflikt: Wer bekommt die Strecke? (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-streckenkonflikt-demo.streamlit.app/)**

Interaktive **Fall-Demo** zur Trassenvergabe auf einer eingleisigen Strecke im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning).
**Dritter Baustein der Reihe Bahn/Schienenverkehr** nach dem [Taktfahrplan](https://github.com/sebastian-hanisch/taktfahrplan-demo) (dort stand die Mindest-Zugfolge nur als Vorgriff) und dem
[Crew Pairing](https://github.com/sebastian-hanisch/crew-pairing-demo).

Züge von drei Bahnunternehmen wollen im selben Zeitfenster über eine eingleisige Strecke; ein Abschnitt trägt immer nur einen Zug, begegnen und überholen geht nur in den Stationen. Die Demo
vergleicht **Regeln der Trassenvergabe** (Erstanmelder, Vorrang), eine **verbesserte Reihenfolge** und die **exakte Lösung** (OR-Tools CP-SAT) und fragt, **was die Regel kostet und was Fairness
zwischen den Unternehmen kostet**.

## Kernfrage

Wie viel Gesamtverspätung kostet es, die Trassen nach dem Erstanmelder- oder einem Vorrangprinzip zu vergeben statt nach dem Optimum, und was kostet es, die Verspätung gerecht auf die Unternehmen
zu verteilen? Strukturell ist das ein Job-Shop mit Routen wie in [job-shop-demo](https://github.com/sebastian-hanisch/job-shop-demo) (Kulisse neu); der eigene Aufsatz ist die **Fairness**: Min-Max der mittleren
Verspätung je Unternehmen, gefolgt von der kleinsten Gesamtverspätung bei gehaltener Fairness.

## Befunde und Korrekturen gegenüber dem Plan

- **Die Lücke der Regeln ist zum Teil strukturell, nicht nur eine Frage der Reihenfolge.** Erstanmelder und Vorrang vergeben die Trasse **Zug für Zug und ganz**; das Optimum darf Züge abschnittsweise verzahnen
  (ein Zug wartet in einer Station, bis ein Gegenzug vorbei ist, obwohl er weiterfahren könnte). Gegen eine Vollaufzählung aller Operations-Reihenfolgen (kleine Netze) stimmt das CP-SAT-Optimum genau;
  auf mindestens einem kleinen Netz ist es strikt besser als jede Zug-Reihenfolge (`tests/test_exact.py`).
- **Deshalb gibt es eine fünfte Stufe, „Reihenfolge verbessert“.** Eine einfache Lokalsuche über die Reihenfolge der Zug-für-Zug-Planung schließt den größten Teil der Lücke des Erstanmelder-Prinzips
  (siehe Befunde). Ohne sie wäre der Vergleich gegen eine bewusst schwache Regel geführt worden.
- **Der Optimum-Lauf wird bei 10 Zügen im Zeitfenster zäh:** in 16 von 20 Netzen bewiesen, bei 12 Zügen nur noch selten. Die Demo bietet deshalb 6 / 8 / 10 Züge, und alle Abstände zum Optimum stehen
  nur für Netze mit bewiesenem Optimum.
- Port 8960 (8958 gehört dem Crew Pairing).

## Modell

- **Strecke:** 5 Abschnitte zwischen 6 Stationen, ein Gleis je Abschnitt (absoluter Blockabstand): ein Zug im Abschnitt, danach 1 bis 3 min Räumzeit, bevor ein anderer Zug (gleich welcher
  Richtung) einfahren darf. In Stationen darf beliebig gewartet werden (Ausweichgleise). Fahrzeit 6 min je Abschnitt (Schnellzug) oder 10 min (langsamer Zug).
- **Züge:** Operatoren A, B, C; jeder Zug fährt die ganze Strecke in eine Richtung, Wunschabfahrt am Start in den ersten 120 min; Operator A fährt mehr Schnellzüge (60 gegen 30 %). Alles ganzzahlig mit
  **SplitMix64** (`trs_rng.py`, `trs_model.py`).
- **Verspätung** = Ankunft am Ziel minus (Wunschabfahrt + ungestörte Fahrzeit). **Fairness** gemessen als Spreizung der mittleren Verspätung je Operator (größte minus kleinste) und Jain-Index.

## Methodik

- **Erstanmelder** und **Vorrang** (`trs_model.py`): Serienplanung, jeder Zug nimmt auf jedem Abschnitt die früheste freie Lage; Reihenfolge nach Wunschabfahrt bzw. erst alle Züge des bevorzugten
  Operators. **Reihenfolge verbessert:** Lokalsuche, die einzelne Züge in der Reihenfolge verschiebt, solange die Gesamtverspätung sinkt.
- **Optimum und fair** (`trs_exact.py`): CP-SAT-Intervallmodell, je Abschnitt NoOverlap. Fair in zwei Stufen: kleinste (ganzzahlig aufgerundete) größte mittlere Verspätung, dann kleinste Summe unter
  dieser Grenze.
- **Vorgerechnete Messreihe** (`tools/sweep.py` → `data/trs_results.json`, rund eine Minute parallel): 9 Varianten (Zugzahl, Räumzeit, Anteil von Operator A, bevorzugter Operator) mit je 20 Netzen,
  alle fünf Verfahren. Live läuft das gewählte Netz.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. 20 Netze je Variante (Seeds 100–119), Mittel ± Standardfehler, **Gesamtverspätung über dem Optimum** (Basis = Optimum), nur Netze mit bewiesenem Optimum und
bewiesener fairer Lösung.

| Frage | Befund |
|---|---|
| Was kostet das Erstanmelder-Prinzip? (8 Züge) | **58 ± 8 %** mehr Gesamtverspätung als das Optimum. |
| Und Vorrang für einen Operator? | **81 ± 10 %**; Vorrang für B 68 ± 8 %, für C 73 ± 8 %. |
| Wie viel schließt eine verbesserte Reihenfolge? | Fast alles der Regel-Lücke: **16 ± 5 %** statt 58 %; bei 6 Zügen 12 ± 4 %, bei 10 Zügen 24 ± 4 %. Der Rest ist die Zug-für-Zug-Vergabe. |
| Was kostet Fairness? | **3.3 ± 1.0 %** über dem Optimum (8 Züge), in 14 von 20 Netzen unter 5 %; bei 6 Zügen 8.0 ± 3.8 %, bei 10 Zügen 4.2 ± 0.9 %. |
| Wie ungleich verteilt Vorrang die Verspätung? | Spreizung der mittleren Verspätung zwischen den Operatoren **41.6 min** bei Vorrang für A gegen **5.7 min** bei der fairen Lösung (Erstanmelder 14.4 min, Optimum 12.6 min). |
| Wirkt die Zugzahl? | Optimum der Gesamtverspätung im Mittel **47.5 / 93.5 / 151.4 min** bei 6 / 8 / 10 Zügen; Erstanmelder über Optimum 52 / 58 / 66 %. |
| Und die Räumzeit? | Optimum **75.6 / 93.5 / 113.1 min** bei 1 / 2 / 3 min Räumzeit; Erstanmelder über Optimum 69 / 58 / 58 %. |
| Wie lange rechnet CP-SAT? | Median beider Läufe 0.1 s (6 Züge), 0.3 s (8 Züge), 7.8 s (10 Züge); bei 10 Zügen ist das Optimum in nur 16 von 20 Netzen bewiesen. |

## Ehrliche Grenzen

- Die Regeln vergeben die Trasse **Zug für Zug und ganz**; ein Fahrdienstleiter kann Züge in einzelnen Abschnitten verzahnen. Die Lücke des Erstanmelder-Prinzips ist deshalb eine Obergrenze dessen, was
  Regeln kosten, die verbesserte Reihenfolge eine Untergrenze.
- Synthetische Strecke: ein Zug fährt immer die ganze Strecke, Wunschabfahrten sind fest, die Ausweichgleise unbegrenzt, jede Verspätungsminute zählt für alle Unternehmen gleich, keine Fahrzeitreserven,
  keine Trassenpreise und keine Rechtslage. Die Zahlen belegen Größenordnungen auf diesen Netzen.
- Fairness wird nur als Min-Max der **mittleren** Verspätung je Unternehmen gemessen; andere Gerechtigkeitsmaße (Anteil verspäteter Züge, längste Verspätung) wären ein Ausbau.
- Die Spreizung der **optimalen** Lösung hängt davon ab, welche der gleich guten Lösungen CP-SAT zurückgibt (mehrere Worker); Gesamtverspätung und Optimum sind eindeutig, die Spreizung dieser einen Lösung nicht.

## Tests

Siehe `tests/`: Strecke und Serienplanung von Hand gerechnet (frühester freier Platz, drei Züge auf zwei Abschnitten), **CP-SAT gegen die Vollaufzählung aller Operations-Reihenfolgen** (Gesamtverspätung,
Min-Max, faire Stufe), unabhängiger Prüfer für jeden Fahrplan, Statistik an einer von Hand gerechneten Mini-Ergebnisdatei, Preset-Kriterien mit künstlichen Werten (jedes Kriterium kippt einzeln),
`test_claims.py` (jede README-Zahl gegen die Ergebnisdatei), AppTest-Rauchtests (Voreinstellung, jedes Preset, Randwerte, Permalink, Exakt-Tab). Keine Wall-Clock-Assertions.
`tools/mutation_check.py` baut einzelne Fehler in die Module ein und prüft, ob die Tests sie finden.

```
python -m pytest tests -q
```

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `trs_constants.py` | feste Annahmen, Regler-Stufen, Presets |
| `trs_rng.py`, `trs_model.py` | SplitMix64; Strecke, Züge, Serienplanung, Prüfer, Kennzahlen |
| `trs_exact.py` | CP-SAT-Modell: Gesamtverspätung, Min-Max, fair |
| `trs_evaluation.py` | Live-Rechnung der fünf Verfahren, Meldungen, Bildfahrplan-Daten |
| `trs_results.py`, `trs_stories.py`, `trs_presets.py` | Auswertung der Messreihe; Preset-Kriterien; Permalink und Presets |
| `trs_visualization.py`, `trs_pdf_export.py` | Plotly-Figuren; Trassenplan als PDF |
| `data/trs_results.json` | Ergebnisse der Messreihe |
| `tools/` | `sweep.py`, `preset_search.py`, `mutation_check.py`, `PRESET_SWEEP.md` |

## Bewusst nicht umgesetzt

Teilstrecken-Fahrten und Verkehrshalte, Fahrzeitreserven, Trassenpreise, weitere Fairnessmaße, Mehrgleisstrecken und Überholbahnhöfe mit begrenzter Kapazität, Störungsmanagement, Fahrzeugumlauf und Rangieren.

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Die Messreihe neu erzeugen: `python tools/sweep.py`.

Gebaut mit Streamlit, Plotly, NumPy, OR-Tools und fpdf2.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html).
