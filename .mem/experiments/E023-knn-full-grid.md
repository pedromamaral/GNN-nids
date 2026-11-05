# E023 k-NN decomposition full grid, UNSW GCN+GAT (A015)
Status: ANALYSED 2026-11-05: SUPPORTED, UNSW and eps ≤.10 only. Ran 2026-10-29 on GPUserver1 (container gnn_pedroamaral_phase1_gpu0_20261029_214223). Serves C1 (robustness of K05; does NOT retest K04).
## Hypothesis
K04/K05 hold at 5 training × 5 attack seeds: structure effect < .05 and adaptive gain < .03 at ε ∈ {0.05, 0.10} for GCN and GAT (one-sided Wilcoxon over training seeds, attack seeds averaged within).
## Change
Config-only: Phase 2 k-NN decomposition script with seeds 42-46 × attack seeds 42-46 (corrected 2026-11-05 from "0-4": queue_E023.sh:6 and run_phase1.sh use 42-46), ε {0.05, 0.10} (L∞ on standardised features, malicious nodes only), UNSW GCN + GAT, k=5, L=1, 20 PGD steps. FGSM has 1 attack seed.
## Config
scripts/queue_E023.sh (GPUserver1; wraps `container.sh phase1` with TRAIN_MISSING=1; attack seeds 42-46 = run_phase1 default; report -> results/decomposition). Not smoke-tested locally (no torch); phase1 path unchanged.
## Success criterion
- Supported: structure effect ≤ .05 and adaptive gain ≤ .03 in 5/5 training seeds for both models.
- Refuted: either threshold crossed in 5/5 seeds (Wilcoxon p=.031) → revise C1.
## Results
Source: .mem/results/E023.json (aggregates only, ΔF1 = clean − attacked). Means and sd pool the 25 training×attack cells (ddof=1; 05b:66-87).

| model, ε | structure effect (pgd, B) | sd | adaptive gain | worst-case training-seed gain | feature (pgd, A) | combined (pgd_rebuild, C) | interaction (pgd) |
|---|---|---|---|---|---|---|---|
| GCN .05 | .00157 | .00012 | .00172 | .0027 | .00249 | .00421 | .00026 |
| GCN .10 | .00284 | .00007 | .00385 | .0113 | .00778 | .01163 | .00101 |
| GAT .05 | .00043 | .00007 | .00085 | .0087 | .00827 | .00912 | .00044 |
| GAT .10 | .00082 | .00011 | .00362 | .0280 | .03485 | .03848 | .00263 |

Check: adaptive gain = combined(pgd_rebuild) − feature(pgd) reproduces all 4 means. Structure cells are ≤.0032 everywhere (Samuelson: mean + 4.8 sd, n=25).
Worst-case column = mean + 1.96(sd_C + sd_A), the largest deviation 5 equal groups of 5 can have given a pooled sd. It is an analytic ceiling, not an observed value, and assumes a complete 5×5 grid (the JSON does not hold structure_n/adaptive_n).
## Interpretation
- Thresholds hold in every case: structure effect is ≥17× below .05, mean adaptive gain ≥7× below .03. A Refuted outcome (5/5 above threshold) is impossible. With 5/5 seeds below threshold, the one-sided Wilcoxon gives p=.031.
- The structure effect is small but real: mean/sd is 6-38. On GCN it is a large share of the feature effect (63% at ε .05, 37% at ε .10; GAT 5%, 2%). So "inconsequential" holds in absolute F1, not relatively.
- These budgets are weak: the largest ΔF1 is .038 (GAT, ε .10). Structure effect and gain grow with ε (×1.8-1.9 and ×2.2-4.2 from .05 to .10). Larger ε evidence is still the 1-seed pilot (E006).
- Not covered: ToN; K04 graph ablation (06 is not in this queue, so E007 stays 1 seed); churn values (saved in decomposition_summary.csv, not in the JSON).
- Protocol mismatch: 05b's Wilcoxon pools n=25 cells (pseudo-replicated) and does not match this card's training-seed test. Per-seed exact counts need the fetched decomposition.csv files. go_no_go.csv verdict column not in the JSON; 05b requires mean ≥ threshold, so these means imply NO-GO.
- Reproducibility: sha is null in the JSON.
## Verdict
SUPPORTED for UNSW GCN+GAT at ε ≤.10 (5/5 seeds by analytic ceiling). C1 structure-effect half firm on that scope. C1 "gains nothing from the graph" (K04) is not strengthened; see A038.
