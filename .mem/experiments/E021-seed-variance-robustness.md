# E021 Training-seed variance of adversarial robustness, CTU-13 (A031)
Status: PLANNED 2026-10-23 (D20). Serves C4 (reframed), G2.
## Hypothesis
At matched clean performance, the GNN-ip shaping vulnerability Δ_A (β .5) varies ≫ attack-seed noise (≤.01) across 15 training seeds (CV ≥ .3), is not predicted by clean metrics (|r| < .8 with clean recall@1%FPR, val PR-AUC, val F1), and the sign of S (joint vs separate) flips across seeds. MLP host-ip is the tabular contrast (E020: Δ_A .51-.62).
## Change
- Train E-GraphSAGE cwbal ip (E014 settings, 50 ep, w10k) for seeds 47-56 (42-46 reuse E014 ckpts); MLP host-ip + scaler for 47-56 via --model-cache.
- 08 joint attack, reduced grid: detectors gnn_ip, mlp_host_ip; delay off (K15: irrelevant); β .1/.5; ρ 0/.5/1 + budget-matched A/B for S; attack seeds 0,1; 30 PGD steps (converged, K15).
- 08 summary: add signed S per ρ (S_max_abs unsigned, G clipped ≥0 — E020 analysis note).
- Per seed also save clean predictors: test recall@1%FPR, val PR-AUC, val F1, threshold, mean malicious logit margin.
## Config
scripts/queue_E021.sh (GPUserver2). Output results/E021/seed_<s>/<ts>/{rows,summary}.csv + clean_stats.json.
## Success criterion
- Supported: CV(Δ_A, β .5) ≥ .3 over 15 GNN seeds, max/min ≥ 3, |Spearman r| < .8 with every clean predictor; S(β .5, ρ .5) sign differs in ≥ 3/15 seeds. MLP host-ip CV reported as contrast.
- Refuted: CV < .3 or a clean predictor explains it (|r| ≥ .8) → seed 42 was a tail draw; report seed spread as a caveat only.
## Results
(pending)
