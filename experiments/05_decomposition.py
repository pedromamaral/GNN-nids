#!/usr/bin/env python3
"""Decomposition of adversarial degradation into feature and induced-structure effects.

Phase 1 ("kill experiment") of the paper plan (docs/PAPER_ROADMAP.md).

For each attack and epsilon, the same adversarial features X_adv are evaluated
under three conditions (see ``src/analysis/decomposition.py``):

    A : (X_adv, E)       pure feature effect  -- what 02_feature_attacks.py reports
    B : (X,     E_rec)   pure induced-structure effect
    C : (X_adv, E_rec)   deployment: the defender rebuilds the graph

where E_rec = kNN(X_adv). Attacks:

    fgsm         gradient on the fixed graph (deterministic: one run per checkpoint)
    pgd          gradient on the fixed graph, random start
    pgd_rebuild  construction-aware PGD: graph rebuilt from the current features
                 at every step. Its condition C is C* in the paper plan.

One run = one checkpoint (one training seed) x several attack seeds.
Rows are appended to ``decomposition.csv`` in the run directory; aggregate
across runs with ``experiments/05b_decomposition_report.py``.

Example:
    python experiments/05_decomposition.py \\
        --dataset cicids2017-patator --model gcn --k 5 \\
        --checkpoint results/runs/<run>/best_checkpoint.pt --training-seed 42 \\
        --attack-seeds 42 43 44 45 46 --epsilons 0.05 0.10 --deterministic
"""

import argparse
import csv
import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.dataset import load_split_datasets
from data.download import CICIDS2017_SUBSETS
from models import GCN_NIDS, GAT_NIDS
from training.trainer import Trainer

from attacks.fgsm import fgsm_attack
from attacks.pgd import pgd_attack
from attacks.construction_aware import construction_aware_pgd
from analysis.decomposition import CONDITIONS, CONDITION_DESCRIPTIONS, build_conditions, check_reconstruction, churn_between


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
# The k-NN builder logs every construction at INFO; this experiment rebuilds thousands of graphs.
logging.getLogger("data.graph_builder").setLevel(logging.WARNING)
logging.getLogger("src.data.graph_builder").setLevel(logging.WARNING)

DEFAULT_CONFIG_PATH = Path("configs/base_config.yaml")
ATTACKS = ("fgsm", "pgd", "pgd_rebuild")


# ---------------------------------------------------------------------------
# Small helpers (kept local so this script does not depend on 02_*.py)
# ---------------------------------------------------------------------------

def load_config(config_path: Path) -> dict:
    if not config_path.exists() or yaml is None:
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def set_deterministic(enabled: bool) -> None:
    if enabled:
        # warn_only: some PyG scatter kernels have no deterministic CUDA implementation;
        # an unattended server run should warn, not abort. Seeds are still fixed.
        torch.use_deterministic_algorithms(True, warn_only=True)
        if torch.cuda.is_available():
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


def build_model(model_name: str, num_node_features: int, hidden_dim: int, dropout: float, hidden_layers: int = 1):
    if model_name == "gcn":
        return GCN_NIDS(num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers)
    if model_name == "gat":
        return GAT_NIDS(num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers)
    raise ValueError(f"Unsupported model type: {model_name}")


def read_checkpoint_metadata(checkpoint_path: Path) -> dict:
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    return checkpoint.get("metadata", {}) or {}


def validate_checkpoint_metadata(metadata: dict, checkpoint_path: Path, expected_k: int, expected_seed: int) -> None:
    checkpoint_k = metadata.get("k")
    if checkpoint_k is not None and int(checkpoint_k) != int(expected_k):
        raise ValueError(f"Checkpoint {checkpoint_path} was trained with k={checkpoint_k}, but --k={expected_k}.")
    checkpoint_seed = metadata.get("seed")
    if checkpoint_seed is not None and int(checkpoint_seed) != int(expected_seed):
        raise ValueError(
            f"Checkpoint {checkpoint_path} was trained with seed={checkpoint_seed}, but --training-seed={expected_seed}."
        )


