import trs_evaluation as E
from trs_pdf_export import _clean, generate_plan_pdf


def test_clean_replaces_every_character_fpdf2_cannot_encode():
    cleaned = _clean("Verspätung – Ø ≤ 10 → 3 € … − 2 ↔")
    cleaned.encode("latin-1")
    assert not any(c in cleaned for c in "–€→−↔…≤Ø")


def test_plan_pdf_is_a_pdf():
    run = E.run_live({"trains": 6, "clear": 2, "share": 50, "favoured": 0, "seed": 500})
    pdf = generate_plan_pdf(run["trains"], run["results"]["opt"]["starts"], "Trassenplan – Test", ["Zeile 1 – mit Gedankenstrich", "Zeile 2 ≤ Ø"])
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1000
