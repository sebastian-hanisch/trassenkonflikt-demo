"""Trassenplan als PDF (fpdf2, Kernschrift Helvetica: Umlaute gehen, Gedankenstrich, Euro-Zeichen, Emoji und U+2212 nicht)."""
from __future__ import annotations

from fpdf import FPDF

import trs_constants as C
import trs_model as M

_REPLACE = {"–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "→": "->", "↔": "<->", "…": "...", "€": "EUR", "·": ".", "Ø": "Durchschnitt"}


def _clean(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_plan_pdf(trains: list, starts: dict, title: str, summary_lines: list) -> bytes:
    """Je Zug: Operator, Richtung, Wunschabfahrt, Einfahrt in jeden Abschnitt, Ankunft und Verspätung."""
    delays = M.delays(trains, C.N_SEG, starts)
    arr = M.arrivals(trains, C.N_SEG, starts)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    for t in trains:
        direction = "aufwärts (Station 0 -> %d)" % C.N_SEG if t.up else "abwärts (Station %d -> 0)" % C.N_SEG
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, _clean(f"Zug {t.idx + 1} - Operator {C.op_name(t.op)} - {'Schnellzug' if t.fast else 'langsamer Zug'} - {direction}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        legs = ", ".join(f"Abschnitt {j}: {starts[t.idx][j]}" for j in M.route(t, C.N_SEG))
        pdf.multi_cell(0, 4.5, _clean(f"  Wunschabfahrt {t.request} min; Einfahrt (min): {legs}; Ankunft {arr[t.idx]} min; Verspätung {delays[t.idx]} min"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    return bytes(pdf.output())