def append_csv(row: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def create_run_directory(args: argparse.Namespace, hidden_layers: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = (
        f"{timestamp}_{args.dataset}_{args.model}_k_{args.k}_L{hidden_layers}"
        f"_training_seed_{args.training_seed}"
    )
    run_dir = Path(args.output_dir) / name
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = Path(args.output_dir) / f"{name}_{suffix}"
    run_dir.mkdir(parents=True)
    return run_dir


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def attack_window(model, data, attack: str, epsilon: float, args: argparse.Namespace):
    """Return (adversarial window, precomputed rebuilt graph or None)."""
    if attack == "fgsm":
        return fgsm_attack(model, data, epsilon=epsilon), None
    if attack == "pgd":
        return pgd_attack(model, data, epsilon=epsilon, alpha=args.alpha, steps=args.steps, random_start=True), None
    if attack == "pgd_rebuild":
        adv = construction_aware_pgd(
            model,
            data,
            epsilon=epsilon,
            alpha=args.alpha,
            steps=args.steps,
            k=args.k,
            metric=args.metric,
            rebuild_every=args.rebuild_every,
            random_start=True,
        )
        return adv, (adv.edge_index, getattr(adv, "edge_attr", None))
    raise ValueError(f"Unsupported attack: {attack}")


def evaluate_attack(trainer, test_dataset, attack: str, epsilon: float, args: argparse.Namespace) -> dict:
    """Attack every window once and evaluate all conditions on the same X_adv."""
    per_condition = {cond: [] for cond in CONDITIONS}
    ncr_global, ncr_malicious = [], []

    for data in test_dataset:
        data_dev = data.clone().to(trainer.device)
        adv, rebuilt = attack_window(trainer.model, data_dev, attack, epsilon, args)
        conditions = build_conditions(data, adv, k=args.k, metric=args.metric, rebuilt_graph=rebuilt)
        for cond in CONDITIONS:
            per_condition[cond].append(conditions[cond])

        ncr_global.append(churn_between(data, conditions["C"]))
        malicious = np.flatnonzero(data.y.cpu().numpy().reshape(-1) == 1)
        if malicious.size > 0:
            ncr_malicious.append(churn_between(data, conditions["C"], node_indices=malicious))

    metrics = {cond: trainer.evaluate(per_condition[cond]) for cond in CONDITIONS}
    return {
        "metrics": metrics,
        "ncr_global": float(np.mean(ncr_global)) if ncr_global else 0.0,
        "ncr_malicious": float(np.mean(ncr_malicious)) if ncr_malicious else 0.0,
    }


def run_decomposition(args: argparse.Namespace) -> dict:
    config = load_config(DEFAULT_CONFIG_PATH)
    train_config = config.get("train", config)
    set_deterministic(args.deterministic)

    metadata = read_checkpoint_metadata(args.checkpoint)
    validate_checkpoint_metadata(metadata, args.checkpoint, args.k, args.training_seed)

    hidden_layers = args.hidden_layers if args.hidden_layers is not None else int(metadata.get("hidden_layers", 1))
    hidden_dim = args.hidden_dim if args.hidden_dim is not None else int(metadata.get("hidden_dim", 64))
    dropout = args.dropout if args.dropout is not None else float(metadata.get("dropout", 0.5))
    window_size = args.window_size or metadata.get("window_size") or train_config.get("window_size", 1000)

    run_dir = create_run_directory(args, hidden_layers)
    csv_path = run_dir / "decomposition.csv"

    _, _, test_dataset = load_split_datasets(
        name=args.dataset, root="data/graphs", rebuild=False, window_size=window_size, k=args.k
    )
    test_dataset = [test_dataset[i] for i in range(len(test_dataset))]
    if args.max_windows is not None:
        test_dataset = test_dataset[: args.max_windows]

    model = build_model(args.model, test_dataset[0].x.shape[1], hidden_dim, dropout, hidden_layers)
    trainer = Trainer(
        model=model,
        device=args.device or train_config.get("device", "auto"),
        epochs=1,
        patience=1,
        output_dir=str(run_dir),
        batch_size=train_config.get("batch_size", 1),
    )
    trainer.load_checkpoint(args.checkpoint)

    # Sanity check: condition B is only meaningful if kNN(X_clean) == E.
    reconstruction = check_reconstruction(test_dataset, k=args.k, metric=args.metric, max_windows=args.sanity_windows)
    logger.info("Reconstruction check: %s", reconstruction)
    if reconstruction["mean_churn"] > args.reconstruction_tolerance:
        message = (
            f"Rebuilding the graph from CLEAN features changes {reconstruction['mean_churn']:.4f} of neighbour slots "
            f"(tolerance {args.reconstruction_tolerance}). Condition B would mix attack and construction effects. "
            "Check metric/k/bidirectional against the training graphs, or pass --allow-reconstruction-mismatch."
        )
        if not args.allow_reconstruction_mismatch:
            raise RuntimeError(message)
        logger.warning(message)

    clean_metrics = trainer.evaluate(test_dataset)
    logger.info("Clean metrics: %s", clean_metrics)

    results = {
        "dataset": args.dataset,
        "model": args.model,
        "k": args.k,
        "metric": args.metric,
        "hidden_layers": hidden_layers,
        "training_seed": args.training_seed,
        "attack_seeds": args.attack_seeds,
        "checkpoint": str(args.checkpoint),
        "window_size": window_size,
        "num_windows": len(test_dataset),
        "reconstruction_check": reconstruction,
        "clean_metrics": clean_metrics,
        "conditions": {c: {"features": f, "graph": g} for c, (f, g) in CONDITION_DESCRIPTIONS.items()},
        "runs": [],
    }

    for attack in args.attacks:
        # FGSM is deterministic given the weights: one run is enough.
        seeds = args.attack_seeds[:1] if attack == "fgsm" else args.attack_seeds
        for epsilon in args.epsilons:
            for attack_seed in seeds:
                set_seed(attack_seed)
                logger.info("%s eps=%s attack_seed=%s", attack, epsilon, attack_seed)
                outcome = evaluate_attack(trainer, test_dataset, attack, epsilon, args)

                effective_alpha = None
                if attack != "fgsm":
                    effective_alpha = args.alpha if args.alpha is not None else 2.5 * epsilon / args.steps

                for cond in CONDITIONS:
                    m = outcome["metrics"][cond]
                    features, graph = CONDITION_DESCRIPTIONS[cond]
                    row = {
                        "dataset": args.dataset,
                        "model": args.model,
                        "k": args.k,
                        "metric": args.metric,
                        "hidden_layers": hidden_layers,
                        "attack": attack,
                        "epsilon": epsilon,
                        "alpha": effective_alpha,
                        "steps": args.steps if attack != "fgsm" else None,
                        "rebuild_every": args.rebuild_every if attack == "pgd_rebuild" else None,
                        "training_seed": args.training_seed,
                        "attack_seed": attack_seed,
                        "condition": cond,
                        "features": features,
                        "graph": graph,
                        "clean_f1": clean_metrics["f1"],
                        "clean_recall": clean_metrics["recall"],
                        "f1": m["f1"],
                        "precision": m["precision"],
                        "recall": m["recall"],
                        "accuracy": m["accuracy"],
                        "roc_auc": m.get("roc_auc"),
                        "delta_f1": clean_metrics["f1"] - m["f1"],
                        "delta_recall": clean_metrics["recall"] - m["recall"],
                        "ncr_global": outcome["ncr_global"],
                        "ncr_malicious": outcome["ncr_malicious"],
                        "checkpoint": str(args.checkpoint),
                    }
                    append_csv(row, csv_path)

                results["runs"].append({"attack": attack, "epsilon": epsilon, "attack_seed": attack_seed, **outcome})
                logger.info(
                    "  F1  A=%.4f  B=%.4f  C=%.4f  (clean %.4f)  NCR_mal=%.4f",
                    outcome["metrics"]["A"]["f1"],
                    outcome["metrics"]["B"]["f1"],
                    outcome["metrics"]["C"]["f1"],
                    clean_metrics["f1"],
                    outcome["ncr_malicious"],
                )

    with (run_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, default=float)
    logger.info("Decomposition complete. Results in %s", run_dir)
    return results


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cicids_choices = sorted(CICIDS2017_SUBSETS.keys())
    parser.add_argument("--dataset", choices=["nsl-kdd"] + cicids_choices, required=True)
    parser.add_argument("--model", choices=["gcn", "gat"], required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--attack-seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--metric", default="cosine", help="k-NN metric; must match the training graphs.")
    parser.add_argument("--hidden-dim", type=int, default=None, help="Default: from checkpoint metadata, else 64.")
    parser.add_argument("--hidden-layers", type=int, default=None, help="Default: from checkpoint metadata, else 1.")
    parser.add_argument("--dropout", type=float, default=None, help="Default: from checkpoint metadata, else 0.5.")
    parser.add_argument("--window-size", type=int, default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--attacks", nargs="+", choices=ATTACKS, default=list(ATTACKS))
    parser.add_argument("--epsilons", type=float, nargs="+", default=[0.05, 0.10])
    parser.add_argument("--alpha", type=float, default=None, help="PGD step; default 2.5 * eps / steps.")
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--rebuild-every", type=int, default=1, help="pgd_rebuild: rebuild the graph every N steps.")
    parser.add_argument("--max-windows", type=int, default=None, help="Use only the first N test windows (smoke runs).")
    parser.add_argument("--sanity-windows", type=int, default=50, help="Windows used by the reconstruction check.")
    parser.add_argument("--reconstruction-tolerance", type=float, default=0.01)
    parser.add_argument("--allow-reconstruction-mismatch", action="store_true")
    parser.add_argument("--output-dir", default=str(Path("results") / "decomposition"))
    parser.add_argument("--deterministic", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    run_decomposition(parse_args())


if __name__ == "__main__":
    main()
