# Strategy (digest of docs/LITERATURE_REVIEW.md, 2026-10-12)

Lit graph: docs/lit-graph/gnn-nids/ (in repo: kg_nodes/edges.jsonl, gap_matrix.json, citation_graph.graphml). Shared lit-graph root: ~/Library/CloudStorage/OneDrive-FCTNOVA/Docencia/Research/lit-graph/ (gnn-nids copied there 2026-10-14; repo copy is the working copy).

## Venue
Computers & Security (main). Stretch: IEEE TIFS/TDSC. Conference route: ACSAC, RAID. Fallback for Avenue #2: Computer Networks / IEEE TNSM.

## Novelty claim
First feature/structure/interaction decomposition of adversarial effects for GNN NIDS; first attacker combining own-flow shaping with injection under one budget; explanation of why feature-derived graphs give no structural robustness while address-derived graphs give it but expose an injection surface.

## Gaps
- G1 k-NN redundancy has no mechanism or attack analysis (only #10 preprint claims redundancy).
- G2 No feature/structure/interaction decomposition anywhere.
- G3 No own-flow-shaping + injection attacker (GIANT = injection only).
- G4 Construction-as-defence untested in NIDS.
- G5 No chronological + same-split XGBoost comparison for endpoint GNNs.

## Closest work (threats to novelty)
- #10 "From Flow Features to Communication Topology" (Preprints.org 2026): CICIoMT2024, window level, RF baseline; k-NN redundancy claim, no mechanism, no attacks.
- GIANT (WWW 2026, doi 10.1145/3774904.3792601): joint injection (endpoints + features of injected flows), injection-only, random 80/20 split, no tabular baselines, no k-NN graphs.
- Venturi et al. 2024 (arXiv 2403.11830): feature and structural attacks evaluated separately; GNN robust to features, one injected flow collapses E-GraphSAGE. Venturi 2025 (NCA): adversarial-training defence.
- R+R ACSAC 2025 / arXiv 2609.12263: critique of unsupervised temporal host-graph GIDS; encoder-free control ranks first on 2/4 datasets; 2 crafted edges evade.
- E-GraphSAGE (Lo et al., NOMS 2022): random 70/30, reported baselines, source IPs remapped. Pujol-Perich 2022: accuracy similar to MLP/RF, robust to size/IAT shifts.

## Strongest baselines (our protocol, results/*.json)
REF lines live in conclusions.md. Literature numbers are on random splits and not comparable (TODO: extract their F1s into REF lines if a comparison table is needed).
