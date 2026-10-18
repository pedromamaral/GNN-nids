# STATE — 2026-10-18 (E020 deployed; E017 implement→deploy→analyze; E018/E019 deploy)
Branch main @ b75daf1 (pushed) · Phase: Avenue #1, Part 3 main thread (D16-D18). Part 1 settled (C1), Part 2 negative (D15).

## Just done (this session)
- E017: src/attacks/context_attack.py + experiments/08_context_decomposition.py (8719ee5); pilot run + fetched (.mem/results/E017.json) + analysed: GO (K15, D18). GNN ip superadditive (G .03-.11, S up to +.086); host-context MLP/XGB subadditive (G ≤.023, S down to −.118); plain XGB B=0 (sanity).
- E020 implemented (D18): `--delay-modes free off [coupled]`, `--restarts`, host-window recall (summary_hostwin*.csv), `--model-cache`; 00 train_xgboost/train_mlp expose `.model`; tests/test_context_attack.py 17 pass (with 00 tests). Smoke PASSED on GPUserver2; seed-42 model cache at results/E020_models/seed_42. Card .mem/experiments/E020-part3-full.md. scripts/queue_E020.sh ready.
- E018 deployed + FINISHED (glob fix in scripts/queue_E018.sh); 07 ran, 0 label mismatches; results/E018_threshold_free.json on GPUserver2, NOT fetched.
- E019 implemented (scripts/queue_E019.sh, config-only) + deployed on GPUserver1.
- tools/summarize_run.py: reads 08 summary*.csv + rows.csv (limit 20000 keys); tabular branch skips dirs with rows.csv.

## Active runs
- E019 | GPUserver1 | queue:queue_E019.sh | 4th of 15 GNN trainings (ip seed 45) at 18:00; ~85 min/training → ETA ~Mon 10-19 12:00-14:00 server clock | log logs/queue_E019.log (ends E019_DONE). RISK: disk 5.2 GB free (caches cleared per node key).
- E020 | GPUserver2 | queue:queue_E020.sh (launched 10-18, container started) | seed-42 strength checks (steps100, restarts3) then main grid seeds 42-46 | ETA ~15-16 h | log logs/queue_E020.log (ends E020_DONE) | registered in runs.md.

## Open problem
Does the GNN-ip joint-attack gain (K15) survive free delay for every condition, stronger PGD (100 steps / 3 restarts), host-window detection, and 5 training seeds? That decides C4.

## EXACT next steps (cheap model for 1-2, /clear between phases)
1. (done) E020 deployed.
2. (done) E018 fetched -> .mem/results/E018.json (tabular summaries + 07 output under `threshold_free`; local copy runs/E018/E018_threshold_free.json).
3. (Opus) `research-think analyze E018`; later fetch/analyze E019, then E020 (strength check first: G, Δ_A must move < .01).
Later: ToN port of the attack (NetFlow-v3 raw fields, new E id); paper-plan (Parts 1-2 settled); A028 likely covered by the scenario-disjoint CTU-13 split (close it).

## Read next
STATE + runs.md + infra.md (deploy); E018 card + E016 card (fetch/analyze); E020 card + K15 + D18 (E020 analysis).
