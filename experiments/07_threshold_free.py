#!/usr/bin/env python3
"""E016: threshold-free comparison of the GNN against tabular baselines from per-flow score dumps.

Inputs (numpy + std lib only, runs server-side):
    --gnn  LABEL=scores.npz   from 06_graph_ablation.py --save-scores  (one per node_key; keys <run>|<split>|{score,y,window})
    --tab  LABEL=scores.npz   from 00_tabular_baselines.py --save-scores (keys <model>|<seed>|<split>, <split>|y, <split>|scenario)
    --target LABEL            the GNN variant that must beat the others (default: ip)

Reports per model and seed: PR-AUC, ROC-AUC, F1@0.5, F1@val-tuned threshold (test, pooled and per scenario).
Gap = target - best competitor (best = highest seed-mean for that metric), per seed and seed-mean, with a paired
moving-block bootstrap over test windows (block = --block windows). Bootstrap uses binned scores (--bins) for
speed; point estimates are exact. Prints and writes a JSON. Mismatching test labels between sources abort.
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np

METRICS = ("pr_auc", "roc_auc", "f1_05", "f1_tuned")


def average_precision(y, s):
    order = np.argsort(-s, kind="stable")
    y = y[order]
    tp = np.cumsum(y)
    prec = tp / np.arange(1, len(y) + 1)
    return float((prec * y).sum() / max(y.sum(), 1))


def roc_auc(y, s):
    ranks = np.argsort(np.argsort(s, kind="stable"), kind="stable") + 1.0
    n1, n0 = y.sum(), (1 - y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def f1_at(y, s, thr):
    p = s >= thr
    tp = float((p & (y == 1)).sum())
    d = p.sum() + y.sum()
    return 2 * tp / d if d else 0.0


def tuned_threshold(y, s):
    order = np.argsort(-s, kind="stable")
    ys, ss = y[order], s[order]
    tp = np.cumsum(ys)
    f1 = 2 * tp / (np.arange(1, len(ys) + 1) + ys.sum())
    last = np.r_[ss[1:] != ss[:-1], True]  # only cut between distinct scores
    f1 = np.where(last, f1, -1)
    i = int(np.argmax(f1))
    return float(ss[i])


def point_metrics(y_val, s_val, y, s):
    thr = tuned_threshold(y_val, s_val)
    return {"pr_auc": average_precision(y, s), "roc_auc": roc_auc(y, s),
            "f1_05": f1_at(y, s, 0.5), "f1_tuned": f1_at(y, s, thr), "threshold": thr}


def bin_scores(s, bins):
    s = np.clip(s.astype(np.float64), 1e-7, 1 - 1e-7)
    t = np.log(s / (1 - s))
    return np.clip(((t + 16.2) / 32.4 * bins).astype(np.int64), 0, bins - 1)


def binned_metrics(pos, neg, thr_bin):
    """pos/neg: (R, B) histograms (bin B-1 = highest score). Returns pr_auc, f1_05 (bin of 0.5), f1_tuned."""
    cp = np.cumsum(pos[:, ::-1], axis=1)  # TP when predicting positive for bins >= b
    cn = np.cumsum(neg[:, ::-1], axis=1)
    total_pos = cp[:, -1:]
    prec = cp / np.maximum(cp + cn, 1)
    rec = cp / np.maximum(total_pos, 1)
    rec_prev = np.concatenate([np.zeros_like(rec[:, :1]), rec[:, :-1]], axis=1)
    ap = ((rec - rec_prev) * prec).sum(axis=1)
    f1 = 2 * cp / np.maximum(cp + cn + total_pos, 1)

    def at(b):
        return f1[np.arange(len(f1)), (pos.shape[1] - 1 - b)]
    return ap, at(np.full(len(f1), bin_scores(np.array([0.5]), pos.shape[1])[0])), at(thr_bin)


def seed_of(name):
    m = re.search(r"seed_(\d+)", name)
    return int(m.group(1)) if m else None


def load_gnn(label, path):
    z = np.load(path)
    runs = {}
    for key in z.files:
        run, split, field = key.split("|")
        runs.setdefault(seed_of(run), {}).setdefault(split, {})[field] = z[key]
    return {(label, seed): d for seed, d in runs.items()}


def load_tab(label, path):
    z = np.load(path)
    out, y = {}, {s: z[f"{s}|y"] for s in ("validation", "test")}
    for key in z.files:
        parts = key.split("|")
        if len(parts) == 3:
            model, seed, split = parts
            out.setdefault((f"{label}:{model}", int(seed)), {})["val" if split == "validation" else "test"] = z[key]
    scen = z["test|scenario"] if "test|scenario" in z.files else None
    return out, y, scen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gnn", action="append", default=[], metavar="LABEL=NPZ")
    ap.add_argument("--tab", action="append", default=[], metavar="LABEL=NPZ")
    ap.add_argument("--target", default="ip")
    ap.add_argument("--block", type=int, default=10)
    ap.add_argument("--resamples", type=int, default=10000)
    ap.add_argument("--bins", type=int, default=512)
    ap.add_argument("--rng", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("results/threshold_free.json"))
    a = ap.parse_args()

    models = {}  # (label, seed) -> {"val": scores, "test": scores}
    y_val = y_test = windows = scen = None
    mismatches = {}
    for spec in a.gnn:
        label, path = spec.split("=", 1)
        for (lab, seed), d in load_gnn(label, path).items():
            models[(lab, seed)] = {"val": d["val"]["score"], "test": d["test"]["score"]}
            for split, yy in (("val", d["val"]["y"]), ("test", d["test"]["y"])):
                ref = y_val if split == "val" else y_test
                if ref is None:
                    if split == "val":
                        y_val = yy
                    else:
                        y_test, windows = yy, d["test"]["window"]
                else:
                    mismatches[f"{lab}/{seed}/{split}"] = int((ref != yy).sum()) if len(ref) == len(yy) else -1
    for spec in a.tab:
        label, path = spec.split("=", 1)
        d, ys, sc = load_tab(label, path)
        models.update(d)
        scen = sc if sc is not None else scen
        for split, yy in (("val", ys["validation"]), ("test", ys["test"])):
            ref = y_val if split == "val" else y_test
            mismatches[f"{label}/{split}"] = int((ref != yy).sum()) if len(ref) == len(yy) else -1
    bad = {k: v for k, v in mismatches.items() if v != 0}
    print(f"label mismatches (0 = identical flows): {bad or 'none'} over {len(mismatches)} checks")
    if bad:
        raise SystemExit("test/val flows differ between sources; cannot compare")

    keys = sorted(models, key=lambda k: (k[0], k[1]))
    seeds = sorted({s for _, s in keys})
    labels = sorted({l for l, _ in keys})
    point = {k: point_metrics(y_val, models[k]["val"], y_test, models[k]["test"]) for k in keys}
    per_scen = {}
    if scen is not None:
        for sc in np.unique(scen):
            m = scen == sc
            per_scen[int(sc)] = {f"{l}/{s}": point_metrics(y_val, models[(l, s)]["val"], y_test[m], models[(l, s)]["test"][m])
                                 for l, s in keys}

    def mean_metric(l, metric):
        return float(np.mean([point[(l, s)][metric] for s in seeds if (l, s) in point]))

    result = {"mismatches": mismatches, "point": {f"{l}/{s}": v for (l, s), v in point.items()}, "per_scenario": per_scen,
              "block": a.block, "resamples": a.resamples, "bins": a.bins, "gaps": {}}
    comps = [l for l in labels if l != a.target]
    best = {m: max(comps, key=lambda l: mean_metric(l, m)) for m in METRICS}

    # Bootstrap: histograms per block of windows, per model (pos/neg), val-tuned threshold bin from validation.
    nb = int(np.ceil((windows.max() + 1) / a.block))
    blk = windows // a.block
    B = a.bins
    hist = {}
    thr_bin = {}
    for k in keys:
        b = bin_scores(models[k]["test"], B)
        h = np.zeros((2, nb, B))
        np.add.at(h, (y_test.astype(int), blk, b), 1)
        hist[k] = h
        thr_bin[k] = bin_scores(np.array([point[k]["threshold"]]), B)[0]
    rng = np.random.default_rng(a.rng)
    boot = {m: {} for m in ("pr_auc", "f1_05", "f1_tuned")}
    chunk = 250
    for k in keys:
        for m in boot:
            boot[m][k] = []
    for start in range(0, a.resamples, chunk):
        n = min(chunk, a.resamples - start)
        draws = rng.integers(0, nb, size=(n, nb))
        w = np.stack([np.bincount(d, minlength=nb) for d in draws]).astype(np.float64)  # (n, nb)
        for k in keys:
            pos, neg = w @ hist[k][1], w @ hist[k][0]
            ap_, f05, ft = binned_metrics(pos, neg, np.full(n, thr_bin[k]))
            boot["pr_auc"][k].append(ap_)
            boot["f1_05"][k].append(f05)
            boot["f1_tuned"][k].append(ft)
    for m in boot:
        for k in keys:
            boot[m][k] = np.concatenate(boot[m][k])

    for m in ("pr_auc", "f1_05", "f1_tuned"):
        comp = best[m]
        gaps = {s: point[(a.target, s)][m] - point[(comp, s)][m] for s in seeds}
        mean_boot = np.mean([boot[m][(a.target, s)] - boot[m][(comp, s)] for s in seeds], axis=0)
        lo, hi = np.percentile(mean_boot, [2.5, 97.5])
        result["gaps"][m] = {"best_competitor": comp, "per_seed": gaps, "mean": float(np.mean(list(gaps.values()))),
                             "min_seed": float(min(gaps.values())), "ci95_mean": [float(lo), float(hi)]}
    result["roc_auc_means"] = {l: mean_metric(l, "roc_auc") for l in labels}
    result["means"] = {m: {l: mean_metric(l, m) for l in labels} for m in METRICS}

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1, default=float))
    print("seed-mean per model:")
    for m in METRICS:
        print(f"  {m:9s} " + "  ".join(f"{l}={v:.3f}" for l, v in result["means"][m].items()))
    for m, g in result["gaps"].items():
        print(f"gap {m}: vs {g['best_competitor']} mean={g['mean']:+.3f} min_seed={g['min_seed']:+.3f} CI95={g['ci95_mean']}")
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
