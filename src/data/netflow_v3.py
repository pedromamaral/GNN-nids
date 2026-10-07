"""
NetFlow-v3 datasets (University of Queensland) for the paper.

Source: https://staff.itee.uq.edu.au/marius/NIDS_datasets/
Reference: Luay et al., "Temporal Analysis of NetFlow Datasets for Network
Intrusion Detection Systems", arXiv:2503.04404.

All NetFlow-v3 datasets share the same 53 NetFlow features plus ``Label``
(binary) and ``Attack`` (class name). This module:

- loads one CSV, sorted by ``FLOW_START_MILLISECONDS`` (stable, so ties keep
  file order), optionally keeping only a contiguous time slice;
- drops identifiers and timestamps from the features;
- log-transforms the heavy-tailed counters and standardises with statistics
  fitted on the training split only.

The chronological split itself lives in ``splits.chronological_split``.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Dataset name -> file name under data/raw/netflow-v3/
NETFLOW_V3_DATASETS: Dict[str, str] = {
    "nf-unsw-nb15-v3": "NF-UNSW-NB15-v3.csv",
    "nf-ton-iot-v3": "NF-ToN-IoT-v3.csv",
    "nf-cse-cic-ids2018-v3": "NF-CSE-CIC-IDS2018-v3.csv",
}
NETFLOW_V3_RAW_SUBDIR = "netflow-v3"

TIME_COLUMN = "FLOW_START_MILLISECONDS"
LABEL_COLUMN = "Label"
ATTACK_COLUMN = "Attack"

# Never used as features: they identify hosts or positions in time rather than
# describing the flow. DNS_QUERY_ID is a random transaction identifier.
IDENTIFIER_COLUMNS = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT", "DNS_QUERY_ID"]
TIMESTAMP_COLUMNS = ["FLOW_START_MILLISECONDS", "FLOW_END_MILLISECONDS"]

# Testbed artefacts, also never used as features. TTL encodes the hop distance
# of the capture hosts rather than the behaviour of the flow: on
# NF-UNSW-NB15-v3, MIN_TTL alone reaches test F1 0.999 (TTL 31 is always
# benign, 62 always an attack). An attacker also sets the initial TTL of its
# own packets, so it would be a trivial evasion route. See the decision log in
# docs/PAPER_ROADMAP.md (2026-10-07).
ARTEFACT_COLUMNS = ["MIN_TTL", "MAX_TTL"]

# Codes, flags and bounded values: kept on their original scale. Every other
# feature is a non-negative counter, size, duration, rate or IAT and gets log1p.
NON_LOG_COLUMNS = {
    "PROTOCOL",
    "L7_PROTO",
    "TCP_FLAGS",
    "CLIENT_TCP_FLAGS",
    "SERVER_TCP_FLAGS",
    "TCP_WIN_MAX_IN",
    "TCP_WIN_MAX_OUT",
    "ICMP_TYPE",
    "ICMP_IPV4_TYPE",
    "DNS_QUERY_TYPE",
    "FTP_COMMAND_RET_CODE",
}


def is_netflow_v3(name: str) -> bool:
    return name in NETFLOW_V3_DATASETS


def dataset_variant_id(name: str, max_flows: Optional[int] = None, slice_start: Optional[float] = None) -> str:
    """Directory-safe identifier of a dataset plus its time slice.

    The full dataset keeps its plain name, so caches and split indices of a
    slice never collide with those of the full dataset.
    """
    if max_flows is None and not slice_start:
        return name
    parts = [name]
    if max_flows is not None:
        parts.append(f"{int(max_flows)}flows")
    if slice_start:
        parts.append(f"from{float(slice_start):g}")
    return "_".join(parts)


def feature_columns(columns: List[str]) -> List[str]:
    """Feature columns of a NetFlow-v3 header, in file order."""
    excluded = (
        set(IDENTIFIER_COLUMNS) | set(TIMESTAMP_COLUMNS) | set(ARTEFACT_COLUMNS) | {LABEL_COLUMN, ATTACK_COLUMN}
    )
    return [c for c in columns if c not in excluded]


def load_netflow_v3(
    path: str,
    max_flows: Optional[int] = None,
    slice_start: Optional[float] = None,
    chunksize: int = 1_000_000,
) -> pd.DataFrame:
    """Load a NetFlow-v3 CSV sorted by flow start time.

    Args:
        path: CSV file.
        max_flows: Keep only this many flows, contiguous in time (None: all).
        slice_start: Where the slice starts, as a fraction of the time-sorted
            flows (0.0 = earliest). Ignored when ``max_flows`` is None.
        chunksize: Rows read at a time, to bound peak memory on large files.

    Returns:
        DataFrame with the feature columns, ``FLOW_START_MILLISECONDS``,
        ``Label`` and ``Attack``, in chronological order, index 0..n-1.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"NetFlow-v3 file not found: {path}")
    if slice_start is not None and not 0.0 <= slice_start < 1.0:
        raise ValueError(f"slice_start must be in [0, 1), got {slice_start}")
    if max_flows is not None and max_flows < 1:
        raise ValueError(f"max_flows must be positive, got {max_flows}")

    header = pd.read_csv(path, nrows=0).columns.tolist()
    missing = [c for c in (TIME_COLUMN, LABEL_COLUMN, ATTACK_COLUMN) if c not in header]
    if missing:
        raise ValueError(f"{path.name} is not a NetFlow-v3 file: missing columns {missing}")
    features = feature_columns(header)

    # Pass 1: timestamps only, to choose the rows and their chronological order.
    times = pd.read_csv(path, usecols=[TIME_COLUMN], dtype={TIME_COLUMN: np.int64})[TIME_COLUMN].to_numpy()
    n_total = times.size
    order = np.argsort(times, kind="stable")
    start = 0
    stop = n_total
    if max_flows is not None:
        start = int(round((slice_start or 0.0) * n_total))
        stop = min(n_total, start + int(max_flows))
    selected = order[start:stop]
    rank = np.full(n_total, -1, dtype=np.int64)
    rank[selected] = np.arange(selected.size)

    # Pass 2: the selected rows, chunk by chunk.
    usecols = features + [TIME_COLUMN, LABEL_COLUMN, ATTACK_COLUMN]
    dtypes = {c: np.float64 for c in features}
    dtypes.update({TIME_COLUMN: np.int64, LABEL_COLUMN: np.int64, ATTACK_COLUMN: str})
    parts = []
    for chunk in pd.read_csv(path, usecols=usecols, dtype=dtypes, chunksize=chunksize):
        chunk_rank = rank[chunk.index.to_numpy()]
        keep = chunk_rank >= 0
        if keep.any():
            part = chunk.loc[keep, usecols]
            part.index = chunk_rank[keep]
            parts.append(part)
    df = pd.concat(parts).sort_index()
    df.index = pd.RangeIndex(len(df))

    logger.info(
        "Loaded %d of %d flows from %s (time-sorted, rows %d..%d), attack fraction %.4f",
        len(df), n_total, path.name, start, stop - 1, float(df[LABEL_COLUMN].mean()),
    )
    return df


