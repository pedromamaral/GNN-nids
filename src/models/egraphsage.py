"""
E-GraphSAGE-style edge classifier for endpoint graphs (Lo et al., NOMS 2022).

Nodes are endpoints, edges are flows with features. Each layer updates a node
from its own state and the mean over incident flows of [neighbour state, flow
features]; flows are seen from both endpoints (edges are mirrored for message
passing). A flow is classified from the final states of its two endpoints.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import MessagePassing

from .base import BaseGNN


class EdgeSAGEConv(MessagePassing):
	"""h_v' = W [h_v || mean_{(u,v)} (h_u || e_uv)]."""

	def __init__(self, node_dim: int, edge_dim: int, out_dim: int):
		super().__init__(aggr="mean")
		self.lin = nn.Linear(node_dim + node_dim + edge_dim, out_dim)

	def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
		aggregated = self.propagate(edge_index, x=x, edge_attr=edge_attr)
		return self.lin(torch.cat([x, aggregated], dim=-1))

	def message(self, x_j: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
		return torch.cat([x_j, edge_attr], dim=-1)


class EGraphSAGE_NIDS(BaseGNN):
	"""Edge classification on endpoint graphs. Returns logits of shape [num_flows, num_classes]."""

	def __init__(
		self,
		num_node_features: int,
		num_edge_features: int,
		hidden_dim: int,
		num_classes: int = 2,
		dropout: float = 0.5,
		hidden_layers: int = 2,
	):
		super().__init__(num_node_features, hidden_dim, num_classes, dropout)
		self.num_edge_features = num_edge_features
		dims = [num_node_features] + [hidden_dim] * hidden_layers
		self.convs = nn.ModuleList(EdgeSAGEConv(dims[i], num_edge_features, dims[i + 1]) for i in range(hidden_layers))
		self.classifier = nn.Linear(2 * hidden_dim, num_classes)

	def get_embeddings(self, data: Data) -> torch.Tensor:
		"""Node embeddings after message passing over mirrored flow edges."""
		edge_index, edge_attr = data.edge_index, data.edge_attr
		both = torch.cat([edge_index, edge_index.flip(0)], dim=1)
		both_attr = torch.cat([edge_attr, edge_attr], dim=0)
		h = data.x
		for conv in self.convs:
			h = F.relu(conv(h, both, both_attr))
			h = F.dropout(h, p=self.dropout, training=self.training)
		return h

	def forward(self, data: Data) -> torch.Tensor:
		h = self.get_embeddings(data)
		src, dst = data.edge_index
		return self.classifier(torch.cat([h[src], h[dst]], dim=-1))
