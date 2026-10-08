#!/usr/bin/env python3
"""Does a trained flow GNN use its graph? Evaluate one checkpoint under different graphs.

On the clean test windows, the same model is evaluated with:
    knn      the k-NN graph it was trained on (reference)
    none     no edges: each flow sees only itself (GCN/GAT add self-loops)
    random   k random neighbours per flow, made bidirectional like the k-NN graph

If F1 under ``none`` and ``random`` matches ``knn``, the model ignores its
neighbours, and no change of structure (induced or adversarial) can matter.
``changed`` is the fraction of flow predictions that differ from ``knn``.

Everything else (dataset, k, window size, slice, architecture) is read from
the checkpoint metadata written by 01_baseline_training.py.

Example (inside the container, from the repository root):

    python experiments/06_graph_ablation.py \\
        --checkpoints results/runs/*_nf-unsw-nb15-v3_gcn_k_5_seed_42/best_checkpoint.pt

Output: results/graph_ablation/<timestamp>/graph_ablation.csv
"""

import argparse
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
from torch_geometric.data import Data

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.dataset import load_split_datasets  # noqa: E402
from models import GAT_NIDS, GCN_NIDS  # noqa: E402
from utils.metrics import binary_classification_metrics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("graph_ablation")
logging.getLogger("data.graph_builder").setLevel(logging.WARNING)

GRAPHS = ("knn", "none", "random")


def random_graph(num_nodes: int, k: int, rng: np.random.Generator) -> torch.Tensor:
    """k distinct random other nodes per node, plus reverse edges (no duplicates, no self-loops)."""
    k = min(k, num_nodes - 1)
    if k < 1:
        return torch.empty((2, 0), dtype=torch.long)
    # Draw from 0..n-2 and shift past i, so the node itself is never chosen.
    draws = np.argsort(rng.random((num_nodes, num_nodes - 1)), axis=1)[:, :k]
    rows = np.arange(num_nodes)[:, None]
    targets = draws + (draws >= rows)
    src = np.repeat(np.arange(num_nodes), k)
    dst = targets.reshape(-1)
    pairs = np.unique(np.concatenate([np.stack([src, dst], 1), np.stack([dst, src], 1)]), axis=0)
    return torch.as_tensor(pairs.T, dtype=torch.long)


def with_graph(data: Data, graph: str, k: int, rng: np.random.Generator) -> Data:
    if graph == "knn":
        edge_index = data.edge_index
    elif graph == "none":
        edge_index = torch.empty((2, 0), dtype=torch.long)
    elif graph == "random":
        edge_index = random_graph(data.num_nodes, k, rng)
    else:
        raise ValueError(f"Unknown graph: {graph}")
    return Data(x=data.x, edge_index=edge_index, y=data.y)


def build_model(metadata: dict, num_features: int) -> torch.nn.Module:
    cls = {"gcn": GCN_NIDS, "gat": GAT_NIDS}[metadata["model"]]
    return cls(
        num_features,
        int(metadata.get("hidden_dim", 64)),
        dropout=float(metadata.get("dropout", 0.5)),
        hidden_layers=int(metadata.get("hidden_layers", 1)),
    )


@torch.no_grad()
def predict(model: torch.nn.Module, windows: List[Data], device: torch.device) -> np.ndarray:
    model.eval()
    return np.concatenate([model(w.to(device)).argmax(dim=-1).cpu().numpy() for w in windows])


def evaluate_checkpoint(path: Path, args: argparse.Namespace, device: torch.device) -> List[Dict]:
    # Full load, like Trainer.load_checkpoint: checkpoints are written by 01 on our own servers.
    checkpoint = torch.load(path, map_location="cpu")
    metadata = checkpoint.get("metadata") or {}
    for key in ("dataset", "model", "k"):
        if key not in metadata:
            raise ValueError(f"{path}: checkpoint metadata lacks '{key}' (train it with 01_baseline_training.py)")
    k = int(metadata["k"])

    _, _, test = load_split_datasets(
        name=metadata["dataset"],
        root="data/graphs",
        window_size=int(metadata.get("window_size", 1000)),
        k=k,
        max_flows=metadata.get("max_flows"),
        slice_start=metadata.get("slice_start"),
    )
    windows = [test[i] for i in range(len(test))]
    if args.max_windows is not None:
        windows = windows[: args.max_windows]
    y = np.concatenate([w.y.numpy() for w in windows])

    model = build_model(metadata, windows[0].x.shape[1])
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)

    reference = predict(model, windows, device)
    rows = []
    for graph in GRAPHS:
        seeds = args.random_seeds if graph == "random" else [None]
        for seed in seeds:
            rng = np.random.default_rng(seed if seed is not None else 0)
            pred = reference if graph == "knn" else predict(
                model, [with_graph(w, graph, k, rng) for w in windows], device
            )
            metrics = binary_classification_metrics(y, pred)
            rows.append({
                "checkpoint": str(path),
                "dataset": metadata["dataset"],
                "model": metadata["model"],
                "k": k,
                "training_seed": metadata.get("seed"),
                "graph": graph,
                "graph_seed": seed,
                "windows": len(windows),
                "f1": metrics["f1"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "accuracy": metrics["accuracy"],
                "changed": float(np.mean(pred != reference)),
                "changed_malicious": float(np.mean(pred[y == 1] != reference[y == 1])) if (y == 1).any() else None,
            })
            logger.info("%s %s %s graph=%s seed=%s: F1=%.4f changed=%.4f",
                        metadata["dataset"], metadata["model"], metadata.get("seed"), graph, seed,
                        metrics["f1"], rows[-1]["changed"])
    return rows


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate trained flow GNNs with the k-NN graph, no graph, and random graphs.")
    parser.add_argument("--checkpoints", nargs="+", type=Path, required=True)
    parser.add_argument("--random-seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", type=Path, default=Path("results") / "graph_ablation")
    return parser.parse_args(argv)


def main(argv=None) -> Path:
    args = parse_args(argv)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    rows: List[Dict] = []
    for path in args.checkpoints:
        rows.extend(evaluate_checkpoint(path, args, device))

    out_dir = args.output_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "graph_ablation.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Results in %s", out_path)
    return out_path


if __name__ == "__main__":
    main()
