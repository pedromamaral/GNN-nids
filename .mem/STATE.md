# STATE — 2026-11-05 (E023 analysed: SUPPORTED on UNSW, eps ≤.10)
Branch main, sha dab1cbd (+ uncommitted .mem edits and .claude/settings.json) · Phase: Avenue #1 closers before paper-plan. C1 structure half firm on UNSW (K05), K04 ablation still 1 seed; C2 negative (K11, K14); C3 closed (K17); C4 'separate suffices' (K15, CTU-13 only); seed lottery (K16, CTU-13 only).

## Just done (this session)
- analyze E023 → SUPPORTED, UNSW GCN+GAT, eps .05/.10, 5×5 (K05 edited). Structure effect ≤.0028 (cells ≤.0032), adaptive gain ≤.0038 (training-seed analytic ceiling .028 < .03; assumes complete grid), feature ΔF1 ≤.035.
- Caveats: JSON is aggregates only; structure effect is 37-63% of GCN feature effect (small in absolute F1 only); budgets are weak; E023 did NOT run ablation (K04), ToN or eps >.10. 05b's Wilcoxon pools n=25, unlike the card's training-seed test.
- A015 → tried. D24: A038 (5-seed k-NN ablation) runs before paper-plan, as E027 (E026 reserved for the ToN rerun).
- Files: E023 card (attack seeds corrected to 42-46), E027 card (new), LEDGER E023/E027, conclusions K05, avenues A015/A038, decisions D24.
- .claude/settings.json: deny rule `Read(./results/**)` now uses the absolute path of top-level results/, because it blocked .mem/results/. Uncommitted, Pedro to review.

## Active runs
None recorded in this session's reading. runs_status.sh wrongly prints queues as "ended" while alive — check pgrep.

## Open problem
Is the ToN low-FPR floor caused by saturation (fixable on logits) or by a drifted benign tail (K10/K11)? This decides the E026 rerun. Is K16 novel given underspecification (D'Amour et al.)?
## EXACT next step
1. E025 IMPLEMENTED (sha 30b3d11, not pushed/smoke-tested, per previous STATE). Next: push origin main, pull on GPUserver1, `SMOKE=1 scripts/queue_E025.sh`, then `research-do deploy E025`; fetch → `research-think analyze E025` → E026 per the card's decision rule.
2. `research-do implement E027` (A038, D24, required before paper-plan): 5-seed k-NN ablation + per-seed decomposition.csv and churn fetch for E023. Then deploy, fetch, `research-think analyze E027`.
3. `research-do implement A035` (host-disjoint check of E022).
4. `research-think paper-plan` (paper.md stale: F1 row says ablation needs A015, but E023 did not run it). Small TODO: re-export E022 block-bootstrap CIs.
- Caveats: GPUserver1 disk ~4.6 GB free.

## Read next
STATE + INDEX; E025 card, K18, D23. For C1: E027 card, E023 card, K04, K05, D24.
