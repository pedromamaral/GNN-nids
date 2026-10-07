#!/usr/bin/env python3
"""Baseline training script for flow-centric node classification."""

import argparse
import csv
import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in lightweight test environments
    yaml = None

# Make src importable when the script is run from the repository root.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.dataset import load_split_datasets
from models import GCN_NIDS, GAT_NIDS
from training.trainer import Trainer
from torch_geometric.data import Data
from data.download import DATASET_CHOICES, DEFAULT_DATASET

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


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(
    model_name: str,
    num_node_features: int,
    hidden_dim: int,
    dropout: float,
    hidden_layers: int = 1,
) -> torch.nn.Module:
    if model_name == "gcn":
        return GCN_NIDS(num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers)
    if model_name == "gat":
        return GAT_NIDS(num_node_features, hidden_dim, dropout=dropout, hidden_layers=hidden_layers)
    raise ValueError(f"Unsupported model type: {model_name}")


def build_synthetic_graphs(
    num_graphs: int = 2,
    num_nodes: int = 32,
    num_node_features: int = 12,
) -> list[Data]:
    graphs = []
    for _ in range(num_graphs):
        x = torch.randn(num_nodes, num_node_features, dtype=torch.float32)
        edge_index = torch.randint(0, num_nodes, (2, num_nodes * 4), dtype=torch.long)
        y = torch.randint(0, 2, (num_nodes,), dtype=torch.long)
        graphs.append(Data(x=x, edge_index=edge_index, y=y))
    return graphs


def save_metrics_json(metrics: dict, output_dir: Path, filename: str = "metrics.json") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / filename
    with metrics_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    return metrics_path


def save_config_yaml(config: dict, output_dir: Path, filename: str = "config.yaml") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / filename
    with config_path.open("w", encoding="utf-8") as handle:
        if yaml is None:
            handle.write("{}\n")
        else:
            yaml.safe_dump(config, handle)
    return config_path


