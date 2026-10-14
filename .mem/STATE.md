# STATE — 2026-10-14 (research-do implement E013)
Branch main · local commits 0b3aecd (mem init) + 8c72704 (E013 code), NOT PUSHED (auto mode blocked `git push`; Pedro pushes) · Phase: Avenue #1, A2 (Part 2 go/no-go).

## Just done
- 00: `--xgb-device` (XGBoost device separate from --device; default = --device).
- 01 + Trainer: `--class-weight none|balanced` (CE weights n/(2 n_c) from train labels; run dir tag `_cwbal`; weights logged in metrics.json). Tests added to tests/test_training.py; NOT run yet (no torch locally).
- Lit graph copied to OneDrive lit-graph/gnn-nids/ (+ review.md, runs.log).
- Success thresholds for C2/C4 proposed in project.md (awaiting Pedro's OK).

## Active runs
None. GPUserver2 GPU idle, 32 GB disk; GPUserver1 GPU ~99% (others), 11 GB disk.

## Latest results
E008 ToN GNN ip 0.937 vs XGB 0.872; E009 ablation suggests window composition (K06); E011 CTU-13 GNN all-benign (K09); E012 crashed (XGB OOM, disk).

## Open problem
Is ToN's GNN gain topology, host profile or window composition? Decided by E013 (A023).

## EXACT next step
1. Pedro: `git push origin main`.
2. research-do deploy E013: `ssh GPUserver2 'cd ~/GNN-nids && git pull && scripts/container.sh test tests/test_training.py tests/test_tabular_baselines.py'`, then launch the queue in .mem/experiments/E013-a2c-rerun.md (queue pattern in infra.md), register rows in runs.md.

## Read next
.mem/experiments/E013-a2c-rerun.md, .mem/infra.md, .mem/runs.md.
