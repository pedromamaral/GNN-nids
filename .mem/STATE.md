# STATE — 2026-10-14 (research-do implement + deploy E013)
Branch main · pushed; servers at abd90c1+ (balanced weights fall back to ones if a class is absent; 30 tests pass on GPUserver2) · Phase: Avenue #1, A2 (Part 2 go/no-go).

## Just done
- 00: `--xgb-device` (XGBoost device separate from --device; default = --device).
- 01 + Trainer: `--class-weight none|balanced` (CE weights n/(2 n_c) from train labels; run dir tag `_cwbal`; weights logged in metrics.json). Tests in tests/test_training.py pass on GPUserver2.
- Lit graph copied to OneDrive lit-graph/gnn-nids/ (+ review.md, runs.log).
- Success thresholds for C2/C4 proposed in project.md (awaiting Pedro's OK).

## Active runs
E013-q2 GPUserver2 queue_e013.sh (ToN window → ToN host ip → ctu13 host ip → ctu13 GNN ip/isolated/ipport cwbal), started 10-14 ~18:45 local.
E013-q1 GPUserver1 queue_e013.sh (ToN host ipport), started ~18:15 local. GPUserver1 GPU 100% (others).

## Latest results
E008 ToN GNN ip 0.937 vs XGB 0.872; E009 ablation suggests window composition (K06); E011 CTU-13 GNN all-benign (K09); E012 crashed (XGB OOM, disk).

## Open problem
Is ToN's GNN gain topology, host profile or window composition? Decided by E013 (A023).

## EXACT next step
Come back in a few hours: `research-do status` (tools/runs_status.sh). When the tabular runs finish: `research-do fetch E013` (summarize_run.py E013 GPUserverN:results/tabular/<dir> ...), then `research-think analyze E013` (A023 framing; check against C2 thresholds in project.md).

## Read next
.mem/runs.md, .mem/experiments/E013-a2c-rerun.md.
