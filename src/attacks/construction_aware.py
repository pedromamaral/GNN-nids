"""
Construction-aware PGD for feature-derived (k-NN) flow graphs.

In a flow-centric NIDS the graph is not given: it is rebuilt from the observed
flow features at inference time. An attacker who perturbs its own flows'
features therefore also moves those flows inside the k-NN graph. Standard PGD
(``attacks.pgd``) ignores this: it differentiates through a *fixed* graph.

This attack rebuilds the k-NN graph from the current adversarial features
every ``rebuild_every`` steps, takes the gradient through the GNN on that
graph, and returns the adversarial features together with the graph the
defender would actually build from them. The k-NN step itself is not
differentiable; the attack treats it as piecewise constant (the graph only
changes between steps), which is the natural white-box adaptive attack for a
non-differentiable pre-processing stage.

Evaluating its output corresponds to condition C* in the decomposition
experiment (``experiments/05_decomposition.py``).
"""

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data

from .pgd import _frozen_feature_columns

try:
    from analysis.neighbor_churn import knn_graph_tensors
except ModuleNotFoundError:  # pragma: no cover - fallback for direct test imports
    from src.analysis.neighbor_churn import knn_graph_tensors


def construction_aware_pgd(
    model: nn.Module,
    data: Data,
    epsilon: float = 0.03,
    alpha: Optional[float] = None,
    steps: int = 20,
    k: int = 5,
    metric: str = "cosine",
    bidirectional: bool = True,
    rebuild_every: int = 1,
    attack_only_malicious: bool = True,
    random_start: bool = True,
    feature_mask: Optional[torch.Tensor] = None,
    clip_min: Optional[float] = None,
    clip_max: Optional[float] = None,
) -> Data:
    """PGD whose forward pass uses the k-NN graph rebuilt from the current features.

    Args:
        model: Trained GNN (``GCN_NIDS`` / ``GAT_NIDS``).
        data: Clean window (``x``, ``edge_index``, ``y``).
        epsilon: L∞ budget in standardised feature units.
        alpha: Step size; defaults to ``2.5 * epsilon / steps`` (same as ``pgd_attack``).
        steps: Number of PGD iterations.
        k, metric, bidirectional: Graph-construction parameters. They must match
            the ones used to build the training graphs.
        rebuild_every: Rebuild the graph every N steps (1 = every step).
        attack_only_malicious: Perturb only nodes with ``y == 1``.
        random_start: Start from a uniform point in the ε-ball.
        feature_mask: Optional boolean tensor (num_features,) of attacker-controllable
            features; others are never perturbed.
        clip_min, clip_max: Optional bounds applied to perturbed nodes.

    Returns:
        A new ``Data`` whose ``x`` holds the adversarial features and whose
        ``edge_index``/``edge_attr`` are the k-NN graph rebuilt from them
        (the defender's view).
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be positive, got {epsilon}")
    if steps <= 0:
        raise ValueError(f"steps must be positive, got {steps}")
    if rebuild_every <= 0:
        raise ValueError(f"rebuild_every must be positive, got {rebuild_every}")
    if alpha is None:
        alpha = 2.5 * epsilon / steps
    if alpha <= 0:
        raise ValueError(f"alpha must be positive, got {alpha}")

    model.eval()
    device = data.x.device
    x_original = data.x.detach().clone()
    x_adv = x_original.clone()

    if attack_only_malicious:
        mask = data.y == 1
        if mask.sum() == 0:
            return data.clone()
    else:
        mask = torch.ones(data.num_nodes, dtype=torch.bool, device=device)

    frozen_features = _frozen_feature_columns(feature_mask, x_original.shape[1], device)

    def _project(x: torch.Tensor) -> torch.Tensor:
        x = x_original + torch.clamp(x - x_original, min=-epsilon, max=epsilon)
        if clip_min is not None:
            x[mask] = torch.clamp(x[mask], min=clip_min)
        if clip_max is not None:
            x[mask] = torch.clamp(x[mask], max=clip_max)
        x[~mask] = x_original[~mask]
        if frozen_features is not None:
            x[:, frozen_features] = x_original[:, frozen_features]
        return x

    if random_start:
        with torch.no_grad():
            noise = torch.empty_like(x_adv).uniform_(-epsilon, epsilon)
            x_adv = _project(x_adv + noise)

    edge_index, edge_attr = data.edge_index, getattr(data, "edge_attr", None)

    for step in range(steps):
        if step % rebuild_every == 0:
            edge_index, edge_attr = knn_graph_tensors(x_adv, k=k, metric=metric, bidirectional=bidirectional)

        x_adv = x_adv.detach().requires_grad_(True)
        data_step = data.clone()
        data_step.x = x_adv
        data_step.edge_index = edge_index
        data_step.edge_attr = edge_attr

        with torch.enable_grad():
            logits = model(data_step)
            if attack_only_malicious:
                loss = F.cross_entropy(logits[mask], data.y[mask])
            else:
                loss = F.cross_entropy(logits, data.y)
            model.zero_grad(set_to_none=True)
            loss.backward()
            grad_sign = x_adv.grad.sign()

        with torch.no_grad():
            x_next = x_adv.detach().clone()
            x_next[mask] = x_next[mask] + alpha * grad_sign[mask]
            x_adv = _project(x_next)

    x_adv = x_adv.detach()
    final_edge_index, final_edge_attr = knn_graph_tensors(x_adv, k=k, metric=metric, bidirectional=bidirectional)

    data_adv = data.clone()
    data_adv.x = x_adv
    data_adv.edge_index = final_edge_index
    data_adv.edge_attr = final_edge_attr
    return data_adv
