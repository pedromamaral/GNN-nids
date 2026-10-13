"""Tests for the CTU-13 loader, preprocessor, scenario-disjoint split and graph construction."""

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from data.ctu13 import (  # noqa: E402
    CTU13_DEFAULT_SPLIT,
    CTU13_SCENARIOS,
    Ctu13Preprocessor,
    load_ctu13,
    scenario_segments,
)
from data.dataset import load_split_datasets  # noqa: E402

HEADER = "StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,dTos,TotPkts,TotBytes,SrcBytes,Label"


def write_scenario(path: Path, n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        proto = ["tcp", "udp", "icmp"][i % 3]
        state = {"tcp": ["S_RA", "FSPA_FSPA", "SRPA_FSPA"][(i // 3) % 3], "udp": "CON", "icmp": "ECO"}[proto]
        sport = "0x0303" if proto == "icmp" else str(1024 + i)
        label = ["flow=From-Botnet-V42-TCP-CC", "flow=From-Normal-V42-UDP-DNS", "flow=Background-UDP-Established"][(i // 2) % 3]
        src = "147.32.84.165" if "Botnet" in label else f"10.0.{seed}.{i % 20}"
        stos = "" if i % 7 == 0 else "0"
        t = pd.Timestamp("2011-08-10 09:00:00") + pd.Timedelta(seconds=int(rng.integers(0, 3600)), microseconds=i)
        rows.append(f"{t.strftime('%Y/%m/%d %H:%M:%S.%f')},{rng.random():.6f},{proto},{src},{sport},  <->,"
                    f"147.32.80.{i % 5},53,{state},{stos},0,{rng.integers(1, 20)},{rng.integers(60, 5000)},"
                    f"{rng.integers(30, 60)},{label}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n")


class Ctu13Fixture(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.raw = self.temp_dir / "data" / "raw" / "ctu13" / "CTU-13-Dataset"
        self.sizes = {}
        for n, (fname, _) in CTU13_SCENARIOS.items():
            self.sizes[n] = 30 + n
            write_scenario(self.raw / str(n) / fname, self.sizes[n], seed=n)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)


class TestCtu13Loader(Ctu13Fixture):
    def test_labels_order_and_segments(self):
        df = load_ctu13(str(self.raw), [9, 10], with_endpoints=True)
        self.assertEqual(len(df), self.sizes[9] + self.sizes[10])
        self.assertEqual(set(df["Attack"]), {"Botnet", "Normal", "Background"})
        np.testing.assert_array_equal(df["Label"].to_numpy(), (df["Attack"] == "Botnet").to_numpy().astype(int))
        self.assertEqual(scenario_segments(df), [(0, self.sizes[9]), (self.sizes[9], len(df))])
        for a, b in scenario_segments(df):
            self.assertTrue((np.diff(df["START_MS"].to_numpy()[a:b]) >= 0).all())
        icmp = df["Proto"] == "icmp"
        self.assertTrue((df.loc[icmp, "SRC_PORT"] == 0x0303).all())
        self.assertTrue((df["SRC_IP"] > 0).all())

    def test_drop_background(self):
        df = load_ctu13(str(self.raw), [1], background="drop")
        self.assertNotIn("Background", set(df["Attack"]))

    def test_preprocessor(self):
        train = load_ctu13(str(self.raw), [1, 2])
        test = load_ctu13(str(self.raw), [9])
        pre = Ctu13Preprocessor()
        X, y = pre.preprocess(train, fit=True)
        self.assertEqual(X.shape[1], 36)
        self.assertTrue(np.isfinite(X).all())
        np.testing.assert_allclose(X.mean(axis=0)[np.std(X, axis=0) > 0], 0.0, atol=1e-5)
        Xt, _ = pre.preprocess(test, fit=False)
        self.assertEqual(Xt.shape, (len(test), 36))
        raw = Ctu13Preprocessor.raw_features(train)
        tcp = (train["Proto"] == "tcp").to_numpy()
        fspa = (train["State"] == "FSPA_FSPA").to_numpy()
        self.assertTrue((raw.loc[fspa, "tcp_dst_F"] == 1).all())
        self.assertTrue((raw.loc[~tcp, [c for c in raw.columns if c.startswith("tcp_")]] == 0).all().all())


class TestCtu13Dataset(Ctu13Fixture):
    def test_scenario_disjoint_endpoint_graphs(self):
        root = str(self.temp_dir / "data" / "graphs")
        train, val, test = load_split_datasets(name="ctu13", root=root, window_size=20, graph="endpoint", node_key="ip")
        for ds, split in ((train, "train"), (val, "validation"), (test, "test")):
            sizes = [self.sizes[n] for n in CTU13_DEFAULT_SPLIT[split]]
            self.assertEqual(sum(g.edge_index.shape[1] for g in ds), sum(sizes))
            # Windows never cross scenarios: one partial window per scenario.
            self.assertEqual(len(ds), sum(int(np.ceil(s / 20)) for s in sizes))

    def test_knn_graphs(self):
        root = str(self.temp_dir / "data" / "graphs")
        _, _, test = load_split_datasets(name="ctu13", root=root, window_size=20, k=3)
        self.assertEqual(sum(g.num_nodes for g in test), sum(self.sizes[n] for n in CTU13_DEFAULT_SPLIT["test"]))
        self.assertEqual(test[0].x.shape[1], 36)


class TestCtu13TabularContext(Ctu13Fixture):
    def test_host_context_runs_per_scenario(self):
        spec = importlib.util.spec_from_file_location("tab", REPO_ROOT / "experiments" / "00_tabular_baselines.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        args = module.parse_args(["--dataset", "ctu13", "--ctu13-dir", str(self.raw), "--context", "host",
                                  "--node-key", "ip", "--context-window", "10"])
        data = module.prepare_data(args)
        self.assertEqual(data["train"]["X"].shape[1], 36 * 3 + 2)
        self.assertEqual(len(data["test"]["y"]), sum(self.sizes[n] for n in CTU13_DEFAULT_SPLIT["test"]))


if __name__ == "__main__":
    unittest.main()
