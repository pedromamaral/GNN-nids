#!/usr/bin/env python3
"""Check that the raw files and split indices needed by an experiment are present.

Usage (inside the container or a venv, from the repository root):
    python scripts/check_data.py                       # Phase 1 defaults
    python scripts/check_data.py cicids2017-ddos nsl-kdd

CICIDS2017 is not downloaded automatically. Get the "MachineLearningCVE" CSVs
from https://www.unb.ca/cic/datasets/ids-2017.html and place them in
data/raw/cicids2017/ (or point DATA_RAW at the directory that holds them).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data.download import CICIDS2017_SUBSETS  # noqa: E402

PHASE1_DEFAULT = ["cicids2017-selected", "cicids2017-patator"]
NSL_KDD_FILES = ["KDDTrain+.txt", "KDDTest+.txt"]


def check(dataset: str, root: Path) -> bool:
    ok = True
    if dataset.startswith("cicids2017"):
        raw_dir = root / "data" / "raw" / "cicids2017"
        files = CICIDS2017_SUBSETS.get(dataset)
        if files is None:
            print(f"  ? unknown CICIDS2017 subset '{dataset}'")
            return False
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
    datasets = sys.argv[1:] or PHASE1_DEFAULT
    results = [check(d, root) for d in datasets]
    if all(results):
        print("\nAll required raw files are present.")
        return 0
    print("\nSome raw files are missing. CICIDS2017: download the MachineLearningCVE CSVs from "
          "https://www.unb.ca/cic/datasets/ids-2017.html into data/raw/cicids2017/.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
