# Running experiments on the GPU servers

All experiments run inside the container defined in `docker/`. The code, the datasets and the results stay on the host. The container only provides the environment, so `git pull` updates the code without rebuilding the image.

## Requirements on each server

- Docker with Compose v2 (`docker compose version`).
- The NVIDIA Container Toolkit. Check it with `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`.
- A clone of `https://github.com/pedromamaral/GNN-nids.git`.
- The raw CICIDS2017 CSVs, as described in the next section.

## One-time setup on a server

```bash
git clone https://github.com/pedromamaral/GNN-nids.git gnn-nids && cd gnn-nids

# Raw data: either copy into data/raw/cicids2017/ ...
mkdir -p data/raw/cicids2017
scp otherhost:/path/to/MachineLearningCVE/*.csv data/raw/cicids2017/
# ... or keep it elsewhere and point DATA_RAW at it (it must contain cicids2017/)
export DATA_RAW=/data/datasets/raw

scripts/container.sh build          # ~10 min the first time (CUDA + PyTorch + PyG)
scripts/container.sh check-data     # lists missing raw files
scripts/container.sh test           # full test suite inside the container
```

CICIDS2017 comes from the UNB *MachineLearningCVE* CSVs (<https://www.unb.ca/cic/datasets/ids-2017.html>). Phase 1 needs three of them:
- `Tuesday-WorkingHours.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
- `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`

The split indices are versioned in `data/splits/`, so the train/val/test partition is identical on every server.

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
GPU=0 DATASETS=cicids2017-patator MODELS="gcn gat" scripts/container.sh -d phase1
GPU=1 DATASETS=cicids2017-selected MODELS="gcn gat" scripts/container.sh -d phase1
```

## Splitting Phase 1 across two servers

Each run writes its own timestamped directory, so results from different servers can simply be merged. Split by dataset, one per server or GPU:

| Server | Command |
|---|---|
| A (idle now) | `GPU=0 DATASETS=cicids2017-patator scripts/container.sh -d phase1` |
| B (when free) | `GPU=0 DATASETS=cicids2017-selected scripts/container.sh -d phase1` |

Afterwards, copy `results/runs/` and `results/decomposition/` from B to A and run `scripts/container.sh report`. Use `rsync -av serverB:gnn-nids/results/ results/`.

If only server A is available, run both datasets there, one per GPU if it has two, or one after the other.

## Reusing João's checkpoints

If João's trained models are available, copy his `results/runs/<run>/` directories into `results/runs/`. `run_phase1.sh` finds them by name, using the pattern `*_<dataset>_<model>_k_5_seed_<seed>`, and skips the training. The checkpoints carry metadata (k, seed), which `05_decomposition.py` validates.

## What to commit

Commit code and configuration only. `results/`, `logs/` and `data/raw|graphs/` are git-ignored.

Keep the result tables from `05b` by copying `results/decomposition/*.csv` into a dated folder outside the repository, or into the paper's shared folder.
