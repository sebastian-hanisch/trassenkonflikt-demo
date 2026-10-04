"""Strecke, Serienplanung und Kennzahlen: von Hand gerechnete Mini-Instanzen, Prüfer, SplitMix64 gegen Referenzwerte, eingefrorene Züge."""
import itertools

import trs_model as M
import trs_rng
from trs_model import Train


def mini():
    # 2 Abschnitte (Stationen 0-1-2), Räumzeit 2. Zug 0: aufwärts, schnell (6 min je Abschnitt), Wunsch 0. Zug 1: abwärts, langsam (10), Wunsch 0. Zug 2: aufwärts langsam, Wunsch 5.
    return [Train(0, 0, True, True, 0), Train(1, 1, False, False, 0), Train(2, 0, True, False, 5)]


def test_splitmix64_reference_values():
    r = trs_rng.SplitMix64(0)
    assert r.next() == 0xE220A8397B1DCDAF and r.next() == 0x6E789E6AA1B965F4 and r.next() == 0x06C45D188009454F
    assert trs_rng.SplitMix64(5).randrange(1000) == trs_rng.SplitMix64(5).below(1000)


def test_free_slot_finds_the_earliest_gap():
    occ = [(10, 20), (30, 40)]
    assert M.free_slot(occ, 0, 10) == 0          # [0,10) passt vor dem ersten Block
    assert M.free_slot(occ, 5, 10) == 20         # [5,15) schneidet (10,20): nach 20 -> [20,30) passt genau vor (30,40)
    assert M.free_slot(occ, 5, 11) == 40         # [20,31) schneidet (30,40): erst nach 40
    assert M.free_slot(occ, 45, 5) == 45 and M.free_slot([], 7, 5) == 7


def test_dispatch_by_hand_on_the_mini_instance():
    tr = mini()
    s = M.dispatch(tr, 2, 2, [0, 1, 2])
    # Zug 0: Abschnitt 0 ab 0 (belegt [0,8)), Abschnitt 1 ab 6 (belegt [6,14)).
    assert s[0] == {0: 0, 1: 6}
    # Zug 1 abwärts: Abschnitt 1 zuerst; frühestens 0, aber [0,12) schneidet [6,14): Start 14 -> Ankunft 24; Abschnitt 0 ab 24 ([24,36)).
    assert s[1] == {1: 14, 0: 24}
    # Zug 2 aufwärts, Wunsch 5: Abschnitt 0 belegt [0,8) und [24,36): Start 8 ([8,20) passt vor 24), dann Abschnitt 1 ab 18: belegt [6,14),[14,26): Start 26.
    assert s[2] == {0: 8, 1: 26}
    d = M.delays(tr, 2, s)
    assert d == {0: 0, 1: 24 + 10 - 0 - 20, 2: 26 + 10 - (5 + 20)} == {0: 0, 1: 14, 2: 11}
    assert M.valid_schedule(tr, 2, 2, s)
    m = M.metrics(tr, 2, s, 3)
    assert m["total"] == 25 and m["avg"] == [5.5, 14.0, 0.0] and m["spread"] == 8.5 and m["max_avg"] == 14.0 and m["max_delay"] == 14


def test_metrics_spread_and_jain_ignore_operators_without_trains():
    tr = mini()
    s = M.dispatch(tr, 2, 2, [0, 1, 2])
    m = M.metrics(tr, 2, s, 3)                      # Operator 2 hat keinen Zug
    assert m["avg"][2] == 0.0 and m["spread"] == max(m["avg"][:2]) - min(m["avg"][:2])
    assert 0.5 < m["jain"] <= 1.0 and abs(m["jain"] - (sum(m["avg"][:2]) ** 2) / (2 * sum(a * a for a in m["avg"][:2]))) < 1e-12


def test_order_changes_the_result_and_validator_rejects_overlaps():
    tr = mini()
    a = M.dispatch(tr, 2, 2, [0, 1, 2])
    b = M.dispatch(tr, 2, 2, [1, 0, 2])
    assert M.metrics(tr, 2, a, 3)["total"] != M.metrics(tr, 2, b, 3)["total"]
    bad = {i: dict(v) for i, v in a.items()}
    bad[1][1] = 8                                   # Zug 1 fährt in Abschnitt 1 gleichzeitig mit Zug 0 ([6,14) und [8,20))
    assert not M.valid_schedule(tr, 2, 2, bad)
    early = {i: dict(v) for i, v in a.items()}
    early[2][0] = 3                                 # vor der Wunschabfahrt 5
    assert not M.valid_schedule(tr, 2, 2, early)
    skip = {i: dict(v) for i, v in a.items()}
    skip[0][1] = 3                                  # Abschnitt 1 betreten, bevor der Zug Abschnitt 0 verlassen hat (Ankunft 6)
    assert not M.valid_schedule(tr, 2, 2, skip)


def test_rules_orders_and_local_search():
    tr = M.generate(8, 3, 5, 120, 100, [50, 30, 20])
    fc = M.order_fcfs(tr)
    assert [tr[i].request for i in fc] == sorted(t.request for t in tr)
    pr = M.order_priority(tr, 1)
    ops = [tr[i].op for i in pr]
    assert ops == sorted(ops, key=lambda o: o != 1)                       # erst alle Züge des bevorzugten Operators
    total = lambda order: M.metrics(tr, 5, M.dispatch(tr, 5, 2, order), 3)["total"]
    better = M.improve_order(tr, 5, 2, fc, 3)
    assert sorted(better) == sorted(fc) and total(better) <= total(fc) and total(better) < total(fc)     # auf diesem Netz bringt die Suche etwas


def test_generator_is_deterministic_and_frozen():
    a, b = M.generate(8, 3, 5, 120, 100, [50, 30, 20]), M.generate(8, 3, 5, 120, 100, [50, 30, 20])
    assert a == b and len(a) == 8 and [t.idx for t in a] == list(range(8)) and [t.request for t in a] == sorted(t.request for t in a)
    assert M.generate(8, 3, 5, 120, 101, [50, 30, 20]) != a
    assert all(t.request % 5 == 0 and 0 <= t.request < 120 and 0 <= t.op < 3 for t in a)
    big = M.generate(2000, 3, 5, 120, 1, [50, 30, 20])
    shares = [sum(1 for t in big if t.op == o) / 2000 for o in range(3)]
    assert all(abs(s - e) < 0.04 for s, e in zip(shares, (0.5, 0.3, 0.2)))
