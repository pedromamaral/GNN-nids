# STATE — 2026-10-17 (research-do implement/deploy/fetch E016 + research-think analyze E016 + ideate)
Branch main (pushed) · Phase: Avenue #1. Part 2 closed negative (D15); main thread → Part 3 (D16).

## Just done
- E016 implemented (71498ca: --save-scores in 00/06, experiments/07_threshold_free.py), run, fetched -> .mem/results/E016.json. REFUTED: PR-AUC GNN ip .855 < MLP host-ip .953 (5/5, all scenarios); F1@0.5 gain = threshold placement (K14).
- D15: C2 negative on ToN + CTU-13 ("context, not topology"). D16: drift correction → Part 3; E015/A027 parked; A029 dropped.
- Cards: E017 (Part 3 spec + pilot), E018 (class-weighted tabular CTU-13), E019 (ToN GNN 5 seeds + PR-AUC).
- Gotcha: src/data/ is read-denied for Claude; flow alignment checked by labels in 07 instead.

## E018 implemented (sha below), awaiting deploy
Next: `research-do deploy E018` (verify E016 npz glob names first).

## Active runs
None. Both servers idle.

## Experiments left before writing (in order)
1. E018 (CPU, ~2 h) and E019 (GPUserver1, ~8-10 GPU-h est.) — background closers for Part 2.
2. E017 — Part 3 spec written in the card FIRST (think phase), then code + CTU-13 seed-42 pilot.
3. E020 — Part 3 full: 5 training seeds × ≥2 attack seeds × 3 budgets × 4 detectors, CTU-13 + ToN.
4. E021 — Part 1 robustness: k-NN decomposition 5 training × 5 attack seeds (A015).
5. Check A028 is already covered by D06's scenario-disjoint split (test 9/10/13 unseen); close or define.
Optional: A013 construction/robust-aggregation defence (C5) after E020.

## EXACT next step
`research-do implement E018` (cheaper model), then `research-do implement E019`; in parallel `research-think` on the strongest model to finish the E017 spec (threat model, controllable features, cost λ, budgets) before any Part 3 code.

## Read next
.mem/experiments/E017-part3-spec-pilot.md, E018-*.md, E019-*.md, D15-D16 in decisions.md, K14 in conclusions.md.
