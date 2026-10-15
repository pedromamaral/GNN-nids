# Avenue registry (anti-repeat). Grep before proposing anything.
# id | status | idea | claim | experiments | conclusion | date
# status: proposed · active · tried · dropped · parked · needed-for-paper

A001 | dropped | k-NN feature-structure coupling as the MAIN paper claim | C1 | E006,E007 | coupling real but inconsequential (K04,K05); kept as Part 1 only | 2026-10-12
A002 | dropped | CTU-13 to rescue k-NN graphs | C1 | - | redundancy comes from feature-derived construction, not the dataset | 2026-10-12
A003 | dropped | graph construction (threshold, degree cap) as defence for k-NN graphs | C5 | E007 | graph is redundant, nothing to defend; kept only for endpoint graphs (A013) | 2026-10-12
A004 | dropped | address/endpoint-graph attack paper on its own | C4 | - | overlaps GIANT (WWW 2026); framing = decomposition + own-flow shaping instead | 2026-10-12
A005 | active | Avenue #1: decomposition on k-NN + endpoint graphs, joint attacker (THE paper) | C1-C4 | - | D05 | 2026-10-12
A006 | tried | keep TTL (MIN_TTL, MAX_TTL) as features | - | E001 | testbed artefact, single-feature F1 0.9992; dropped (K01, D03) | 2026-10-07
A007 | dropped | optimised edge attacks (Nettack/Metattack) on k-NN graphs | C1 | - | attacker cannot edit edges of a feature-derived graph; random edges kept as upper bound | 2026-10-05
A008 | active | A2: endpoint E-GraphSAGE vs XGBoost vs isolated control (go/no-go for Part 2) | C2 | E008,E009 | UNSW: topology adds nothing (K02); ToN ip > XGB but confounded (K06) | 2026-10-13
A009 | tried | window-composition / host-profile controls (00 --context window, host ip/ipport) to explain ToN GNN gain | C2 | E010,E013 | UNSW saturated (K02); ToN: host ipport XGB .931 ≈ GNN (K11); CTU-13 host ctx +.08, window ctx hurts (K12) → tried | 2026-10-14
A010 | tried | class-weighted (or focal) loss in Trainer for endpoint GNN on CTU-13 | C3 | E011,E013 | class weights fix collapse: ip F1 0→.844 (K09) → tried | 2026-10-14
A011 | tried | --xgb-device cpu (hist, n_jobs 16) or lower max_bin for context features (16.5M×88/134) | C2 | E012,E013 | GPU OOM 11.6 GB > 10.7 GB free | 2026-10-14
A012 | proposed | A4: joint attacker = own-flow shaping (edge features) + decoy injection (structure), traffic-cost budget; decomposition adapter for endpoint graphs | C4 | - | - | 2026-10-12
A013 | parked | Avenue #2: construction-as-defence for endpoint graphs (node key, window, degree cap, external-endpoint policy, min flows/edge) | C5 | - | optional section; after A012 | 2026-10-12
A014 | parked | Avenue #3: short negative-result paper on k-NN graphs (letter/workshop) | C1 | E006,E007 | folded into Part 1; #10 preprint pre-empts headline | 2026-10-12
A015 | needed-for-paper | Phase 2 k-NN decomposition full grid 5 training × 5 attack seeds, ε∈{0.05,0.10} (UNSW GCN+GAT) | C1 | - | only for robustness of Part 1 claims | 2026-10-12
A016 | needed-for-paper | A5: 5-seed grid for endpoint GNNs + all controls | C2,C3 | - | - | 2026-10-12
A017 | parked | constrained attack: attacker-controllable feature mask + validity projection (integrality, non-negativity) | C4 | - | becomes the "own-flow shaping" constraint set of A012 | 2026-10-05
A018 | parked | per-node neighbour churn as evasion detector (drop if AUC<0.85) | C5 | - | k-NN-specific; likely moot | 2026-10-05
A019 | parked | PGD adversarial-training baseline (compare at equal clean F1) | C4,C5 | - | Venturi 2025 already does this for E-GraphSAGE | 2026-10-05
A020 | dropped | NSL-KDD / CICIDS2017 (thesis datasets) | - | - | not relevant to paper (D02) | 2026-10-06
A021 | parked | NF-CSE-CIC-IDS2018-v3 as 4th dataset | C2 | - | only if reviewers need more datasets | 2026-10-06
A022 | active | GNN multi-seed noise (endpoint models, 5 seeds) before claiming any GNN gap | C2 | E014 | only seed 42 so far; now priority: CTU-13 ip/isolated/ipport cwbal x5 seeds | 2026-10-15
A023 | active | Part 2 framing decision: window≈GNN → temporal-confounder finding; host≈GNN → host behavioural profile; GNN>both → topology real | C2 | E013 | ToN: host profile (K11); CTU-13: GNN ip > all controls on 1 seed (K12) → dataset-dependent, pending A022+A025 | 2026-10-15
A024 | parked | k-NN sensitivity sweep k∈{3,5,10,15,20} (04_k_sensitivity.py) | C1 | - | graph redundant at k=5; only if reviewers ask | 2026-10-14
A025 | active | CTU-13 shuffled-endpoint ablation (06 on cwbal ip checkpoint: none/random_dst/random_src/random) to test C2(d) | C2 | E014 | needs only existing checkpoint on GPUserver2 (cheap) | 2026-10-15
A026 | proposed | threshold-free/recalibrated metric on ToN (PR-AUC, F1 at val-tuned or best threshold) since F1@0.5 breaks under drift (XGB host ip .20 vs AUC .955) | C2 | - | check not already in protocol: fixed F1@0.5 | 2026-10-15
A027 | proposed | neighbour-aggregate XGB: own features + mean/max/count of 1-hop peers' flow features per host/window, to test whether CTU-13/ToN GNN gain is feature aggregation not message passing | C2 | E015 | extends C2(a) control set (D12); CPU, 5 seeds | 2026-10-15
