#!/usr/bin/env python3
"""A/B/C decomposition on context detectors, CTU-13 (E017 pilot, D17; then E020).

Shaping-only (A, rho=0), injection-only (B, rho=1) and joint (C_rho) attacks at equal
traffic-cost budget beta (extra bytes / the bot host's clean bytes per window), against
MLP host-ip and GNN ip (white-box PGD) and XGB host-ip / plain XGB (transfer from MLP
host-ip). Models: GNN ip from ``--gnn-checkpoint`` (01, endpoint, node key ip); MLP and XGB
are refitted here with 00's trainers for ``--seed``. See src/attacks/context_attack.py.

    python experiments/08_context_decomposition.py --gnn-checkpoint <best_checkpoint.pt> \\
        --attack-seeds 0 1 --betas 0.05 0.1 0.25 0.5

Output: results/context_decomposition/<ts>/{rows.csv,summary.csv,config.json}
"""

import argparse
import csv
import importlib.util
import json
import logging
import pickle
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from attacks.context_attack import Chunk, N_VOLUME, build_plan, host_context_t, make_context, run_attack  # noqa: E402
from data.ctu13 import CTU13_DEFAULT_SPLIT, Ctu13Preprocessor, load_ctu13, scenario_segments  # noqa: E402
from data.endpoint_graph import endpoint_keys  # noqa: E402
from data.netflow_v3 import DST_IP, DST_PORT, SRC_IP, SRC_PORT  # noqa: E402

logger = logging.getLogger("context_decomposition")
VOLUME_NAMES = ["log_Dur", "log_TotPkts", "log_TotBytes", "log_SrcBytes", "log_DstBytes", "log_BytesPerPkt"]


