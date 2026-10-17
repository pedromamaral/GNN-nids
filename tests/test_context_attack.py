"""Tests for src/attacks/context_attack.py and experiments/08_context_decomposition.py (E017)."""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from attacks import context_attack as ca  # noqa: E402
from data.ctu13 import Ctu13Preprocessor  # noqa: E402


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "experiments" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_frame(n, rng):
    pkts = rng.integers(1, 40, n).astype(float)
    src = pkts * rng.integers(60, 500, n)
    tot = src + rng.integers(0, 3000, n)
    return pd.DataFrame({
        "Dur": rng.random(n) * 30, "TotPkts": pkts, "TotBytes": tot, "SrcBytes": src,
        "sTos": rng.integers(0, 2, n).astype(float), "dTos": np.zeros(n),
        "Proto": rng.choice(["tcp", "udp", "icmp"], n), "Dir": rng.choice(["->", "<->"], n),
        "State": rng.choice(["S_RA", "SR_SA", "CON", "INT"], n), "Label": np.zeros(n, dtype=np.int64),
    })


def make_chunk(rng, n=400, window=100, n_bot_hosts=3):
    df = synthetic_frame(n, rng)
    pre = Ctu13Preprocessor()
    X, _ = pre.preprocess(df, fit=True)
    y = np.zeros(n, dtype=np.int64)
    y[rng.random(n) < 0.3] = 1
    src = np.where(y == 1, rng.integers(0, n_bot_hosts, n), rng.integers(100, 140, n)).astype(np.int64)
    dst = rng.integers(200, 230, n).astype(np.int64)
    raw = df[["Dur", "TotPkts", "TotBytes", "SrcBytes"]].to_numpy(dtype=np.float64)
    chunk = ca.Chunk(X, raw, y, src, dst, np.arange(n) // window)
    mean = torch.as_tensor(pre.scaler.mean_, dtype=torch.float64)
    scale = torch.as_tensor(pre.scaler.scale_, dtype=torch.float64)
    return chunk, df, pre, mean, scale


class TestFeatures(unittest.TestCase):
    def test_volume_features_match_preprocessor(self):
        chunk, df, pre, mean, scale = make_chunk(np.random.default_rng(0))
        raw = torch.as_tensor(chunk.raw)
        vol = ca.volume_features(raw[:, 0], raw[:, 1], raw[:, 2], raw[:, 3], mean, scale)
        np.testing.assert_allclose(vol.numpy(), chunk.X[:, :ca.N_VOLUME], atol=1e-5)
        self.assertEqual(pre.feature_names[:ca.N_VOLUME],
                         ["log_Dur", "log_TotPkts", "log_TotBytes", "log_SrcBytes", "log_DstBytes", "log_BytesPerPkt"])

    def test_host_context_matches_numpy(self):
        tab = load("tabular_baselines", "00_tabular_baselines.py")
        chunk, *_ = make_chunk(np.random.default_rng(1))
        ref = np.vstack([tab.host_context(chunk.X[a:a + 100], chunk.src_key[a:a + 100], chunk.dst_key[a:a + 100], 100)
                         for a in range(0, 400, 100)])
        ctx = ca.make_context(chunk.src_key, chunk.dst_key, chunk.win, "cpu")
        np.testing.assert_allclose(ca.host_context_t(torch.as_tensor(chunk.X), ctx).numpy(), ref, atol=1e-5)

    def test_graph_nodes_do_not_cross_windows(self):
        ctx = ca.make_context(np.array([1, 1]), np.array([2, 2]), np.array([0, 1]), "cpu")
        self.assertEqual(ctx.n_nodes, 4)
        self.assertNotEqual(int(ctx.edge_src[0]), int(ctx.edge_src[1]))


class TestProjection(unittest.TestCase):
    def test_shaping_feasible(self):
        rng = np.random.default_rng(2)
        n = 50
        raw = torch.as_tensor(np.stack([rng.random(n) * 10, rng.integers(1, 20, n), rng.integers(500, 9000, n), rng.integers(100, 4000, n)], 1).astype(float))
        g = torch.as_tensor(rng.integers(0, 5, n))
        budget = torch.full((5,), 3000.0, dtype=torch.float64)
        dsrc, dpkts, ddur = ca.project_shaping(torch.rand(n, dtype=torch.float64) * 9e4, torch.rand(n, dtype=torch.float64) * 900,
                                               torch.rand(n, dtype=torch.float64) * 99, raw, g, budget)
        dsrc, dpkts, ddur = ca.integerize_shaping(dsrc, dpkts, ddur, raw)
        spent = torch.zeros(5, dtype=torch.float64).index_add_(0, g, dsrc)
        self.assertTrue((spent <= budget).all())
        self.assertTrue((dsrc >= 0).all() and (dpkts >= 0).all() and (ddur >= 0).all())
        self.assertTrue((dpkts * ca.MIN_PKT_BYTES <= dsrc).all())
        self.assertTrue((ddur <= raw[:, 0]).all())

    def test_no_delay_without_shaping_budget(self):
        raw = torch.tensor([[5.0, 3.0, 1000.0, 500.0]], dtype=torch.float64)
        _, _, ddur = ca.project_shaping(torch.ones(1, dtype=torch.float64), torch.ones(1, dtype=torch.float64),
                                        torch.full((1,), 4.0, dtype=torch.float64), raw, torch.zeros(1, dtype=torch.long),
                                        torch.zeros(1, dtype=torch.float64))
        self.assertEqual(float(ddur), 0.0)

    def test_decoys_within_budget(self):
        n = 30
        dst = torch.full((n,), 200.0, dtype=torch.float64)
        g = torch.as_tensor(np.arange(n) % 3)
        budget = torch.full((3,), 5000.0, dtype=torch.float64)
        dur, pkts, src = ca.project_decoys(torch.rand(n, dtype=torch.float64), torch.full((n,), 5.0, dtype=torch.float64),
                                           torch.full((n,), 900.0, dtype=torch.float64), dst, torch.ones(n, dtype=torch.float64), g, budget)
        dur, pkts, src = ca.integerize_decoys(dur, pkts, src, dst)
        cost = torch.zeros(3, dtype=torch.float64).index_add_(0, g, src + dst)
        self.assertTrue((cost <= budget).all())
        self.assertTrue((pkts >= 1).all() and (src >= ca.DECOY_MIN_SRC).all())


class TestPlanAndAttack(unittest.TestCase):
    def setUp(self):
        self.chunk, _, _, self.mean, self.scale = make_chunk(np.random.default_rng(3))

    def test_plan_budgets_and_split(self):
        rng = np.random.default_rng(0)
        a = ca.build_plan(self.chunk, 0.5, 0.0, rng)
        b = ca.build_plan(self.chunk, 0.5, 1.0, rng)
        c = ca.build_plan(self.chunk, 0.5, 0.5, rng)
        self.assertEqual(len(a.dec_group), 0)
        self.assertTrue((b.budget_shape == 0).all())
        np.testing.assert_allclose(c.budget_shape + c.budget_decoy, 0.5 * c.base_bytes)
        self.assertGreater(len(b.dec_group), 0)
        # decoys come from bot hosts to destinations seen in the same window
        self.assertTrue(np.isin(b.dec_src_key, self.chunk.src_key[self.chunk.y == 1]).all())
        zero = ca.build_plan(self.chunk, 0.0, 0.0, rng)
        self.assertEqual(len(zero.dec_group), 0)

    def test_shaping_lowers_logit_within_budget(self):
        rng = np.random.default_rng(0)
        plan = ca.build_plan(self.chunk, 0.5, 0.0, rng)
        fn = lambda X, ctx: -X[:, 3]  # noqa: E731  low logit = more SrcBytes
        clean = ca.run_attack(self.chunk, ca.build_plan(self.chunk, 0.0, 0.0, rng), fn, 0.0, self.mean, self.scale, rng, "cpu", steps=5)
        res = ca.run_attack(self.chunk, plan, fn, 0.0, self.mean, self.scale, rng, "cpu", steps=10)
        bots = self.chunk.y == 1
        np.testing.assert_allclose(clean["X"].numpy(), self.chunk.X, atol=1e-5)  # beta=0 leaves flows unchanged
        self.assertLess(float(fn(res["X"], res["ctx"])[:len(bots)][bots].mean()), float(fn(clean["X"], clean["ctx"])[bots].mean()))
        self.assertTrue((res["group_shape"].numpy() <= plan.budget_shape + 1e-6).all())
        np.testing.assert_allclose(res["X"].numpy()[~bots], self.chunk.X[~bots])

    def test_injection_cannot_move_context_free_model(self):
        rng = np.random.default_rng(0)
        plan = ca.build_plan(self.chunk, 0.5, 1.0, rng)
        fn = lambda X, ctx: X[:, :6].sum(1)  # noqa: E731  ignores context
        res = ca.run_attack(self.chunk, plan, fn, 0.0, self.mean, self.scale, rng, "cpu", steps=5)
        self.assertGreater(res["m"], 0)
        np.testing.assert_allclose(res["X"].numpy()[:len(self.chunk.y)], self.chunk.X, atol=1e-5)
        self.assertTrue((res["group_decoy"].numpy() <= plan.budget_decoy + 1e-6).all())

    def test_injection_moves_context_model(self):
        rng = np.random.default_rng(0)
        plan = ca.build_plan(self.chunk, 0.5, 1.0, rng)

        def fn(X, ctx):
            return ca.host_context_t(X, ctx)[:, 6:12].sum(1)  # source-host mean volume

        res = ca.run_attack(self.chunk, plan, fn, 0.0, self.mean, self.scale, rng, "cpu", steps=8)
        clean = ca.run_attack(self.chunk, ca.build_plan(self.chunk, 0.0, 0.0, rng), fn, 0.0, self.mean, self.scale, rng, "cpu", steps=1)
        bots = self.chunk.y == 1
        self.assertLess(float(fn(res["X"], res["ctx"])[:len(bots)][bots].mean()), float(fn(clean["X"], clean["ctx"])[bots].mean()))


class TestSummary(unittest.TestCase):
    def test_g_and_s(self):
        m = load("context_decomposition", "08_context_decomposition.py")
        grid = m.condition_grid([0.1], [0.0, 0.5, 1.0], True)
        self.assertIn((0.05, 0.0), grid)
        self.assertIn((0.05, 1.0), grid)
        recall = {(0.0, 0.0): 0.9, (0.1, 0.0): 0.8, (0.1, 1.0): 0.9, (0.1, 0.5): 0.7, (0.05, 0.0): 0.85, (0.05, 1.0): 0.9}
        rows = pd.DataFrame([{"detector": "d", "origin": "white", "attack_seed": 0, "beta": b, "rho": r, "recall": v}
                             for (b, r), v in recall.items()])
        out = m.summarize(rows, [0.0, 0.5, 1.0]).iloc[0]
        self.assertAlmostEqual(out.delta_A, 0.1)
        self.assertAlmostEqual(out.delta_B, 0.0)
        self.assertAlmostEqual(out.delta_Cstar, 0.2)
        self.assertAlmostEqual(out.G, 0.1)
        self.assertAlmostEqual(out.S_max_abs, 0.2 - 0.05 - 0.0)


if __name__ == "__main__":
    unittest.main()
