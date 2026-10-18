# E018 Class-weighted tabular on CTU-13 (A030)
Status: DONE 2026-10-18 — SUPPORTED (F1@0.5 edge is mostly loss weighting). Closes the F1@0.5 confound in K14.
## Hypothesis
With a matched training prior (XGB scale_pos_weight = n_neg/n_pos, MLP BCE pos_weight = n_neg/n_pos, as GNN cwbal), tabular host-ip F1@0.5 reaches ≥ GNN ip − .058; i.e. the GNN's F1@0.5 edge is the loss weighting, not the graph.
## Change
00_tabular_baselines.py `--class-weight balanced` (default off); plain + host-ip, XGB+MLP, seeds 42-46, `--save-scores`; rerun 07 with the E016 GNN npz.
## Success criterion
Supported if gap GNN ip − best class-weighted tabular < .058 on F1@0.5. Refuted (GNN keeps a real fixed-threshold advantage, report it as calibration robustness) otherwise.
## Implementation
- 00_tabular_baselines.py `--class-weight {none,balanced}` (default none = unchanged): XGB scale_pos_weight, MLP BCE pos_weight = n_neg/n_pos of train. Syntax-checked only (no torch locally); smoke test pending in container.
- scripts/queue_E018.sh: 00 plain + host-ip (CPU XGB, seeds 42-46, --save-scores) -> 07 vs E016 GNN npz (globs results/E016_gnn_*{ip,ipport,isolated}*/scores.npz — verify names at deploy).
## Results (.mem/results/E018.json, key threshold_free; 5 seeds; 0 label mismatches / 32 checks; GNN = E016 npz)
| seed-mean | GNN ip | MLP host-ip cw | XGB host-ip cw | XGB plain cw | MLP plain cw |
|---|---|---|---|---|---|
| PR-AUC | .855 | **.929** (unw .953) | .824 (.886) | .806 (.763) | .734 (.718) |
| F1@0.5 | **.855** | .804 (.617) | .642 (.614) | .720 (.531) | .614 (.484) |
| F1@val-tuned | .477 | .503 | **.661** (.716) | .503 | .464 |
Gaps GNN ip − best cw competitor (block 10 windows, 10k resamples, 512 bins):
- F1@0.5 vs MLP host-ip cw: +.051, seeds +.042/−.003/+.087/−.022/+.150 (3/5 positive), CI [−.035, +.139]
- PR-AUC vs MLP host-ip cw: −.074 (5/5 negative), CI [−.177, −.012]
- F1@val-tuned vs XGB host-ip cw: −.184 (5/5), CI [−.390, −.079]
Per test scenario 0/1/2 (PR-AUC, F1@0.5), GNN ip vs MLP host-ip cw: (.899,.901) vs (.913,.659); (.896,.942) vs (.996,.986); (.381,.359) vs (.847,.820). The GNN F1@0.5 edge is in scenario 0 only.
## Interpretation
- Matched prior closes most of the +.199 F1@0.5 gap (→ +.051 < .058 floor, CI spans 0, 2/5 seeds negative). Class weighting lifts tabular F1@0.5 by +.12 to +.19 and costs MLP/XGB host-ip some PR-AUC (−.02/−.06).
- PR-AUC verdict of K14 unchanged (GNN still below MLP host-ip, CI excludes 0).
- Residual: GNN ip keeps the best scenario-0 fixed-threshold F1 (.90 vs ≤.66) but is far worse on scenario 2 (.36 vs .82); no uniform advantage.
## Verdict
H SUPPORTED: no significant GNN F1@0.5 advantage under a matched training prior. C2 negative on CTU-13 holds on every metric.
