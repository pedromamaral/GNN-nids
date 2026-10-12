"""
Endpoint graphs for flow classification (E-GraphSAGE style).

Nodes are network endpoints and every flow is a directed edge from its source
to its destination endpoint, carrying the flow's (preprocessed) features. The
task is edge classification: one label per flow.

Protocol choices that keep the comparison with the k-NN pipeline fair:

- Graphs are built per window of consecutive flows (the same chronological
  split and windowing as the k-NN graphs), never over the whole dataset.
- Endpoint identities never reach the model: nodes are relabelled 0..n-1 per
  window and carry a constant feature, so a model cannot memorise that a given
  IP is an attacker. Only the connectivity is used.
- ``node_key="isolated"`` gives every flow its own pair of endpoints. The model
  then sees each flow alone, which is the no-topology control.
"""

import logging
from typing import List

import numpy as np
import torch
from torch_geometric.data import Data

logger = logging.getLogger(__name__)

NODE_KEYS = ("ipport", "ip", "isolated")


def endpoint_keys(src_ip, src_port, dst_ip, dst_port, node_key: str = "ipport"):
    """Integer keys identifying the source and destination endpoint of each flow.

    ipport: (IP, L4 port), as in E-GraphSAGE. ip: the host only. isolated:
    distinct keys for every flow end, so no two flows share an endpoint.
    """
    src_ip = np.asarray(src_ip, dtype=np.int64)
    dst_ip = np.asarray(dst_ip, dtype=np.int64)
    if node_key == "ip":
        return src_ip, dst_ip
    if node_key == "ipport":
        return (src_ip << 16) | np.asarray(src_port, dtype=np.int64), (dst_ip << 16) | np.asarray(dst_port, dtype=np.int64)
    if node_key == "isolated":
        n = src_ip.size
        return np.arange(n, dtype=np.int64) * 2, np.arange(n, dtype=np.int64) * 2 + 1
    raise ValueError(f"Unknown node_key {node_key!r}; expected one of {NODE_KEYS}")


def build_endpoint_graph(X: np.ndarray, y: np.ndarray, src_key: np.ndarray, dst_key: np.ndarray) -> Data:
    """One endpoint graph: flows as directed edges between relabelled endpoints.

    Returns a Data object with ``x`` (num_nodes, 1) of ones, ``edge_index``
    (2, num_flows) in flow order, ``edge_attr`` (num_flows, num_features) and
    ``y`` (num_flows,). Edge i is flow i of the window.
    """
    keys, inverse = np.unique(np.concatenate([src_key, dst_key]), return_inverse=True)
    n_flows = src_key.size
    edge_index = np.stack([inverse[:n_flows], inverse[n_flows:]]).astype(np.int64)
    return Data(
        x=torch.ones((keys.size, 1), dtype=torch.float32),
        edge_index=torch.as_tensor(edge_index, dtype=torch.long),
        edge_attr=torch.as_tensor(np.asarray(X, dtype=np.float32)),
        y=torch.as_tensor(np.asarray(y, dtype=np.int64)),
        num_nodes=int(keys.size),
    )


def build_endpoint_windows(
    X: np.ndarray,
    y: np.ndarray,
    src_key: np.ndarray,
    dst_key: np.ndarray,
    window_size: int = 1000,
) -> List[Data]:
    """Endpoint graphs over consecutive, non-overlapping windows of flows."""
    if window_size < 1:
        raise ValueError("window_size must be at least 1")
    n = len(y)
    if not (len(X) == len(src_key) == len(dst_key) == n):
        raise ValueError("X, y and endpoint keys must have the same length")
    graphs = [
        build_endpoint_graph(X[s:s + window_size], y[s:s + window_size], src_key[s:s + window_size], dst_key[s:s + window_size])
        for s in range(0, n, window_size)
    ]
    logger.info(
        "Built %d endpoint graphs (window=%d): %d flows, mean %.1f nodes per graph",
        len(graphs), window_size, n, float(np.mean([g.num_nodes for g in graphs])) if graphs else 0.0,
    )
    return graphs
