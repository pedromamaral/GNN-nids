"""Helpers for measuring structural side effects of feature-space attacks.

Neighbor Churn Rate (NCR) compares the neighbourhood sets of a k-NN graph
before and after the node features are perturbed and the graph rebuilt:

    NCR = sum_i |N_i  symmetric-difference  N_i^rec|
          / sum_i max(|N_i|, |N_i^rec|)

Because both lost and newly introduced neighbours are counted, NCR ranges over
[0, 2].  For directed k-NN neighbourhoods of equal size k it reduces to
``2 * (1 - |N_i & N_i^rec| / k)``, i.e. twice the neighbourhood dissimilarity.

IMPORTANT: when only a subset of nodes is perturbed (the usual case, where the
attack targets malicious flows only), averaging over *all* nodes makes NCR
scale with the base rate of the perturbed class rather than with the strength
of the attack.  Use ``node_mask`` / ``neighbor_churn_report`` to also report
the churn restricted to the perturbed nodes, which is the quantity that is
comparable across datasets with different class balance.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

try:
    from data.graph_builder import FlowGraphBuilder
except ModuleNotFoundError:  # pragma: no cover - fallback for direct test imports
    from src.data.graph_builder import FlowGraphBuilder


def rebuild_knn_graph(
    x: np.ndarray,
    k: int = 5,
    metric: str = "cosine",
    bidirectional: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """Rebuild a k-NN graph from node features using the existing graph builder."""
    builder = FlowGraphBuilder()
    return builder.build_knn_graph(x, k=k, metric=metric, bidirectional=bidirectional)


def _validate(edge_index: np.ndarray, name: str) -> None:
    if edge_index.ndim != 2 or edge_index.shape[0] != 2:
        raise ValueError(
            f"{name} must have shape (2, num_edges); got {edge_index.shape}"
        )


def _adjacency_sets(
    original_edge_index: np.ndarray,
    attacked_edge_index: np.ndarray,
    num_nodes: Optional[int] = None,
) -> Tuple[List[Set[int]], List[Set[int]], int]:
    """Build per-node out-neighbour sets for both graphs."""
    _validate(original_edge_index, "original_edge_index")
    _validate(attacked_edge_index, "attacked_edge_index")

    inferred = 0
    for ei in (original_edge_index, attacked_edge_index):
        if ei.size:
            inferred = max(inferred, int(ei.max()) + 1)
    n = int(num_nodes) if num_nodes is not None else inferred

    original: List[Set[int]] = [set() for _ in range(n)]
    attacked: List[Set[int]] = [set() for _ in range(n)]

    for src, dst in original_edge_index.T:
        original[int(src)].add(int(dst))
    for src, dst in attacked_edge_index.T:
        attacked[int(src)].add(int(dst))

    return original, attacked, n


def compute_neighbor_churn(
    original_edge_index: np.ndarray,
    attacked_edge_index: np.ndarray,
    node_mask: Optional[Sequence[bool]] = None,
    num_nodes: Optional[int] = None,
) -> float:
    """Fraction of changed neighbour slots between two directed graphs.

    Args:
        original_edge_index: (2, E) edge index of the clean graph.
        attacked_edge_index: (2, E') edge index of the rebuilt graph.
        node_mask: Optional boolean mask over nodes.  When given, the average is
            restricted to the selected nodes (e.g. the perturbed ones).
        num_nodes: Optional explicit node count.  Needed when the graph has
            isolated nodes that would otherwise not appear in the edge index.

    Returns:
        NCR in [0, 2].  Returns 0.0 when there is nothing to compare.
    """
    if original_edge_index.size == 0 and attacked_edge_index.size == 0:
        return 0.0

    original, attacked, n = _adjacency_sets(
        original_edge_index, attacked_edge_index, num_nodes
    )

    if node_mask is None:
        selected = range(n)
    else:
        mask = np.asarray(node_mask, dtype=bool)
        if mask.shape[0] < n:
            mask = np.pad(mask, (0, n - mask.shape[0]), constant_values=False)
        selected = np.nonzero(mask[:n])[0].tolist()

    changed_count = 0
    total_slots = 0
    for node_idx in selected:
        total_slots += max(len(original[node_idx]), len(attacked[node_idx]))
        changed_count += len(original[node_idx] ^ attacked[node_idx])

    if total_slots == 0:
        return 0.0

    return changed_count / total_slots


def neighbor_churn_report(
    original_edge_index: np.ndarray,
    attacked_edge_index: np.ndarray,
    perturbed_mask: Sequence[bool],
    num_nodes: Optional[int] = None,
) -> Dict[str, float]:
    """NCR reported over all nodes, over perturbed nodes, and over their neighbourhood.

    ``ncr_all`` reproduces the original (base-rate dependent) definition.
    ``ncr_perturbed`` is the attack-strength measure that is comparable across
    datasets with different class balance.  ``ncr_affected`` additionally
    includes the clean nodes that were adjacent to a perturbed node in either
    graph, i.e. the nodes whose message passing could have changed.
    """
    original, attacked, n = _adjacency_sets(
        original_edge_index, attacked_edge_index, num_nodes
    )

    mask = np.asarray(perturbed_mask, dtype=bool)
    if mask.shape[0] < n:
        mask = np.pad(mask, (0, n - mask.shape[0]), constant_values=False)
    mask = mask[:n]

    affected = mask.copy()
    for node_idx in np.nonzero(mask)[0]:
        for neighbour in original[node_idx] | attacked[node_idx]:
            if neighbour < n:
                affected[neighbour] = True

    n_perturbed = int(mask.sum())
    return {
        "ncr_all": compute_neighbor_churn(
            original_edge_index, attacked_edge_index, num_nodes=n
        ),
        "ncr_perturbed": compute_neighbor_churn(
            original_edge_index, attacked_edge_index, node_mask=mask, num_nodes=n
        ),
        "ncr_affected": compute_neighbor_churn(
            original_edge_index, attacked_edge_index, node_mask=affected, num_nodes=n
        ),
        "num_nodes": float(n),
        "num_perturbed": float(n_perturbed),
        "perturbed_fraction": float(n_perturbed / n) if n else 0.0,
    }