def append_csv_summary(summary: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not output_path.exists()
    with output_path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(summary.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(summary)
    return output_path


def create_run_directory(
    dataset: str,
    model: str,
    k: int,
    seed: int,
    base_dir: Path = Path("results") / "runs",
    hidden_layers: int = 1,
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 1-layer runs keep the original naming so existing checkpoints stay discoverable.
    layers_tag = f"_L{hidden_layers}" if hidden_layers != 1 else ""
    run_name = f"{timestamp}_{dataset}_{model}_k_{k}{layers_tag}_seed_{seed}"
    run_dir = base_dir / run_name
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = base_dir / f"{run_name}_{suffix}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def setup_training_log(run_dir: Path) -> logging.Handler:
    log_path = run_dir / "training_log.txt"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    return handler

def set_deterministic(enabled: bool) -> None:
    if enabled:
        torch.use_deterministic_algorithms(True)

        if torch.cuda.is_available():
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False


def run_training(args: argparse.Namespace) -> dict:
    config = load_config(DEFAULT_CONFIG_PATH)
    train_config = config.get("train", config)

    seed = (
        getattr(args, "seed", None)
        if getattr(args, "seed", None) is not None
        else train_config.get("seed", 42)
    )

    set_deterministic(getattr(args, "deterministic", False))
    set_seed(seed)

    training_config = {
        "epochs": args.epochs if args.epochs is not None else train_config.get("epochs", 100),
        "learning_rate": args.learning_rate if args.learning_rate is not None else train_config.get("learning_rate", 0.001),
        "weight_decay": args.weight_decay if args.weight_decay is not None else train_config.get("weight_decay", 0.0005),
        "patience": args.patience if args.patience is not None else train_config.get("patience", 15),
        "batch_size": args.batch_size if args.batch_size is not None else train_config.get("batch_size", 1),
        "device": args.device if args.device is not None else train_config.get("device", "auto"),
    }

    window_size = (args.window_size if args.window_size is not None else train_config.get("window_size", 1000))

    hidden_layers = getattr(args, "hidden_layers", 1)
    run_dir = create_run_directory(args.dataset, args.model, args.k, seed, hidden_layers=hidden_layers)
    run_id = run_dir.name
    timestamp = run_dir.name.split("_")[0]

    log_handler = setup_training_log(run_dir)
    try:
        if args.dry_run:
            train_dataset = build_synthetic_graphs(num_graphs=2, num_nodes=16, num_node_features=12)
            val_dataset = build_synthetic_graphs(num_graphs=1, num_nodes=16, num_node_features=12)
            test_dataset = build_synthetic_graphs(num_graphs=1, num_nodes=16, num_node_features=12)
            logger.info("Dry-run mode: using synthetic datasets for a minimal execution path.")
        else:
            # Load formal train/validation/test splits
            train_dataset, val_dataset, test_dataset = load_split_datasets(
                name=args.dataset,
                root="data/graphs",
                rebuild=args.rebuild_data,
                window_size=window_size,
                k=args.k,
                max_flows=getattr(args, "max_flows", None),
                slice_start=getattr(args, "slice_start", None),
            )

        num_node_features = (
            train_dataset[0].x.shape[1]
            if not args.dry_run
            else 12
        )
        model = build_model(
            args.model,
            num_node_features=num_node_features,
            hidden_dim=args.hidden_dim,
            dropout=args.dropout,
            hidden_layers=hidden_layers,
        )

        trainer = Trainer(
            model=model,
            device=training_config["device"],
            learning_rate=training_config["learning_rate"],
            weight_decay=training_config["weight_decay"],
            epochs=training_config["epochs"],
            patience=training_config["patience"],
            output_dir=str(run_dir),
            batch_size=training_config["batch_size"],
        )
        trainer.metadata = {
            "dataset": args.dataset,
            "model": args.model,
            "k": args.k,
            "seed": seed,
            "deterministic": getattr(args, "deterministic", False),
            "window_size": window_size,
            "max_flows": getattr(args, "max_flows", None),
            "slice_start": getattr(args, "slice_start", None),
            "hidden_dim": args.hidden_dim,
            "hidden_layers": hidden_layers,
            "dropout": args.dropout,
        }

        # Training with validation for early stopping
        fit_result = trainer.fit(train_dataset, val_dataset=val_dataset, dry_run=args.dry_run)

        # Load best checkpoint for final evaluation        
        best_checkpoint = fit_result.get("best_checkpoint")

        if best_checkpoint:
            logger.info("Loading best checkpoint for final evaluation: %s", best_checkpoint)
            trainer.load_checkpoint(best_checkpoint)

        # Evaluation on all splits
        train_metrics = trainer.evaluate(train_dataset)
        val_metrics = trainer.evaluate(val_dataset)
        test_metrics = trainer.evaluate(test_dataset)

        # Get split information for metadata
        from data.splits import SplitManager
        split_manager = SplitManager(args.dataset, data_dir="data/splits")
        split_config = split_manager.load_split_config() if split_manager.splits_exist() else {}
        split_metadata_path = str(split_manager.split_dir / "split_config.json")

        full_config = {
            "run_id": run_id,
            "timestamp": timestamp,
            "dataset": args.dataset,
            "model": args.model,
            "dry_run": args.dry_run,
            "config_file": str(DEFAULT_CONFIG_PATH),
            "loaded_config": config,
            "split_metadata_path": split_metadata_path,
            "split_config": split_config,
            "runtime_config": {
                "epochs": training_config["epochs"],
                "learning_rate": training_config["learning_rate"],
                "weight_decay": training_config["weight_decay"],
                "patience": training_config["patience"],
                "batch_size": training_config["batch_size"],
                "device": training_config["device"],
                "window_size": window_size,
                "max_flows": getattr(args, "max_flows", None),
                "slice_start": getattr(args, "slice_start", None),
                "k": args.k,
                "seed": seed,
                "deterministic": getattr(args, "deterministic", False),
                "hidden_dim": args.hidden_dim,
                "hidden_layers": hidden_layers,
                "dropout": args.dropout,
            },
        }

        results = {
            "run_id": run_id,
            "timestamp": timestamp,
            "config": full_config,
            "fit": fit_result,
            "metrics": {
                "train": train_metrics,
                "validation": val_metrics,
                "test": test_metrics,
            },
        }

        save_config_yaml(full_config, run_dir, filename="config.yaml")
        metrics_file = save_metrics_json(results, run_dir, filename="metrics.json")

        summary = {
            "run_id": run_id,
            "timestamp": timestamp,
            "dataset": args.dataset,
            "model": args.model,
            "epochs": training_config["epochs"],
            "window_size": window_size,
            "k": args.k,
            "seed": seed,
            "deterministic": getattr(args, "deterministic", False),
            "hidden_dim": args.hidden_dim,
            "dropout": args.dropout,
            "learning_rate": training_config["learning_rate"],
            "weight_decay": training_config["weight_decay"],
            "patience": training_config["patience"],
            "batch_size": training_config["batch_size"],
            "train_accuracy": train_metrics["accuracy"],
            "train_f1": train_metrics["f1"],
            "validation_accuracy": val_metrics["accuracy"],
            "validation_f1": val_metrics["f1"],
            "test_accuracy": test_metrics["accuracy"],
            "test_f1": test_metrics["f1"],
            "test_roc_auc": test_metrics.get("roc_auc"),
            "best_checkpoint": fit_result["best_checkpoint"],
        }

        summary_csv_path = run_dir / "summary.csv"
        append_csv_summary(summary, summary_csv_path)

        global_summary_path = Path("results") / "experiments_summary.csv"
        append_csv_summary(summary, global_summary_path)

        logger.info("Baseline training complete.")
        logger.info("Saved config: %s", run_dir / "config.yaml")
        logger.info("Saved metrics: %s", metrics_file)
        logger.info("Saved summary: %s", summary_csv_path)
        logger.info("Saved checkpoint: %s", fit_result["best_checkpoint"])

        return results
    finally:
        logging.getLogger().removeHandler(log_handler)
        log_handler.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate a flow-centric GNN baseline.")
    parser.add_argument("--model", choices=["gcn", "gat"], default="gcn")
    parser.add_argument(
        "--dataset",
        choices=DATASET_CHOICES,
        default=DEFAULT_DATASET,
    )
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--window-size", type=int, default=None)
    parser.add_argument("--max-flows", type=int, default=None,
                        help="NetFlow-v3: use only this many time-contiguous flows (default: all)")
    parser.add_argument("--slice-start", type=float, default=None,
                        help="NetFlow-v3: start of the --max-flows slice, as a fraction of the time-sorted flows")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--weight-decay", type=float, default=None)
    parser.add_argument("--patience", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--hidden-layers", type=int, default=1, help="Number of message-passing layers (depth ablation).")
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--rebuild-data", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=None, help="Training seed. Overrides the seed defined in base_config.yaml.")
    parser.add_argument("--deterministic", action="store_true", help="Enable deterministic PyTorch operations where supported.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.k < 1:
        raise ValueError("--k must be at least 1")
    run_training(args)


if __name__ == "__main__":
    main()
