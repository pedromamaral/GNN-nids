"""Tests for endpoint graphs (flows as edges between endpoints) and the E-GraphSAGE edge classifier."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Batch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from data.endpoint_graph import build_endpoint_graph, build_endpoint_windows, endpoint_keys  # noqa: E402
from data.netflow_v3 import ENDPOINT_COLUMNS, feature_columns, ipv4_to_int, load_netflow_v3  # noqa: E402
from data.dataset import load_split_datasets  # noqa: E402
from models import EGraphSAGE_NIDS  # noqa: E402
from test_netflow_v3 import NETFLOW_V3_HEADER, make_netflow_frame  # noqa: E402


class TestEndpointKeys(unittest.TestCase):
    def test_ipv4_to_int(self):
        values = ipv4_to_int(pd.Series(["10.0.0.1", "192.168.1.255", "0.0.0.0"]))
        np.testing.assert_array_equal(values, [167772161, 3232236031, 0])

    def test_non_ipv4_values_hash_outside_the_ipv4_range(self):
        values = ipv4_to_int(pd.Series(["fe80::1", "10.0.0.1", "fe80::1", "not-an-ip"]))
        self.assertEqual(values[1], 167772161)
        self.assertEqual(values[0], values[2])
        self.assertTrue(values[0] >= 1 << 32 and values[3] >= 1 << 32)
        self.assertNotEqual(values[0], values[3])

    def test_node_keys(self):
        src_ip, dst_ip = np.array([1, 1, 2]), np.array([3, 3, 3])
        src_port, dst_port = np.array([1000, 1001, 1000]), np.array([80, 80, 443])
        s, d = endpoint_keys(src_ip, src_port, dst_ip, dst_port, "ip")
        np.testing.assert_array_equal(s, src_ip)
        s, d = endpoint_keys(src_ip, src_port, dst_ip, dst_port, "ipport")
        self.assertEqual(len(set(s)), 3)
        self.assertEqual(d[0], d[1])
        self.assertNotEqual(d[0], d[2])
        s, d = endpoint_keys(src_ip, src_port, dst_ip, dst_port, "isolated")
        self.assertEqual(len(set(s) | set(d)), 6)
        with self.assertRaises(ValueError):
            endpoint_keys(src_ip, src_port, dst_ip, dst_port, "mac")


class TestEndpointGraph(unittest.TestCase):
    def setUp(self):
        self.X = np.arange(12, dtype=np.float32).reshape(4, 3)
        self.y = np.array([0, 1, 0, 1])
        # Flows: A->B, A->C, B->C, D->A  (keys are arbitrary large integers)
        self.src = np.array([10_000, 10_000, 20_000, 40_000])
        self.dst = np.array([20_000, 30_000, 30_000, 10_000])

    def test_flows_become_edges_between_relabelled_endpoints(self):
        g = build_endpoint_graph(self.X, self.y, self.src, self.dst)
        self.assertEqual(g.num_nodes, 4)
        self.assertEqual(tuple(g.edge_index.shape), (2, 4))
        self.assertTrue(int(g.edge_index.max()) < 4)  # no raw keys survive
        np.testing.assert_array_equal(g.edge_attr.numpy(), self.X)
        np.testing.assert_array_equal(g.y.numpy(), self.y)
        self.assertTrue(torch.equal(g.x, torch.ones(4, 1)))
        # A is the source of flows 0 and 1 and the destination of flow 3
        a = int(g.edge_index[0, 0])
        self.assertEqual(int(g.edge_index[0, 1]), a)
        self.assertEqual(int(g.edge_index[1, 3]), a)

    def test_windows(self):
        graphs = build_endpoint_windows(self.X, self.y, self.src, self.dst, window_size=3)
        self.assertEqual([g.edge_index.shape[1] for g in graphs], [3, 1])
        self.assertEqual(graphs[1].num_nodes, 2)
        with self.assertRaises(ValueError):
            build_endpoint_windows(self.X, self.y[:3], self.src, self.dst)


class TestEGraphSAGE(unittest.TestCase):
    def _graph(self, X, src, dst):
        return build_endpoint_graph(X, np.zeros(len(src), dtype=np.int64), np.asarray(src), np.asarray(dst))

    def test_output_is_one_row_per_flow_also_when_batched(self):
        torch.manual_seed(0)
        model = EGraphSAGE_NIDS(num_node_features=1, num_edge_features=3, hidden_dim=8, hidden_layers=2)
        rng = np.random.default_rng(0)
        g1 = self._graph(rng.normal(size=(5, 3)), [1, 1, 2, 3, 4], [2, 3, 3, 1, 1])
        g2 = self._graph(rng.normal(size=(2, 3)), [7, 8], [8, 9])
        model.eval()
        self.assertEqual(tuple(model(g1).shape), (5, 2))
        batched = model(Batch.from_data_list([g1, g2]))
        self.assertEqual(tuple(batched.shape), (7, 2))
        torch.testing.assert_close(batched[:5], model(g1))
        torch.testing.assert_close(batched[5:], model(g2))

    def test_shared_endpoints_propagate_but_isolated_flows_do_not(self):
        torch.manual_seed(0)
        model = EGraphSAGE_NIDS(num_node_features=1, num_edge_features=3, hidden_dim=8, hidden_layers=2).eval()
        X = np.random.default_rng(1).normal(size=(3, 3)).astype(np.float32)
        X_changed = X.copy()
        X_changed[2] += 5.0  # change flow 2 only

        shared = ([1, 1, 1], [2, 3, 4])  # all flows share source endpoint 1
        a = model(self._graph(X, *shared))[0]
        b = model(self._graph(X_changed, *shared))[0]
        self.assertFalse(torch.allclose(a, b))

        iso = endpoint_keys(np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3), "isolated")
        a = model(self._graph(X, *iso))[0]
        b = model(self._graph(X_changed, *iso))[0]
        torch.testing.assert_close(a, b)


class TestEndpointDataset(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        raw_dir = self.temp_dir / "data" / "raw" / "netflow-v3"
        raw_dir.mkdir(parents=True)
        self.raw = make_netflow_frame(n=400, seed=2)
        self.raw["IPV4_DST_ADDR"] = [f"10.0.1.{i % 7}" for i in range(400)]
        self.raw["L4_DST_PORT"] = 80.0
        self.csv = raw_dir / "NF-UNSW-NB15-v3.csv"
        self.raw.to_csv(self.csv, index=False)
        self.root = str(self.temp_dir / "data" / "graphs")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_loader_returns_endpoints_but_not_as_features(self):
        df = load_netflow_v3(self.csv, with_endpoints=True, chunksize=50)
        for col in ENDPOINT_COLUMNS:
            self.assertIn(col, df.columns)
            self.assertNotIn(col, feature_columns(df.columns.tolist()))
        expected = self.raw.sort_values("FLOW_START_MILLISECONDS", kind="stable")
        np.testing.assert_array_equal(df["SRC_IP"].to_numpy(), ipv4_to_int(expected["IPV4_SRC_ADDR"]))
        self.assertEqual(len(feature_columns(NETFLOW_V3_HEADER)), len(feature_columns(df.columns.tolist())))

    def test_endpoint_splits(self):
        train, val, test = load_split_datasets(name="nf-unsw-nb15-v3", root=self.root, window_size=50,
                                               graph="endpoint", node_key="ip")
        self.assertEqual(sum(g.edge_index.shape[1] for g in train), 240)
        self.assertEqual(sum(g.edge_index.shape[1] for g in test), 80)
        g = test[0]
        self.assertEqual(g.edge_attr.shape[1], len(feature_columns(NETFLOW_V3_HEADER)))
        self.assertEqual(g.y.shape[0], g.edge_index.shape[1])
        # 7 destination hosts, so far fewer nodes than flows with node_key="ip"
        self.assertLess(g.num_nodes, 2 * g.edge_index.shape[1])
        self.assertTrue((Path(self.root) / "nf-unsw-nb15-v3" / "endpoint_ip").exists())

    def test_isolated_control_has_two_nodes_per_flow(self):
        _, _, test = load_split_datasets(name="nf-unsw-nb15-v3", root=self.root, window_size=50,
                                         graph="endpoint", node_key="isolated")
        g = test[0]
        self.assertEqual(g.num_nodes, 2 * g.edge_index.shape[1])

    def test_endpoint_graphs_rejected_for_thesis_datasets(self):
        with self.assertRaises(ValueError):
            load_split_datasets(name="nsl-kdd", root=self.root, graph="endpoint")


if __name__ == "__main__":
    unittest.main()
