# experiments/02_feature_attacks.py

#!/usr/bin/env python3
"""Feature-space adversarial attacks against trained GNN-NIDS baselines."""

import argparse
import csv
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in lightweight test environments
    yaml = None

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.dataset import load_split_datasets
from data.download import CICIDS2017_SUBSETS
from models import GCN_NIDS, GAT_NIDS
from training.trainer import Trainer

from attacks.fgsm import fgsm_attack
from attacks.pgd import pgd_attack, default_step_size
from analysis.neighbor_churn import neighbor_churn_report, rebuild_knn_graph


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("configs/base_config.yaml")


def load_config(config_path: Path) -> dict:
    if not config_path.exists() or yaml is None:
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def set_seed(seed: int, deterministic: bool = False) -> None:
    """Seed every RNG used by the pipeline.

    ``deterministic`` additionally forces deterministic kernels so that two runs
    with the same seed produce identical numbers. Without it results can drift
    in the last decimals between runs even at a fixed seed, which would make a
    multi-seed study measure non-determinism on top of genuine training
    variance.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    if deterministic:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        os.environ["PYTHONHASHSEED"] = str(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def build_model(model_name: str, num_node_features: int, hidden_dim: int, dropout: float, hidden_layers: int = 1):
    if model_name == "gcn":
        return GCN_NIDS(
            num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers
        )
    if model_name == "gat":
        return GAT_NIDS(
            num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers
        )
    raise ValueError(f"Unsupported model type: {model_name}")


def create_attack_run_directory(dataset: str, model: str, k: int, base_dir: Path = Path("results") / "feature_attacks") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{timestamp}_{dataset}_{model}_k_{k}_feature_attacks"
    run_dir = base_dir / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def save_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)


def append_csv(row: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def build_attacked_dataset(model, dataset, attack_name: str, epsilon: float, alpha, steps: int, device: str, random_start: bool = True):
    attacked_graphs = []

    for data in dataset:
        data = data.to(device)

        if attack_name == "fgsm":
            adv_data = fgsm_attack(model, data, epsilon=epsilon)
        elif attack_name == "pgd":
            adv_data = pgd_attack(
                model, data, epsilon=epsilon, alpha=alpha, steps=steps,
                random_start=random_start,
            )
        else:
            raise ValueError(f"Unsupported attack: {attack_name}")

        attacked_graphs.append(adv_data.cpu())

    return attacked_graphs


def compute_neighbor_churn_rates(
    clean_dataset, attacked_dataset, k: int = 5, attack_only_malicious: bool = True
) -> list[dict]:
    """Per-graph neighbour churn, reported over all / perturbed / affected nodes.

    ``ncr_all`` averages over every node and therefore scales with the base rate
    of the perturbed class; ``ncr_perturbed`` restricts the average to the nodes
    the attack actually moved and is the quantity comparable across datasets
    with different class balance.
    """
    reports = []
    for clean_data, attacked_data in zip(clean_dataset, attacked_dataset):
        clean_x = clean_data.x.detach().cpu().numpy()
        attacked_x = attacked_data.x.detach().cpu().numpy()
        labels = clean_data.y.detach().cpu().numpy()

        perturbed_mask = (labels == 1) if attack_only_malicious else (labels == labels)

        original_edge_index, _ = rebuild_knn_graph(clean_x, k=k, bidirectional=True)
        attacked_edge_index, _ = rebuild_knn_graph(attacked_x, k=k, bidirectional=True)

        reports.append(
            neighbor_churn_report(
                original_edge_index,
                attacked_edge_index,
                perturbed_mask,
                num_nodes=int(clean_data.num_nodes),
            )
        )

    return reports


def validate_checkpoint_metadata(checkpoint_path: Path, expected_k: int) -> None:
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    metadata = checkpoint.get("metadata", {}) or {}
    checkpoint_k = metadata.get("k")
    if checkpoint_k is not None and int(checkpoint_k) != int(expected_k):
        raise ValueError(
            f"Checkpoint {checkpoint_path} was trained with k={checkpoint_k}, but requested k={expected_k}."
        )


def run_feature_attacks(args: argparse.Namespace) -> dict:
    config = load_config(DEFAULT_CONFIG_PATH)
    train_config = config.get("train", config)
    seed = (
        args.seed if getattr(args, "seed", None) is not None
        else train_config.get("seed", 42)
    )
    set_seed(seed, deterministic=getattr(args, "deterministic", False))

    device_config = train_config.get("device", "auto")
    window_size = args.window_size if args.window_size is not None else config.get("window_size", 1000)

    run_dir = create_attack_run_directory(args.dataset, args.model, args.k)

    # PGD step size: default to the Madry et al. heuristic so the attack can
    # actually traverse the epsilon-ball instead of saturating on step 1.
    def resolve_alpha(epsilon: float) -> float:
        alpha = getattr(args, "alpha", None)
        return alpha if alpha is not None else default_step_size(epsilon, args.steps)

    _, _, test_dataset = load_split_datasets(
        name=args.dataset,
        root="data/graphs",
        rebuild=False,
        window_size=window_size,
        k=args.k,
        ordered_windows=getattr(args, "ordered_windows", False),
    )

    num_node_features = test_dataset[0].x.shape[1]

    model = build_model(
        args.model,
        num_node_features=num_node_features,
        hidden_dim=args.hidden_dim,
        dropout=args.dropout,
        hidden_layers=getattr(args, "layers", 1),
    )

    trainer = Trainer(
        model=model,
        device=device_config,
        learning_rate=train_config.get("learning_rate", 0.001),
        weight_decay=train_config.get("weight_decay", 0.0005),
        epochs=1,
        patience=1,
        output_dir=str(run_dir),
        batch_size=train_config.get("batch_size", 1),
    )

    logger.info("Loading baseline checkpoint: %s", args.checkpoint)
    validate_checkpoint_metadata(args.checkpoint, args.k)
    trainer.load_checkpoint(args.checkpoint)

    clean_metrics = trainer.evaluate(test_dataset)

    results = {
        "dataset": args.dataset,
        "model": args.model,
        "k": args.k,
        "checkpoint": str(args.checkpoint),
        "window_size": window_size,
        "clean_metrics": clean_metrics,
        "attacks": [],
    }

    summary_csv = run_dir / "feature_attack_summary.csv"

    for attack_name in args.attacks:
        for epsilon in args.epsilons:
            logger.info("Running %s attack with epsilon=%s", attack_name, epsilon)

            attacked_dataset = build_attacked_dataset(
                model=trainer.model,
                dataset=test_dataset,
                attack_name=attack_name,
                epsilon=epsilon,
                alpha=resolve_alpha(epsilon),
                steps=args.steps,
                device=trainer.device,
                random_start=not getattr(args, "no_random_start", False),
            )

            attacked_metrics = trainer.evaluate(attacked_dataset)
            churn_reports = compute_neighbor_churn_rates(test_dataset, attacked_dataset, k=args.k)

            def _mean(key):
                return float(np.mean([r[key] for r in churn_reports])) if churn_reports else 0.0

            def _std(key):
                return float(np.std([r[key] for r in churn_reports])) if len(churn_reports) > 1 else 0.0

            neighbor_churn_rate = _mean("ncr_all")
            neighbor_churn_std = _std("ncr_all")
            neighbor_churn_perturbed = _mean("ncr_perturbed")
            neighbor_churn_perturbed_std = _std("ncr_perturbed")
            neighbor_churn_affected = _mean("ncr_affected")
            perturbed_fraction = _mean("perturbed_fraction")

            logger.info(
                "Average neighbor churn rate for %s epsilon=%s: %.4f",
                attack_name,
                epsilon,
                neighbor_churn_rate,
            )

            row = {
                "dataset": args.dataset,
                "model": args.model,
                "k": args.k,
                "attack": attack_name,
                "epsilon": epsilon,
                "alpha": resolve_alpha(epsilon) if attack_name == "pgd" else None,
                "steps": args.steps if attack_name == "pgd" else None,
                "clean_accuracy": clean_metrics["accuracy"],
                "clean_precision": clean_metrics["precision"],
                "clean_recall": clean_metrics["recall"],
                "clean_f1": clean_metrics["f1"],
                "clean_roc_auc": clean_metrics.get("roc_auc"),
                "attacked_accuracy": attacked_metrics["accuracy"],
                "attacked_precision": attacked_metrics["precision"],
                "attacked_recall": attacked_metrics["recall"],
                "attacked_f1": attacked_metrics["f1"],
                "attacked_roc_auc": attacked_metrics.get("roc_auc"),
                "delta_accuracy": clean_metrics["accuracy"] - attacked_metrics["accuracy"],
                "delta_f1": clean_metrics["f1"] - attacked_metrics["f1"],
                "delta_recall": clean_metrics["recall"] - attacked_metrics["recall"],
                "neighbor_churn_rate": neighbor_churn_rate,
                "neighbor_churn_rate_std": neighbor_churn_std,
                "neighbor_churn_perturbed": neighbor_churn_perturbed,
                "neighbor_churn_perturbed_std": neighbor_churn_perturbed_std,
                "neighbor_churn_affected": neighbor_churn_affected,
                "perturbed_fraction": perturbed_fraction,
                "ordered_windows": getattr(args, "ordered_windows", False),
                "seed": seed,
            }

            append_csv(row, summary_csv)

            results["attacks"].append({
                "attack": attack_name,
                "epsilon": epsilon,
                "metrics": attacked_metrics,
                "delta": {
                    "accuracy": row["delta_accuracy"],
                    "f1": row["delta_f1"],
                    "recall": row["delta_recall"],
                },
                "neighbor_churn_rate": neighbor_churn_rate,
                "neighbor_churn_perturbed": neighbor_churn_perturbed,
                "neighbor_churn_affected": neighbor_churn_affected,
                "perturbed_fraction": perturbed_fraction,
                "neighbor_churn_reports": churn_reports,
            })

    save_json(results, run_dir / "metrics.json")
    logger.info("Feature attack experiment complete. Results saved to %s", run_dir)

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FGSM/PGD feature-space attacks on trained GNN baselines.")

    parser.add_argument("--model", choices=["gcn", "gat"], default="gcn")

    cicids_choices = sorted(list(CICIDS2017_SUBSETS.keys()))
    parser.add_argument(
        "--dataset",
        choices=["nsl-kdd"] + cicids_choices,
        default="nsl-kdd",
    )

    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--window-size", type=int, default=None)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Training/eval seed. Overrides train.seed in the config. Vary this across "
             "runs to measure model-level variance; it does NOT change the persisted "
             "splits (fixed random_state=42) nor invalidate the graph caches.",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Force deterministic kernels so the same seed reproduces the same numbers.",
    )
    parser.add_argument(
        "--layers",
        type=int,
        default=1,
        help="Number of message-passing layers; must match the checkpoint being loaded.",
    )


    parser.add_argument("--attacks", nargs="+", choices=["fgsm", "pgd"], default=["fgsm", "pgd"])
    parser.add_argument("--epsilons", nargs="+", type=float, default=[0.01, 0.03, 0.05, 0.10])

    parser.add_argument(
        "--alpha",
        type=float,
        default=None,
        help="PGD step size. Default: 2.5*epsilon/steps (Madry et al.). "
             "A fixed small alpha makes PGD saturate the epsilon-ball and collapse onto FGSM.",
    )
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument(
        "--no-random-start",
        action="store_true",
        help="Disable the random start inside the epsilon-ball (legacy behaviour).",
    )
    parser.add_argument(
        "--ordered-windows",
        action="store_true",
        help="Build graphs from capture-ordered windows instead of the shuffled split order.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_feature_attacks(args)


if __name__ == "__main__":
    main()