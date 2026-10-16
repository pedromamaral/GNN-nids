# E014 CTU-13 topology test: 5 seeds + shuffled-endpoint ablation (A022, A025)
Status: IMPLEMENTED (not deployed). Decides C2 on CTU-13 (project.md C2, D12).
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
(results pending)

- 10-16 fix 3ec549a: 06_graph_ablation.py window_counts/.cpu() (lines 129,160); rerun 06 only (01 x12 done).
