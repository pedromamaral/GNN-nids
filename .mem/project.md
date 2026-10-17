# Project

**Working title:** Robust to Features, Fragile to Structure? Decomposing Adversarial Effects in Graph-Based Network Intrusion Detection. Target: Computers & Security (D05). Detail: docs/PAPER_ROADMAP.md.

## Research question
For GNN-based NIDS, does evaluating feature and structure attacks separately misjudge the robustness of the deployed system, and does the answer depend on where the graph comes from (feature-derived k-NN vs endpoint/address graphs)?

## Target claims
- C1 (Part 1) Feature-derived k-NN graphs are redundant: neighbours are near-copies, so the GNN gains nothing from the graph, and an attack's induced rewiring (14-38% of neighbours) has no effect. Status: supported (K04, K05).
- C2 (Part 2) Under one protocol (chronological split, identity hidden, XGBoost/MLP on the same flows), endpoint GNNs do / do not beat tabular baselines; any gain is due to topology rather than window composition or host profile. Status: NEGATIVE on ToN + CTU-13 — gains are host context (K11, K14, D15).
- C3 (Part 2) Scenario-disjoint CTU-13 (unseen infected captures) as the identity-leakage control. Status: OPEN (K08, K09).
- C4 (Part 3) A/B/C decomposition (feature / induced structure / interaction) on endpoint graphs with a joint attacker (own-flow shaping + decoy injection, one traffic-cost budget) shows separate evaluation misjudges robustness; compare with injection-only (GIANT) and separate (Venturi) evaluation. Status: not started (A012).
- C5 (optional) Graph construction (node key, window, degree cap) as a training-free defence for endpoint graphs. Status: parked (A013).

## Protocol (fixed, D03/D04/D06)
NetFlow-v3 (NF-UNSW-NB15-v3 dev, NF-ToN-IoT-v3) + CTU-13; chronological 60/20/20 by FLOW_START_MILLISECONDS (CTU-13: by scenario); windows of consecutive flows; scaler on train only; 44 features (no IPs, ports, DNS_QUERY_ID, timestamps, TTL); endpoint nodes anonymised per window.

## Metrics
- Primary: test F1 (malicious = positive), threshold 0.5; ROC-AUC secondary; per-class detection rate (per_class.csv).
- Attacks: ΔF1 per condition (clean, A, B, C, C*); structure effect = F1(clean)−F1(B); adaptive gain = F1(pgd,A)−F1(pgd_rebuild,C).
- Seeds: 5 training seeds (42-46) for any claim; attack seeds ≥2.

## Success criteria
- k-NN go/no-go (Phase 2, applied): GO if structure effect ≥0.05 or adaptive gain ≥0.03 (one-sided Wilcoxon p<0.05). Result: NO-GO everywhere (K05).
- C2 (revised 2026-10-15, D12) : "topology helps" iff, evaluated PER DATASET (ToN, CTU-13; no pooled verdict), (a) GNN(real graph) − max(isolated, XGB, MLP, window ctx, host ctx, neighbour-aggregate XGB [A027]) ≥ max(0.02, 2× pooled seed std) test F1; (b) positive in 5/5 seeds (one-sided Wilcoxon p=0.031; seeds vary init only, split is fixed); (c) 95% block-bootstrap CI over test windows excludes 0, block length fixed BEFORE running (≥1 CTU-13 scenario or ≥N windows; record N in the card); (d) shuffled-endpoint ablation costs ≥0.02 F1, reported as test-time shuffle (checkpoint) or train-time shuffle (retrained) — label which; if test-time is borderline, retrain on shuffled graphs.
- C4 (proposed 2026-10-14, revised 2026-10-15 D12, threshold OK provisional until A012 defines the cost model): at equal traffic-cost budget, |interaction| = |ΔF1(C) − ΔF1(A) − ΔF1(B)| ≥ 0.03, or joint attack beats best separate attack by ≥0.03; attack seeds averaged within each training seed (n=5, 5/5 required, Wilcoxon p=0.031) or hierarchical bootstrap — not n=15 pooled (nested, pseudo-replicated). Same 0.03 as the k-NN adaptive-gain rule. Below threshold = "separate evaluation suffices" (weaker but reportable).
