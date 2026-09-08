"""
Random structural perturbations for PyTorch Geometric graphs.

These are *random* topology perturbations (uniform edge deletion / uniform edge
insertion incident to malicious nodes), not optimised adversarial attacks: no
gradient, surrogate model or candidate-edge scoring is involved.  They are
useful as a noise baseline against which an optimised structural attack (e.g.
Nettack / Metattack / a gradient-based topology PGD) can be compared, and should
be reported as such.

Budget semantics
----------------
``perturbation_rate`` is interpreted relative to the *candidate* edge
population, i.e. the existing directed edges incident to at least one malicious
node, for BOTH removal and addition (``budget_reference="candidate"``).  This
makes the two perturbation types directly comparable on a shared axis.

``budget_reference="total"`` reproduces the earlier behaviour, where addition
was budgeted as a fraction of *all* edges in the graph while removal used the
candidate population.  Under that setting the two curves are not comparable,
especially on datasets where malicious flows are a small minority.
"""

from typing import Optional

import torch
from torch_geometric.data import Data
from torch.nn.functional import cosine_similarity


def _candidate_edge_mask(data: Data, attack_only_malicious: bool) -> Optional[torch.Tensor]:
    """Boolean mask over ``edge_index`` selecting edges incident to malicious nodes."""
    edge_index = data.edge_index
    if not attack_only_malicious:
        return torch.ones(edge_index.size(1), dtype=torch.bool, device=edge_index.device)

    node_mask = data.y == 1
    if node_mask.sum() == 0:
        return None
    return node_mask[edge_index[0]] | node_mask[edge_index[1]]


def _budget(
    data: Data,
    perturbation_rate: float,
    candidate_count: int,
    budget_reference: str,
) -> int:
    """Number of undirected edge pairs to perturb."""
    if budget_reference == "candidate":
        population = candidate_count
    elif budget_reference == "total":
        population = data.edge_index.size(1)
    else:
        raise ValueError(
            f"budget_reference must be 'candidate' or 'total', got {budget_reference!r}"
        )
    return max(1, int((population * perturbation_rate) / 2))


def edge_removal_attack(
    data: Data,
    perturbation_rate: float = 0.10,
    attack_only_malicious: bool = True,
    budget_reference: str = "candidate",
    generator: Optional[torch.Generator] = None,
) -> Data:
    """Remove a random subset of edges incident to malicious nodes.

    Reverse edges of every removed edge are removed as well, so the graph stays
    symmetric.

    Raises:
        ValueError: if ``perturbation_rate`` is outside (0, 1].
    """
    if perturbation_rate <= 0 or perturbation_rate > 1:
        raise ValueError(f"perturbation_rate must be in (0,1], got {perturbation_rate}")

    data_adv = data.clone()
    edge_index = data.edge_index

    candidate_mask = _candidate_edge_mask(data, attack_only_malicious)
    if candidate_mask is None:
        return data_adv

    candidate_idx = candidate_mask.nonzero(as_tuple=False).view(-1)
    if candidate_idx.numel() == 0:
        return data_adv

    num_remove = _budget(data, perturbation_rate, candidate_idx.numel(), budget_reference)
    num_remove = min(num_remove, candidate_idx.numel())

    order = torch.randperm(candidate_idx.numel(), generator=generator, device="cpu")
    remove_idx = candidate_idx[order[:num_remove].to(candidate_idx.device)]

    # Canonical (undirected) key for each selected edge, so the reverse edge goes too.
    num_nodes = int(data.num_nodes)
    src, dst = edge_index[0], edge_index[1]
    lo = torch.minimum(src, dst)
    hi = torch.maximum(src, dst)
    keys = lo.to(torch.int64) * num_nodes + hi.to(torch.int64)

    removed_keys = keys[remove_idx]
    keep_edges = ~torch.isin(keys, removed_keys)

    data_adv.edge_index = edge_index[:, keep_edges]
    if getattr(data, "edge_attr", None) is not None:
        data_adv.edge_attr = data.edge_attr[keep_edges]

    return data_adv


def edge_addition_attack(
    data: Data,
    perturbation_rate: float = 0.10,
    attack_only_malicious: bool = True,
    avoid_duplicates: bool = True,
    budget_reference: str = "candidate",
    generator: Optional[torch.Generator] = None,
) -> Data:
    """Insert random new edges originating at malicious nodes.

    Destinations are sampled uniformly over all nodes.  Reverse edges are added
    as well, so the graph stays symmetric.

    Raises:
        ValueError: if ``perturbation_rate`` is outside (0, 1].
    """
    if perturbation_rate <= 0 or perturbation_rate > 1:
        raise ValueError(f"perturbation_rate must be in (0,1], got {perturbation_rate}")

    data_adv = data.clone()
    edge_index = data.edge_index
    device = edge_index.device

    candidate_mask = _candidate_edge_mask(data, attack_only_malicious)
    if candidate_mask is None:
        return data_adv

    if attack_only_malicious:
        source_nodes = (data.y == 1).nonzero(as_tuple=False).view(-1)
    else:
        source_nodes = torch.arange(data.num_nodes, device=device)
    if source_nodes.numel() == 0:
        return data_adv

    num_add = _budget(
        data, perturbation_rate, int(candidate_mask.sum()), budget_reference
    )

    num_nodes = int(data.num_nodes)
    existing = set()
    if avoid_duplicates:
        keys = (edge_index[0].to(torch.int64) * num_nodes + edge_index[1].to(torch.int64))
        existing = set(keys.tolist())

    new_edges_list = []
    max_attempts = num_add * 10
    attempts = 0
    while len(new_edges_list) < num_add and attempts < max_attempts:
        attempts += 1
        src_pos = torch.randint(0, source_nodes.numel(), (1,), generator=generator)
        dst = int(torch.randint(0, num_nodes, (1,), generator=generator).item())
        src = int(source_nodes[int(src_pos.item())].item())

        if src == dst:
            continue

        key = src * num_nodes + dst
        rkey = dst * num_nodes + src
        if avoid_duplicates and (key in existing or rkey in existing):
            continue

        new_edges_list.append((src, dst))
        if avoid_duplicates:
            existing.add(key)
            existing.add(rkey)

    if not new_edges_list:
        return data_adv

    new_edges = torch.tensor(new_edges_list, dtype=torch.long, device=device).t().contiguous()
    new_edges = torch.cat([new_edges, new_edges.flip(0)], dim=1)

    data_adv.edge_index = torch.cat([edge_index, new_edges], dim=1)

    if getattr(data, "edge_attr", None) is not None:
        new_edge_attr = cosine_similarity(
            data.x[new_edges[0]], data.x[new_edges[1]], dim=1
        ).view(-1, 1)
        data_adv.edge_attr = torch.cat(
            [data.edge_attr, new_edge_attr.to(data.edge_attr.dtype)], dim=0
        )

    return data_adv


def malicious_degree_stats(data: Data) -> dict:
    """Mean/max out-degree of malicious nodes -- useful to explain addition results."""
    node_mask = data.y == 1
    if node_mask.sum() == 0:
        return {"mean_degree": 0.0, "max_degree": 0.0, "num_malicious": 0.0}
    deg = torch.bincount(data.edge_index[0], minlength=int(data.num_nodes)).float()
    mal_deg = deg[node_mask]
    return {
        "mean_degree": float(mal_deg.mean()),
        "max_degree": float(mal_deg.max()),
        "num_malicious": float(int(node_mask.sum())),
    }


# Explicit aliases: these perturbations are random baselines, not optimised attacks.
random_edge_removal = edge_removal_attack
random_edge_addition = edge_addition_attack
