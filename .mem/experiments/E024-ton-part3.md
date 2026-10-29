# E024 ToN port of Part 3 joint shaping+decoy attack (A033)
Status: PLANNED 2026-10-29 (D22, needed-for-paper). Serves C4 generality, K15/K16.
## Hypothesis
On NF-ToN-IoT-v3, as on CTU-13 (K15, K16): (a) at equal byte budget the joint attack ≈ best single attack on GNN ip (G ≥ .03 in ≤ 1/5 seeds) and is subadditive on host-context tabular; (b) GNN-ip shaping vulnerability Δ_A varies across training seeds far more than attack noise (CV ≥ .3), while MLP/XGB host-ip stays tight.
## Change
- Port the 08 joint attack (E017/E020 spec D17) to NetFlow-v3 features: map the raw controllable fields (bytes, packets, duration twins of Dur/TotPkts/SrcBytes) with increase-only shaping in raw space; decoys from bot hosts to popular benign destinations; operating point 1% FPR.
- Detectors: GNN ip (E019 settings), MLP host-ip, XGB host-ip (transfer). Delay off (K15). β .1/.5, ρ 0/.5/1. 5 training seeds (10 if the ToN spread is ambiguous) × 2 attack seeds; signed S, clean_stats.json.
## Config
(implement: cfg / queue_E024.sh; ToN data location per infra.md)
## Success criterion
- K15 replicates: G ≥ .03 in ≤ 1/5 GNN seeds, S < 0 on host-ip 5/5.
- K16 replicates: GNN CV(Δ_A, β .5) ≥ .3 and MLP CV < .15.
- Either fails → report a dataset dependence (no claim of generality).
## Results
(pending)
