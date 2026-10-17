# STATE — 2026-10-17 (research-do status/fetch E014 + research-think analyze E014 + ideate)
Branch main @ 7d88d45 (pushed) · Phase: Avenue #1, A2 (Part 2 go/no-go), C2 on CTU-13 undecided.

## Just done
- E014 finished (E014_DONE), fetched -> .mem/results/E014.json (12 runs seeds 43-46 + graph_ablation 20261016_130624; seed 42 in E013.json). window_counts.npz (630 KB) left on GPUserver2:results/graph_ablation/20261016_130624/.
- Analysed: card E014 (verdict INCONCLUSIVE), LEDGER, A022/A025 -> tried, A023 updated, K12 revised, K13 new.
- Ideate: D14; A026 -> active (E016, card written), A027 -> active (E015), A029 proposed (E017, train-time shuffle).
- Gotcha: zsh does not word-split $var -> use ${=specs} when passing many specs to summarize_run.py.

## Active runs
None. GPUserver1 idle; GPUserver2 idle (31G free). E014 containers/caches: data/graphs/* cleaned by queue.

## Latest results
- CTU-13 (E014, 5 seeds): GNN ip F1 .855±.031 vs isolated .616 / ipport .656 / tabular host-ip ≤.617; seed std .029 (floor .058).
- BUT AUC ip .993 ≈ XGB host-ip .991 < MLP host-ip .996; val gap only +.02/.05; test-time shuffle .39-.49 < isolated (out of distribution) (K13).
- ToN: host behavioural profile, not topology (K11).

## Open problem
Is the CTU-13 F1 gain detection power or 0.5-threshold placement under drift? Best hypothesis: largely threshold/calibration (AUC parity). E016 decides; E015 tests the aggregation explanation.

## EXACT next step
`research-do implement E016` (cheaper model): per-flow score dump flag for GNN eval (15 ckpts) + 00 tabular (XGB/MLP plain & host-ip, 5 seeds), metric/bootstrap script server-side; check identical test flows first. Then `research-do implement E015` (CPU, parallel). E017 only if E016 gap >= .058.

## Read next
.mem/experiments/E016-threshold-free-ctu13.md, E015-neighbour-agg-xgb.md, .mem/codebase.md, D14 in decisions.md, K13 in conclusions.md.
