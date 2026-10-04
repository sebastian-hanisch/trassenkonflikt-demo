"""Reproduktion der Messreihe (Minuten, nicht in der CI): 9 Varianten (Zugzahl, Räumzeit, Anteil von Operator A, bevorzugter Operator) mit je 20 Netzen,
alle vier Verfahren (Erstanmelder, Vorrang, Optimum, fair).

  python tools/sweep.py            schreibt data/trs_results.json
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import trs_constants as C  # noqa: E402
from trs_evaluation import run_live  # noqa: E402


def one(args):
    name, trains, clear, share, favoured, seed = args
    run = run_live({"trains": trains, "clear": clear, "share": share, "favoured": favoured, "seed": seed}, cp_limit=C.SWEEP_CP_LIMIT)
    rec = {"variant": name, "seed": seed, "n": len(run["trains"]), "ops": [sum(1 for t in run["trains"] if t.op == o) for o in range(C.N_OPS)], "methods": {}}
    for key, v in run["results"].items():
        m = v["metrics"]
        rec["methods"][key] = {"total": m["total"], "avg": m["avg"], "max_avg": m["max_avg"], "spread": m["spread"], "jain": m["jain"], "max_delay": m["max_delay"],
                               "status": v["status"], "time": v.get("time", 0.0), "valid": v["valid"]}
    return rec


def main():
    t0 = time.time()
    jobs = [(name, n, cl, sh, fav, seed) for name, n, cl, sh, fav in C.SWEEP_VARIANTS for seed in C.SWEEP_SEEDS]
    with ProcessPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(one, jobs))
    res = {"meta": {"seeds": [C.SWEEP_SEEDS.start, C.SWEEP_SEEDS.stop], "n_seg": C.N_SEG, "window": C.WINDOW, "fast_pct": list(C.FAST_PCT), "cp_limit": C.SWEEP_CP_LIMIT,
                    "variants": [v[0] for v in C.SWEEP_VARIANTS]}, "rows": rows}
    out = ROOT / C.RESULTS_FILE
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    print("geschrieben:", out, round(out.stat().st_size / 1024), "KB,", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
