"""
CTU-13 botnet captures (Stratosphere Lab, CVUT Prague; Garcia et al., 2014).

Source: https://mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/ (only the
``*.binetflow`` files are needed; the archive also contains malware samples,
which are not extracted).

Each scenario is one Argus bidirectional NetFlow capture of the same campus
network with one botnet running. Labels in the files:

- ``From-Botnet``: any flow from an infected lab host (the label is defined by
  host identity, so models must not see IPs; endpoint graphs relabel nodes);
- ``From-Normal`` / ``To-Normal`` / ``Normal-*``: verified clean lab hosts;
- ``Background``: the remaining campus traffic, unverified. Treated as benign
  by default (common practice; it adds label noise), or dropped.

Splits are scenario-disjoint (``CTU13_DEFAULT_SPLIT``): test scenarios are new
runs of botnet families seen in training (Neris, Rbot, Virut), validation adds
an unseen family (NSIS.ay). Flows are sorted by start time within each scenario,
and graphs are windowed per scenario. Infected IPs are reused across scenarios
(e.g. 147.32.84.165), so the split separates captures, not hosts; identities are
hidden from the models instead.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from .netflow_v3 import DST_IP, DST_PORT, SRC_IP, SRC_PORT, ipv4_to_int

logger = logging.getLogger(__name__)

CTU13_NAME = "ctu13"
CTU13_RAW_SUBDIR = "ctu13/CTU-13-Dataset"

# Scenario -> (file, botnet family), from the dataset READMEs.
CTU13_SCENARIOS: Dict[int, Tuple[str, str]] = {
    1: ("capture20110810.binetflow", "Neris"),
    2: ("capture20110811.binetflow", "Neris"),
    3: ("capture20110812.binetflow", "Rbot"),
    4: ("capture20110815.binetflow", "Rbot"),
    5: ("capture20110815-2.binetflow", "Virut"),
    6: ("capture20110816.binetflow", "Menti"),
    7: ("capture20110816-2.binetflow", "Sogou"),
    8: ("capture20110816-3.binetflow", "Murlo"),
    9: ("capture20110817.binetflow", "Neris"),
    10: ("capture20110818.binetflow", "Rbot"),
    11: ("capture20110818-2.binetflow", "Rbot"),
    12: ("capture20110819.binetflow", "NSIS.ay"),
    13: ("capture20110815-3.binetflow", "Virut"),
}
CTU13_DEFAULT_SPLIT: Dict[str, List[int]] = {
    "train": [1, 2, 3, 4, 5, 6, 7, 8],
    "validation": [11, 12],
    "test": [9, 10, 13],
}

TIME_COLUMN = "START_MS"
LABEL_COLUMN = "Label"
ATTACK_COLUMN = "Attack"      # label category: Botnet / Normal / Background
SCENARIO_COLUMN = "Scenario"

PROTOCOLS = ["tcp", "udp", "icmp"]
DIRECTIONS = ["<->", "->", "<-", "<?>"]
TCP_FLAGS = "FSPAURCE"
NON_TCP_STATES = ["CON", "INT"]


def _parse_hex(value: str) -> int:
    try:
        return int(value, 16)
    except ValueError:
        return -1


def scenario_path(raw_dir: str, scenario: int) -> Path:
    return Path(raw_dir) / str(scenario) / CTU13_SCENARIOS[scenario][0]


def _label_category(labels: pd.Series) -> np.ndarray:
    text = labels.astype(str).str.replace("flow=", "", regex=False)
    category = np.full(len(text), "Background", dtype=object)
    category[text.str.contains("Botnet", regex=False).to_numpy()] = "Botnet"
    category[text.str.contains("Normal", regex=False).to_numpy() & (category == "Background")] = "Normal"
    return category


def load_ctu13(
    raw_dir: str,
    scenarios: Sequence[int],
    background: str = "benign",
    with_endpoints: bool = False,
) -> pd.DataFrame:
    """Load CTU-13 scenarios, each sorted by start time, concatenated in the given order.

    Returns the raw fields needed by ``Ctu13Preprocessor`` plus ``START_MS``,
    ``Label`` (1 = botnet), ``Attack`` (Botnet/Normal/Background) and
    ``Scenario``; with ``with_endpoints`` also SRC_IP/SRC_PORT/DST_IP/DST_PORT.
    """
    if background not in ("benign", "drop"):
        raise ValueError("background must be 'benign' or 'drop'")
    frames = []
    for scenario in scenarios:
        path = scenario_path(raw_dir, scenario)
        if not path.exists():
            raise FileNotFoundError(f"CTU-13 scenario {scenario} not found: {path}")
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df.columns = [c.strip() for c in df.columns]
        out = pd.DataFrame({
            TIME_COLUMN: (pd.to_datetime(df["StartTime"], format="%Y/%m/%d %H:%M:%S.%f").astype("int64") // 1_000_000),
            "Dur": pd.to_numeric(df["Dur"], errors="coerce"),
            "Proto": df["Proto"].str.strip().str.lower(),
            "Dir": df["Dir"].str.strip(),
            "State": df["State"].str.strip(),
            "sTos": pd.to_numeric(df["sTos"], errors="coerce"),
            "dTos": pd.to_numeric(df["dTos"], errors="coerce"),
            "TotPkts": pd.to_numeric(df["TotPkts"], errors="coerce"),
            "TotBytes": pd.to_numeric(df["TotBytes"], errors="coerce"),
            "SrcBytes": pd.to_numeric(df["SrcBytes"], errors="coerce"),
        })
        out[ATTACK_COLUMN] = _label_category(df["Label"])
        out[LABEL_COLUMN] = (out[ATTACK_COLUMN] == "Botnet").astype(np.int64)
        out[SCENARIO_COLUMN] = scenario
        if with_endpoints:
            out[SRC_IP] = ipv4_to_int(df["SrcAddr"])
            out[DST_IP] = ipv4_to_int(df["DstAddr"])
            # Ports may be hex (ICMP type/code) or empty; they only define endpoints.
            for col, src in ((SRC_PORT, "Sport"), (DST_PORT, "Dport")):
                text = df[src].str.strip()
                port = pd.to_numeric(text, errors="coerce")
                is_hex = text.str.startswith("0x")
                port[is_hex] = text[is_hex].apply(_parse_hex)
                out[col] = port.fillna(-1).astype(np.int64)
        if background == "drop":
            out = out[out[ATTACK_COLUMN] != "Background"]
        out = out.sort_values(TIME_COLUMN, kind="stable")
        frames.append(out)
        logger.info("CTU-13 scenario %d (%s): %d flows, botnet fraction %.4f",
                    scenario, CTU13_SCENARIOS[scenario][1], len(out), float(out[LABEL_COLUMN].mean()))
    return pd.concat(frames, ignore_index=True)


def scenario_segments(df: pd.DataFrame) -> List[Tuple[int, int]]:
    """[start, stop) row ranges of consecutive scenarios, for per-scenario windowing."""
    values = df[SCENARIO_COLUMN].to_numpy()
    if values.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(values)) + 1
    bounds = np.concatenate([[0], cuts, [values.size]])
    return [(int(a), int(b)) for a, b in zip(bounds[:-1], bounds[1:])]


class Ctu13Preprocessor:
    """Argus fields -> 36 numeric features; scaler fitted on the training scenarios only."""

    LOG_FIELDS = ["Dur", "TotPkts", "TotBytes", "SrcBytes"]

    def __init__(self):
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: Optional[List[str]] = None

    @staticmethod
    def raw_features(df: pd.DataFrame) -> pd.DataFrame:
        out = {}
        for col in Ctu13Preprocessor.LOG_FIELDS:
            out[f"log_{col}"] = np.log1p(df[col].fillna(0).clip(lower=0).to_numpy(dtype=np.float64))
        dst_bytes = (df["TotBytes"].fillna(0) - df["SrcBytes"].fillna(0)).clip(lower=0)
        out["log_DstBytes"] = np.log1p(dst_bytes.to_numpy(dtype=np.float64))
        pkts = df["TotPkts"].fillna(0).clip(lower=1)
        out["log_BytesPerPkt"] = np.log1p((df["TotBytes"].fillna(0) / pkts).to_numpy(dtype=np.float64))
        out["sTos"] = df["sTos"].fillna(0).to_numpy(dtype=np.float64)
        out["dTos"] = df["dTos"].fillna(0).to_numpy(dtype=np.float64)
        proto = df["Proto"]
        for p in PROTOCOLS:
            out[f"proto_{p}"] = (proto == p).to_numpy(dtype=np.float64)
        out["proto_other"] = (~proto.isin(PROTOCOLS)).to_numpy(dtype=np.float64)
        direction = df["Dir"]
        for d in DIRECTIONS:
            out[f"dir_{d}"] = (direction == d).to_numpy(dtype=np.float64)
        out["dir_other"] = (~direction.isin(DIRECTIONS)).to_numpy(dtype=np.float64)
        state = df["State"]
        is_tcp = (proto == "tcp").to_numpy()
        sides = state.str.split("_", n=1, expand=True).reindex(columns=[0, 1]).fillna("")
        for side, label in ((0, "src"), (1, "dst")):
            text = sides[side]
            for flag in TCP_FLAGS:
                out[f"tcp_{label}_{flag}"] = (text.str.contains(flag, regex=False).to_numpy() & is_tcp).astype(np.float64)
        for s in NON_TCP_STATES:
            out[f"state_{s}"] = ((state == s).to_numpy() & ~is_tcp).astype(np.float64)
        out["state_other"] = (~state.isin(NON_TCP_STATES).to_numpy() & ~is_tcp).astype(np.float64)
        return pd.DataFrame(out)

    def preprocess(self, df: pd.DataFrame, fit: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        raw = self.raw_features(df)
        if fit:
            self.feature_names = list(raw.columns)
            self.scaler = StandardScaler()
            X = self.scaler.fit_transform(raw.to_numpy())
            logger.info("Fitted StandardScaler on %d CTU-13 features (%d flows)", X.shape[1], X.shape[0])
        else:
            if self.scaler is None:
                raise ValueError("Scaler not fitted. Call preprocess(fit=True) on the training scenarios first.")
            X = self.scaler.transform(raw[self.feature_names].to_numpy())
        return X.astype(np.float32), df[LABEL_COLUMN].to_numpy(dtype=np.int64)

    def get_state(self) -> dict:
        return {"scaler": self.scaler, "feature_names": self.feature_names}

    def load_preprocessed(self, state_path: str) -> None:
        # Pickle, like the other preprocessors: written by this code, never downloaded.
        with open(state_path, "rb") as f:
            state = pickle.load(f)
        self.scaler = state["scaler"]
        self.feature_names = state["feature_names"]
