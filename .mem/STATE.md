# STATE — 2026-10-17 (E016 implement→analyze, ideate D16, E017 spec D17)
Branch main @ a268e4a (pushed) · Phase: Avenue #1. Part 2 closed negative (D15); main thread → Part 3 (D16, D17).

## Just done
- E016 (71498ca: --save-scores in 00/06, experiments/07_threshold_free.py) run + fetched -> .mem/results/E016.json. REFUTED: PR-AUC GNN ip .855 < MLP host-ip .953 (5/5 seeds, all scenarios); F1@0.5 gain = threshold placement (K14).
- D15: C2 negative on ToN + CTU-13 ("context, not topology"); project.md C2 status updated. D16: drift correction → Part 3; A027/E015 parked, A029 dropped; A012/A016/A030 active.
- D17 + E017 card: Part 3 spec fixed (bytes cost β, raw-space increase-only shaping of Dur/TotPkts/SrcBytes, optimised decoys, 1% FPR operating point, equal-budget G/S metrics; C4 revised in project.md).
- E018 implemented in a parallel session (1be1da7: 00 --class-weight balanced + queue script), not deployed.
- Permissions: src/data/ now readable (Pedro changed the .claude/settings.json deny to absolute //…/data/**; UNCOMMITTED in working tree).

## Active runs
None. Both servers idle.

## Experiments left before writing (in order)
1. E018 (CPU ~2 h) + E019 (GPUserver1, ~8-10 GPU-h est.): Part 2 closers.
2. E017: code src/attacks/context_attack.py + experiments/08_context_decomposition.py, then CTU-13 seed-42 pilot (~3 GPU-h).
3. E020: Part 3 full (5 training seeds × ≥2 attack seeds × 4 β × 5 ρ × 4 detectors, CTU-13 + ToN).
4. E021: Part 1 k-NN decomposition 5 × 5 seeds (A015).
5. A028: check if D06 scenario-disjoint split already covers it; close or define.
Optional: A013 defence (C5) after E020.

## Open problem
Does a joint shaping+injection attacker beat separate evaluation on context detectors (C4)? Only remaining novelty (G2/G3).

## EXACT next step
Commit .claude/settings.json if it should be shared. Then (cheaper model) `research-do deploy E018` (verify E016 npz glob names first), `research-do implement E019`, `research-do implement E017`.

## Read next
.mem/experiments/E017-part3-spec-pilot.md, E018-*.md, E019-*.md, D15-D17 in decisions.md, K14 in conclusions.md.

## 2026-10-18 update (research-do)
- E017 pilot finished and fetched: .mem/results/E017.json (160 metrics; dir results/E017_pilot/20261017_222359 on GPUserver2). 08 + context_attack implemented (8719ee5), tools/summarize_run.py now reads 08 summary.csv.
- E017 analysed: GO (K15, D18). EXACT next step: `research-do implement E020` per D18 (delay-only condition, PGD steps/restarts check on seed 42 first, host-window recall, 5 training seeds CTU-13); E018/E019 deploy still pending (CPU / GPUserver1, can run in parallel).
