"""
Dataset download module for GNN Adversarial NIDS.

This module handles downloading NSL-KDD and validating manually placed
datasets (CICIDS2017, NetFlow-v3).
"""

import os
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List

from .netflow_v3 import NETFLOW_V3_DATASETS, NETFLOW_V3_RAW_SUBDIR

# Configure logging
logger = logging.getLogger(__name__)


# Explicit CICIDS2017 dataset variants mapping
# Each key maps to a list of required CSV filenames (placed under data/raw/cicids2017)
CICIDS2017_SUBSETS = {
    "cicids2017-ddos": [
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    ],
    "cicids2017-portscan": [
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    ],
    "cicids2017-patator": [
        "Tuesday-WorkingHours.pcap_ISCX.csv",
    ],
    "cicids2017-selected": [
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
        "Tuesday-WorkingHours.pcap_ISCX.csv",
    ],
}

# Every name accepted by --dataset: the paper's NetFlow-v3 sets first, then the thesis datasets.
DATASET_CHOICES = sorted(NETFLOW_V3_DATASETS) + ["nsl-kdd"] + sorted(CICIDS2017_SUBSETS)
DEFAULT_DATASET = "nf-unsw-nb15-v3"


class DatasetDownloader:
    """Downloads and validates NSL-KDD datasets."""

    # NSL-KDD dataset URLs
    NSL_KDD_URLS = {
        "KDDTrain+.txt": "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain+.txt",
        "KDDTest+.txt": "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest+.txt",
    }

    def __init__(self, base_dir: str = "data/raw/nsl-kdd"):
        """Initialize the downloader.

        Args:
            base_dir: Base directory to store downloaded datasets.
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DatasetDownloader initialized with base_dir: {self.base_dir}")

    def download_file(self, url: str, filename: str, force: bool = False) -> bool:
        """Download a single file from URL.

        Args:
            url: URL to download from.
            filename: Filename to save as.
            force: Force re-download if file exists.

        Returns:
            True if download successful, False otherwise.
        """
        filepath = self.base_dir / filename

        # Check if file already exists
        if filepath.exists() and not force:
            logger.info(f"File already exists: {filepath}")
            return True

        try:
            logger.info(f"Downloading {filename} from {url}...")
            urllib.request.urlretrieve(url, filepath)
            logger.info(f"Successfully downloaded: {filepath}")
            return True
        except urllib.error.URLError as e:
            logger.error(f"Failed to download {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            return False

    def validate_file(self, filename: str) -> bool:
        """Validate downloaded file.

        Args:
            filename: Filename to validate.

        Returns:
            True if file exists and has content, False otherwise.
        """
        filepath = self.base_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return False
        if filepath.stat().st_size == 0:
            logger.warning(f"File is empty: {filepath}")
            return False
        logger.info(f"File validation passed: {filepath}")
        return True

    def download_nsl_kdd(self, force: bool = False) -> bool:
        """Download NSL-KDD training and testing datasets.

        Args:
            force: Force re-download of existing files.

        Returns:
            True if both files downloaded successfully, False otherwise.
        """
        logger.info("Starting NSL-KDD download...")
        success = True

        for filename, url in self.NSL_KDD_URLS.items():
            if not self.download_file(url, filename, force):
                success = False
                logger.error(f"Failed to download {filename}")
            elif not self.validate_file(filename):
                success = False
                logger.error(f"Validation failed for {filename}")

        if success:
            logger.info("NSL-KDD download completed successfully")
        else:
            logger.warning("NSL-KDD download completed with errors")

        return success

    def download_cicids2017(
        self,
        base_dir: Optional[str] = None,
        subset_name: Optional[str] = None,
    ) -> bool:
        """Validate manual placement of CICIDS2017 CSV files.

        If `subset_name` is provided and matches a key in CICIDS2017_SUBSETS,
        only the required files for that subset are validated. Otherwise any
        CSV files present in the target directory are considered acceptable.

        Args:
            base_dir: Optional directory where CSV files are located.
                If not provided, uses self.base_dir.
            subset_name: Optional subset name to validate (e.g. 'cicids2017-ddos').

        Returns:
            True if required CSV file(s) exist, False otherwise.
        """
        target_dir = Path(base_dir) if base_dir else self.base_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        if subset_name:
            required = CICIDS2017_SUBSETS.get(subset_name)
            if required is None:
                logger.error(f"Unknown CICIDS2017 subset: {subset_name}")
                return False

            missing = [f for f in required if not (target_dir / f).exists()]
            if missing:
                logger.warning(
                    "Missing required CICIDS2017 CSV files for subset %s: %s",
                    subset_name,
                    missing,
                )
                return False

            logger.info(
                "All required CICIDS2017 CSV files for subset %s found in %s",
                subset_name,
                target_dir,
            )
            return True

        # Fallback: accept any CSV files
        csv_files = list(target_dir.glob("*.csv"))
        if len(csv_files) == 0:
            logger.warning(
                "No CICIDS2017 CSV files found in %s. "
                "Please download the CICIDS2017 CSV files manually and place them in this directory: %s",
                target_dir,
            )
            logger.info("Expected path pattern: data/raw/cicids2017/*.csv")
            logger.info(
                "Example: download CICIDS2017 from Kaggle, extract CSV files, "
                "and copy them into the target directory."
            )
            return False

        logger.info(
            "Found %d CICIDS2017 CSV file(s) in %s",
            len(csv_files),
            target_dir,
        )
        return True

    def download_netflow_v3(self, dataset_name: str, base_dir: Optional[str] = None) -> bool:
        """Validate manual placement of a NetFlow-v3 CSV.

        The files are not downloaded automatically (UQ deposit terms). Get them
        from https://staff.itee.uq.edu.au/marius/NIDS_datasets/ and save them
        under data/raw/netflow-v3/ with the names in NETFLOW_V3_DATASETS.

        Args:
            dataset_name: One of NETFLOW_V3_DATASETS (e.g. 'nf-unsw-nb15-v3').
            base_dir: Directory holding the CSV. Defaults to self.base_dir.

        Returns:
            True if the CSV exists and is not empty, False otherwise.
        """
        filename = NETFLOW_V3_DATASETS.get(dataset_name)
        if filename is None:
            logger.error(f"Unknown NetFlow-v3 dataset: {dataset_name}")
            return False
        path = (Path(base_dir) if base_dir else self.base_dir) / filename
        if not path.exists() or path.stat().st_size == 0:
            logger.warning(
                "NetFlow-v3 file missing or empty: %s. Download it from "
                "https://staff.itee.uq.edu.au/marius/NIDS_datasets/ and save it as %s/%s.",
                path, f"data/raw/{NETFLOW_V3_RAW_SUBDIR}", filename,
            )
            return False
        logger.info(f"NetFlow-v3 file found: {path}")
        return True

    def download_all(self, force: bool = False) -> bool:
        """Download all available datasets.

        Args:
            force: Force re-download of existing files.

        Returns:
            True if all downloads successful, False otherwise.
        """
        logger.info("Starting download of all datasets...")
        success = self.download_nsl_kdd(force=force)
        cicids_success = DatasetDownloader(base_dir=Path(self.base_dir).parent / "cicids2017").download_cicids2017()
        return success and cicids_success

    def get_dataset_path(self, dataset_name: str) -> Optional[Path]:
        """Get path to a downloaded dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Path to dataset if it exists, None otherwise.
        """
        filepath = self.base_dir / dataset_name
        if filepath.exists():
            return filepath
        logger.warning(f"Dataset not found: {dataset_name}")
        return None

    def list_datasets(self) -> List[str]:
        """List all available downloaded datasets.

        Returns:
            List of dataset filenames.
        """
        datasets = [f.name for f in self.base_dir.glob("*.txt")] + [f.name for f in self.base_dir.glob("*.csv")]
        logger.info(f"Found {len(datasets)} datasets")
        return datasets


if __name__ == "__main__":
    # Setup logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Example usage
    downloader = DatasetDownloader()
    success = downloader.download_nsl_kdd()
    if success:
        datasets = downloader.list_datasets()
        print(f"Available datasets: {datasets}")
