# Codebase map (python package `src`, scripts in experiments/; run from repo root inside the container)

## Entry points
| script | does | outputs |
|---|---|---|
| experiments/00_tabular_baselines.py | XGBoost + MLP on single flows, same split/features; `--context none|host|window`, `--node-key ip|ipport`, `--context-window 10000`, `--seeds` (default 42-46), `--device`, `--n-jobs` | results/tabular/<ts>_<ds>[_ctx]/ |
| experiments/01_baseline_training.py | train GNN: `--model gcn|gat|egraphsage --graph knn|endpoint --node-key ipport|ip|isolated --k 5 --window-size --epochs --seed --hidden-layers --deterministic --max-flows --slice-start` | results/runs/<ts>_<ds>_<model>_{k_5|endpoint_<nk>_w<W>_L<L>}_seed_<s>/ |
| experiments/02_feature_attacks.py | FGSM/PGD on trained k-NN GNN (fixed graph) | results/feature_attacks/ |
| experiments/03_structural_attacks.py | random edge perturbations (upper bound) | results/structural_attacks/ |
| experiments/04_k_sensitivity.py | k sweep | results/... metrics.json |
| experiments/05_decomposition.py | one checkpoint × attack seeds × {fgsm,pgd,pgd_rebuild} × ε × {A,B,C} (k-NN only; endpoint adapter = A012) | results/(pilot/)decomposition/<run>/ |
| experiments/05b_decomposition_report.py | mean±std, effects, Wilcoxon go/no-go | decomposition_summary.csv, go_no_go.csv |
| experiments/06_graph_ablation.py | evaluate checkpoint under knn/none/random (k-NN) or graph/none/random_dst/random_src/random (endpoint) | results/graph_ablation/<ts>/graph_ablation.csv |
| scripts/run_phase1.sh | batch: find/train checkpoints → 05 → 05b (env DATASETS MODELS TRAINING_SEEDS ATTACK_SEEDS EPSILONS K LAYERS) | |
| scripts/container.sh | container jobs (see infra.md) | logs/<name>.log |
| scripts/check_data.py | lists missing raw files | |

## Modules
- src/data/netflow_v3.py — NetFlow-v3 loader: registry, ARTEFACT_COLUMNS (TTL), identifier drop, chronological 60/20/20, train-only scaler.
- src/data/ctu13.py — CTU-13 .binetflow loader, scenario split (D06).
- src/data/endpoint_graph.py — per-window endpoint graphs, anonymised constant-feature nodes, node_key.
- src/data/graph_builder.py — k-NN flow graph (FlowGraphBuilder.build_knn_graph; index tie-break). Phase 4 hooks (min_similarity, max_in_degree) NOT implemented.
- src/data/dataset.py — PyG dataset + graph cache (data/graphs/). splits.py, download.py; preprocess.py = legacy NSL-KDD.
- src/models/{gcn,gat,egraphsage,base}.py — egraphsage = edge classifier (Lo et al. 2022).
- src/training/trainer.py — fit loop, early stopping on val F1 (patience), history; NO class weighting yet (A010). evaluator.py.
- src/attacks/{fgsm,pgd}.py (feature_mask= arg), construction_aware.py (pgd_rebuild: rebuild k-NN each step), structural.py (random edges).
- src/analysis/decomposition.py (A/B/C conditions, effects), neighbor_churn.py.
- src/utils/metrics.py — binary metrics (f1, precision, recall, accuracy, roc_auc).
- configs/base_config.yaml — train defaults (epochs 100, lr 1e-3, wd 5e-4, patience 15, window 1000). CLI overrides.

## Tests
`scripts/container.sh test` (pytest; one test file per module in tests/). Add tests for every new module.

## Adding an experiment
1. Add flags to 00/01/05/06 (preferred) or a new experiments/0N_*.py writing metrics.json/CSV into results/<family>/<ts>_<...>/.
2. If the output layout is new, extend tools/summarize_run.py (CSV_SPECS or a new kind).
3. Test in container → push → launch (infra.md) → register in runs.md + LEDGER.
