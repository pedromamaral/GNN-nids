# E016 Threshold-free metrics + bootstrap, CTU-13 GNN vs tabular (A026)
Status: PLANNED. Decides C2(a),(c) on CTU-13 after K13 (D14).
## Hypothesis
H: the GNN ip gain on CTU-13 (+.199 F1@0.5, E014) is detection power, not threshold placement under drift: GNN ip - max(XGB, MLP; plain and host-ip; GNN isolated/ipport) >= .058 (2x seed std, K13) on PR-AUC AND on F1 at a validation-tuned threshold, 5/5 seeds; block-bootstrap 95% CI excludes 0.
## Change
- Per-flow score dump (test + val; flow index, scenario id, window id, label, score) for: 15 E013/E014 GNN ckpts (ip/isolated/ipport x seeds 42-46, eval only, no retraining); XGB + MLP plain and host-ip, seeds 42-46 (rerun 00 with a score-dump flag, CPU XGB as E013).
- Metric script (std lib + numpy, runs server-side): PR-AUC, ROC-AUC, F1@0.5, F1@val-tuned threshold (threshold maximising val F1), per test scenario (9/10/13); paired moving-block bootstrap on test windows, block = 10 windows (as fixed in E014), 10k resamples.
- Check first that tabular and GNN test flows are identical (same flow ids, same order); report mismatch count.
## Config
GPUserver2 (CTU-13 data only there). Flags behind a switch (default off) so baselines are unchanged. Clean data/graphs/* after (D09).
## Success criterion
Supported: gap >= .058 on PR-AUC and tuned F1, 5/5 seeds, CI excludes 0 -> run A029/E017. Refuted: gap < .058 on either -> C2 fails on CTU-13 (context, not topology; D13 framing). Report per-scenario gaps either way.
## Results
(pending)
