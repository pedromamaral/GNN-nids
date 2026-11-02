# STATE — 2026-11-02 (E024 fetched; E023 finished, not fetched)
Branch main, sha 5b59860 (+ this commit) · Phase: Avenue #1 closers before paper-plan. Part 1 C1 pending E023 analysis; C2 negative (K11, K14); C3 closed (K17); C4 'separate suffices' (K15); seed lottery (K16).

## Just done (this session)
- implement E024 (sha 12fab85): `Space` abstraction in src/attacks/context_attack.py (CTU13_SPACE default, netflow_space for ToN); 08 `--dataset nf-ton-iot-v3`; scripts/queue_E024.sh (SMOKE=1 mode); tests TestNetflowSpace (193 pass on GPUserver1; test_k_sensitivity failure is pre-existing, Trainer mock/yaml).
- smoke clean (MLP torch-vs-00 diff 2.3e-4) -> deploy -> E024_DONE 10-31 00:16 server clock (~1.2 h/seed) -> fetch: .mem/results/E024.json, 5 runs (s42-s46), 732 metrics each incl. clean_stats. No interpretation yet.
- Files: card E024 (spec, limitation L1), LEDGER E024, runs.md, codebase unchanged (module map same; 08 now dataset-generic).

## Active runs
None. E023 (GPUserver1, k-NN 5x5 UNSW GCN+GAT) finished (E023_DONE in logs/queue_E023.log), fetched 11-02 (.mem/results/E023.json; summarize_run.py now reads decomposition_effects.csv). runs_status.sh wrongly prints queues as "ended" while alive (matches first container name) — check pgrep.

## Open problem
Do K15 / K16 generalise to ToN? (E024 criteria in card: K15 G>=.03 in <=1/5 GNN seeds and S<0 on host-ip 5/5; K16 GNN CV(Delta_A, beta .5)>=.3 and MLP CV<.15; else report dataset dependence.) Is K16 novel given underspecification (D'Amour et al.)?

## EXACT next step
1. `research-think analyze E024` and `analyze E023` (E023.json has only the aggregated report; per-seed dirs under GPUserver1:results/decomposition/<ts>_..._seed_N can be fetched if analysis needs seed spread; use bash for multi-spec calls, zsh doesn't word-split) (strong model, one phase per session).
2. `research-do implement A035` (host-disjoint check: does E022 have per-flow scores + src IPs, else re-score ckpts).
3. Then `research-think paper-plan` (paper.md stale: still says C2 OPEN / C4 not started). Small TODO: re-export E022 block-bootstrap CIs into E022.json.
- Caveats: GPUserver1 disk ~4.6 GB free; results/E024_models and E024_smoke are small. Fix runs_status.sh queue detection (optional).

## Read next
STATE + INDEX; E024 card + results/E024.json via summarize (never cat); K15, K16, D17, D22; strategy-plan.md (docs/lit-graph/gnn-nids/).
