# E013 rerun of E012 with fixes (A009, A010, A011, A023)
Code (commit 8c72704): 00 `--xgb-device` (XGBoost device separate from MLP); 01 `--class-weight balanced` (CE weights n/(2 n_c) from train labels; run dir tag `_cwbal`; weights in metrics.json runtime_config). Tests: tests/test_training.py (balanced weights, modes). NOT yet run (needs push → server).
Runs (all `--xgb-device cpu --n-jobs 16`):
- GPUserver2: 00 ToN --context window; 00 ToN --context host --node-key ip; 00 ctu13 --context host --node-key ip
- GPUserver1: 00 ToN --context host --node-key ipport
- GPUserver2 (CTU-13 only there): 01 ctu13 --graph endpoint --model egraphsage --node-key {ip,isolated,ipport} --window-size 10000 --epochs 50 --seed 42 --deterministic --class-weight balanced
Before GNN runs: `df -h ~` ≥ 15 GB; delete data/graphs/* after the batch (D09).
Decides A023 (Part 2 framing) together with E008 ToN ip 0.937.
