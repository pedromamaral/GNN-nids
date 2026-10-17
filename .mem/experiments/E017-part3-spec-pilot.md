# E017 Part 3 threat/cost model + A/B/C pilot on context detectors, CTU-13 (A012)
Status: PLANNED (D16). Serves C4, G2, G3.
## Hypothesis
At equal traffic-cost budget, separate evaluation misjudges context detectors: |ΔF1(C) − ΔF1(A) − ΔF1(B)| ≥ .03, or the joint attack beats the best separate attack by ≥ .03 (C4 threshold, D12). Pilot: 1 training seed, ≥2 attack seeds — go/no-go for E020, no claim.
## Spec to write first (in this card, before code)
- Threat model: attacker controls the botnet host's own flows (shaping) and may emit decoy flows from that host (injection); cannot touch benign hosts' flows or labels; knows features, not weights (XGB by transfer from MLP surrogate).
- Controllable features (A017): durations, bytes/packets up/down, inter-arrival-related features; validity projection (non-negative, integer counts, bytes ≥ packets×min size, consistent derived features).
- Cost: c = Σ shaped-feature L∞ change in σ units × #shaped flows + λ × #injected flows; budgets: 3 levels; λ fixed before running.
- A = shaping only (context recomputed from shaped flows); B = injection only (decoys change the host's aggregated context / graph neighbourhood, own flows untouched); C = joint under the same budget; C* = joint, budget split optimised.
- 'Structure/context' for XGB/MLP host-ip = host_context() recomputed with injected flows; for GNN ip = endpoint graph rebuilt with injected edges.
## Detectors
MLP host-ip (white-box, differentiable through mean aggregation), GNN ip cwbal (white-box), XGB host-ip and plain XGB (transfer from MLP surrogate), CTU-13 seed 42, test scenarios 9/10/13, report on botnet flows (recall) + F1 + PR-AUC.
## Success criterion (pilot go/no-go)
GO to E020 if any detector shows the C4 effect ≥ .03 at some budget in both attack seeds; otherwise report 'separate evaluation suffices' (weaker but reportable) and still run E020 at reduced size.
## Results
(pending)
