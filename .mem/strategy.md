# Strategy (digest of docs/LITERATURE_REVIEW.md, 2026-10-12; revised 2026-10-29 after D22)

Lit graph: docs/lit-graph/gnn-nids/ (in repo: kg_nodes/edges.jsonl, gap_matrix.json, citation_graph.graphml). Shared lit-graph root: ~/Library/CloudStorage/OneDrive-FCTNOVA/Docencia/Research/lit-graph/ (gnn-nids copied there 2026-10-14; repo copy is the working copy). No strategy-plan.md yet → run research-strategist (revision) in Cowork, pointing to .mem/avenues.md + .mem/conclusions.md.

## Venue
Computers & Security (main). Stretch: IEEE TIFS/TDSC. Conference route: ACSAC, RAID. Fallback for Avenue #2: Computer Networks / IEEE TNSM.

## Novelty claim (D22 reframe)
Evaluation-methodology paper on GNN-NIDS. Same chronological split, identity hidden, tabular host-context controls, multi-seed and threshold-free metrics show:
(1) feature-derived k-NN graphs are redundant: no structural gain, and attack-induced rewiring has no effect (G1);
(2) endpoint-GNN gains are host context, not topology. Tabular host context beats them and transfers to unseen botnet families, the GNN does not (G5);
(3) the first equal-budget A/B/C decomposition with a joint shaping+decoy attacker finds separate evaluation suffices: joint ≈ best single attack, subadditive on host context (G2, G3);
(4) GNN shaping robustness varies ×30 across training seeds and no clean/val metric predicts it, so single-seed robustness claims are unreliable (G6).

## Gaps
- G1 k-NN redundancy has no mechanism or attack analysis (only #10 preprint claims redundancy).
- G2 No feature/structure/interaction decomposition anywhere.
- G3 No own-flow-shaping + injection attacker (GIANT = injection only).
- G4 Construction-as-defence untested in NIDS (parked, A013).
- G5 No chronological + same-split XGBoost comparison for endpoint GNNs.
- G6 (2026-10-29) GNN-NIDS robustness papers report 1 training seed. Seed variance of adversarial robustness is unmeasured in NIDS. **Novelty threat:** underspecification (D'Amour et al., JMLR 2022) shows the general phenomenon. Our contribution is the NIDS/GNN instance + the contrast with tabular (CV .46 vs .10) + val-unpredictability. Must cite and position. Verify in the strategist revision.

## Closest work (threats to novelty)
- #10 "From Flow Features to Communication Topology" (Preprints.org 2026): CICIoMT2024, window level, RF baseline; k-NN redundancy claim, no mechanism, no attacks.
- GIANT (WWW 2026, doi 10.1145/3774904.3792601): joint injection (endpoints + features of injected flows), injection-only, random 80/20 split, no tabular baselines, no k-NN graphs.
- Venturi et al. 2024 (arXiv 2403.11830): feature and structural attacks evaluated separately; GNN robust to features, one injected flow collapses E-GraphSAGE. Venturi 2025 (NCA): adversarial-training defence.
- R+R ACSAC 2025 / arXiv 2609.12263: critique of unsupervised temporal host-graph GIDS; encoder-free control ranks first on 2/4 datasets; 2 crafted edges evade. Closest in spirit to the D22 framing (methodology critique) → differentiate: supervised flow-level GNNs, adversarial decomposition, seed variance.
- Arp et al., Dos and Don'ts of ML in Computer Security (USENIX Sec 2022, doi 10.48550/arxiv.2010.09470): pitfall taxonomy. Our findings instantiate it for GNN-NIDS.
- E-GraphSAGE (Lo et al., NOMS 2022): random 70/30, reported baselines, source IPs remapped. Pujol-Perich 2022: accuracy similar to MLP/RF, robust to size/IAT shifts.
- To check in revision: underspecification (D'Amour et al.); NIDS benchmark-flaw papers since 2023; any GNN-NIDS work reporting seed variance or unseen-family splits.

## Publishability check (2026-10-29)
| item | status |
|---|---|
| novelty | G1-G3, G5 open; G6 novel for NIDS only (underspecification) |
| vs literature | literature numbers are random-split → not comparable; same-split controls are our point |
| effect vs noise | K11/K14/K15/K16/K17 ≫ seed noise (5-15 seeds); C1 1 seed → E023 |
| missing | E023 (C1 seeds), E024 ToN Part 3 (A033); E022 bootstrap CIs (fetch TODO); 2nd GNN parked (A034) |
| reproducibility | configs/queue scripts/shas per run; fixed protocol D03/D04/D06 |
| venue fit | good as a methodology paper (D22) |
Verdict: **iterate** (E023, E024) → paper-plan.

## Strongest baselines (our protocol, results/*.json)
REF lines live in conclusions.md. Literature numbers are on random splits and not comparable (TODO: extract their F1s into REF lines if a comparison table is needed).
