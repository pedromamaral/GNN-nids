# STATE — 2026-11-04 (E024 analysed: INCONCLUSIVE; E025 planned)
Branch main, sha 5b59860 (+ uncommitted .mem edits) · Phase: Avenue #1 closers before paper-plan. Part 1 C1 pending E023 analysis; C2 negative (K11, K14); C3 closed (K17); C4 'separate suffices' (K15, CTU-13 only); seed lottery (K16, CTU-13 only).

## Just done (this session)
- analyze E024 → INCONCLUSIVE (K18). On ToN the 1%-FPR threshold (0.99 quantile of float32 sigmoid probs of TEST benign) is degenerate. Clean recall@1%FPR: GNN ≤.08, MLP ≈0 (thr 1.000), XGB host-ip ≤.12, plain ≤.19 (recall@.5 is .58-.99). Attack deltas are floored, so K15/K16 are untested on ToN, not refuted.
- Code issues (08:152-192): probs not logits; tally `>=` vs clean_stats `>`; no tie handling.
- D23: run the E025 diagnostic (A037, active) before any ToN rerun. Card E025 written with a decision rule. A033 → tried.
- Note: an A036 already existed (seed ensemble, proposed), so the operating-point avenue is A037.
- Files: E024 card, E025 card (new), LEDGER E024/E025, conclusions K18, avenues A033/A037, decisions D23. tools/summarize_run.py has uncommitted local changes (E023 fetch, other session).

## Active runs
None. E023 fetched 11-02 (.mem/results/E023.json, aggregated only), not analysed. runs_status.sh wrongly prints queues as "ended" while alive — check pgrep.

## Open problem
Is the ToN low-FPR floor caused by saturation (fixable on logits) or by a drifted benign tail (K10/K11)? This decides the E026 rerun (1% FPR on logits vs 5% FPR / matched recall vs limitation). Is K16 novel given underspecification (D'Amour et al.)?

## EXACT next step
1. E025 IMPLEMENTED (sha 30b3d11, not pushed/smoke-tested). Next: push origin main, pull on GPUserver1, `SMOKE=1 scripts/queue_E025.sh`, then `research-do deploy E025`. [was: implement E025 (cheap model)]: clean-only scoring on logits, val- vs test-benign thresholds, tie fraction; also patch 08 to use logits and `>=` in both places. Deploy on GPUserver1 (~1 GPU-h), fetch → `research-think analyze E025` → E026 per the card's decision rule.
2. `research-think analyze E023` (C1).
3. `research-do implement A035` (host-disjoint check of E022).
4. `research-think paper-plan` (paper.md stale). Small TODO: re-export E022 block-bootstrap CIs.
- Caveats: GPUserver1 disk ~4.6 GB free.

## Read next
STATE + INDEX; E025 card, K18, D23; codebase.md for 08 (experiments/08_context_decomposition.py:152-192, 409-413).
