# E013 rerun of E012 with fixes (A009, A010, A011, A023)
Code (commit 8c72704): 00 `--xgb-device` (XGBoost device separate from MLP); 01 `--class-weight balanced` (CE weights n/(2 n_c) from train labels; run dir tag `_cwbal`; weights in metrics.json runtime_config). Tests: tests/test_training.py (balanced weights, modes). NOT yet run (needs push → server).
Runs (all `--xgb-device cpu --n-jobs 16`):
- GPUserver2: 00 ToN --context window; 00 ToN --context host --node-key ip; 00 ctu13 --context host --node-key ip
- GPUserver1: 00 ToN --context host --node-key ipport
- GPUserver2 (CTU-13 only there): 01 ctu13 --graph endpoint --model egraphsage --node-key {ip,isolated,ipport} --window-size 10000 --epochs 50 --seed 42 --deterministic --class-weight balanced
Before GNN runs: `df -h ~` ≥ 15 GB; delete data/graphs/* after the batch (D09).
Decides A023 (Part 2 framing) together with E008 ToN ip 0.937.

## Results (results/E013.json; tabular 5 seeds, GNN seed 42 only)
ToN test F1: XGB plain .872 | host ip .201 (AUC .955) | host ipport .931 | window .802±.074 || MLP plain .735 | host ip .906 | host ipport .917 | window .036 (AUC .31) || GNN ip .937 / ipport .899 / isolated .727 (E008)
CTU-13 test F1: XGB plain .531 | host ip .614 | window .405 || MLP .484 | host ip .617 | window .217 || GNN cwbal ip .844 (AUC .992) / isolated .639 / ipport .675 (val .67-.68, best-val .73-.76)
## Interpretation
- ToN: best control (XGB host ipport .931) ≥ GNN ip .937 within seed noise (XGB std .013, MLP .018) → C2(a) delta +0.006 < 0.02: FAIL. Shuffled-dst ablation (E009 .940 ≥ .937) → C2(d) FAIL. Gain = host behavioural profile, not topology. Window context hurts (XGB .802, MLP collapses with AUC<.5 = drift).
- Anomalies: ToN XGB host ip F1 .20 but AUC .955 (threshold miscalibration under drift); ToN MLP window AUC .31 (inverted). Both reflect val→test drift (K10); F1@0.5 is fragile on ToN.
- CTU-13: class weights fix the collapse (K09: 0→.844). GNN ip − max control (isolated .639) = +0.205 ≥ 0.02 → C2(a) met on ONE seed. But ipport .675 ≈ isolated, test≫val, no shuffle ablation, no seeds → (b)(c)(d) untested.
## Verdict
H "ToN gain is topology": REFUTED (host profile). H "topology helps on CTU-13": INCONCLUSIVE (promising, single seed, window-composition confounder as in K06 not excluded).
