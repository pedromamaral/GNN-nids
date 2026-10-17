# E014 CTU-13 topology test: 5 seeds + shuffled-endpoint ablation (A022, A025)
Status: DONE (06 bootstrap not yet computed). Decides C2 on CTU-13 (project.md C2, D12).
## Hypothesis
H: the E013 CTU-13 GNN ip gain (.844 vs isolated .639 / ipport .675, seed 42) is topology: GNN ip - max(controls) >= max(0.02, 2x pooled seed std), 5/5 seeds positive, block-bootstrap CI excludes 0, shuffle costs >= 0.02.
## Change
Seed runs: no code change (01 --seed, --class-weight balanced). 06 is metadata-driven (works on ctu13 endpoint ckpts); added `--save-window-counts` -> window_counts.npz (per-window tn/fp/fn/tp per ckpt|graph|seed) for the block bootstrap, incl. paired ip-vs-isolated/ipport diffs. Test-time shuffle first; train-time only if borderline.
## Config
01 ctu13 --graph endpoint --model egraphsage --node-key {ip,isolated,ipport} --window-size 10000 --epochs 50 --class-weight balanced --seed {42,43,44,45,46} --deterministic (GPUserver2, as E013).
06 on ALL 15 ckpts (ip/isolated/ipport x 5 seeds) with --save-window-counts; modes knn(=real)/none/random_dst/random_src/random; label test-time.
Controls for the max: XGB/MLP host ip (E013, 5 seeds), window, plus E015 neighbour-aggregate XGB.
Bootstrap block length N: TO FIX BEFORE RUNNING (>= 1 CTU-13 scenario or >= N windows): N = 10 consecutive test windows (=100k flows at W=10000), moving-block bootstrap, 10k resamples, paired across models on identical windows. FIXED before running; scenario-level resampling not used (only 3 test scenarios 9/10/13).
Disk: df -h ~ >= 15 GB before; delete data/graphs/* after (D09).
## Success criterion
C2(a)-(d) per project.md, CTU-13 only. Record GNN seed std here (first measurement).
## Results
Commit: see git log `E014:`. Tests: test_window_counts_per_window_confusion (run in container at deploy).
Source: .mem/results/E014.json (+ seed 42 from E013.json). 5 seeds, CTU-13 test (scen. 9/10/13), cwbal, final epoch.
| node_key | test F1 | test AUC | val F1 (final) |
|---|---|---|---|
| ip | .855±.031 | .9933±.0011 | .707 |
| isolated | .616±.031 | .9094±.0170 | .686 |
| ipport | .656±.023 | .9433±.0078 | .661 |
GNN seed std (first measurement): pooled .029 -> C2(a) floor = max(.02, .058) = .058.
ip - max(isolated, ipport) per seed 42..46: .168/.148/.206/.224/.249 (mean .199).
Tabular controls (E013, 5 seeds): XGB host-ip F1 .614 AUC .991; MLP host-ip F1 .617 AUC .996; XGB window .405.
06 test-time ablation (ip ckpts, F1): real .855 / none .492 / random_dst .394 / random_src .451 / random .393. isolated ckpts: all modes .616 (changed=0, sanity OK). ipport: real .656 / none .585 / random_dst .486 / random_src .619 / random .463.
## Interpretation
- C2(a) F1: +.199 over best GNN control, +.238 over best tabular (MLP host-ip .617) >> .058. PASS on F1, pending neighbour-aggregate XGB (E015).
- C2(b): 5/5 seeds positive (min +.148). PASS.
- C2(c): window_counts.npz on GPUserver2, bootstrap not computed. PENDING.
- C2(d) test-time: shuffle costs .36-.46 >> .02. PASS (test-time) but shuffled ip drops BELOW isolated (.616): the graphs are out of distribution, so the size of the cost is exaggerated; it shows the model depends on its neighbourhood, not how much real topology adds.
- ANOMALY 1 (threshold-free): GNN ip AUC .993 ≈ XGB host-ip .991 < MLP host-ip .996. The F1 gap does not show in ranking -> it may be threshold/calibration under drift (cf. K11: F1@0.5 fragile), not detection power.
- ANOMALY 2 (val vs test): on val, ip is only +.02/.05 over isolated/ipport (.707 vs .686/.661); the +.2 gap appears only on the test scenarios -> effect may be specific to scenarios 9/10/13.
## Verdict
H INCONCLUSIVE: (a),(b),(d) pass on F1@0.5, but the AUC parity with tabular host-ip and the val/test gap mean a topology claim is not yet supported. Needed: threshold-free metrics (PR-AUC, F1 at val-tuned threshold) for GNN and tabular on identical flows; per-scenario breakdown + block bootstrap (C2(c)); E015.

- 10-16 fix 3ec549a: 06_graph_ablation.py window_counts/.cpu() (lines 129,160); rerun 06 only (01 x12 done).