class NetFlowV3Preprocessor:
    """Feature pipeline for NetFlow-v3: clean, log-transform, standardise.

    ``preprocess(df, fit=True)`` must be called on the training split only;
    validation and test reuse the fitted state.
    """

    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: Optional[List[str]] = None
        self.posinf_fill: Optional[np.ndarray] = None
        logger.info("NetFlowV3Preprocessor initialized")

    def _log_mask(self) -> np.ndarray:
        return np.array([c not in NON_LOG_COLUMNS for c in self.feature_names])

    def transform_raw(self, df: pd.DataFrame, fit: bool) -> np.ndarray:
        """Everything except the scaler: non-finite values and log1p.

        ``+inf`` (rates over zero duration) becomes the largest finite training
        value of the column; NaN (empty fields) becomes 0.
        """
        if fit:
            self.feature_names = feature_columns(df.columns.tolist())
        elif self.feature_names is None:
            raise ValueError("Preprocessor not fitted. Call preprocess(fit=True) on the training split first.")

        X = df[self.feature_names].to_numpy(dtype=np.float64, copy=True)
        if fit:
            finite = np.where(np.isfinite(X), X, np.nan)
            with np.errstate(all="ignore"):
                fill = np.nanmax(finite, axis=0)
            self.posinf_fill = np.nan_to_num(fill, nan=0.0)
        posinf = np.isposinf(X)
        if posinf.any():
            X[posinf] = np.broadcast_to(self.posinf_fill, X.shape)[posinf]
        X[~np.isfinite(X)] = 0.0

        log_mask = self._log_mask()
        X[:, log_mask] = np.log1p(np.maximum(X[:, log_mask], 0.0))
        return X

    def preprocess(self, df: pd.DataFrame, fit: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        X = self.transform_raw(df, fit=fit)
        if fit:
            self.scaler = StandardScaler()
            X = self.scaler.fit_transform(X)
            logger.info("Fitted StandardScaler on %d NetFlow-v3 features (%d flows)", X.shape[1], X.shape[0])
        else:
            if self.scaler is None:
                raise ValueError("Scaler not fitted. Call preprocess(fit=True) on the training split first.")
            X = self.scaler.transform(X)
        y = df[LABEL_COLUMN].to_numpy(dtype=np.int64)
        return X.astype(np.float32), y

    def get_state(self) -> dict:
        return {
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "posinf_fill": self.posinf_fill,
        }

    def load_preprocessed(self, state_path: str) -> None:
        # Pickle, like the other preprocessors: the state is written by this
        # code when the training split is processed, never downloaded.
        with open(state_path, "rb") as f:
            state = pickle.load(f)
        self.scaler = state["scaler"]
        self.feature_names = state["feature_names"]
        self.posinf_fill = state["posinf_fill"]
        logger.info("Loaded NetFlow-v3 preprocessor state from %s", state_path)
