# E023 k-NN decomposition full grid, UNSW GCN+GAT (A015)
Status: IMPLEMENTED 2026-10-29 (not yet launched). Serves C1 (robustness of K04/K05).
## Hypothesis
K04/K05 hold at 5 training × 5 attack seeds: structure effect < .05 and adaptive gain < .03 at ε ∈ {0.05, 0.10} for GCN and GAT (one-sided Wilcoxon over training seeds, attack seeds averaged within).
## Change
Config-only: Phase 2 k-NN decomposition script with seeds 42-46 × attack seeds 0-4, ε {0.05, 0.10}, UNSW GCN + GAT.
## Config
scripts/queue_E023.sh (GPUserver1; wraps `container.sh phase1` with TRAIN_MISSING=1; attack seeds 42-46 = run_phase1 default; report -> results/decomposition). Not smoke-tested locally (no torch); phase1 path unchanged.
## Success criterion
- Supported: structure effect ≤ .05 and adaptive gain ≤ .03 in 5/5 training seeds for both models.
- Refuted: either threshold crossed in 5/5 seeds (Wilcoxon p=.031) → revise C1.
## Results
(pending)
