# E027 k-NN graph ablation over 5 training seeds, UNSW GCN+GAT (A038)
Status: IMPLEMENTED 2026-11-10 (sha 304cf53, scripts/queue_E027.sh), not yet deployed. Planned 2026-11-05 (D24). Serves C1 (robustness of K04, 1 seed in E007). Runs before paper-plan. E026 is reserved for the ToN rerun (E025 card).
## Hypothesis
K04 holds over training seeds: the k-NN graph adds no detection power over no edges. For each seed, F1(knn) − F1(none) < .02 for GCN and GAT.
## Change
Run experiments/06_graph_ablation.py (knn / none / random) on the 5 E023 training seeds. Report ΔF1 per condition and the fraction of changed predictions.
Also fetch per-seed decomposition.csv and the summary CSVs from E023 (results/decomposition): exact per-seed structure effect and adaptive gain, cell count, go_no_go.csv, churn (ncr_global, ncr_malicious).
## Config
UNSW, k=5, L=1, training seeds 42-46, same checkpoints as E023 if still present. Random graph: fixed number of draws per seed, set at implementation and recorded here.
Implementation: no code change; 06 already takes multiple checkpoints. Queue runs 06 on the 10 E023 checkpoints (all present on GPUserver1, results/runs/*unsw*_{gcn,gat}_k_5_seed_4[2-6]) with `--random-seeds 0 1 2 --save-window-counts --output-dir results/graph_ablation/E027`, then rm data/graphs/*. Random graph: 3 draws per seed (0,1,2). Smoke (1 ckpt, 20 windows) OK 11-10. Disk 4.8 GB free; the k-NN test cache is rebuilt (~30 s) and removed at the end. E023 per-seed files are fetched at the fetch step (decomposition/<run>/decomposition.csv, churn).
Was to check at implementation (done): checkpoints on GPUserver1 (retrain with TRAIN_MISSING if gone), whether 06 supports k-NN checkpoints across seeds, GPU-h, disk (~4.6 GB free on GPUserver1 as of the last STATE).
Out of scope: ToN GCN 5 seeds and eps >.10; they stay 1-seed and are stated as such in the paper unless a later decision adds them.
## Success criterion (set before running)
- Supported: F1(knn) − F1(none) < .02 in 5/5 seeds for both models (.02 as in the C2 rule, project.md).
- Refuted: F1(knn) − F1(none) ≥ .02 in 5/5 seeds for either model → revise C1.
- Anything else: inconclusive, report per-seed values.
- Random-graph drops (E007: UNSW F1 .21 GCN, .15 GAT) are reported, not part of the criterion: they show dependence on a plausible neighbourhood, not a gain from the graph.
## Results
(pending)
