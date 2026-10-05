"""Tests for the feature/structure decomposition (Phase 1 of the paper plan)."""

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analysis.decomposition import build_conditions, check_reconstruction, decomposition_effects
from analysis.neighbor_churn import knn_graph_tensors
from attacks.construction_aware import construction_aware_pgd
from attacks.fgsm import fgsm_attack
from attacks.pgd import pgd_attack
from data.graph_builder import FlowGraphBuilder
from models import GCN_NIDS

REPO_ROOT = Path(__file__).parent.parent


def make_window(n=60, f=8, mal_frac=0.2, k=5, seed=0):
    rng = np.random.default_rng(seed)
    y = np.zeros(n, dtype=np.int64)
    y[: int(n * mal_frac)] = 1
    x = rng.normal(size=(n, f)).astype(np.float32)
    x[y == 1] += 1.5
    return FlowGraphBuilder().build_graph(x, y, method="knn", k=k, bidirectional=True)


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "experiments" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReconstruction(unittest.TestCase):
    def test_rebuild_reproduces_training_graph(self):
        data = make_window()
        edge_index, edge_attr = knn_graph_tensors(data.x, k=5)
        self.assertEqual(set(map(tuple, edge_index.t().tolist())), set(map(tuple, data.edge_index.t().tolist())))
        self.assertEqual(edge_attr.shape, (edge_index.shape[1], 1))

    def test_check_reconstruction_is_exact_on_clean_windows(self):
        report = check_reconstruction([make_window(seed=s) for s in range(3)], k=5)
        self.assertEqual(report["windows"], 3)
        self.assertEqual(report["mean_churn"], 0.0)
        self.assertEqual(report["exact_fraction"], 1.0)


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.data = make_window()
        self.adv = self.data.clone()
        self.adv.x = self.data.x.clone()
        self.adv.x[self.data.y == 1] += 0.8

    def test_conditions_pair_features_and_graphs(self):
        cond = build_conditions(self.data, self.adv, k=5)
        rebuilt, _ = knn_graph_tensors(self.adv.x, k=5)
        torch.testing.assert_close(cond["A"].x, self.adv.x)
        torch.testing.assert_close(cond["A"].edge_index, self.data.edge_index)
        torch.testing.assert_close(cond["B"].x, self.data.x)
        torch.testing.assert_close(cond["B"].edge_index, rebuilt)
        torch.testing.assert_close(cond["C"].x, self.adv.x)
        torch.testing.assert_close(cond["C"].edge_index, rebuilt)
        for c in cond.values():
            self.assertEqual(c.edge_attr.shape[0], c.edge_index.shape[1])

    def test_zero_perturbation_leaves_graph_unchanged(self):
        cond = build_conditions(self.data, self.data.clone(), k=5)
        for name in ("B", "C"):
            self.assertEqual(
                set(map(tuple, cond[name].edge_index.t().tolist())),
                set(map(tuple, self.data.edge_index.t().tolist())),
            )

    def test_perturbation_moves_the_graph(self):
        cond = build_conditions(self.data, self.adv, k=5)
        self.assertNotEqual(
            set(map(tuple, cond["C"].edge_index.t().tolist())),
            set(map(tuple, self.data.edge_index.t().tolist())),
        )

    def test_effects_arithmetic(self):
        eff = decomposition_effects(0.9, {"A": 0.8, "B": 0.85, "C": 0.6})
        self.assertAlmostEqual(eff["feature"], 0.1)
        self.assertAlmostEqual(eff["structure"], 0.05)
        self.assertAlmostEqual(eff["combined"], 0.3)
        self.assertAlmostEqual(eff["interaction"], 0.15)


