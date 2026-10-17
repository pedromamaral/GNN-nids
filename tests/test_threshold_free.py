"""Tests for experiments/07_threshold_free.py (E016 metrics + paired block bootstrap)."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location("threshold_free", REPO_ROOT / "experiments" / "07_threshold_free.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_perfect_and_random(self):
        y = np.array([0, 0, 1, 1])
        s = np.array([0.1, 0.2, 0.8, 0.9])
        self.assertAlmostEqual(self.m.average_precision(y, s), 1.0)
        self.assertAlmostEqual(self.m.roc_auc(y, s), 1.0)
        self.assertAlmostEqual(self.m.f1_at(y, s, 0.5), 1.0)
        self.assertAlmostEqual(self.m.roc_auc(y, s[::-1]), 0.0)

    def test_tuned_threshold_beats_default(self):
        y = np.array([0, 0, 1, 1])
        s = np.array([0.1, 0.2, 0.3, 0.4])  # separable but all below 0.5
        thr = self.m.tuned_threshold(y, s)
        self.assertAlmostEqual(self.m.f1_at(y, s, thr), 1.0)
        self.assertEqual(self.m.f1_at(y, s, 0.5), 0.0)

    def test_end_to_end(self):
        rng = np.random.default_rng(0)
        n = 20000
        yv, yt = (rng.random(n) < .1).astype(np.int8), (rng.random(n) < .1).astype(np.int8)
        win = (np.arange(n) // 500).astype(np.int32)

        def sc(y, q):
            return (1 / (1 + np.exp(-(rng.normal(0, 1, len(y)) + q * y * 2)))).astype(np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for lab, q in (("ip", 2.0), ("isolated", 0.5)):
                d = {}
                for s in (42, 43):
                    run = f"x_gcn_seed_{s}"
                    d.update({f"{run}|val|score": sc(yv, q), f"{run}|val|y": yv, f"{run}|val|window": win,
                              f"{run}|test|score": sc(yt, q), f"{run}|test|y": yt, f"{run}|test|window": win})
                np.savez(tmp / f"g_{lab}.npz", **d)
            t = {"validation|y": yv, "test|y": yt, "test|scenario": (np.arange(n) > n // 2).astype(np.int16)}
            for model in ("xgboost", "mlp"):
                for s in (42, 43):
                    t[f"{model}|{s}|validation"], t[f"{model}|{s}|test"] = sc(yv, 1.0), sc(yt, 1.0)
            np.savez(tmp / "t.npz", **t)
            out = tmp / "o.json"
            argv = ["x", "--gnn", f"ip={tmp / 'g_ip.npz'}", "--gnn", f"isolated={tmp / 'g_isolated.npz'}",
                    "--tab", f"plain={tmp / 't.npz'}", "--resamples", "300", "--out", str(out)]
            old, sys.argv = sys.argv, argv
            try:
                self.m.main()
            finally:
                sys.argv = old
            res = json.loads(out.read_text())
        self.assertGreater(res["gaps"]["pr_auc"]["mean"], 0)
        lo, hi = res["gaps"]["pr_auc"]["ci95_mean"]
        self.assertGreater(lo, 0)
        self.assertLess(lo, hi)
        self.assertEqual(len(res["per_scenario"]), 2)


if __name__ == "__main__":
    unittest.main()
