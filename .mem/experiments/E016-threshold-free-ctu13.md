# E016 Threshold-free metrics + bootstrap, CTU-13 GNN vs tabular (A026)
Status: DONE 2026-10-17 (71498ca) — REFUTED. Decides C2(a),(c) on CTU-13 after K13 (D14).
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
## Implementation (71498ca)
- 06_graph_ablation.py `--save-scores [--scores-only]` -> scores.npz (<run>|val/test|score,y,window; native graph, softmax P(mal)).
- 00_tabular_baselines.py `--save-scores` -> scores.npz (<model>|<seed>|validation/test, validation|y, test|y, test|scenario).
- experiments/07_threshold_free.py `--gnn LABEL=npz ... --tab LABEL=npz ... --target ip`: flow-identity check (labels), PR/ROC-AUC, F1@0.5, F1@val-tuned, per-scenario, paired block bootstrap (binned, 512 bins). tests/test_threshold_free.py passes in container (12 tests with 06/00 tests).
- Deploy: 3x `06 --checkpoints <5 ckpts per node_key> --save-scores --scores-only`; 00 `--dataset ctu13 --save-scores` for context none and `--context host --node-key ip` (both seeds 42-46); then 07. Needs the 15 ckpt paths on GPUserver2 (E013/E014).
- Caveat: src/data/ is read-denied for Claude, so GNN-window vs tabular-flow alignment is verified by the label-identity check in 07 (aborts on mismatch), not by code reading. Scenario ids from tabular side only (index into CTU13_DEFAULT_SPLIT['test']).
## Results (.mem/results/E016.json; 5 seeds; 0 label mismatches over 32 checks -> identical flows)
| seed-mean | GNN ip | GNN ipport | GNN iso | XGB plain | MLP plain | XGB host-ip | MLP host-ip |
|---|---|---|---|---|---|---|---|
| PR-AUC | .855 | .640 | .593 | .763 | .718 | .886 | **.953** |
| ROC-AUC | .993 | .943 | .909 | .958 | .937 | .991 | **.996** |
| F1@0.5 | **.855** | .656 | .616 | .531 | .484 | .614 | .617 |
| F1@val-tuned | .477 | .575 | .495 | .495 | .464 | **.716** | .599 |
| val-tuned thr | .947 | .90 | .933 | .83 | .737 | .079 | .612 |
Gaps GNN ip - best competitor (block 10 windows, 10k resamples, CI of seed-mean gap; bootstrap on 512 score bins, points exact):
- PR-AUC vs MLP host-ip: -.098 (seeds -.082..-.120, 5/5 negative), CI [-.201, -.029]
- F1@0.5 vs GNN ipport: +.199 (min +.148), CI [+.079, +.362] (reproduces E014)
- F1@val-tuned vs XGB host-ip: -.238 (min -.276), CI [-.495, -.110]
Per test scenario (index 0/1/2 into CTU13_DEFAULT_SPLIT['test']; mapping to 9/10/13 not verified), PR-AUC GNN ip vs MLP host-ip: .899/.940, .896/.998, .381/.794 -> GNN lower in every scenario. The F1@0.5 advantage sits in scenario 0 (GNN .901 vs tabular <=.392).
## Interpretation
- Ranking: tabular host-ip MLP ranks botnet flows better than GNN ip in all seeds and all scenarios (PR-AUC); ROC parity (K13) hid this because negatives dominate. The F1@0.5 gain is threshold placement, not detection power.
- Anomaly: val-tuned thresholds transfer badly (tuned F1 < F1@0.5 for 6/7 models; GNN ip thr .95 -> test F1 .48). Validation scenarios do not represent test scenarios (as K10 on ToN), so tuned F1 is a weak criterion; the verdict rests on PR-AUC.
- Confound: GNN trained with balanced CE (K09), tabular unweighted -> GNN's 0.5 sits at a different prior. Part of the F1@0.5 gap is likely class weighting, not the graph (untested; A030).
## Verdict
H REFUTED on PR-AUC (gap -.098, 5/5, CI excludes 0 on the wrong side) and tuned F1. C2(a),(c) fail on CTU-13 -> E017/A029 not run (D14 condition).
