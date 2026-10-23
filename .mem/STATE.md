# STATE — 2026-10-23 (E020 analysed; ideate → E021/E022/E023 planned)
Branch main (sha: see `git log -1`) · Phase: Avenue #1, Part 3 reframed (D19, D20). Part 1 settled (C1); Part 2 CLOSED negative (K11, K14, D15); C4 superadditivity REFUTED (K15).

## Just done (this session)
- analyze E020: PGD converged (matched-ρ C recall ≤.004 diff at 100 steps / 3 restarts); delay irrelevant (D-row Δ≤.005). GNN ip superadditive only in seed 42 (S β.5ρ.5 +.084; seeds 43-46 −.06..−.12; G≥.03 1/5); MLP host-ip subadditive 5/5; XGB ≈additive (transfer non-monotone). → C4 'separate evaluation suffices'. Seed spread of GNN Δ_A (β .5) .08-.55 ≫ attack noise ≤.01.
- Note: 08 summary `S_max_abs` is unsigned and G is clipped ≥0 — signed S must be recomputed from rows (E021 adds it to 08).
- Files: E020 card (results+verdict), LEDGER E020-E023, K15 revised (high), A012 updated, project.md C4 status, D19, D20; avenues A031 active, A015/A028 active, A032 stealthy decoys + A033 ToN port proposed; cards E021/E022/E023 created.

## Active runs
None. Disk: GPUserver1 7.6 GB free (clean data/graphs/* before E022/E023), GPUserver2 31 GB.

## Open problem
Is GNN robustness to shaping a training-seed lottery (E021, A031)? Plus paper closers C3 (E022) and C1 grid (E023).

## EXACT next step
1. (cheaper model) `research-do implement E021` — config/queue only: seeds 47-56 GNN cwbal ip + MLP host-ip cache; 08 reduced grid (gnn_ip, mlp_host_ip; delay off; β .1/.5; ρ 0/.5/1 + budget-matched A/B; attack seeds 0,1); add signed S per ρ to 08 summary; save clean_stats.json per seed. Target GPUserver2.
2. Same session or next: `research-do implement E022` (CTU-13 unseen-scenario split; record split choice as D#) and `implement E023` (k-NN 5×5 grid, config-only); target GPUserver1 sequentially.
3. After results: `research-think analyze E021` → then `research-think strategy` (paper is becoming an evaluation-methodology paper) → `paper-plan`.
- Minor TODOs: LEDGER E018 sha placeholder (`71498ca+cw`); 07 mismatch dict lacks ip/42 for E019.

## Read next
STATE + E021/E022/E023 cards + codebase.md + infra.md (for queue scripts); D20; K15.
