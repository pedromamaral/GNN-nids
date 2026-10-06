# Paper roadmap: from thesis to journal

Working title: *Feature Perturbations Are Structural Perturbations: Adversarial Coupling and Robust Graph Construction in Flow-Centric GNN-based Intrusion Detection*

Target venue: *Computers & Security* (fallbacks: IEEE TNSM, Computer Networks, JNCA).
Full rationale: `Q1_Strategy_GNN-NIDS.md` (supervisor's folder / project).

The thesis code is frozen at tag `v1.0-thesis` (`79d3ed0`). Everything after it is paper work.

## The claim

The graph of a flow-centric NIDS is the k-NN graph of the flow features, rebuilt at inference. A feature-space perturbation `X → X_adv` therefore also changes the graph, `E → E_rec = kNN(X_adv)`. Adversarial-GNN taxonomies treat feature and structure attacks as independent, but here they are not.

The thesis evaluated every feature attack on the **original** graph, i.e. condition A below. It never evaluated the graph the defender would actually build.

| Condition | Features | Graph | Measures |
|---|---|---|---|
| clean | X | E | reference |
| A | X_adv | E | pure feature effect (what fixed-graph evaluation reports) |
| B | X | E_rec | pure induced-structure effect |
| C | X_adv | E_rec | deployment, non-adaptive attacker |
| C* | X*_adv | kNN(X*_adv) | deployment, construction-aware attacker (`pgd_rebuild`) |

## Phases and status

### Phase 0: setup (week 1)
- [x] Read GIANT (WWW 2026, doi:10.1145/3774904.3792601). It targets address-derived graphs only (endpoint/host/line) and is injection-only; feature-derived k-NN graphs are not covered. Novelty confirmed 2026-10-06.
- [ ] Agree authorship and reuse with João; collect his trained checkpoints and `results/` from the server.
- [x] Thesis code tagged `v1.0-thesis`; test suite fixed (edge addition degrades instead of crashing).

### Phase 1: NetFlow-v3 data and temporal protocol (weeks 1–3) ← **current**
Datasets for the paper: **NF-UNSW-NB15-v3** (develop and test on this one first) and **NF-ToN-IoT-v3**, plus NF-CSE-CIC-IDS2018-v3 if compute allows; CTU-13 is optional, for comparison with Galli/Venturi. NSL-KDD and CICIDS2017 are **not** used (decision 2026-10-06). Raw files go in `data/raw/netflow-v3/` as `NF-UNSW-NB15-v3.csv`, `NF-ToN-IoT-v3.csv`, `NF-CSE-CIC-IDS2018-v3.csv` (see `docs/RUNNING_ON_SERVERS.md`).
- [ ] NetFlow-v3 loader (`src/data/netflow_v3.py`), dataset names `nf-unsw-nb15-v3`, `nf-ton-iot-v3`, `nf-cse-cic-ids2018-v3`.
  - Source: <https://staff.itee.uq.edu.au/marius/NIDS_datasets/>. Cite Luay et al., arXiv:2503.04404.
  - Drop identifiers (`IPV4_SRC_ADDR`, `IPV4_DST_ADDR`, `L4_SRC_PORT`, `L4_DST_PORT`) and timestamps from the features.
  - Log-transform heavy-tailed counters; standardise with statistics from the training split only.
  - Label = `Label`; keep `Attack` for per-class analysis.
  - Large sets: a contiguous time slice (configurable size), never random rows, because random rows would break the windows.
- [ ] Register the new names wherever datasets are hard-coded: `download.py`, `dataset.py`, `splits.py`, the `--dataset` choices of `01`–`05`, `scripts/check_data.py` (already knows the file names).
- [ ] Temporal protocol (`src/data/splits.py`):
  - Sort by `FLOW_START_MILLISECONDS`.
  - Chronological 60/20/20 split.
  - Windows of temporally contiguous flows, with no shuffle before windowing.
  - Fit the scaler on train only.
- [ ] Non-graph baselines (`experiments/00_tabular_baselines.py`): XGBoost and MLP on the same features and splits, 5 seeds.
- [ ] Tests for the loader and the split; `05_decomposition.py` reconstruction check passes on NF-UNSW-NB15-v3.

### Phase 2: decomposition, the go/no-go test (weeks 3–5)
Code ready (written before the dataset decision; it works on any dataset the loader provides):
- [x] `src/attacks/construction_aware.py`: `construction_aware_pgd` rebuilds the k-NN graph at every PGD step.
- [x] `src/analysis/decomposition.py`: A/B/C conditions, reconstruction sanity check, effect arithmetic.
- [x] `experiments/05_decomposition.py`: one checkpoint × attack seeds × {fgsm, pgd, pgd_rebuild} × ε × {A, B, C}.
- [x] `experiments/05b_decomposition_report.py`: mean ± std, effects, Wilcoxon go/no-go.
- [x] `scripts/run_phase1.sh` + `scripts/container.sh phase1`: batch runner (finds or trains checkpoints).

To do:
- [ ] Run on NF-UNSW-NB15-v3, GCN and GAT, ε ∈ {0.05, 0.10}, 5 training × 5 attack seeds.
- [ ] Decision recorded below. If GO, repeat on NF-ToN-IoT-v3 in Phase 3.

**Go/no-go rule.** The decision is GO if, in at least one scenario, either test passes consistently across seeds (one-sided Wilcoxon, p < 0.05):
1. Condition B of `pgd` degrades F1 by at least 0.05 (induced structure hurts on its own).
2. F1(`pgd`, A) − F1(`pgd_rebuild`, C) is at least 0.03 (fixed-graph evaluation misjudges the deployed system).

If neither test passes anywhere, switch to the fallback paper (construction-as-defence + protocol, conference-level). See strategy §9.

### Phase 3: full decomposition and constraints (weeks 7–10)
- [ ] Decomposition grid on all NetFlow-v3 datasets, 1 and 2 layers (`--hidden-layers 2` in `01_baseline_training.py`).
- [ ] Constrained attack. Attacker-controllable feature mask (the `feature_mask=` argument already exists in `fgsm_attack`, `pgd_attack` and `construction_aware_pgd`):
  - Controllable: packet counts and sizes, durations, IATs, TCP flags of the attacker's own direction.
  - Not controllable: protocol, ports, destination-side counters.
  - Add a validity projection: non-negativity and integrality in raw units, then re-standardise.
- [ ] Report unconstrained (upper bound) and constrained side by side.

### Phase 4: construction as a training-free defence (weeks 11–15)
- [ ] `FlowGraphBuilder.build_knn_graph`: add `min_similarity` (drop neighbours below τ) and `max_in_degree` (cap how many flows can point to one node). Add both to the dataset cache key and the checkpoint metadata.
- [ ] Sweep k ∈ {3, 5, 10, 15, 20} × {plain, threshold, degree cap} (× cosine/euclidean). Plot clean F1 against F1 under C* (Pareto front).
- [ ] PGD adversarial-training baseline (in the trainer, condition A examples). Compare at equal clean F1.
- [ ] Optional, 3 days max: per-node neighbour churn as an evasion detector (ROC). Drop it if AUC < 0.85.

### Phase 5: writing (weeks 16–22)
- [ ] Draft (compress thesis Ch. 2, 5, 7.2), figures from `05b` tables, internal review, submit.

## Running the decomposition (Phase 2)

Dataset names below assume the Phase 1 loader; until it lands, only the thesis datasets are accepted by the scripts.

On the GPU servers, use the container wrapper. `docs/RUNNING_ON_SERVERS.md` covers setup, data and how to split the grid across servers:

```bash
scripts/container.sh build && scripts/container.sh check-data
GPU=0 scripts/container.sh smoke
GPU=0 scripts/container.sh -d phase1
```

Without containers:

```bash
# inside the Docker container / venv, from the repo root
# 1. checkpoints: either João's (copy into results/runs/) or retrain:
TRAIN_MISSING=1 scripts/run_phase1.sh

# 2. or one checkpoint by hand
python experiments/05_decomposition.py --dataset nf-unsw-nb15-v3 --model gcn --k 5 \
    --checkpoint results/runs/<run>/best_checkpoint.pt --training-seed 42 \
    --attack-seeds 42 43 44 45 46 --epsilons 0.05 0.10 --deterministic

# 3. aggregate + verdict
python experiments/05b_decomposition_report.py
```

Smoke run first: `EXTRA_ARGS="--max-windows 20" DATASETS=nf-unsw-nb15-v3 MODELS=gcn TRAINING_SEEDS=42 scripts/run_phase1.sh`.

**Reconstruction check.** `05_decomposition.py` refuses to run if rebuilding the graph from *clean* features does not reproduce the stored graph (mean churn > 1%). Otherwise condition B would mix construction artefacts with attack effects.
- Duplicate flows are the usual culprit: the neighbour search may not return the node itself first.
- `--allow-reconstruction-mismatch` overrides this, but report the residual churn (it is saved in `metrics.json`).

**Outputs.**
- `results/decomposition/<run>/decomposition.csv`: one row per attack × ε × attack seed × condition.
- `results/decomposition/decomposition_summary.csv`, `decomposition_effects.csv`, `go_no_go.csv`.

## Conventions

- **Seeds:** 5 training seeds (42–46) × 5 attack/perturbation seeds; FGSM uses one attack seed. Never select a checkpoint; aggregate over all of them. Compare conditions with paired Wilcoxon tests over (training_seed, attack_seed).
- **ε** is in standardised-feature units (σ). Always report it as such.
- **Branches:**
  - `main` holds the paper work.
  - Tag `v1.0-thesis` reproduces the dissertation.
  - `old-main` is the earlier fork state; `pedro-main-snapshot` is the old template snapshot (its defence/Nettack files are empty placeholders).

## Decision log

| Date | Decision |
|---|---|
| 2026-10-06 | Datasets: only those relevant to the paper (NetFlow-v3; CTU-13 optional). NSL-KDD and CICIDS2017 dropped entirely, including for the go/no-go run, which waits for the NetFlow-v3 loader. Phases reordered: data/protocol first, decomposition second. |
| 2026-10-06 | GIANT read in full: no overlap. Experiments run in containers via `scripts/container.sh` (see `docs/RUNNING_ON_SERVERS.md`). |
| 2026-10-05 | Plan adopted: Phase 1 decomposition first, go/no-go at week 3. Optimised edge attacks (Nettack/Metattack) dropped: an attacker cannot edit edges in a feature-derived graph. Random edge perturbations are kept only as an upper-bound control. |
