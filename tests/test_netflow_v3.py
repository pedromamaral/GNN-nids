"""
Tests for the NetFlow-v3 loader, preprocessor and the chronological split.

The fixtures write small CSVs with the real NetFlow-v3 header, so no raw data
is needed.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.netflow_v3 import (  # noqa: E402
    ARTEFACT_COLUMNS,
    IDENTIFIER_COLUMNS,
    NETFLOW_V3_DATASETS,
    NON_LOG_COLUMNS,
    TIMESTAMP_COLUMNS,
    NetFlowV3Preprocessor,
    dataset_variant_id,
    feature_columns,
    load_netflow_v3,
)
from data.splits import SplitManager, chronological_split  # noqa: E402
from data.dataset import load_split_datasets  # noqa: E402
from analysis.decomposition import check_reconstruction  # noqa: E402

NETFLOW_V3_HEADER = (
    "FLOW_START_MILLISECONDS,FLOW_END_MILLISECONDS,IPV4_SRC_ADDR,L4_SRC_PORT,IPV4_DST_ADDR,L4_DST_PORT,"
    "PROTOCOL,L7_PROTO,IN_BYTES,IN_PKTS,OUT_BYTES,OUT_PKTS,TCP_FLAGS,CLIENT_TCP_FLAGS,SERVER_TCP_FLAGS,"
    "FLOW_DURATION_MILLISECONDS,DURATION_IN,DURATION_OUT,MIN_TTL,MAX_TTL,LONGEST_FLOW_PKT,SHORTEST_FLOW_PKT,"
    "MIN_IP_PKT_LEN,MAX_IP_PKT_LEN,SRC_TO_DST_SECOND_BYTES,DST_TO_SRC_SECOND_BYTES,RETRANSMITTED_IN_BYTES,"
    "RETRANSMITTED_IN_PKTS,RETRANSMITTED_OUT_BYTES,RETRANSMITTED_OUT_PKTS,SRC_TO_DST_AVG_THROUGHPUT,"
    "DST_TO_SRC_AVG_THROUGHPUT,NUM_PKTS_UP_TO_128_BYTES,NUM_PKTS_128_TO_256_BYTES,NUM_PKTS_256_TO_512_BYTES,"
    "NUM_PKTS_512_TO_1024_BYTES,NUM_PKTS_1024_TO_1514_BYTES,TCP_WIN_MAX_IN,TCP_WIN_MAX_OUT,ICMP_TYPE,"
    "ICMP_IPV4_TYPE,DNS_QUERY_ID,DNS_QUERY_TYPE,DNS_TTL_ANSWER,FTP_COMMAND_RET_CODE,SRC_TO_DST_IAT_MIN,"
    "SRC_TO_DST_IAT_MAX,SRC_TO_DST_IAT_AVG,SRC_TO_DST_IAT_STDDEV,DST_TO_SRC_IAT_MIN,DST_TO_SRC_IAT_MAX,"
    "DST_TO_SRC_IAT_AVG,DST_TO_SRC_IAT_STDDEV,Label,Attack"
).split(",")


def make_netflow_frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    """Synthetic NetFlow-v3 rows in shuffled time order, with a unique row id in IN_PKTS."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {c: rng.integers(0, 1000, size=n).astype(float) for c in NETFLOW_V3_HEADER[:-2]}
    )
    df["IPV4_SRC_ADDR"] = [f"10.0.0.{i % 250}" for i in range(n)]
    df["IPV4_DST_ADDR"] = [f"10.0.1.{i % 250}" for i in range(n)]
    # Times with ties, in shuffled order; IN_PKTS records the original file row.
    df["FLOW_START_MILLISECONDS"] = 1_700_000_000_000 + rng.integers(0, n // 2, size=n)
    df["FLOW_END_MILLISECONDS"] = df["FLOW_START_MILLISECONDS"] + 5
    df["IN_PKTS"] = np.arange(n, dtype=float)
    labels = rng.integers(0, 2, size=n)
    df["Label"] = labels
    df["Attack"] = np.where(labels == 1, "Exploits", "Benign")
    return df[NETFLOW_V3_HEADER]


class TestNetFlowV3Loader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.raw = make_netflow_frame()
        self.csv = self.temp_dir / "NF-TEST-v3.csv"
        self.raw.to_csv(self.csv, index=False)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_registered_names(self):
        self.assertEqual(
            set(NETFLOW_V3_DATASETS),
            {"nf-unsw-nb15-v3", "nf-ton-iot-v3", "nf-cse-cic-ids2018-v3"},
        )

    def test_feature_columns_exclude_identifiers_timestamps_and_labels(self):
        features = feature_columns(NETFLOW_V3_HEADER)
        for col in IDENTIFIER_COLUMNS + TIMESTAMP_COLUMNS + ARTEFACT_COLUMNS + ["Label", "Attack"]:
            self.assertNotIn(col, features)
        self.assertNotIn("MIN_TTL", features)
        self.assertEqual(len(features), 44)
        self.assertTrue(NON_LOG_COLUMNS.issubset(features))

    def test_sorted_by_start_time_with_stable_ties(self):
        df = load_netflow_v3(self.csv)
        self.assertEqual(len(df), len(self.raw))
        expected = self.raw.sort_values("FLOW_START_MILLISECONDS", kind="stable")
        np.testing.assert_array_equal(df["IN_PKTS"].to_numpy(), expected["IN_PKTS"].to_numpy())
        np.testing.assert_array_equal(df.index.to_numpy(), np.arange(len(df)))
        self.assertIn("Attack", df.columns)
        self.assertNotIn("IPV4_SRC_ADDR", df.columns)

    def test_chunked_read_matches_single_read(self):
        whole = load_netflow_v3(self.csv)
        chunked = load_netflow_v3(self.csv, chunksize=17)
        pd.testing.assert_frame_equal(whole, chunked)

    def test_time_slice_is_contiguous_in_time(self):
        full = load_netflow_v3(self.csv)
        sliced = load_netflow_v3(self.csv, max_flows=50, slice_start=0.25, chunksize=31)
        self.assertEqual(len(sliced), 50)
        np.testing.assert_array_equal(
            sliced["IN_PKTS"].to_numpy(), full["IN_PKTS"].to_numpy()[50:100]
        )

    def test_slice_past_the_end_is_truncated(self):
        sliced = load_netflow_v3(self.csv, max_flows=1000, slice_start=0.9)
        self.assertEqual(len(sliced), 20)

    def test_invalid_slice_arguments(self):
        with self.assertRaises(ValueError):
            load_netflow_v3(self.csv, max_flows=10, slice_start=1.0)
        with self.assertRaises(ValueError):
            load_netflow_v3(self.csv, max_flows=0)

    def test_not_a_netflow_file(self):
        bad = self.temp_dir / "bad.csv"
        pd.DataFrame({"a": [1], "b": [2]}).to_csv(bad, index=False)
        with self.assertRaises(ValueError):
            load_netflow_v3(bad)

    def test_variant_id(self):
        self.assertEqual(dataset_variant_id("nf-ton-iot-v3"), "nf-ton-iot-v3")
        self.assertEqual(dataset_variant_id("nf-ton-iot-v3", 2_000_000), "nf-ton-iot-v3_2000000flows")
        self.assertEqual(
            dataset_variant_id("nf-ton-iot-v3", 2_000_000, 0.5), "nf-ton-iot-v3_2000000flows_from0.5"
        )


class TestNetFlowV3Preprocessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        csv = self.temp_dir / "NF-TEST-v3.csv"
        make_netflow_frame(n=300).to_csv(csv, index=False)
        self.df = load_netflow_v3(csv)
        self.train = self.df.iloc[:180].reset_index(drop=True)
        self.test = self.df.iloc[240:].reset_index(drop=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_output_shape_and_dtypes(self):
        pre = NetFlowV3Preprocessor()
        X, y = pre.preprocess(self.train, fit=True)
        self.assertEqual(X.shape, (180, len(feature_columns(NETFLOW_V3_HEADER))))
        self.assertEqual(X.dtype, np.float32)
        self.assertEqual(y.dtype, np.int64)
        np.testing.assert_array_equal(y, self.train["Label"].to_numpy())

    def test_train_is_standardised_and_test_uses_train_statistics(self):
        pre = NetFlowV3Preprocessor()
        X_train, _ = pre.preprocess(self.train, fit=True)
        np.testing.assert_allclose(X_train.mean(axis=0), 0.0, atol=1e-5)
        mean_before = pre.scaler.mean_.copy()
        X_test, _ = pre.preprocess(self.test, fit=False)
        np.testing.assert_array_equal(pre.scaler.mean_, mean_before)
        expected = pre.scaler.transform(pre.transform_raw(self.test, fit=False)).astype(np.float32)
        np.testing.assert_allclose(X_test, expected)

    def test_log_applies_to_counters_only(self):
        pre = NetFlowV3Preprocessor()
        pre.preprocess(self.train, fit=True)
        raw = pre.transform_raw(self.train, fit=False)
        names = pre.feature_names
        in_bytes = names.index("IN_BYTES")
        protocol = names.index("PROTOCOL")
        np.testing.assert_allclose(raw[:, in_bytes], np.log1p(self.train["IN_BYTES"].to_numpy()))
        np.testing.assert_allclose(raw[:, protocol], self.train["PROTOCOL"].to_numpy())

    def test_non_finite_values(self):
        train = self.train.copy()
        train.loc[0, "SRC_TO_DST_SECOND_BYTES"] = np.inf
        train.loc[1, "SRC_TO_DST_SECOND_BYTES"] = np.nan
        pre = NetFlowV3Preprocessor()
        X, _ = pre.preprocess(train, fit=True)
        self.assertTrue(np.isfinite(X).all())
        raw = pre.transform_raw(train, fit=False)
        col = pre.feature_names.index("SRC_TO_DST_SECOND_BYTES")
        finite_max = train["SRC_TO_DST_SECOND_BYTES"].replace(np.inf, np.nan).max()
        self.assertAlmostEqual(raw[0, col], np.log1p(finite_max))
        self.assertEqual(raw[1, col], 0.0)

    def test_transform_before_fit_fails(self):
        with self.assertRaises(ValueError):
            NetFlowV3Preprocessor().preprocess(self.test, fit=False)

    def test_state_round_trip(self):
        import pickle

        pre = NetFlowV3Preprocessor()
        pre.preprocess(self.train, fit=True)
        X_expected, _ = pre.preprocess(self.test, fit=False)
        state_path = self.temp_dir / "state.pkl"
        with open(state_path, "wb") as f:
            pickle.dump(pre.get_state(), f)
        loaded = NetFlowV3Preprocessor()
        loaded.load_preprocessed(str(state_path))
        X, _ = loaded.preprocess(self.test, fit=False)
        np.testing.assert_array_equal(X, X_expected)


class TestChronologicalSplit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_contiguous_ordered_blocks(self):
        train, val, test = chronological_split(1000)
        self.assertEqual((len(train), len(val), len(test)), (600, 200, 200))
        np.testing.assert_array_equal(np.concatenate([train, val, test]), np.arange(1000))

    def test_uneven_sizes_cover_everything(self):
        train, val, test = chronological_split(1003, (0.6, 0.2, 0.2))
        self.assertEqual(len(train) + len(val) + len(test), 1003)
        self.assertEqual(train[-1] + 1, val[0])
        self.assertEqual(val[-1] + 1, test[0])

    def test_invalid_ratios(self):
        with self.assertRaises(ValueError):
            chronological_split(100, (0.6, 0.3, 0.2))

    def _sorted_frame(self, n=100):
        return pd.DataFrame(
            {"FLOW_START_MILLISECONDS": np.arange(n) * 10, "Label": (np.arange(n) >= 80).astype(int)}
        )

    def test_split_manager_records_blocks(self):
        manager = SplitManager("nf-unsw-nb15-v3", data_dir=str(self.temp_dir))
        train, val, test = manager.create_or_load_splits(
            "nf-unsw-nb15-v3", train_df=self._sorted_frame(), netflow_metadata={"max_flows": None}
        )
        self.assertEqual((len(train), len(val), len(test)), (60, 20, 20))
        blocks = manager.load_split_config()["metadata"]["blocks"]
        self.assertEqual(blocks["train"]["end_time"], 590)
        self.assertEqual(blocks["test"]["start_time"], 800)
        self.assertAlmostEqual(blocks["test"]["attack_fraction"], 1.0)
        self.assertAlmostEqual(blocks["train"]["attack_fraction"], 0.0)

    def test_split_manager_reuses_matching_splits(self):
        manager = SplitManager("nf-unsw-nb15-v3", data_dir=str(self.temp_dir))
        first = manager.create_or_load_splits("nf-unsw-nb15-v3", train_df=self._sorted_frame())
        second = manager.create_or_load_splits("nf-unsw-nb15-v3", train_df=self._sorted_frame())
        for a, b in zip(first, second):
            np.testing.assert_array_equal(a, b)

    def test_split_manager_rejects_splits_from_other_data(self):
        manager = SplitManager("nf-unsw-nb15-v3", data_dir=str(self.temp_dir))
        manager.create_or_load_splits(
            "nf-unsw-nb15-v3", train_df=self._sorted_frame(), netflow_metadata={"max_flows": None}
        )
        with self.assertRaises(RuntimeError):
            manager.create_or_load_splits("nf-unsw-nb15-v3", train_df=self._sorted_frame(120))
        with self.assertRaises(RuntimeError):
            manager.create_or_load_splits(
                "nf-unsw-nb15-v3", train_df=self._sorted_frame(), netflow_metadata={"max_flows": 50}
            )

    def test_split_manager_rejects_unsorted_frame(self):
        manager = SplitManager("nf-unsw-nb15-v3", data_dir=str(self.temp_dir))
        df = self._sorted_frame().iloc[::-1].reset_index(drop=True)
        with self.assertRaises(ValueError):
            manager.create_or_load_splits("nf-unsw-nb15-v3", train_df=df)


class TestNetFlowV3Dataset(unittest.TestCase):
    """End-to-end: CSV -> chronological split -> preprocessing -> windowed k-NN graphs."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        raw_dir = self.temp_dir / "data" / "raw" / "netflow-v3"
        raw_dir.mkdir(parents=True)
        raw = make_netflow_frame(n=400, seed=1)
        # Exact duplicates, as in the real data: the last 60 flows repeat flow 0.
        raw.iloc[340:, 2:] = raw.iloc[[0] * 60, 2:].to_numpy()
        raw.to_csv(raw_dir / "NF-UNSW-NB15-v3.csv", index=False)
        self.root = str(self.temp_dir / "data" / "graphs")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_splits_windows_and_scaler(self):
        train, val, test = load_split_datasets(name="nf-unsw-nb15-v3", root=self.root, window_size=40, k=3)
        self.assertEqual(sum(g.num_nodes for g in train), 240)
        self.assertEqual(sum(g.num_nodes for g in val), 80)
        self.assertEqual(sum(g.num_nodes for g in test), 80)
        self.assertEqual([g.num_nodes for g in train], [40] * 6)

        # The scaler is the one fitted on train: train features have zero mean.
        train_x = np.concatenate([g.x.numpy() for g in train])
        np.testing.assert_allclose(train_x.mean(axis=0), 0.0, atol=1e-4)

        # Windows follow time order: test labels are the last 20% of time-sorted labels.
        sorted_df = load_netflow_v3(str(self.temp_dir / "data" / "raw" / "netflow-v3" / "NF-UNSW-NB15-v3.csv"))
        test_y = np.concatenate([g.y.numpy() for g in test])
        np.testing.assert_array_equal(test_y, sorted_df["Label"].to_numpy()[320:])

    def test_reconstruction_check_passes_with_duplicate_flows(self):
        _, _, test = load_split_datasets(name="nf-unsw-nb15-v3", root=self.root, window_size=40, k=3)
        report = check_reconstruction([test[i] for i in range(len(test))], k=3)
        self.assertEqual(report["mean_churn"], 0.0)
        self.assertEqual(report["exact_fraction"], 1.0)

    def test_time_slice_uses_its_own_cache_and_splits(self):
        _, _, test_full = load_split_datasets(name="nf-unsw-nb15-v3", root=self.root, window_size=20, k=3)
        train, val, test = load_split_datasets(
            name="nf-unsw-nb15-v3", root=self.root, window_size=20, k=3, max_flows=100, slice_start=0.5
        )
        self.assertEqual(sum(g.num_nodes for g in train) + sum(g.num_nodes for g in val)
                         + sum(g.num_nodes for g in test), 100)
        self.assertTrue((Path(self.root) / "nf-unsw-nb15-v3_100flows_from0.5" / "k_3").exists())
        self.assertEqual(sum(g.num_nodes for g in test_full), 80)


if __name__ == "__main__":
    unittest.main()
