# E020 Part 3 full: A/B/C decomposition on context detectors, CTU-13 (A012)
Status: ANALYSED 2026-10-23 — REFUTED for GNN superadditivity (K15 revised, D19). Serves C4, G2, G3. Tests: tests/test_context_attack.py 17 pass (with 00 tests).
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
## Results (.mem/results/E020.json; Δ = clean recall@1%FPR − attacked; attack seeds 0/1 averaged within training seed)
- PGD converged: at matched (β,ρ) C recall differs ≤.004 between 30 steps / 100 steps / 3 restarts; Δ_A ≤.008, Δ_B ≤.011. The apparent G drop (.062→.045 at β .1) is the coarser ρ grid (0/.5/1) in the strength runs, not attack weakness.
- Delay irrelevant: delay-only D row Δ ≤.005 on all detectors; free vs off change S by ≤.02.
- GNN ip, signed S at β .5, ρ .5 (seeds 42-46): +.084 −.074 −.116 −.064 −.063; G ≥ .03 in 1/5 seeds (42 only), mean G .022 (free) / .019 (off). Seed 42 is the most shaping-robust model (Δ_A β .5: .08 vs .28-.55 in 43-46), so decoys mattered there only.
- MLP host-ip: S < 0 in 5/5 seeds at every β, ρ (β .5 ρ .5: −.076..−.155); G ≈ 0 (shaping saturates, Δ_A ≈ .5).
- XGB host-ip (transfer from MLP surrogate): S mostly negative per flow; G ≥ .03 in 2-3/5 seeds at β ≥ .25 because transferred A is non-monotone in β (seed 44 Δ_A β .5 = −.015) — transfer artefact, not interaction.
- XGB plain: B ≈ 0 (decoys irrelevant), G ≈ 0, S ≈ +.01.
- Host-window (GNN): S signs mixed (β .5 ρ .5: +.025 −.028 −.044 −.026 +.059); with decoy alarms counted, same picture. Decoy alarm rate at β .5: GNN .21-.44, XGB host-ip .30-.39, MLP .07-.14.
- Training-seed variance of GNN shaping vulnerability is large (Δ_A β .5 range .08-.55) vs attack-seed noise ≤.01.
## Verdict
REFUTED (C4 superadditive branch): joint shaping+decoy is not superadditive on the endpoint GNN (1/5 seeds); it is subadditive on host-context MLP (5/5) and ≈ additive / transfer-noisy on XGB. Equal-budget separate evaluation (best of A, B) is within .03 of the joint attack in 4/5 GNN seeds → C4 lands on the "separate evaluation suffices" branch. K15 superadditivity was a seed-42 artefact.
