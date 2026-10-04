"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prüft, ob die Tests (ohne AppTests) sie finden.

Aufruf (im Projektordner): python tools/mutation_check.py [Teilstring des Dateinamens] [--jobs N] [--indices 5,8-12] [--with-app] [--dry-run]
Jeder Mutant ersetzt genau eine Stelle; Überlebende sind entweder gleichwertig (kein sichtbarer Unterschied) oder eine Lücke der Tests. Die Kopie liegt je Mutant in einem
temporären Ordner; PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht; Quelltexte als LF. Ein Mutant kann in eine Endlosschleife laufen;
nach TIMEOUT Sekunden gilt er als gefunden. `--with-app` nimmt die AppTests hinzu, `--dry-run` prüft nur, ob jede Zeichenkette genau einmal vorkommt."""
import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
WITH_APP = "--with-app" in sys.argv
TIMEOUT = 600
TEST_ORDER = ["test_results.py", "test_presets.py", "test_model.py", "test_exact.py", "test_pdf.py", "test_stories.py", "test_evaluation.py", "test_gaps.py", "test_claims.py"]

MUTANTS = [
    ('trs_model.py', '        if start + length <= a:\n            break', '        if start + length < a:\n            break'),
    ('trs_model.py', '        if start < b:\n            start = max(start, b)', '        if start <= b:\n            start = max(start, b)'),
    ('trs_model.py', '            s = free_slot(occ[j], now, rt + clear)', '            s = free_slot(occ[j], now, rt)'),
    ('trs_model.py', '            now = s + rt\n    return starts', '            now = s + rt + clear\n    return starts'),
    ('trs_model.py', '        now = t.request\n        starts[i] = {}', '        now = 0\n        starts[i] = {}'),
    ('trs_model.py', '    return [t.idx for t in sorted(trains, key=lambda t: (t.request, t.idx))]', '    return [t.idx for t in sorted(trains, key=lambda t: (-t.request, t.idx))]'),
    ('trs_model.py', 'key=lambda t: (t.op != favoured, t.request, t.idx))]', 'key=lambda t: (t.op == favoured, t.request, t.idx))]'),
    ('trs_model.py', '    return list(range(n_seg)) if t.up else list(range(n_seg - 1, -1, -1))', '    return list(range(n_seg)) if not t.up else list(range(n_seg - 1, -1, -1))'),
    ('trs_model.py', '    return {t.idx: arr[t.idx] - (t.request + free_run(t, n_seg)) for t in trains}', '    return {t.idx: arr[t.idx] - t.request for t in trains}'),
    ('trs_model.py', '        if any(b[0] < a[1] for a, b in zip(ivs, ivs[1:])):', '        if any(b[0] < a[1] - 1 for a, b in zip(ivs, ivs[1:])):'),
    ('trs_model.py', '            if s < (t.request if prev_end is None else prev_end):', '            if s < (t.request if prev_end is None else prev_end - 1):'),
    ('trs_model.py', '    return {"total": sum(d.values()), "avg": avg, "max_avg": max(present), "spread": max(present) - min(present),', '    return {"total": sum(d.values()), "avg": avg, "max_avg": max(present), "spread": max(present) - sum(present) / len(present),'),
    ('trs_model.py', '                if t < best_total:', '                if t <= best_total:'),
    ('trs_model.py', '        up = rng.below(2) == 0', '        up = rng.below(2) == 1'),
    ('trs_model.py', '        fast = rng.below(100) < fast_pct[op]', '        fast = rng.below(100) <= fast_pct[op]'),
    ('trs_exact.py', '        model.Add(maxavg * cnt[o] >= sums[o])', '        model.Add(maxavg * cnt[o] >= sums[o] + 1)'),
    ('trs_exact.py', '    maxavg = model.NewIntVar(0, horizon if m_cap is None else m_cap, "maxavg")', '    maxavg = model.NewIntVar(0, horizon if m_cap is None else m_cap + 5, "maxavg")'),
    ('trs_exact.py', '        model.Add(delay[t.idx] == arrival[t.idx] - (t.request + free_run(t, n_seg)))', '        model.Add(delay[t.idx] == arrival[t.idx] - t.request)'),
    ('trs_exact.py', '            model.Add(s >= (t.request if prev_end is None else prev_end))', '            model.Add(s >= (0 if prev_end is None else prev_end))'),
    ('trs_exact.py', '            per_seg[j].append(model.NewFixedSizeIntervalVar(s, rt + clear, f"iv_{t.idx}_{j}"))', '            per_seg[j].append(model.NewFixedSizeIntervalVar(s, rt, f"iv_{t.idx}_{j}"))'),
    ('trs_evaluation.py', '    return 100 * (run["results"][key]["metrics"]["total"] / run["results"]["opt"]["metrics"]["total"] - 1)', '    return 100 * (run["results"]["opt"]["metrics"]["total"] / run["results"][key]["metrics"]["total"] - 1)'),
    ('trs_evaluation.py', '    if p["pct"] < C.FAIR_SMALL_PCT:', '    if p["pct"] <= C.FAIR_SMALL_PCT:'),
    ('trs_evaluation.py', '    if not run["proven"]:', '    if run["proven"]:'),
    ('trs_evaluation.py', '    worst = max(present, key=lambda i: avg[i])', '    worst = min(present, key=lambda i: avg[i])'),
    ('trs_evaluation.py', '        out[key] = {"starts": r["starts"], "status": r["status"],', '        out[key] = {"starts": r["starts"], "status": "OPTIMAL",'),
    ('trs_evaluation.py', '    for key, obj in (("opt", "total"), ("fair", "fair_total")):', '    for key, obj in (("opt", "total"), ("fair", "minmax")):'),
    ('trs_evaluation.py', '        pts.append((starts[t.idx][j], s0))', '        pts.append((starts[t.idx][j] + 1, s0))'),
    ('trs_results.py', '    return row["methods"]["opt"]["status"] == "OPTIMAL" and row["methods"]["fair"]["status"] == "OPTIMAL"', '    return row["methods"]["opt"]["status"] == "OPTIMAL"'),
    ('trs_results.py', '    over = {k: [100 * (r["methods"][k]["total"] / r["methods"]["opt"]["total"] - 1) for r in use]', '    over = {k: [100 * (r["methods"][k]["total"] / r["methods"]["fcfs"]["total"] - 1) for r in use]'),
    ('trs_results.py', '    out["fair_cheaper_than_5pct"] = sum(1 for x in over["fair"] if x < 5.0)', '    out["fair_cheaper_than_5pct"] = sum(1 for x in over["fair"] if x <= 5.0)'),
    ('trs_constants.py', '    b = rest * 3 // 5', '    b = rest * 2 // 5'),
    ('trs_constants.py', 'FAIR_SMALL_PCT = 10.0', 'FAIR_SMALL_PCT = 5.0'),
    ('trs_stories.py', '("rule_costs", "Erstanmelder liegt mindestens 20 % über dem Optimum", lambda f: f["over_fcfs"] >= 20.0)', '("rule_costs", "Erstanmelder liegt mindestens 20 % über dem Optimum", lambda f: f["over_fcfs"] > 20.0)'),
    ('trs_stories.py', 'lambda f: f["spread_fair"] <= 0.5 * f["spread_prio"]', 'lambda f: f["spread_fair"] < 0.5 * f["spread_prio"]'),
]


def check_unique():
    bad = []
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        text = (ROOT / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            bad.append((n, name, old[:70], text.count(old)))
        if old == new:
            bad.append((n, name, "alt == neu", 0))
    return bad


def run_one(args):
    n, name, old, new, base = args
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"tkt_mut{n}_"))
    try:
        shutil.copytree(base, tmp, dirs_exist_ok=True)
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        files = [f"tests/{f}" for f in TEST_ORDER + (["test_app.py"] if WITH_APP else [])]
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *files], cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
            return n, name, old, new, r.returncode == 0, False
        except subprocess.TimeoutExpired:
            return n, name, old, new, False, True                 # Endlosschleife oder zu langsam: gilt als gefunden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0] if args else ""
    jobs = 6
    if "--jobs" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("--jobs") + 1])
        only = "" if only == str(jobs) else only
    wanted = None
    if "--indices" in sys.argv:
        spec = sys.argv[sys.argv.index("--indices") + 1]
        only = "" if only == spec else only
        wanted = set()
        for part in spec.split(","):
            lo, _, hi = part.partition("-")
            wanted.update(range(int(lo), int(hi or lo) + 1))
    bad = check_unique()
    for b in bad:
        print("FEHLER (Stelle nicht eindeutig gefunden):", b)
    if "--dry-run" in sys.argv:
        print(f"{len(MUTANTS)} Mutanten, {len(bad)} Fehler in der Mutantenliste")
        return
    base = pathlib.Path(tempfile.mkdtemp(prefix="tkt_mut_base_"))
    for f in ROOT.glob("*.py"):
        (base / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copytree(ROOT / "tests", base / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "README.md", base / "README.md")
    shutil.copytree(ROOT / "data", base / "data")
    for f in (base / "tests").glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    bad_ids = {b[0] for b in bad}
    work = [(n, name, old, new, base) for n, (name, old, new) in enumerate(MUTANTS, 1) if n not in bad_ids and (not only or only in name) and (wanted is None or n in wanted)]
    survivors, killed = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for n, name, old, new, survived, timeout in pool.map(run_one, work):
            if timeout:
                print(f"[{n:3d}] Zeitüberschreitung (als gefunden gezählt)  {name}", flush=True)
            if survived:
                survivors.append((n, name, old[:70], new[:70]))
                print(f"[{n:3d}] ÜBERLEBT  {name}: {old[:70]!r} -> {new[:70]!r}", flush=True)
            else:
                killed += 1
                print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} überlebt, {len(bad)} Fehler in der Mutantenliste")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
