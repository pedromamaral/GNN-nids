# Running experiments on the GPU servers

All experiments run inside the container defined in `docker/`. The code, the datasets and the results stay on the host. The container only provides the environment, so `git pull` updates the code without rebuilding the image.

## Requirements on each server

- Docker with Compose v2 (`docker compose version`).
- The NVIDIA Container Toolkit. Check it with `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`.
- A clone of `https://github.com/pedromamaral/GNN-nids.git`.
- The raw NetFlow-v3 CSVs, as described in the next section.

## One-time setup on a server

```bash
git clone https://github.com/pedromamaral/GNN-nids.git gnn-nids && cd gnn-nids

# Raw data: either copy into data/raw/netflow-v3/ ...
mkdir -p data/raw/netflow-v3
scp laptop:/path/to/NF-UNSW-NB15-v3.csv data/raw/netflow-v3/
# ... or keep it on a data disk and point DATA_RAW at it (it must contain netflow-v3/)
export DATA_RAW=/data/datasets/raw

scripts/container.sh build          # ~10 min the first time (CUDA + PyTorch + PyG)
scripts/container.sh check-data     # lists missing raw files
scripts/container.sh test           # full test suite inside the container
```

The paper uses only the NetFlow-v3 datasets from the University of Queensland (<https://staff.itee.uq.edu.au/marius/NIDS_datasets/>). They are open access under UQ's deposit terms. Save them under these exact names:

| File in `data/raw/netflow-v3/` | Source |
|---|---|
| `NF-UNSW-NB15-v3.csv` (2.4 M flows; start here) | UQ portal, NF-UNSW-NB15-v3 |
| `NF-ToN-IoT-v3.csv` (27.5 M flows) | <https://espace.library.uq.edu.au/view/UQ:44d7c5e> |
| `NF-CSE-CIC-IDS2018-v3.csv` (20.1 M flows, optional) | <https://espace.library.uq.edu.au/view/UQ:ece9b83> |

Optionally, the CTU-13 `.binetflow` files (<https://www.stratosphereips.org/datasets-ctu13>) go in `data/raw/ctu13/`. NSL-KDD and CICIDS2017 (the thesis datasets) are not used by the paper.

The experiments take these names with `--dataset`. Flows are sorted by `FLOW_START_MILLISECONDS` and split chronologically 60/20/20 (train is the earliest block), so no split indices need to be copied between servers. For a large file, `--max-flows N [--slice-start F]` on `00`–`05` uses N time-contiguous flows starting at fraction F of the timeline. `01` records the slice in the checkpoint, and `05` reuses it.

Non-graph baselines on the same flows and splits:

```bash
GPU=0 scripts/container.sh -d run python experiments/00_tabular_baselines.py --dataset nf-unsw-nb15-v3
```

## Running a job

Run one job per GPU. `GPU=n` selects the host GPU, and each GPU gets its own Compose project, so jobs on different GPUs do not collide.

```bash
GPU=0 scripts/container.sh smoke         # ~5–15 min end-to-end check (throwaway seed 99, results/smoke/)
GPU=0 scripts/container.sh -d phase1     # full Phase 1 in the background
docker logs -f <name printed by the command>    # or: tail -f logs/<name>.log
GPU=0 scripts/container.sh report        # go/no-go table once the runs finish
GPU=0 scripts/container.sh shell         # interactive shell for anything else
```

`phase1` runs `scripts/run_phase1.sh`. For every dataset × model × training seed, it does the following:
1. It looks for a checkpoint in `results/runs/`.
2. If none exists, it trains one, because `TRAIN_MISSING=1` is the default inside the wrapper.
3. It runs `experiments/05_decomposition.py` with 5 attack seeds.
4. When all runs are done, it aggregates the results with `05b_decomposition_report.py`.

Narrow or split the grid with environment variables:

```bash
GPU=0 DATASETS=nf-unsw-nb15-v3 MODELS="gcn gat" scripts/container.sh -d phase1
GPU=1 DATASETS=nf-ton-iot-v3 MODELS="gcn gat" scripts/container.sh -d phase1
```

## Splitting the decomposition grid across two servers

Each run writes its own timestamped directory, so results from different servers can simply be merged. Split by dataset, one per server or GPU:

| Server | Command |
|---|---|
| A (idle now) | `GPU=0 DATASETS=nf-unsw-nb15-v3 scripts/container.sh -d phase1` |
| B (when free) | `GPU=0 DATASETS=nf-ton-iot-v3 scripts/container.sh -d phase1` |

Afterwards, copy `results/runs/` and `results/decomposition/` from B to A and run `scripts/container.sh report`. Use `rsync -av serverB:gnn-nids/results/ results/`.

If only server A is available, run both datasets there, one per GPU if it has two, or one after the other.

## What to commit

Commit code and configuration only. `results/`, `logs/` and `data/raw|graphs/` are git-ignored.

Keep the result tables from `05b` by copying `results/decomposition/*.csv` into a dated folder outside the repository, or into the paper's shared folder.
