# E020 Part 3 full: A/B/C decomposition on context detectors, CTU-13 (A012)
Status: IMPLEMENTED 2026-10-18 (D18), smoke running on GPUserver2 (also builds the seed-42 model cache), not deployed. Serves C4, G2, G3. Tests: tests/test_context_attack.py 17 pass (with 00 tests).
## Hypothesis
As E017 (K15) with the D18 confounds controlled: joint gain G = Δ(C*) − max(Δ(A,β), Δ(B,β)) ≥ .03 or |S| ≥ .03 holds on GNN ip in 5/5 training seeds (and is < .03 / negative on host-context tabular), under free delay, with PGD-converged attacks, and on a host-window view.
## Change (on top of E017 code, 8719ee5)
- `--delay-modes free off [coupled]`: free = delay allowed in every condition incl. B and a delay-only row D (β=0); off = bytes only; coupled = E017 pilot. Clean row = no attack. (src/attacks/context_attack.py `delay=`)
- `--restarts R` (best of R random inits per chunk) and `--steps`: PGD strength check.
- Host-window metrics: `hostwin_recall` (group (window, bot host) detected if one of its botnet flows alarms) and `hostwin_recall_dec` (decoys that alarm also count); summaries summary_hostwin*.csv.
- `--model-cache DIR`: MLP/XGB host-ip/XGB plain + scaler fitted once per training seed (boosters saved as json, predictions via Booster + best_iteration); GNN ckpt per seed from E014 (cwbal ip L2).
- 00 train_xgboost exposes `.model`. summarize_run.py reads 08 summary/rows.
## Config
scripts/queue_E020.sh (GPUserver2): seed 42 strength check (steps 100; steps 30 x3 restarts; β .1/.5, ρ 0/.5/1, attack seed 0, delay free) -> compare with the main run's same configs; then seeds 42-46 x attack seeds 0,1 x delay free/off x β .05-.5 x ρ 0-1 (+ budget-matched A/B for S, + B_replay) x 4 detectors. Output results/E020_main/seed_<s>/<ts>/{rows,summary,summary_hostwin,summary_hostwin_dec}.csv.
## Success criterion
- PGD converged: G and Δ_A change by < .01 between 30 steps/1 restart and 100 steps / 3 restarts; else raise steps for the main run and rerun.
- Supported (C4, endpoint GNN): G ≥ .03 at some β in 5/5 training seeds for delay=free AND delay=off, with host-window G reported; Wilcoxon over 5 seeds as in project.md C4.
- Host-context tabular: G < .03 (negative S) replicates -> state as the contrast result. If the GNN G disappears under free delay or host-window view: report 'separate evaluation suffices'.
## Not done / out of scope
ToN (needs a NetFlow-v3 raw-field attack module, separate E id); PR-AUC under attack; defences (A013).
## Results
(pending)
