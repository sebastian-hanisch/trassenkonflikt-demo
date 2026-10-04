"""Trassenkonflikt auf einer eingleisigen Strecke: Züge, Regeln der Trassenvergabe (Serienplanung), Kennzahlen.

Strecke mit S Abschnitten (Stationen 0..S), je Abschnitt ein Gleis mit absolutem Blockabstand: ein Zug im Abschnitt, danach `clear` min Räumzeit, bevor ein anderer
Zug (gleich welcher Richtung) einfahren darf. In Stationen darf gewartet werden (unbegrenzt Ausweichgleise). Verspätung = Ankunft am Ziel minus (Wunschabfahrt + Fahrzeit).
Kleine Einheiten ohne Zustand; Zufall nur über SplitMix64.
"""
from __future__ import annotations

from dataclasses import dataclass

from trs_rng import SplitMix64

FAST_MIN, SLOW_MIN = 6, 10          # Fahrzeit je Abschnitt (min)


@dataclass(frozen=True)
class Train:
    idx: int
    op: int            # Bahnunternehmen 0..O-1
    up: bool           # aufwärts (Station 0 -> S) oder abwärts
    fast: bool
    request: int       # Wunschabfahrt am Start (min)


def run_time(fast: bool) -> int:
    return FAST_MIN if fast else SLOW_MIN


def route(t: Train, n_seg: int) -> list:
    """Abschnitte in Fahrtrichtung."""
    return list(range(n_seg)) if t.up else list(range(n_seg - 1, -1, -1))


def free_run(t: Train, n_seg: int) -> int:
    """Fahrzeit ohne jede Behinderung."""
    return run_time(t.fast) * n_seg


def generate(n_trains: int, n_ops: int, n_seg: int, window: int, seed: int, shares: list, fast_pct: tuple = (60, 30, 30)) -> list:
    """Zufällige Züge: Operator nach Anteilen `shares` (Prozent, Summe 100), Richtung 50:50, Schnellzug mit Wahrscheinlichkeit fast_pct[op], Wunschabfahrt im Fenster (5-min-Raster);
    nach Wunschabfahrt sortiert und neu nummeriert."""
    rng = SplitMix64(seed)
    trains = []
    for i in range(n_trains):
        r = rng.below(100)
        op, acc = 0, shares[0]
        while r >= acc and op < n_ops - 1:
            op += 1
            acc += shares[op]
        up = rng.below(2) == 0
        fast = rng.below(100) < fast_pct[op]
        trains.append(Train(i, op, up, fast, 5 * rng.below(window // 5)))
    trains.sort(key=lambda t: (t.request, t.idx))
    return [Train(k, t.op, t.up, t.fast, t.request) for k, t in enumerate(trains)]


def free_slot(occ: list, earliest: int, length: int) -> int:
    """Frühester Start >= earliest, bei dem [start, start+length) keinen belegten Bereich schneidet (occ = nach Beginn sortierte Liste (a, b))."""
    start = earliest
    for a, b in occ:
        if start + length <= a:
            break
        if start < b:
            start = max(start, b)
    return start


def dispatch(trains: list, n_seg: int, clear: int, order: list) -> dict:
    """Serienplanung in der Reihenfolge `order` (Zug-Indizes): jeder Zug nimmt auf jedem Abschnitt die frühestmögliche freie Lage. Rückgabe {Zug: {Abschnitt: Einfahrt}}."""
    occ = [[] for _ in range(n_seg)]
    starts = {}
    for i in order:
        t = trains[i]
        now = t.request
        starts[i] = {}
        for j in route(t, n_seg):
            rt = run_time(t.fast)
            s = free_slot(occ[j], now, rt + clear)
            occ[j].append((s, s + rt + clear))
            occ[j].sort()
            starts[i][j] = s
            now = s + rt
    return starts


def order_fcfs(trains: list) -> list:
    """Erstanmelder-Prinzip: nach Wunschabfahrt."""
    return [t.idx for t in sorted(trains, key=lambda t: (t.request, t.idx))]


def order_priority(trains: list, favoured: int) -> list:
    """Vorrang: erst alle Züge des bevorzugten Operators (nach Wunschabfahrt), dann die übrigen in der Reihenfolge der Wunschabfahrt."""
    return [t.idx for t in sorted(trains, key=lambda t: (t.op != favoured, t.request, t.idx))]


def improve_order(trains: list, n_seg: int, clear: int, order: list, n_ops: int) -> list:
    """Lokalsuche über die Reihenfolge der Serienplanung: Zug herausnehmen und an anderer Stelle einfügen, solange die Gesamtverspätung sinkt (Gleichstand: keine Änderung)."""
    def total(o):
        return metrics(trains, n_seg, dispatch(trains, n_seg, clear, o), n_ops)["total"]

    best, best_total, improved = list(order), total(order), True
    while improved:
        improved = False
        for i in range(len(best)):
            for j in range(len(best)):
                if i == j:
                    continue
                cand = list(best)
                cand.insert(j, cand.pop(i))
                t = total(cand)
                if t < best_total:
                    best, best_total, improved = cand, t, True
    return best


def arrivals(trains: list, n_seg: int, starts: dict) -> dict:
    return {t.idx: starts[t.idx][route(t, n_seg)[-1]] + run_time(t.fast) for t in trains}


def delays(trains: list, n_seg: int, starts: dict) -> dict:
    arr = arrivals(trains, n_seg, starts)
    return {t.idx: arr[t.idx] - (t.request + free_run(t, n_seg)) for t in trains}


def valid_schedule(trains: list, n_seg: int, clear: int, starts: dict) -> bool:
    """Unabhängiger Prüfer: Wunschabfahrt, Anschlüsse (nur Warten in Stationen) und keine Überschneidung auf einem Abschnitt (einschließlich Räumzeit)."""
    per_seg = [[] for _ in range(n_seg)]
    for t in trains:
        prev_end = None
        for j in route(t, n_seg):
            s = starts[t.idx][j]
            if s < (t.request if prev_end is None else prev_end):
                return False
            per_seg[j].append((s, s + run_time(t.fast) + clear))
            prev_end = s + run_time(t.fast)
    for ivs in per_seg:
        ivs.sort()
        if any(b[0] < a[1] for a, b in zip(ivs, ivs[1:])):
            return False
    return True


def metrics(trains: list, n_seg: int, starts: dict, n_ops: int) -> dict:
    """Gesamtverspätung, mittlere Verspätung je Operator, Spreizung (größte minus kleinste), größte mittlere Verspätung, Jain-Index der mittleren Verspätungen."""
    d = delays(trains, n_seg, starts)
    sums = [sum(d[t.idx] for t in trains if t.op == o) for o in range(n_ops)]
    cnt = [sum(1 for t in trains if t.op == o) for o in range(n_ops)]
    avg = [s / c if c else 0.0 for s, c in zip(sums, cnt)]
    present = [a for a, c in zip(avg, cnt) if c]            # Operatoren ohne Zug zählen für Spreizung und Jain-Index nicht
    sq = sum(a * a for a in present)
    return {"total": sum(d.values()), "avg": avg, "max_avg": max(present), "spread": max(present) - min(present),
            "jain": (sum(present) ** 2) / (len(present) * sq) if sq > 0 else 1.0, "max_delay": max(d.values()), "delays": d}
