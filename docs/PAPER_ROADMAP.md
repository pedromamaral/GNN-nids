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

### Phase 1: NetFlow-v3 data and temporal protocol (weeks 1–3): done 2026-10-07
Datasets for the paper: **NF-UNSW-NB15-v3** (develop and test on this one first) and **NF-ToN-IoT-v3**, plus NF-CSE-CIC-IDS2018-v3 if compute allows; CTU-13 is optional, for comparison with Galli/Venturi. NSL-KDD and CICIDS2017 are **not** used (decision 2026-10-06). Raw files go in `data/raw/netflow-v3/` as `NF-UNSW-NB15-v3.csv`, `NF-ToN-IoT-v3.csv`, `NF-CSE-CIC-IDS2018-v3.csv` (see `docs/RUNNING_ON_SERVERS.md`).
- [x] NetFlow-v3 loader (`src/data/netflow_v3.py`), dataset names `nf-unsw-nb15-v3`, `nf-ton-iot-v3`, `nf-cse-cic-ids2018-v3`.
  - Source: <https://staff.itee.uq.edu.au/marius/NIDS_datasets/>. Cite Luay et al., arXiv:2503.04404.
  - Drop identifiers (`IPV4_SRC_ADDR`, `IPV4_DST_ADDR`, `L4_SRC_PORT`, `L4_DST_PORT`, and `DNS_QUERY_ID`, a random transaction id), timestamps, and the TTL testbed artefact (`MIN_TTL`, `MAX_TTL`, decision 2026-10-07) from the features: 44 features remain.
  - Log-transform heavy-tailed counters (`log1p`; codes, flags and TCP windows stay linear); standardise with statistics from the training split only. `+inf` rates become the largest finite training value, empty fields 0.
  - Label = `Label`; keep `Attack` for per-class analysis.
  - Large sets: a contiguous time slice (`--max-flows N --slice-start F`), never random rows, because random rows would break the windows.
- [x] Register the new names wherever datasets are hard-coded: `download.py`, `dataset.py`, `splits.py`, the `--dataset` choices of `01`–`05`, `scripts/check_data.py` (already knows the file names).
- [x] Temporal protocol (`src/data/splits.py`):
  - Sort by `FLOW_START_MILLISECONDS`.
  - Chronological 60/20/20 split.
  - Windows of temporally contiguous flows, with no shuffle before windowing.
  - Fit the scaler on train only.
- [x] Non-graph baselines (`experiments/00_tabular_baselines.py`): XGBoost and MLP on the same features and splits, 5 seeds.
- [x] Tests for the loader and the split; `05_decomposition.py` reconstruction check passes on NF-UNSW-NB15-v3 (all 2,368 windows of the three splits rebuild exactly, after making k-NN tie-breaking deterministic).

### Phase 2: decomposition, the go/no-go test (weeks 3–5) ← **current**
Code ready (written before the dataset decision; it works on any dataset the loader provides):
- [x] `src/attacks/construction_aware.py`: `construction_aware_pgd` rebuilds the k-NN graph at every PGD step.
- [x] `src/analysis/decomposition.py`: A/B/C conditions, reconstruction sanity check, effect arithmetic.
- [x] `experiments/05_decomposition.py`: one checkpoint × attack seeds × {fgsm, pgd, pgd_rebuild} × ε × {A, B, C}.
- [x] `experiments/05b_decomposition_report.py`: mean ± std, effects, Wilcoxon go/no-go.
- [x] `scripts/run_phase1.sh` + `scripts/container.sh phase1`: batch runner (finds or trains checkpoints).

