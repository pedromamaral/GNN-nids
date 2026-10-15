# STATE — 2026-10-15 (research-do status/fetch E013 + research-think analyze E013)
Branch main @ 1d01249 (pushed) · servers at abd90c1+ (30 tests pass) · Phase: Avenue #1, A2 (Part 2 go/no-go), E013 analysed.

## Just done
- E013 finished on both servers; fetched to .mem/results/E013.json (7 runs); runs.md cleared.
- Analysis: card, LEDGER, K11/K12 (K06, K09 updated), A009-A011 tried, A023 active, A025/A026 added, D11.
- data/graphs/* already empty on both servers (nothing to clear). Disk free: GPUserver1 11G, GPUserver2 31G.

## Active runs
None (no containers).

## Latest results
- ToN: XGB host-ipport .931 ≈ GNN ip .937 (Δ+.006 < .02) and shuffled-dst .940 → host profile, not topology (K11). Window ctx hurts.
- CTU-13: GNN cwbal ip .844 vs isolated .639 / ipport .675 / best tabular .617 (seed 42 only) → possible topology effect (K12).

## Open problem
Is the CTU-13 GNN gain real topology? Needs 5 seeds (A022) + shuffled-endpoint ablation (A025) to test C2(b)(c)(d). Framing leaning dataset-dependent (D11). C2/C4 thresholds in project.md still await Pedro's OK.

## EXACT next step
`research-think ideate` (or go straight to `research-do implement`): CTU-13 only — 5-seed cwbal GNN ip/isolated/ipport (A022) + 06 shuffle ablation on the ip checkpoint on GPUserver2 (A025). Consider A026 (PR-AUC / tuned threshold) for ToN drift.

## Read next
.mem/experiments/E013-a2c-rerun.md, .mem/avenues.md (A022, A025, A026), .mem/project.md (C2 thresholds).
