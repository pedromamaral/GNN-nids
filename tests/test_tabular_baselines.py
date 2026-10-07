"""Smoke test for experiments/00_tabular_baselines.py on a synthetic NetFlow-v3 file."""

import csv
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_netflow_v3 import make_netflow_frame  # noqa: E402


def load_baselines_module():
    spec = importlib.util.spec_from_file_location("tabular_baselines", REPO_ROOT / "experiments" / "00_tabular_baselines.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTabularBaselines(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.raw_dir = self.temp_dir / "raw"
        self.raw_dir.mkdir()
        df = make_netflow_frame(n=500, seed=3)
        # Make the label learnable from one feature.
        df["IN_BYTES"] = np.where(df["Label"] == 1, 50_000.0, 10.0)
        df.to_csv(self.raw_dir / "NF-UNSW-NB15-v3.csv", index=False)
        self.module = load_baselines_module()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_runs_both_models_for_each_seed(self):
        args = self.module.parse_args([
            "--dataset", "nf-unsw-nb15-v3",
            "--raw-dir", str(self.raw_dir),
            "--output-dir", str(self.temp_dir / "out"),
            "--seeds", "1", "2",
            "--device", "cpu",
            "--n-jobs", "1",
            "--xgb-estimators", "10",
            "--mlp-epochs", "30",
            "--mlp-patience", "30",
            "--mlp-learning-rate", "0.01",
            "--mlp-batch-size", "32",
        ])
        out_dir = self.module.run(args)

        with (out_dir / "results.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2 * 2 * 3)  # models x seeds x splits
        test_f1 = [float(r["f1"]) for r in rows if r["split"] == "test"]
        self.assertTrue(all(f1 > 0.9 for f1 in test_f1), test_f1)

        with (out_dir / "per_class.csv").open() as handle:
            classes = {r["attack"] for r in csv.DictReader(handle)}
        self.assertEqual(classes, {"Benign", "Exploits"})

        config = json.loads((out_dir / "config.json").read_text())
        self.assertEqual(config["sizes"], {"train": 300, "validation": 100, "test": 100})
        with (out_dir / "summary.csv").open() as handle:
            summary = {r["model"]: r for r in csv.DictReader(handle)}
        self.assertEqual(set(summary), {"xgboost", "mlp"})
        self.assertEqual(summary["mlp"]["seeds"], "2")


if __name__ == "__main__":
    unittest.main()