Pilots (one training seed, 2 attack seeds, a subset of test windows, ε ∈ {0.05, 0.1, 0.25, 0.5}; outputs in `results/pilot/` on the servers):
- [x] 2026-10-07, NF-UNSW-NB15-v3, GCN, 100 windows (clean F1 0.976): induced structure has almost no effect. The structure effect (B) is at most 0.0027 F1 and the adaptive gain at most 0.009 at every ε, far below the 0.05/0.03 thresholds. This is not because the perturbations are too small: the feature effect (A) is 0.20 at ε = 0.25 and 0.79 at ε = 0.5, and 14–38% of malicious nodes' neighbours change. The GCN also trails XGBoost on clean data (0.96 vs 0.9995 on the full test set).
- [x] 2026-10-08, NF-ToN-IoT-v3, GCN, 300 windows (test F1 0.81; XGBoost 0.87): the structure effect is ≤ 0.0004 at every ε, and the adaptive gain is at most 0.019 (ε = 0.25), with 30% of malicious neighbours changed. No-go.
- [x] 2026-10-08, NF-UNSW-NB15-v3, GAT, 100 windows (test F1 0.986): the structure effect is ≤ 0.001 and the adaptive gain ≤ 0.004. No-go.
- [x] 2026-10-08, graph ablation (`experiments/06_graph_ablation.py`, full test sets). F1 with the k-NN graph / no edges / random graph (k = 5, mean of 3 seeds):
  - UNSW GCN: 0.975 / 0.995 / 0.21.
  - UNSW GAT: 0.986 / 0.995 / 0.15.
  - ToN GCN: 0.812 / 0.814 / 0.815.

  Removing the k-NN edges changes only 0.2–1.2% of predictions and never lowers F1, so the k-NN neighbourhood carries no information beyond the flow's own features: its neighbours are near-copies of it. This is why condition B is ≈ 0, and it will hold for any feature-derived k-NN graph, CTU-13 included. On UNSW, random neighbours collapse F1, so the models are sensitive to neighbours that are unlike the flow. A feature-bounded attacker cannot produce such neighbours, because the rebuilt k-NN neighbours stay close to the perturbed flow.
- [ ] Decision on the paper direction (see the decision log once taken). CTU-13 is unlikely to change this, since the redundancy comes from the k-NN construction itself, not from the dataset.

Tabular baselines without TTL (`00`, 5 seeds, test F1): NF-UNSW-NB15-v3 XGBoost 0.9995, MLP 0.9985. NF-ToN-IoT-v3 XGBoost ≈ 0.87, MLP ≈ 0.70–0.75 (chronological drift: 27% attacks in train, 55% in test; Backdoor recall ≈ 0). Random ±0.1σ noise drops XGBoost F1 to 0.77 (UNSW) and 0.20 (ToN): clean ease is not robustness.

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
| 2026-10-07 | **TTL dropped from the features** (`MIN_TTL`, `MAX_TTL`; `ARTEFACT_COLUMNS` in `src/data/netflow_v3.py`). Evidence on NF-UNSW-NB15-v3, test split: `MIN_TTL` alone gives F1 0.9992 (depth-2 XGBoost); TTL 31 is benign in all 421,980 flows, 62 is attack in all 10,622, 254 is attack in 30,704 of 30,706. With all 46 features the tabular baselines reach F1 0.9999 (XGBoost) and 0.9992 (MLP); XGBoost's gain is dominated by `MIN_TTL` (2915 vs 38 for the next feature). **For the paper:** TTL reflects the hop distance between the testbed's attack and victim hosts, not the behaviour of the flow (a known UNSW-NB15 artefact); a detector relying on it does not transfer to other networks; and the attacker sets the initial TTL of its own packets, so it would be a one-feature evasion route that makes the adversarial analysis trivial. Without TTL, XGBoost still reaches F1 0.9995, so the dataset stays easy for clean detection; see Phase 2 pilot. |
| 2026-10-07 | NetFlow-v3 protocol: flows sorted by start time, chronological 60/20/20, windows of 1000 consecutive flows, scaler on train only. On NF-UNSW-NB15-v3 the attack fraction is 3.0% in train and 8.7–9.3% in validation and test; every validation and test window contains attacks. k-NN ties (≈30% of flows in a window are exact duplicates) are broken by flow index, so the graph is a deterministic function of the features. `DNS_QUERY_ID` is dropped as an identifier. |
| 2026-10-06 | Datasets: only those relevant to the paper (NetFlow-v3; CTU-13 optional). NSL-KDD and CICIDS2017 dropped entirely, including for the go/no-go run, which waits for the NetFlow-v3 loader. Phases reordered: data/protocol first, decomposition second. |
| 2026-10-06 | GIANT read in full: no overlap. Experiments run in containers via `scripts/container.sh` (see `docs/RUNNING_ON_SERVERS.md`). |
| 2026-10-05 | Plan adopted: Phase 1 decomposition first, go/no-go at week 3. Optimised edge attacks (Nettack/Metattack) dropped: an attacker cannot edit edges in a feature-derived graph. Random edge perturbations are kept only as an upper-bound control. |
