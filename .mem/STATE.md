# STATE — 2026-10-18 (E018 fetched + analysed; E019/E020 running)
Branch main @ 6fba678 (pushed) · Phase: Avenue #1, Part 3 main thread (D16-D18). Part 1 settled (C1), Part 2 negative (D15, now on every metric).

## Just done (this session)
- E018 fetched: .mem/results/E018.json (tabular summaries + 07 output under key `threshold_free`; local copy runs/E018/E018_threshold_free.json). Note: .mem/results/ is gitignored (local only).
- E018 analysed: SUPPORTED (A030 tried). Class-weighted tabular closes GNN F1@0.5 gap +.199 → +.051 (CI [−.035,+.139], 3/5 seeds); PR-AUC gap −.074 vs MLP host-ip cw (CI excl 0). K14 revised; card + LEDGER written.
- E020 checked: queue alive on GPUserver2 at 19:45 (tab aseed=1 delay=off rows); ssh launcher exit 255 was harmless.
- TODO: LEDGER E018 sha is a placeholder (`71498ca+cw`) — replace with the commit that added `--class-weight`.

## Active runs
- E019 | GPUserver1 | queue:queue_E019.sh | 15 GNN trainings (~85 min each) then 06/00/07 | ETA ~Mon 10-19 12:00-14:00 server clock | log logs/queue_E019.log (ends E019_DONE). RISK: disk ~5 GB free.
- E020 | GPUserver2 | queue:queue_E020.sh | seed-42 strength checks (steps100, restarts3) then main grid seeds 42-46 | ETA ~10-19 morning-midday | log logs/queue_E020.log (ends E020_DONE).

## Open problem
Does the GNN-ip joint-attack gain (K15) survive free delay off, stronger PGD (100 steps / 3 restarts), host-window detection, and 5 training seeds? That decides C4.

## EXACT next steps (cheap model for do-phases, /clear between phases)
1. `research-do status` (when ETAs pass) → `research-do fetch E019` / `fetch E020` (E020: summarize_run reads 08 summary*.csv + rows.csv).
2. (Opus) `research-think analyze E019`, then `analyze E020` (strength check first: G, Δ_A must move < .01 between steps30 and steps100/restarts3).
Later: ToN port of the attack (NetFlow-v3 raw fields, new E id); paper-plan (Parts 1-2 settled); close A028 (covered by scenario-disjoint CTU-13 split).

## Read next
STATE + runs.md + infra.md (status/fetch); E019 card + E016/E018 cards (E019 analysis); E020 card + K15 + D17/D18 (E020 analysis).
