#!/usr/bin/env python3
"""Non-graph baselines (roadmap Phase 1): XGBoost and an MLP on single flows.

Uses exactly the flows, features, chronological 60/20/20 split and
train-only preprocessing of the GNN pipeline (src/data/netflow_v3.py), so the
numbers are directly comparable with 01_baseline_training.py. Each model is
trained once per seed; validation is used only for early stopping.

Example (inside the container, from the repository root):

    python experiments/00_tabular_baselines.py --dataset nf-unsw-nb15-v3
    python experiments/00_tabular_baselines.py --dataset nf-ton-iot-v3 --models xgboost --seeds 42 43

Outputs in results/tabular/<timestamp>_<dataset>/:
    results.csv     one row per model x seed x split
    per_class.csv   test detection rate per Attack class, per model x seed
    summary.csv     test metrics, mean and std over seeds
    config.json
"""

import argparse
import csv
import json
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.netflow_v3 import (  # noqa: E402
    ATTACK_COLUMN,
    NETFLOW_V3_DATASETS,
    NETFLOW_V3_RAW_SUBDIR,
    NetFlowV3Preprocessor,
    dataset_variant_id,
    load_netflow_v3,
)
from data.splits import chronological_split  # noqa: E402
from utils.metrics import binary_classification_metrics  # noqa: E402

logger = logging.getLogger("tabular_baselines")

MODELS = ("xgboost", "mlp")
METRICS = ("accuracy", "precision", "recall", "f1", "roc_auc")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(name: str) -> str:
    if name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return name


def prepare_data(args: argparse.Namespace) -> Dict[str, Dict[str, np.ndarray]]:
    """Time-sorted flows -> chronological blocks -> train-fitted preprocessing."""
    csv_path = Path(args.raw_dir) / NETFLOW_V3_DATASETS[args.dataset]
    df = load_netflow_v3(str(csv_path), max_flows=args.max_flows, slice_start=args.slice_start)
    blocks = chronological_split(len(df))

    preprocessor = NetFlowV3Preprocessor()
    data = {}
    for split, idx in zip(("train", "validation", "test"), blocks):
        part = df.iloc[idx].reset_index(drop=True)
        X, y = preprocessor.preprocess(part, fit=(split == "train"))
        data[split] = {"X": X, "y": y, "attack": part[ATTACK_COLUMN].astype(str).to_numpy()}
        logger.info("%s: %d flows, attack fraction %.4f", split, len(y), float(y.mean()))
    return data


def train_xgboost(data, seed: int, device: str, args: argparse.Namespace):
    import xgboost as xgb

    model = xgb.XGBClassifier(
        n_estimators=args.xgb_estimators,
        max_depth=args.xgb_max_depth,
        learning_rate=args.xgb_learning_rate,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        device=device,
        objective="binary:logistic",
        eval_metric="logloss",
        early_stopping_rounds=args.xgb_early_stopping,
        random_state=seed,
        n_jobs=args.n_jobs,
    )
    model.fit(
        data["train"]["X"], data["train"]["y"],
        eval_set=[(data["validation"]["X"], data["validation"]["y"])],
        verbose=False,
    )
    info = {"best_iteration": int(model.best_iteration)}

    def predict_scores(X: np.ndarray) -> np.ndarray:
        return model.predict_proba(X)[:, 1]

    return predict_scores, info


class FlowMLP(torch.nn.Module):
    def __init__(self, in_dim: int, hidden: List[int], dropout: float):
        super().__init__()
        layers: List[torch.nn.Module] = []
        prev = in_dim
        for width in hidden:
            layers += [torch.nn.Linear(prev, width), torch.nn.ReLU(), torch.nn.Dropout(dropout)]
            prev = width
        layers.append(torch.nn.Linear(prev, 1))
        self.net = torch.nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def _mlp_scores(model: FlowMLP, X: np.ndarray, device: str, batch_size: int) -> np.ndarray:
    model.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(X), batch_size):
            xb = torch.from_numpy(X[start:start + batch_size]).to(device)
            out.append(torch.sigmoid(model(xb)).cpu().numpy())
    return np.concatenate(out)


def train_mlp(data, seed: int, device: str, args: argparse.Namespace):
    set_seed(seed)
    X_train = torch.from_numpy(data["train"]["X"])
    y_train = torch.from_numpy(data["train"]["y"].astype(np.float32))
    model = FlowMLP(X_train.shape[1], args.mlp_hidden, args.mlp_dropout).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=args.mlp_learning_rate, weight_decay=args.mlp_weight_decay)
    loss_fn = torch.nn.BCEWithLogitsLoss()
    generator = torch.Generator().manual_seed(seed)

    best_f1, best_state, best_epoch, stale = -1.0, None, 0, 0
    for epoch in range(1, args.mlp_epochs + 1):
        model.train()
        perm = torch.randperm(len(X_train), generator=generator)
        for start in range(0, len(perm), args.mlp_batch_size):
            idx = perm[start:start + args.mlp_batch_size]
            xb, yb = X_train[idx].to(device), y_train[idx].to(device)
            optimiser.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            optimiser.step()

        val_scores = _mlp_scores(model, data["validation"]["X"], device, args.mlp_batch_size)
        val_f1 = binary_classification_metrics(data["validation"]["y"], (val_scores >= 0.5).astype(int))["f1"]
        logger.info("mlp seed=%d epoch=%d val_f1=%.4f", seed, epoch, val_f1)
        if val_f1 > best_f1:
            best_f1, best_epoch, stale = val_f1, epoch, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= args.mlp_patience:
                break
    model.load_state_dict(best_state)
    info = {"best_epoch": best_epoch, "best_validation_f1": float(best_f1)}

    def predict_scores(X: np.ndarray) -> np.ndarray:
        return _mlp_scores(model, X, device, args.mlp_batch_size)

    return predict_scores, info


