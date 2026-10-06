#!/usr/bin/env python3
"""Check that the raw files and split indices needed by an experiment are present.

Usage (inside the container or a venv, from the repository root):
    python scripts/check_data.py                       # the paper's main dataset
    python scripts/check_data.py nf-unsw-nb15-v3 nf-ton-iot-v3

Datasets are not downloaded automatically. NetFlow-v3 CSVs come from
https://staff.itee.uq.edu.au/marius/NIDS_datasets/ and go in data/raw/netflow-v3/
(or point DATA_RAW at a directory with the same sub-folders).
The thesis datasets (cicids2017-*, nsl-kdd) are still recognised but not used by the paper.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data.download import CICIDS2017_SUBSETS  # noqa: E402

DEFAULT_DATASETS = ["nf-unsw-nb15-v3"]
NSL_KDD_FILES = ["KDDTrain+.txt", "KDDTest+.txt"]
NETFLOW_V3_FILES = {
    "nf-unsw-nb15-v3": "NF-UNSW-NB15-v3.csv",
    "nf-ton-iot-v3": "NF-ToN-IoT-v3.csv",
    "nf-cse-cic-ids2018-v3": "NF-CSE-CIC-IDS2018-v3.csv",
}


def check(dataset: str, root: Path) -> bool:
    ok = True
    if dataset.startswith("cicids2017"):
        raw_dir = root / "data" / "raw" / "cicids2017"
        files = CICIDS2017_SUBSETS.get(dataset)
        if files is None:
            print(f"  ? unknown CICIDS2017 subset '{dataset}'")
            return False
    elif dataset in NETFLOW_V3_FILES:
        raw_dir = root / "data" / "raw" / "netflow-v3"
        files = [NETFLOW_V3_FILES[dataset]]
    elif dataset == "nsl-kdd":
        raw_dir = root / "data" / "raw" / "nsl-kdd"
        files = NSL_KDD_FILES
    else:
        print(f"  ? unknown dataset '{dataset}'")
        return False

    print(f"{dataset}:")
    for name in files:
        path = raw_dir / name
        if path.exists():
            print(f"  ok       {path.relative_to(root)}  ({path.stat().st_size / 1e6:.1f} MB)")
        else:
            print(f"  MISSING  {path.relative_to(root)}")
            ok = False

    split_dir = root / "data" / "splits" / dataset
    if split_dir.exists() and any(split_dir.iterdir()):
        print(f"  ok       {split_dir.relative_to(root)}/ (fixed split indices, from the repository)")
    else:
        print(f"  note     {split_dir.relative_to(root)}/ missing: splits will be created on first run")
    return ok


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    datasets = sys.argv[1:] or DEFAULT_DATASETS
    results = [check(d, root) for d in datasets]
    if all(results):
        print("\nAll required raw files are present.")
        return 0
    print("\nSome raw files are missing. NetFlow-v3: download from "
          "https://staff.itee.uq.edu.au/marius/NIDS_datasets/ into data/raw/netflow-v3/ "
          "using the file names above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
