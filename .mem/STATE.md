# STATE — 2026-10-29 (E021+E022 analysed; strategy → D22 reframe; E023 running)
Branch main (sha: see `git log -1`) · Phase: Avenue #1, closers before paper-plan. Part 1 C1 pending E023; C2 negative (K11, K14); C3 closed (K17); C4 'separate suffices' (K15); seed lottery (K16).

## Just done (this session)
- analyze E021: GNN-ip Δ_A β.5 .388±.180 over 15 seeds (CV .46, ×30, attack noise ≤.006). No clean/val predictor |ρ|>.54. MLP host-ip CV .10, ρ .93 with clean recall. G≥.03 1/15 → K15 holds. New K16.
- summarize_run.py: clean_stats merge bug fixed (limit=100 hit by 360 table metrics; commit b6ad608). E021.json re-fetched (5575 metrics).
- analyze E022 (unseen families 6/7/8/12): PR-AUC XGB host-ip .670 vs plain .117 (+.55, 5/5); GNN ip .129 ≈ plain. Leakage refuted, C3 closed → K17. Bootstrap CIs not in JSON (fetch TODO).
- strategy: D22 reframes the paper as evaluation-methodology (k-NN redundant · host context not topology · separate eval suffices · seed lottery). New title placeholder in project.md. strategy.md revised: G6 + underspecification novelty threat + publishability table, verdict iterate.
- Files: E021/E022 cards, LEDGER (E021, E022, E024 planned), conclusions K15 rev, K16, K17; avenues A028/A031 tried, A015/A033 needed-for-paper, A034 parked; project.md C3/C4/title; decisions D22; new card E024-ton-part3.md.

## Active runs
- E023 GPUserver1 (k-NN 5×5 grid UNSW GCN+GAT, queue_E023.sh, log logs/queue_E023.log ends E023_DONE), started 10-29 ~21:42 server clock, ETA unmeasured.

## Open problem
Do K15 (separate suffices) and K16 (seed lottery) generalise beyond CTU-13? → E024 (ToN port of Part 3, A033). Is K16 novel given underspecification (D'Amour et al.)? → strategist revision.

## EXACT next step
1. `research-do implement E024` (cheaper model): port 08 joint attack to NetFlow-v3 ToN features (card E024-ton-part3.md, spec D17).
2. `research-do status` → when E023_DONE: `research-do fetch E023`, then `research-think analyze E023`.
3. Pedro in Cowork: `research-strategist` revision (underspecification + NIDS evaluation-pitfall literature), pointing to .mem/avenues.md + .mem/conclusions.md.
4. After E023 + E024: `research-think paper-plan` (paper.md is stale: still says C2 OPEN / C4 not started).
- Small TODO: re-export E022 block-bootstrap CIs into E022.json.

## Read next
STATE + E024 card + D17 + D22 + codebase.md + infra.md (for implement); K15, K16.
