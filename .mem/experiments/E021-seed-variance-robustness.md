# E021 Training-seed variance of adversarial robustness, CTU-13 (A031)
Status: ANALYSED 2026-10-29 (H1/H2 supported, H3 substantively refuted). Serves C4 (reframed), G2.
## Hypothesis
At matched clean performance, the GNN-ip shaping vulnerability Δ_A (β .5) varies ≫ attack-seed noise (≤.01) across 15 training seeds (CV ≥ .3), is not predicted by clean metrics (|r| < .8 with clean recall@1%FPR, val PR-AUC, val F1), and the sign of S (joint vs separate) flips across seeds. MLP host-ip is the tabular contrast (E020: Δ_A .51-.62).
## Change
- Train E-GraphSAGE cwbal ip (E014 settings, 50 ep, w10k) for seeds 47-56 (42-46 reuse E014 ckpts); MLP host-ip + scaler for 47-56 via --model-cache.
- 08 joint attack, reduced grid: detectors gnn_ip, mlp_host_ip; delay off (K15: irrelevant); β .1/.5; ρ 0/.5/1 + budget-matched A/B for S; attack seeds 0,1; 30 PGD steps (converged, K15).
- 08 summary: add signed S per ρ (S_max_abs unsigned, G clipped ≥0 — E020 analysis note).
- Per seed also save clean predictors: test recall@1%FPR, val PR-AUC, val F1, threshold, mean malicious logit margin.
## Config
scripts/queue_E021.sh (GPUserver2). Output results/E021/seed_<s>/<ts>/{rows,summary}.csv + clean_stats.json.
## Implementation (2026-10-23)
08: `--no-xgb` (skips XGB fit/load/attack); summary gains signed `S_signed_mean` + `S_rho<r>` columns; per-seed `clean_stats.json` (gnn_ip, mlp_host_ip: test PR-AUC, test recall@1%FPR, mean malicious logit margin, val F1 from 01 metrics.json / MLP cache). Val PR-AUC not stored by 01 -> test clean PR-AUC used as the PR-AUC predictor. MLP unweighted (matches E020 caches 42-46), GNN cwbal. Seeds 42-46 clean_stats need a rerun of 08 (cheap, included in queue); MLP val F1 absent for 42-46 caches (null).
Config: scripts/queue_E021.sh (trains 47-56 via 01, then 08 x15). Commit sha: see git log (E021).

## Success criterion
- Supported: CV(Δ_A, β .5) ≥ .3 over 15 GNN seeds, max/min ≥ 3, |Spearman r| < .8 with every clean predictor; S(β .5, ρ .5) sign differs in ≥ 3/15 seeds. MLP host-ip CV reported as contrast.
- Refuted: CV < .3 or a clean predictor explains it (|r| ≥ .8) → seed 42 was a tail draw; report seed spread as a caveat only.
## Results (2026-10-29, .mem/results/E021.json; per-flow white-box `white/` rows, delay off, mean of attack seeds 0/1)
| detector, β | Δ_A mean±sd | CV | min-max | attack noise Δ_A / S | S(ρ.5) >0 | G≥.03 | Spearman Δ_A vs clean rec@1%FPR / rec@.5 |
|---|---|---|---|---|---|---|---|
| GNN ip .1 | .195±.139 | .72 | .010-.533 | ≤.003 / ≤.008 | 8/15 (mean +.001) | 1/15 | .41 / .43 |
| GNN ip .5 | .388±.180 | .46 | .020-.605 | ≤.006 / ≤.008 | 3/15 (s42 +.063, s49 +.020, s56 +.005; mean −.051) | 1/15 (s42 .080) | .44 / .54 |
| MLP host-ip .1 | .480±.042 | .09 | .379-.545 | ≤.001 | 0/15 | 0/15 | .93 / .24 |
| MLP host-ip .5 | .539±.055 | .10 | .429-.622 | ≤.003 | 0/15 (mean −.110) | 0/15 | .93 / .29 |
- GNN clean recall@1%FPR .924±.021 (narrow), but Δ_A β.5 spans 30×. Robust GNN seeds: 42 (.081), 49 (.020), 55 (.112); then 43 .28; 11/15 sit at .38-.61 ≈ the MLP level.
- GNN − MLP paired Δ_A: β.1 −.286 (GNN lower 14/15), β.5 −.152 (13/15); Δ_C* β.5 −.137 (13/15).
- Host-window Δ_A ranks the same as per-flow (Spearman .92 at β.5).
- clean_stats re-fetched 2026-10-29 (summarize_run bug: `limit=100` hit by the 360 table metrics already in the dict). Spearman of Δ_A with each GNN clean predictor (β.1 / β.5, n=15): test PR-AUC −.09/−.18, recall@1%FPR .41/.44, logit margin .04/−.01, threshold .20/.31, val F1 .11/−.06, val ROC-AUC −.16/−.44. GNN clean spread: PR-AUC .862±.035, val F1 .765±.018, margin 2.68±1.09. For MLP host-ip, test PR-AUC (.85) and recall@1%FPR (.93) do predict Δ_A.
## Interpretation
GNN-ip shaping robustness is a training-seed lottery. Seed sd .18 is 30× the attack noise, and the clean operating point does not predict it (|ρ| ≤ .54). The MLP's vulnerability is set by its clean operating point (CV .10, ρ .93). The joint-vs-separate verdict does not really flip: S>0 beyond noise in 2/15 seeds and G≥.03 in 1/15 (s42) → K15 holds at n=15.
## Verdict
- H1 seed variance ≫ attack noise (CV ≥ .3, max/min ≥ 3): SUPPORTED (CV .46, ×30).
- H2 not explained by clean metrics (|r| < .8): SUPPORTED for all 7 predictors (max |ρ| .54, recall@0.5). Val-based selection (val F1, val ROC-AUC) cannot pick the robust seeds.
- H3 S sign flips in ≥ 3/15: met only nominally (3/15, of which s56 +.005 is within noise). Substantively REFUTED: separate evaluation suffices in 14/15 seeds.
