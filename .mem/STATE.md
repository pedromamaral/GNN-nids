# STATE — 2026-10-14 (research-do implement + deploy E013)
Branch main · pushed; servers at abd90c1+ (balanced weights fall back to ones if a class is absent; 30 tests pass on GPUserver2) · Phase: Avenue #1, A2 (Part 2 go/no-go); E013 analysed 10-15.

## Just done
- 00: `--xgb-device` (XGBoost device separate from --device; default = --device).
- 01 + Trainer: `--class-weight none|balanced` (CE weights n/(2 n_c) from train labels; run dir tag `_cwbal`; weights logged in metrics.json). Tests in tests/test_training.py pass on GPUserver2.
- Lit graph copied to OneDrive lit-graph/gnn-nids/ (+ review.md, runs.log).
- Success thresholds for C2/C4 proposed in project.md (awaiting Pedro's OK).

## Active runs
None. E013 finished 10-15 (both queues); fetched to .mem/results/E013.json (7 runs). Containers already gone.

## Latest results
E008 ToN GNN ip 0.937 vs XGB 0.872; E009 ablation suggests window composition (K06); E011 CTU-13 GNN all-benign (K09); E012 crashed (XGB OOM, disk).

## Open problem
Is ToN's GNN gain topology, host profile or window composition? Decided by E013 (A023).

## EXACT next step
`research-think ideate` (or decide directly): run A022+A025 on CTU-13 only: 5-seed cwbal GNN (ip/isolated/ipport) + shuffled-endpoint ablation on the ip checkpoint; consider A026 (PR-AUC / threshold) for ToN. Then `research-do implement`/`deploy`. Delete data/graphs/* caches on both servers.

## Read next
.mem/runs.md, .mem/experiments/E013-a2c-rerun.md.
