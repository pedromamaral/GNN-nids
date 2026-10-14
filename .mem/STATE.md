# STATE — 2026-10-14 (research-memory init)
Branch main · sha: see `git log -1` (commit "mem: init .mem/ research memory") · Phase: Avenue #1, step A2 (Part 2 go/no-go) blocked on controls.

## Just done
- .mem/ created from .mem/_import.md + server result dirs; E001-E012 reconstructed; results JSON for E001,E002,E005-E011.
- tools/summarize_run.py (gnn/tabular/csv/generic; runs server-side over ssh) and tools/runs_status.sh: both tested on real dirs.

## Active runs
None (both servers idle on our side, 17:20). GPUserver1 GPU ~99% busy (other users), 11 GB disk; GPUserver2 GPU idle, 32 GB disk.

## Latest results
- E008: ToN E-GraphSAGE ip 0.937 > XGB 0.872 (E002) > isolated 0.727; UNSW all ≈0.997-0.9995 (saturated, K02).
- E009: ToN ip model keeps 0.91-0.94 with shuffled endpoints, 0.79 without edges → window-composition confounder? (K06)
- E011: CTU-13 XGB 0.531, window context hurts (0.405); GNN ip all-benign (K09).
- E012: ToN window/host controls + ctu13 host ip CRASHED (XGB GPU OOM); ctu13 GNN isolated/ipport crashed (disk).

## Open problem
Is ToN's GNN gain topology, host profile or window composition? Best hypothesis: window composition (K06). Decided by ToN `--context window` vs `--context host` vs GNN ip 0.937 (A023).

## EXACT next step (research-do, implement → deploy)
1. 00_tabular_baselines.py: add `--xgb-device` (default = --device); run XGB on CPU hist n_jobs 16 for context runs (A011). Test, push.
2. Trainer: optional class-weighted CrossEntropyLoss (`--class-weight balanced`) in 01 (A010; src/training/trainer.py:49). Test, push.
3. Launch E013 = E012 rerun: GPUserver2 (CTU-13 lives there): ToN window, ToN host ip, ctu13 host ip, ctu13 GNN ip/isolated/ipport with class weights; GPUserver1: ToN host ipport. Check `df -h` first; delete data/graphs/* after batch (D09).

## Read next
.mem/experiments/E012-a2c-crashed.md, .mem/codebase.md, .mem/infra.md; code: experiments/00_tabular_baselines.py (rg -n "xgb|device"), src/training/trainer.py:40-60.