def load_script(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "experiments" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- detectors

class MLPDetector:
    white_box = True

    def __init__(self, name, model, device):
        self.name, self.model, self.device = name, model.to(device).eval(), device

    def logit(self, X, ctx):
        return self.model(host_context_t(X, ctx))

    @torch.no_grad()
    def score(self, X, ctx):
        return torch.sigmoid(self.logit(X, ctx)).cpu().numpy()


class GNNDetector:
    white_box = True

    def __init__(self, name, model, device):
        self.name, self.model, self.device = name, model.to(device).eval(), device

    def logit(self, X, ctx):
        data = Data(x=torch.ones((ctx.n_nodes, 1), device=X.device),
                    edge_index=torch.stack([ctx.edge_src, ctx.edge_dst]), edge_attr=X)
        out = self.model(data)
        return out[:, 1] - out[:, 0]

    @torch.no_grad()
    def score(self, X, ctx):
        return torch.sigmoid(self.logit(X, ctx)).cpu().numpy()


class XGBDetector:
    white_box = False

    def __init__(self, name, predict, host):
        self.name, self.predict, self.host = name, predict, host

    @torch.no_grad()
    def score(self, X, ctx):
        feats = host_context_t(X, ctx) if self.host else X
        return self.predict(feats.cpu().numpy())


# ---------------------------------------------------------------- data

def load_test(args, scaler_source: Ctu13Preprocessor):
    df = load_ctu13(args.ctu13_dir, CTU13_DEFAULT_SPLIT["test"], with_endpoints=True)
    X, y = scaler_source.preprocess(df, fit=False)
    src, dst = endpoint_keys(df[SRC_IP], df[SRC_PORT], df[DST_IP], df[DST_PORT], "ip")
    raw = np.stack([df[c].fillna(0).clip(lower=0).to_numpy(dtype=np.float64)
                    for c in ("Dur", "TotPkts", "TotBytes", "SrcBytes")], axis=1)
    return X, y, raw, src, dst, scenario_segments(df)


def make_chunks(X, y, raw, src, dst, segments, window: int, chunk_flows: int, max_chunks=None) -> List[Chunk]:
    """Whole windows (per scenario, as 00 / the endpoint dataset), grouped into chunks of ~chunk_flows."""
    win = np.empty(len(y), dtype=np.int64)
    offset = 0
    for a, b in segments:
        win[a:b] = offset + np.arange(b - a) // window
        offset += (b - a + window - 1) // window
    step = max(1, chunk_flows // window) * window
    chunks = []
    for a, b in segments:
        for s in range(a, b, step):
            e = min(s + step, b)
            chunks.append(Chunk(X[s:e], raw[s:e], y[s:e], src[s:e], dst[s:e], win[s:e]))
    return chunks[:max_chunks] if max_chunks else chunks


# ---------------------------------------------------------------- evaluation

def clean_threshold(det, chunks, device, fpr=0.01):
    scores = []
    for ch in chunks:
        ctx = make_context(ch.src_key, ch.dst_key, ch.win, device)
        s = det.score(torch.as_tensor(ch.X, device=device), ctx)
        scores.append(s[ch.y == 0])
    return float(np.quantile(np.concatenate(scores), 1.0 - fpr))


def clean_stats(det, chunks, device, thr):
    """Clean-performance predictors for E021: test PR-AUC, recall at the 1%-FPR threshold, mean malicious logit margin."""
    from sklearn.metrics import average_precision_score
    scores, labels = [], []
    for ch in chunks:
        ctx = make_context(ch.src_key, ch.dst_key, ch.win, device)
        scores.append(det.score(torch.as_tensor(ch.X, device=device), ctx)); labels.append(ch.y)
    s, y = np.concatenate(scores), np.concatenate(labels)
    logit = lambda v: np.log(np.clip(v, 1e-6, 1 - 1e-6) / (1 - np.clip(v, 1e-6, 1 - 1e-6)))  # noqa: E731
    return {"test_pr_auc": float(average_precision_score(y, s)), "test_recall_at_1pct_fpr": float((s[y == 1] > thr).mean()),
            "mean_malicious_logit_margin": float(logit(s[y == 1]).mean() - logit(thr)), "threshold": float(thr)}


def tally(det, thr, ch, res, plan) -> Counter:
    s = det.score(res["X"], res["ctx"])
    orig, dec, y = s[:res["n"]], s[res["n"]:], ch.y
    c = Counter()
    for tag, t in (("1", thr), ("05", 0.5)):
        pos = orig >= t
        c[f"tp{tag}"] += int((pos & (y == 1)).sum())
        c[f"fp{tag}"] += int((pos & (y == 0)).sum())
        c[f"fn{tag}"] += int((~pos & (y == 1)).sum())
    c["bots"] += int((y == 1).sum())
    c["benign"] += int((y == 0).sum())
    c["decoys"] += res["m"]
    c["decoy_alarm"] += int((dec >= thr).sum())
    # Host-window view (D18c): a (window, bot host) group is detected if one of its botnet flows
    # alarms (hw_own) or, counting alarming decoys as detections of the host too, if any flow does (hw_any).
    n_groups = len(plan.budget_shape)
    if n_groups:
        own = np.bincount(plan.g_bot[orig[plan.bot] >= thr], minlength=n_groups) > 0
        dec_hit = (np.bincount(plan.dec_group[dec >= thr], minlength=n_groups) > 0) if res["m"] else np.zeros(n_groups, bool)
        c["hw_groups"] += n_groups
        c["hw_own"] += int(own.sum())
        c["hw_any"] += int((own | dec_hit).sum())
    return c


def metrics(c: Counter) -> Dict[str, float]:
    f1 = lambda tp, fp, fn: 2 * tp / max(2 * tp + fp + fn, 1)  # noqa: E731
    return {
        "recall": c["tp1"] / max(c["bots"], 1), "fpr": c["fp1"] / max(c["benign"], 1),
        "f1": f1(c["tp1"], c["fp1"], c["fn1"]),
        "recall_05": c["tp05"] / max(c["bots"], 1), "fpr_05": c["fp05"] / max(c["benign"], 1),
        "f1_05": f1(c["tp05"], c["fp05"], c["fn05"]),
        "decoys": c["decoys"], "decoy_alarm_rate": c["decoy_alarm"] / max(c["decoys"], 1),
        "hostwin_recall": c["hw_own"] / max(c["hw_groups"], 1), "hostwin_recall_dec": c["hw_any"] / max(c["hw_groups"], 1),
    }


def condition_grid(betas, rhos, superadd: bool):
    """(beta, rho) configs: the full grid plus the budget-matched A/B runs that S needs."""
    grid = {(0.0, 0.0)}
    for b in betas:
        for r in rhos:
            grid.add((round(b, 6), r))
            if superadd and 0 < r < 1:
                grid.add((round((1 - r) * b, 6), 0.0))
                grid.add((round(r * b, 6), 1.0))
    return sorted(grid)


def summarize(rows: pd.DataFrame, rhos, col: str = "recall") -> pd.DataFrame:
    """Per detector x delay mode x attack seed x beta: Delta_A, Delta_B, Delta_C*, G, S (D17).

    Delta = clean ``col`` - attacked ``col`` (clean = the 'clean' rows). Only A/B/C rows enter; the
    delay-only (D) and replay rows are separate conditions.
    """
    out = []
    clean = {(r.detector, r.origin, r.attack_seed): getattr(r, col) for r in rows.itertuples() if r.condition == "clean"}
    keys = ["detector", "origin", "attack_seed", "delay"]
    for key, g in rows[rows.condition.isin(["A", "B", "C"])].groupby(keys):
        base = clean[key[:3]]
        delta = {(r.beta, r.rho): base - getattr(r, col) for r in g.itertuples()}
        for beta in sorted({b for b, _ in delta}):
            if any((beta, r) not in delta for r in rhos):  # budget-matched helper betas
                continue
            ds = {r: delta[(beta, r)] for r in rhos}
            best = max(ds, key=ds.get)
            s_vals = {r: ds[r] - delta[(round((1 - r) * beta, 6), 0.0)] - delta[(round(r * beta, 6), 1.0)]
                      for r in ds if 0 < r < 1 and (round((1 - r) * beta, 6), 0.0) in delta and (round(r * beta, 6), 1.0) in delta}
            out.append({**dict(zip(keys, key)), "beta": beta, "delta_A": ds[0.0], "delta_B": ds[1.0],
                        "delta_Cstar": ds[best], "rho_star": best,
                        "G": ds[best] - max(ds[0.0], ds[1.0]),
                        "S_max_abs": max((abs(v) for v in s_vals.values()), default=float("nan")),
                        "S_signed_mean": float(np.mean(list(s_vals.values()))) if s_vals else float("nan"),
                        **{f"S_rho{r}": v for r, v in s_vals.items()},
                        "S_by_rho": json.dumps({str(r): v for r, v in s_vals.items()})})
    return pd.DataFrame(out)


def fit_models(args, device, tab, cache: Path):
    """Fit MLP host-ip, XGB host-ip, XGB plain and the preprocessor for ``--seed``; save them in ``cache``."""
    base = ["--dataset", "ctu13", "--ctu13-dir", args.ctu13_dir, "--context", "host", "--node-key", "ip",
            "--context-window", str(args.context_window), "--class-weight", args.class_weight,
            "--device", str(device), "--xgb-device", "cpu", "--n-jobs", str(args.n_jobs)]
    targs = tab.parse_args(base)
    data = tab.prepare_ctu13(targs)
    mlp_predict, mlp_info = tab.train_mlp(data, args.seed, str(device), targs)
    xgb_host = None
    if not args.no_xgb:
        xgb_host, host_info = tab.train_xgboost(data, args.seed, "cpu", targs)
        plain = {s: {**d, "X": d["X"][:, :36]} for s, d in data.items()}
        xgb_plain, plain_info = tab.train_xgboost(plain, args.seed, "cpu", targs)
    pre = Ctu13Preprocessor()
    pre.preprocess(load_ctu13(args.ctu13_dir, CTU13_DEFAULT_SPLIT["train"]), fit=True)
    assert pre.feature_names[:N_VOLUME] == VOLUME_NAMES, pre.feature_names[:N_VOLUME]
    cache.mkdir(parents=True, exist_ok=True)
    torch.save({"state": mlp_predict.model.state_dict(), "hidden": targs.mlp_hidden, "dropout": targs.mlp_dropout},
               cache / "mlp.pt")
    if not args.no_xgb:
        xgb_host.model.get_booster().save_model(str(cache / "xgb_host.json"))
        xgb_plain.model.get_booster().save_model(str(cache / "xgb_plain.json"))
    with (cache / "scaler.pkl").open("wb") as fh:
        pickle.dump(pre.get_state(), fh)
    (cache / "info.json").write_text(json.dumps({"seed": args.seed, "class_weight": args.class_weight,
                                                 "context_window": args.context_window,
                                                 "mlp_best_validation_f1": mlp_info["best_validation_f1"],
                                                 **({} if args.no_xgb else {"xgb_host_best_iteration": host_info["best_iteration"],
                                                                            "xgb_plain_best_iteration": plain_info["best_iteration"]})}))
    (cache / "done").touch()
    return data, mlp_predict, xgb_host


def booster_predictor(path: Path, best_iteration: int, n_jobs: int):
    import xgboost as xgb
    bst = xgb.Booster()
    bst.load_model(str(path))
    bst.set_param({"nthread": n_jobs})
    return lambda X: bst.predict(xgb.DMatrix(X), iteration_range=(0, best_iteration + 1))


# ---------------------------------------------------------------- main

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ctu13-dir", default="data/raw/ctu13/CTU-13-Dataset")
    p.add_argument("--gnn-checkpoint", type=Path, required=True)
    p.add_argument("--seed", type=int, default=42, help="training seed of the refitted MLP / XGB")
    p.add_argument("--attack-seeds", type=int, nargs="+", default=[0, 1])
    p.add_argument("--betas", type=float, nargs="+", default=[0.05, 0.10, 0.25, 0.50])
    p.add_argument("--rhos", type=float, nargs="+", default=[0.0, 0.25, 0.5, 0.75, 1.0])
    p.add_argument("--no-superadd", action="store_true", help="skip the budget-matched A/B runs needed for S")
    p.add_argument("--replay", action="store_true", help="also run B_replay (benign flows replayed unchanged, rho=1)")
    p.add_argument("--delay-modes", nargs="+", default=["free", "off"], choices=["free", "off", "coupled"],
                   help="free: delay allowed in every condition (also B and the delay-only D row); off: bytes only; "
                        "coupled: E017 pilot (delay only with a shaping share)")
    p.add_argument("--restarts", type=int, default=1, help="random initialisations per attack (best kept)")
    p.add_argument("--model-cache", type=Path, default=None,
                   help="directory with the fitted models for --seed (written on first use, reused afterwards)")
    p.add_argument("--no-xgb", action="store_true", help="E021: skip the XGB detectors (not fitted, not attacked)")
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--step-frac", type=float, default=0.2)
    p.add_argument("--chunk-flows", type=int, default=400_000)
    p.add_argument("--max-chunks", type=int, default=None, help="smoke test: first N chunks per detector family")
    p.add_argument("--context-window", type=int, default=10000)
    p.add_argument("--class-weight", choices=["none", "balanced"], default="none")
    p.add_argument("--device", default="auto")
    p.add_argument("--n-jobs", type=int, default=8)
    p.add_argument("--output-dir", type=Path, default=Path("results/context_decomposition"))
    return p.parse_args(argv)


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    args = parse_args(argv)
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else
                          "cpu" if args.device == "auto" else args.device)
    tab = load_script("00_tabular_baselines.py", "tabular_baselines")
    abl = load_script("06_graph_ablation.py", "graph_ablation")
    out_dir = args.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Detectors, fitted once per training seed (cache) and reloaded from disk either way.
    cache = args.model_cache or out_dir / "models"
    data = mlp_predict = xgb_host_fit = None
    if not (cache / "done").exists():
        data, mlp_predict, xgb_host_fit = fit_models(args, device, tab, cache)
    info = json.loads((cache / "info.json").read_text())
    for key in ("seed", "class_weight", "context_window"):
        if info[key] != getattr(args, key):
            raise SystemExit(f"model cache {cache} was fitted with {key}={info[key]}, not {getattr(args, key)}")
    mlp_state = torch.load(cache / "mlp.pt", map_location="cpu")
    mlp_model = tab.FlowMLP(36 * 3 + 2, mlp_state["hidden"], mlp_state["dropout"])
    mlp_model.load_state_dict(mlp_state["state"])
    xgb_host = xgb_plain = None
    if not args.no_xgb:
        xgb_host = booster_predictor(cache / "xgb_host.json", info["xgb_host_best_iteration"], args.n_jobs)
        xgb_plain = booster_predictor(cache / "xgb_plain.json", info["xgb_plain_best_iteration"], args.n_jobs)

    ckpt = torch.load(args.gnn_checkpoint, map_location="cpu")
    meta = ckpt["metadata"]
    if meta.get("graph") != "endpoint" or meta.get("node_key") != "ip":
        raise SystemExit("--gnn-checkpoint must be an endpoint-graph, node-key ip checkpoint")
    if meta.get("seed") is not None and int(meta["seed"]) != args.seed:
        logger.warning("GNN checkpoint seed %s differs from --seed %d", meta.get("seed"), args.seed)
    gnn = abl.build_model(meta, 1, 36)
    gnn.load_state_dict(ckpt["model_state_dict"])
    gnn_window = int(meta.get("window_size", 1000))

    pre = Ctu13Preprocessor()
    pre.load_preprocessed(str(cache / "scaler.pkl"))
    assert pre.feature_names[:N_VOLUME] == VOLUME_NAMES, pre.feature_names[:N_VOLUME]
    mean = torch.as_tensor(pre.scaler.mean_, dtype=torch.float64, device=device)
    scale = torch.as_tensor(pre.scaler.scale_, dtype=torch.float64, device=device)
    X, y, raw, src, dst, segments = load_test(args, pre)
    if data is not None:
        assert np.allclose(X, data["test"]["X"][:, :36]), "test features differ from 00's"
    logger.info("test: %d flows, %d botnet", len(y), int(y.sum()))

    mlp = MLPDetector("mlp_host_ip", mlp_model, device)
    families = [
        {"name": "tab", "window": args.context_window, "white": mlp,
         "targets": [] if args.no_xgb else [XGBDetector("xgb_host_ip", xgb_host, True), XGBDetector("xgb_plain", xgb_plain, False)]},
        {"name": "gnn", "window": gnn_window, "white": GNNDetector("gnn_ip", gnn, device), "targets": []},
    ]
    # (beta, rho, replay, delay mode, label); the clean row runs no attack (delay off, zero budgets).
    grid = [g for g in condition_grid(args.betas, args.rhos, not args.no_superadd) if g[0] > 0]
    configs = [(0.0, 0.0, False, "off", "clean")]
    for mode in args.delay_modes:
        if mode == "free":
            configs.append((0.0, 0.0, False, mode, "D"))  # delay-only attacker
        configs += [(b, r, False, mode, "AC" if 0 < r < 1 else "A" if r == 0 else "B") for b, r in grid]
        if args.replay:
            configs += [(b, 1.0, True, mode, "B_replay") for b in args.betas]
    rows = []
    clean_info = {}
    for fam in families:
        chunks = make_chunks(X, y, raw, src, dst, segments, fam["window"], args.chunk_flows, args.max_chunks)
        dets = [fam["white"]] + fam["targets"]
        thr = {d.name: clean_threshold(d, chunks, device) for d in dets}
        t = float(np.clip(thr[fam["white"].name], 1e-6, 1 - 1e-6))
        thr_logit = float(np.log(t / (1 - t)))
        logger.info("%s: %d chunks, thresholds at 1%% FPR: %s", fam["name"], len(chunks), thr)
        clean_info[fam["white"].name] = clean_stats(fam["white"], chunks, device, thr[fam["white"].name])
        if fam["name"] == "tab" and data is not None:  # the torch context path must reproduce 00's numpy path
            ch, n = chunks[0], len(chunks[0].y)
            ctx0 = make_context(ch.src_key, ch.dst_key, ch.win, device)
            ours = mlp.score(torch.as_tensor(ch.X, device=device), ctx0)
            ref = mlp_predict(data["test"]["X"][:n])
            logger.info("MLP torch-vs-00 max |diff| = %.2e", float(np.abs(ours - ref).max()))
            assert np.abs(ours - ref).max() < 1e-3, "torch host context does not match 00"
            if not args.no_xgb:
                ours_x = xgb_host(host_context_t(torch.as_tensor(ch.X, device=device), ctx0).cpu().numpy())
                logger.info("XGB booster-vs-00 max |diff| = %.2e", float(np.abs(ours_x - xgb_host_fit(data["test"]["X"][:n])).max()))
        for aseed in args.attack_seeds:
            for beta, rho, replay, mode, label in configs:
                tallies = {d.name: Counter() for d in dets}
                cost_shape = cost_decoy = base_bytes = 0.0
                for ci, ch in enumerate(chunks):
                    rng = np.random.default_rng([aseed, ci, int(round(beta * 1e4)), int(round(rho * 100)), int(replay),
                                                 ["off", "free", "coupled"].index(mode)])
                    plan = build_plan(ch, beta, rho, rng, replay=replay)
                    res = run_attack(ch, plan, fam["white"].logit, thr_logit, mean, scale, rng, device,
                                     steps=args.steps, step_frac=args.step_frac, optimise=not replay,
                                     delay=mode, restarts=args.restarts)
                    for key, budget in (("group_shape", plan.budget_shape), ("group_decoy", plan.budget_decoy)):
                        if res[key] is not None:
                            assert (res[key].cpu().numpy() <= budget + 1e-6).all(), f"{key} over budget"
                    cost_shape += res["cost_shape"]; cost_decoy += res["cost_decoy"]; base_bytes += float(plan.base_bytes.sum())
                    for d in dets:
                        tallies[d.name] += tally(d, thr[d.name], ch, res, plan)
                    del res
                cond = "C" if label == "AC" else label
                for d in dets:
                    rows.append({"family": fam["name"], "detector": d.name, "origin": "white" if d is fam["white"] else "transfer",
                                 "train_seed": args.seed, "attack_seed": aseed, "delay": "-" if cond == "clean" else mode,
                                 "steps": args.steps, "restarts": args.restarts, "beta": beta, "rho": rho, "condition": cond,
                                 "threshold": thr[d.name], "cost_shape": cost_shape, "cost_decoy": cost_decoy,
                                 "base_bytes": base_bytes, **metrics(tallies[d.name])})
                logger.info("%s aseed=%d delay=%s beta=%.4g rho=%.2f %s: %s", fam["name"], aseed, mode, beta, rho, cond,
                            {d.name: round(rows[-len(dets) + i]["recall"], 4) for i, d in enumerate(dets)})
                pd.DataFrame(rows).to_csv(out_dir / "rows.csv", index=False)
    df = pd.DataFrame(rows)
    for col, name in (("recall", "summary.csv"), ("hostwin_recall", "summary_hostwin.csv"),
                      ("hostwin_recall_dec", "summary_hostwin_dec.csv")):
        summarize(df, args.rhos, col).to_csv(out_dir / name, index=False)
    gm = Path(args.gnn_checkpoint).parent / "metrics.json"
    if gm.exists():
        gv = json.loads(gm.read_text()).get("validation", {})
        clean_info["gnn_ip"]["val_f1"] = gv.get("f1")
    clean_info["mlp_host_ip"]["val_f1"] = info.get("mlp_best_validation_f1")
    (out_dir / "clean_stats.json").write_text(json.dumps({"train_seed": args.seed, **clean_info}, indent=2))
    (out_dir / "config.json").write_text(json.dumps({**vars(args), "gnn_window": gnn_window, "gnn_meta": {k: v for k, v in meta.items() if isinstance(v, (int, float, str, type(None)))}},
                                                    indent=2, default=str))
    logger.info("Results in %s", out_dir)
    return out_dir


if __name__ == "__main__":
    main()