TRAINERS = {"xgboost": train_xgboost, "mlp": train_mlp}


def evaluate(scores: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    return binary_classification_metrics(y, (scores >= 0.5).astype(int), scores)


def per_class_detection(scores: np.ndarray, attack: np.ndarray) -> List[Tuple[str, int, float]]:
    """Fraction of flows of each Attack class predicted as malicious (for Benign: the false-positive rate)."""
    predicted = scores >= 0.5
    rows = []
    for name in sorted(np.unique(attack)):
        mask = attack == name
        rows.append((name, int(mask.sum()), float(predicted[mask].mean())))
    return rows


def write_csv(path: Path, rows: List[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarise(results: List[dict]) -> List[dict]:
    summary = []
    for model in sorted({r["model"] for r in results}):
        rows = [r for r in results if r["model"] == model and r["split"] == "test"]
        entry = {"model": model, "seeds": len(rows)}
        for metric in METRICS:
            values = np.array([r[metric] for r in rows if r[metric] is not None], dtype=float)
            entry[f"{metric}_mean"] = float(values.mean()) if values.size else None
            entry[f"{metric}_std"] = float(values.std(ddof=1)) if values.size > 1 else 0.0
        summary.append(entry)
    return summary


def run(args: argparse.Namespace) -> Path:
    device = resolve_device(args.device)
    variant = dataset_variant_id(args.dataset, args.max_flows, args.slice_start)
    out_dir = Path(args.output_dir) / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{variant}"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = prepare_data(args)
    config = {
        "dataset": args.dataset,
        "variant": variant,
        "max_flows": args.max_flows,
        "slice_start": args.slice_start,
        "split": "chronological 60/20/20",
        "sizes": {s: int(len(d["y"])) for s, d in data.items()},
        "attack_fraction": {s: float(d["y"].mean()) for s, d in data.items()},
        "num_features": int(data["train"]["X"].shape[1]),
        "device": device,
        "args": vars(args),
        "runs": [],
    }

    results, per_class = [], []
    for model_name in args.models:
        for seed in args.seeds:
            set_seed(seed)
            started = time.time()
            predict_scores, info = TRAINERS[model_name](data, seed, device, args)
            elapsed = time.time() - started
            for split in ("train", "validation", "test"):
                metrics = evaluate(predict_scores(data[split]["X"]), data[split]["y"])
                results.append({"model": model_name, "seed": seed, "split": split, **metrics})
            test_scores = predict_scores(data["test"]["X"])
            for attack, count, rate in per_class_detection(test_scores, data["test"]["attack"]):
                per_class.append({"model": model_name, "seed": seed, "attack": attack,
                                  "flows": count, "predicted_malicious": rate})
            config["runs"].append({"model": model_name, "seed": seed, "train_seconds": elapsed, **info})
            test_f1 = results[-1]["f1"]
            logger.info("%s seed=%d: test F1=%.4f (%.0fs)", model_name, seed, test_f1, elapsed)

    write_csv(out_dir / "results.csv", results)
    write_csv(out_dir / "per_class.csv", per_class)
    summary = summarise(results)
    write_csv(out_dir / "summary.csv", summary)
    with (out_dir / "config.json").open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, default=str)

    for entry in summary:
        logger.info(
            "%s test F1 = %.4f ± %.4f, ROC-AUC = %s (%d seeds)",
            entry["model"], entry["f1_mean"], entry["f1_std"],
            "n/a" if entry["roc_auc_mean"] is None else f"{entry['roc_auc_mean']:.4f}", entry["seeds"],
        )
    logger.info("Results in %s", out_dir)
    return out_dir


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XGBoost and MLP baselines on the NetFlow-v3 flows and splits.")
    parser.add_argument("--dataset", choices=sorted(NETFLOW_V3_DATASETS), default="nf-unsw-nb15-v3")
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44, 45, 46])
    parser.add_argument("--max-flows", type=int, default=None,
                        help="use only this many time-contiguous flows (default: all)")
    parser.add_argument("--slice-start", type=float, default=None,
                        help="start of the --max-flows slice, as a fraction of the time-sorted flows")
    parser.add_argument("--raw-dir", default=f"data/raw/{NETFLOW_V3_RAW_SUBDIR}")
    parser.add_argument("--output-dir", default="results/tabular")
    parser.add_argument("--device", default="auto", help="auto, cpu or cuda")
    parser.add_argument("--n-jobs", type=int, default=8, help="XGBoost CPU threads")
    parser.add_argument("--xgb-estimators", type=int, default=1000)
    parser.add_argument("--xgb-max-depth", type=int, default=8)
    parser.add_argument("--xgb-learning-rate", type=float, default=0.1)
    parser.add_argument("--xgb-early-stopping", type=int, default=50)
    parser.add_argument("--mlp-hidden", nargs="+", type=int, default=[128, 64])
    parser.add_argument("--mlp-dropout", type=float, default=0.2)
    parser.add_argument("--mlp-learning-rate", type=float, default=1e-3)
    parser.add_argument("--mlp-weight-decay", type=float, default=1e-5)
    parser.add_argument("--mlp-batch-size", type=int, default=4096)
    parser.add_argument("--mlp-epochs", type=int, default=30)
    parser.add_argument("--mlp-patience", type=int, default=5)
    return parser.parse_args(argv)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    run(parse_args())


if __name__ == "__main__":
    main()
