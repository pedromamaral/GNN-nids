# STATE — 2026-10-23 (E020 analysed; ideate → E021/E022/E023 planned)
Branch main (sha: see `git log -1`) · Phase: Avenue #1, Part 3 reframed (D19, D20). Part 1 settled (C1); Part 2 CLOSED negative (K11, K14, D15); C4 superadditivity REFUTED (K15).

## Just done (this session)
- analyze E020: PGD converged (matched-ρ C recall ≤.004 diff at 100 steps / 3 restarts); delay irrelevant (D-row Δ≤.005). GNN ip superadditive only in seed 42 (S β.5ρ.5 +.084; seeds 43-46 −.06..−.12; G≥.03 1/5); MLP host-ip subadditive 5/5; XGB ≈additive (transfer non-monotone). → C4 'separate evaluation suffices'. Seed spread of GNN Δ_A (β .5) .08-.55 ≫ attack noise ≤.01.
- Note: 08 summary `S_max_abs` is unsigned and G is clipped ≥0 — signed S must be recomputed from rows (E021 adds it to 08).
- Files: E020 card (results+verdict), LEDGER E020-E023, K15 revised (high), A012 updated, project.md C4 status, D19, D20; avenues A031 active, A015/A028 active, A032 stealthy decoys + A033 ToN port proposed; cards E021/E022/E023 created.

## Active runs
E021 queue on GPUserver2 (launched 2026-10-23, log logs/queue_E021.log, ends E021_DONE). Impl sha 67a18c8 (08 --no-xgb, signed S cols, clean_stats.json). E022/E023 not yet implemented.

## Open problem
Is GNN robustness to shaping a training-seed lottery (E021, A031)? Plus paper closers C3 (E022) and C1 grid (E023).

## EXACT next step
1. `research-do implement E023` (k-NN 5x5 grid, config-only).
2. `research-do deploy E022` after E021 is running/finished: queue_E022.sh self-waits for E021_DONE on GPUserver2 (launch it early; it sleeps). First 01 run with CTU13_SPLIT=unseen is the real smoke test: check status soon after start.
3. Later: `status`, `fetch E021` / `E022`, then `research-think analyze`.
- Notes: E021 MLP unweighted (E020 caches), GNN cwbal; E022 split in D21 (family-disjoint, host IPs not controlled).

## Read next
STATE + E021/E022/E023 cards + codebase.md + infra.md (for queue scripts); D20; K15.
