"""Tests for the graph construction used by experiments/06_graph_ablation.py."""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import torch
from torch_geometric.data import Data

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_module():
    spec = importlib.util.spec_from_file_location("graph_ablation", REPO_ROOT / "experiments" / "06_graph_ablation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestGraphAblation(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_random_graph_has_k_out_neighbours_no_self_loops_and_is_symmetric(self):
        edge_index = self.module.random_graph(50, 5, np.random.default_rng(0)).numpy()
        self.assertEqual(int(np.sum(edge_index[0] == edge_index[1])), 0)
        edges = set(map(tuple, edge_index.T))
        self.assertTrue(all((d, s) in edges for s, d in edges))
        self.assertTrue((np.bincount(edge_index[0], minlength=50) >= 5).all())
        self.assertEqual(len(edges), edge_index.shape[1])  # no duplicates

    def test_random_graph_is_seeded(self):
        a = self.module.random_graph(30, 3, np.random.default_rng(7))
        b = self.module.random_graph(30, 3, np.random.default_rng(7))
        self.assertTrue(torch.equal(a, b))

    def test_tiny_windows(self):
        self.assertEqual(self.module.random_graph(1, 5, np.random.default_rng(0)).shape, (2, 0))
        self.assertEqual(self.module.random_graph(3, 5, np.random.default_rng(0)).shape[1], 6)

    def test_with_graph(self):
        data = Data(x=torch.randn(10, 4), edge_index=torch.tensor([[0, 1], [1, 0]]), y=torch.zeros(10, dtype=torch.long))
        rng = np.random.default_rng(0)
        self.assertTrue(torch.equal(self.module.with_graph(data, "knn", 3, rng).edge_index, data.edge_index))
        self.assertEqual(self.module.with_graph(data, "none", 3, rng).edge_index.shape, (2, 0))
        self.assertGreater(self.module.with_graph(data, "random", 3, rng).edge_index.shape[1], 0)


if __name__ == "__main__":
    unittest.main()
