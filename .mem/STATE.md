# STATE — 2026-10-22 (E019 analysed; E020 fetched, awaiting analysis)
Branch main @ 7b5388a (pushed) · Phase: Avenue #1, Part 3 main thread (D16-D18). Part 1 settled (C1); Part 2 CLOSED negative on both datasets, 5 seeds + PR-AUC (K11, K14, D15).

## Just done (this session)
- status: E019 (GPUserver1) and E020 (GPUserver2) both finished cleanly (logs end E019_DONE / E020_DONE, 0 error lines).
- fetch E019 -> .mem/results/E019.json (15 GNN runs from results/runs/ + 3 tabular; 07 output under key `threshold_free`; 3 `incomplete` entries = scores.npz-only dirs, harmless).
- fetch E020 -> .mem/results/E020.json (main seeds 42-46 + strength_steps100 + strength_restarts3; summary.csv/hostwin/rows.csv metrics, 4576 keys per main run).
- tools/summarize_run.py: fixed ZeroDivisionError in table_metrics (empty group from blank CSV cells).
- analyze E019: SUPPORTED. ToN GNN ip PR-AUC .903 < XGB host-ipport .954 (gap −.051, 5/5, CI [−.115,−.007]); F1@0.5 .883±.096. K11 -> high; A016 tried; REF GNN seed noise filled; project.md C2 closed.

## Active runs
None. Disk: GPUserver1 8 GB free, GPUserver2 31 GB.

## Open problem
Does the GNN-ip joint-attack gain (K15: G .03-.11, S up to +.086, 1 seed) survive free delay off, stronger PGD (steps100 / restarts3), host-window detection, and 5 training seeds? That decides C4.

## EXACT next step
1. (Opus, fresh session) `research-think analyze E020`. Order: (a) strength check — G and Δ_A must move < .01 between steps30 (main seed 42) and steps100 / restarts3; if not, attack is too weak and the main grid is unreliable; (b) delay off vs free; (c) G/S per detector averaged over attack seeds within each training seed, 5/5 rule + Wilcoxon (project.md C4 criterion); (d) host-window summaries (summary_hostwin*.csv).
2. Then `research-think ideate` or `paper-plan` depending on C4 verdict. Later: ToN port of the attack (new E id); close A028.
- Minor TODOs: LEDGER E018 sha placeholder (`71498ca+cw`) -> commit that added `--class-weight`; 07 mismatch dict lacks ip/42 for E019 (check before the ToN table goes into the paper).

## Read next
STATE + E020 card + E017 card + K15 + D17/D18 + project.md C4 criterion; .mem/results/E020.json via a short python aggregation (never print whole file — 4576 keys/run).
