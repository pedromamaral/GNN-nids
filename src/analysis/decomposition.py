"""Feature / induced-structure decomposition of adversarial degradation.

In a flow-centric NIDS whose graph is the k-NN graph of the flow features, a
feature-space perturbation X -> X_adv also changes the graph E -> E_rec once
the defender rebuilds it. To separate the two effects, the same perturbed
features are evaluated under four conditions:

    clean : (X,     E)      reference
    A     : (X_adv, E)      pure feature effect (what fixed-graph evaluation reports)
    B     : (X,     E_rec)  pure induced-structure effect
    C     : (X_adv, E_rec)  deployment: features and rebuilt graph

with E_rec = kNN(X_adv). For a construction-aware attack (``construction_aware_pgd``)
condition C is the adaptive deployment condition, written C* in the paper plan.

Degradations are measured as clean metric minus condition metric:

    feature     = clean - A
    structure   = clean - B
    combined    = clean - C
    interaction = combined - feature - structure

A positive interaction means the two effects amplify each other.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import torch
from torch_geometric.data import Data

try:
    from analysis.neighbor_churn import compute_neighbor_churn, knn_graph_tensors
except ModuleNotFoundError:  # pragma: no cover - fallback for direct test imports
    from src.analysis.neighbor_churn import compute_neighbor_churn, knn_graph_tensors


CONDITIONS = ("A", "B", "C")
CONDITION_DESCRIPTIONS = {
    "A": ("X_adv", "E"),
    "B": ("X", "E_rec"),
    "C": ("X_adv", "E_rec"),
}


def _with(data: Data, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: Optional[torch.Tensor]) -> Data:
    """Return a clean copy of ``data`` with the given features and graph."""
    return Data(
        x=x.detach().clone(),
        edge_index=edge_index.clone(),
        edge_attr=None if edge_attr is None else edge_attr.clone(),
        y=data.y.clone(),
    )


def build_conditions(
    clean: Data,
    adversarial: Data,
    k: int,
    metric: str = "cosine",
    bidirectional: bool = True,
    rebuilt_graph: Optional[tuple] = None,
) -> Dict[str, Data]:
    """Build the A/B/C graphs for one window.

    Args:
        clean: Clean window as stored in the dataset (X, E).
        adversarial: Window whose ``x`` holds X_adv. Its ``edge_index`` is ignored.
        k, metric, bidirectional: Construction parameters used for E_rec.
        rebuilt_graph: Optional precomputed ``(edge_index, edge_attr)`` for
            kNN(X_adv), e.g. the graph returned by ``construction_aware_pgd``.

    Returns:
        Dict mapping "A", "B", "C" to ``Data`` objects on CPU.
    """
    clean = clean.cpu()
    x_clean = clean.x
    x_adv = adversarial.x.detach().cpu()
    edge_attr = getattr(clean, "edge_attr", None)

    if rebuilt_graph is None:
        rebuilt_edge_index, rebuilt_edge_attr = knn_graph_tensors(x_adv, k=k, metric=metric, bidirectional=bidirectional)
    else:
        rebuilt_edge_index, rebuilt_edge_attr = (t.cpu() if t is not None else None for t in rebuilt_graph)

    return {
        "A": _with(clean, x_adv, clean.edge_index, edge_attr),
        "B": _with(clean, x_clean, rebuilt_edge_index, rebuilt_edge_attr),
        "C": _with(clean, x_adv, rebuilt_edge_index, rebuilt_edge_attr),
    }


def churn_between(clean: Data, other: Data, node_indices: Optional[np.ndarray] = None) -> float:
    """Neighbour churn rate between the clean graph and another graph of the same window."""
    return compute_neighbor_churn(
        clean.edge_index.detach().cpu().numpy(),
        other.edge_index.detach().cpu().numpy(),
        node_indices=node_indices,
    )


def check_reconstruction(
    dataset: Sequence[Data],
    k: int,
    metric: str = "cosine",
    bidirectional: bool = True,
    max_windows: Optional[int] = None,
) -> Dict[str, float]:
    """Check that kNN(X_clean) reproduces the stored training graph.

    Condition B is only meaningful if rebuilding from *clean* features gives
    back the graph the model was trained and evaluated on. Any residual churn
    here (e.g. from duplicate flows, where the self-index is not returned first
    by the neighbour search) is a construction artefact that would otherwise be
    attributed to the attack.

    Returns:
        ``{"windows": n, "mean_churn": ..., "max_churn": ..., "exact_fraction": ...}``
    """
    churns: List[float] = []
    for idx, data in enumerate(dataset):
        if max_windows is not None and idx >= max_windows:
            break
        rebuilt, _ = knn_graph_tensors(data.x, k=k, metric=metric, bidirectional=bidirectional)
        churns.append(
            compute_neighbor_churn(
                data.edge_index.detach().cpu().numpy(),
                rebuilt.detach().cpu().numpy(),
            )
        )
    if not churns:
        return {"windows": 0, "mean_churn": 0.0, "max_churn": 0.0, "exact_fraction": 1.0}
    arr = np.asarray(churns)
    return {
        "windows": int(arr.size),
        "mean_churn": float(arr.mean()),
        "max_churn": float(arr.max()),
        "exact_fraction": float(np.mean(arr == 0.0)),
    }


def decomposition_effects(clean_value: float, values: Dict[str, float]) -> Dict[str, float]:
    """Turn per-condition metric values into feature/structure/combined/interaction effects."""
    feature = clean_value - values["A"]
    structure = clean_value - values["B"]
    combined = clean_value - values["C"]
    return {
        "feature": feature,
        "structure": structure,
        "combined": combined,
        "interaction": combined - feature - structure,
    }
