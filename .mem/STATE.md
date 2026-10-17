# STATE — 2026-10-16 (research-do status/implement/deploy E014)
Branch main @ ccbb316 (pushed) · servers at 5be087d+ · Phase: Avenue #1, A2 (Part 2 go/no-go), E014 running.

## Just done
- E014 queue_E014.sh: 01 ctu13 cwbal {ip,isolated,ipport} x seeds 43-46 (12 runs) finished on GPUserver2; step 06 crashed (cuda tensor .numpy() in window_counts).
- Fixed 06_graph_ablation.py lines 129,160 (.cpu()), sha 3ec549a; card note added.
- Relaunched 06 only: queue_E014b.sh on GPUserver2 (started 10-16 ~13:22 server clock; pytest, 06 --save-window-counts on seeds 42-46 ckpts, rm data/graphs/*). runs.md row = running.

## Active runs
E014b on GPUserver2. Done when logs/queue_E014b.log ends E014_DONE (check tools/runs_status.sh). GPUserver1 idle (12G free), GPUserver2 31G free.

## Latest results (unchanged, from E013)
- ToN: XGB host-ipport .931 ≈ GNN ip .937 -> host profile, not topology (K11).
- CTU-13: GNN cwbal ip .844 vs isolated .639 / ipport .675 / tabular .617 (seed 42 only) -> possible topology (K12); E014 tests with 5 seeds + shuffle.

## Open problem
Is the CTU-13 GNN gain real topology? E014 (A022, A025). C2/C4 thresholds in project.md still await Pedro's OK.

## EXACT next step
`research-do implement E016` (card E016-threshold-free-ctu13.md, D14); E015 implement next (CPU, parallel). E017/A029 only if E016 gap survives.

## Read next
.mem/experiments/E014-ctu13-seeds-shuffle.md, E015 card, .mem/avenues.md (A022, A025, A026), .mem/project.md (C2 thresholds).