class TestConstructionAwarePGD(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.data = make_window()
        self.model = GCN_NIDS(self.data.x.shape[1], 16, dropout=0.0)
        self.model.eval()

    def test_respects_budget_and_leaves_benign_nodes(self):
        eps = 0.1
        adv = construction_aware_pgd(self.model, self.data, epsilon=eps, steps=5, k=5)
        delta = (adv.x - self.data.x).abs()
        self.assertLessEqual(float(delta.max()), eps + 1e-6)
        benign = self.data.y == 0
        torch.testing.assert_close(adv.x[benign], self.data.x[benign])

    def test_returns_graph_rebuilt_from_adversarial_features(self):
        adv = construction_aware_pgd(self.model, self.data, epsilon=0.3, steps=5, k=5)
        rebuilt, _ = knn_graph_tensors(adv.x, k=5)
        torch.testing.assert_close(adv.edge_index, rebuilt)
        self.assertEqual(adv.edge_attr.shape[0], adv.edge_index.shape[1])

    def test_feature_mask_freezes_columns(self):
        mask = torch.zeros(self.data.x.shape[1], dtype=torch.bool)
        mask[:3] = True
        adv = construction_aware_pgd(self.model, self.data, epsilon=0.3, steps=5, k=5, feature_mask=mask)
        torch.testing.assert_close(adv.x[:, 3:], self.data.x[:, 3:])
        self.assertGreater(float((adv.x[:, :3] - self.data.x[:, :3]).abs().max()), 0.0)

    def test_invalid_rebuild_every(self):
        with self.assertRaises(ValueError):
            construction_aware_pgd(self.model, self.data, epsilon=0.1, rebuild_every=0)

    def test_no_malicious_nodes_returns_copy(self):
        data = self.data.clone()
        data.y = torch.zeros_like(data.y)
        adv = construction_aware_pgd(self.model, data, epsilon=0.1, steps=2)
        torch.testing.assert_close(adv.x, data.x)


class TestFeatureMaskOnExistingAttacks(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.data = make_window()
        self.model = GCN_NIDS(self.data.x.shape[1], 16, dropout=0.0)
        self.mask = torch.tensor([True, False] * (self.data.x.shape[1] // 2))

    def test_pgd_feature_mask(self):
        adv = pgd_attack(self.model, self.data, epsilon=0.2, steps=3, feature_mask=self.mask)
        torch.testing.assert_close(adv.x[:, ~self.mask], self.data.x[:, ~self.mask])

    def test_fgsm_feature_mask(self):
        adv = fgsm_attack(self.model, self.data, epsilon=0.2, feature_mask=self.mask)
        torch.testing.assert_close(adv.x[:, ~self.mask], self.data.x[:, ~self.mask])

    def test_wrong_mask_length(self):
        with self.assertRaises(ValueError):
            pgd_attack(self.model, self.data, epsilon=0.2, steps=1, feature_mask=torch.ones(3, dtype=torch.bool))


class TestDecompositionExperiment(unittest.TestCase):
    """End-to-end smoke test of 05_decomposition.py and 05b_decomposition_report.py on synthetic windows."""

    def test_script_and_report(self):
        decomposition = load_script("decomposition_05", "05_decomposition.py")
        report = load_script("decomposition_report_05b", "05b_decomposition_report.py")

        windows = [make_window(seed=s) for s in range(3)]
        num_features = windows[0].x.shape[1]

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = GCN_NIDS(num_features, 16, dropout=0.0)
            checkpoint = tmp / "best_checkpoint.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "metadata": {"k": 5, "seed": 42, "hidden_dim": 16, "hidden_layers": 1, "dropout": 0.0},
                },
                checkpoint,
            )

            args = decomposition.parse_args(
                [
                    "--dataset", "nsl-kdd",
                    "--model", "gcn",
                    "--checkpoint", str(checkpoint),
                    "--training-seed", "42",
                    "--attack-seeds", "1", "2",
                    "--epsilons", "0.2",
                    "--steps", "3",
                    "--device", "cpu",
                    "--output-dir", str(tmp / "decomposition"),
                ]
            )
            with patch.object(decomposition, "load_split_datasets", return_value=(None, None, windows)):
                results = decomposition.run_decomposition(args)

            self.assertEqual(results["reconstruction_check"]["mean_churn"], 0.0)
            # fgsm: 1 seed; pgd and pgd_rebuild: 2 seeds each -> 5 runs
            self.assertEqual(len(results["runs"]), 5)

            csv_files = list((tmp / "decomposition").rglob("decomposition.csv"))
            self.assertEqual(len(csv_files), 1)
            rows = csv_files[0].read_text().strip().splitlines()
            self.assertEqual(len(rows) - 1, 5 * 3)

            out_dir = tmp / "report"
            self.assertEqual(report.main(["--results-dir", str(tmp / "decomposition"), "--out-dir", str(out_dir)]), 0)
            for name in ("decomposition_summary.csv", "decomposition_effects.csv", "go_no_go.csv"):
                self.assertTrue((out_dir / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
