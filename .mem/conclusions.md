# Conclusions (what we currently believe)

## Reference numbers (test F1 unless stated; mean±std over 5 seeds)
REF | UNSW XGBoost (44 feat, no TTL) | 0.9995±0.0000, AUC 1.000 | E002
REF | UNSW MLP | 0.9985±0.0001 | E002
REF | ToN XGBoost | 0.8717±0.0029, AUC 0.937 | E002
REF | ToN E-GraphSAGE 5 seeds ip/ipport/isolated | F1 .883±.096 / .909±.017 / .789±.110; PR-AUC .903 / .900 / .877 | E019
REF | ToN PR-AUC XGB host-ipport / plain / MLP host-ipport | .954 / .930 / .915 | E019
REF | ToN MLP | 0.7345±0.0175, AUC 0.849 | E002
REF | CTU-13 XGBoost (test 9/10/13) | 0.5308±0.0004, AUC 0.959 | E011
REF | CTU-13 MLP | 0.4840±0.0265, AUC 0.937 | E011
REF | UNSW with TTL: XGBoost / MLP | 0.9999 / 0.9992 | E001
REF | k-NN GNN seed 42: UNSW GCN / UNSW GAT / ToN GCN | 0.975 / 0.986 / 0.812 | E005
REF | E-GraphSAGE w10k seed 42, UNSW ipport/ip/isolated | 0.9973 / 0.9388 / 0.9975 | E008
REF | E-GraphSAGE w10k seed 42, ToN ipport/ip/isolated | 0.8990 / 0.9372 / 0.7270 | E008
REF | seed noise XGBoost | std ≤0.003 F1 | E002,E010,E011
REF | seed noise MLP ToN | std 0.0175 | E002
REF | seed noise GNN (endpoint, 5 seeds) | CTU-13 cwbal ip F1 std .031 (pooled .029); ToN ip F1 std .096 (s45 .714) but ROC-AUC std .003; ToN ipport .017, isolated .110 | E014,E019
REF | ToN XGB host ip / host ipport / window | 0.201±0.032 / 0.9307±0.0127 / 0.8017±0.0743 | E013
REF | ToN MLP host ip / host ipport / window | 0.906±0.026 / 0.917±0.014 / 0.036±0.033 | E013
REF | CTU-13 XGB host ip / MLP host ip | 0.614±0.012 / 0.617±0.025 | E013
REF | CTU-13 E-GraphSAGE cwbal seed 42, ip/isolated/ipport | 0.844 / 0.639 / 0.675 | E013

## Conclusions
K01 | TTL is a testbed artefact on UNSW: MIN_TTL alone F1 0.9992; TTL 31 always benign, 62 always attack; dropped (D03). Without it XGBoost still 0.9995 | E001,E002 | high | 2026-10-07
K02 | UNSW is saturated: every variant (tabular, host ip/ipport, window context, endpoint GNN) is 0.998-1.000 → no room to show context/topology gains on UNSW | E002,E008,E010 | high | 2026-10-13
K03 | Clean ease ≠ robustness: random ±0.05σ noise drops UNSW XGBoost to 0.78 (±0.5σ → 0.35); ToN ±0.1σ → 0.20; UNSW LR 0.9907, depth-2 tree 0.9927 | E003 | medium (numbers from import, no json) | 2026-10-07
K04 | k-NN graph is redundant: removing edges changes 0.2-1.2% of predictions and never lowers F1 (UNSW GCN knn/none/random 0.975/0.995/0.21; GAT 0.986/0.995/0.15; ToN GCN 0.812/0.814/0.815) — neighbours are near-copies | E007 | high | 2026-10-08
K05 | k-NN feature-structure coupling is real (14-38% malicious neighbours rewired) but inconsequential: structure effect ≤0.005, adaptive gain ≤0.019, feature effect large (UNSW GCN 0.20 at ε=0.25) → k-NN go/no-go NO-GO on all 3 pilots | E006 | high (1 training seed, 2 attack seeds) | 2026-10-08
K06 | ToN endpoint GNN ip (0.937) > XGBoost (0.872), but ablation shows it needs a neighbourhood, not the real one (none 0.790, shuffled dst 0.940, src 0.910, both 0.915) → suspected window-composition confounder; untested on ToN because the controls crashed | E008,E009,E012 | resolved by K11 | 2026-10-15
K07 | UNSW ip endpoint model is brittle: any shuffle → F1 0.00-0.04, no edges 0.52; ipport model survives src shuffle (0.906) but not dst (0.43) | E009 | medium | 2026-10-13
K08 | CTU-13 scenario-disjoint split is hard (XGBoost 0.53) and window context hurts (XGBoost 0.405±0.168, MLP 0.217, MLP AUC 0.65) | E011 | medium | 2026-10-13
K09 | CTU-13 E-GraphSAGE ip collapses to all-benign (F1 0, AUC 0.82): imbalance (~2% botnet); balanced CE weights fix it (ip test F1 0.844, AUC 0.992, seed 42) | E011,E013 | medium | 2026-10-13
K10 | ToN val F1 does not rank test F1 (isolated best val 0.961 → test 0.727; ip 0.939 → 0.937): temporal drift val→test; model selection on val is unreliable on ToN | E008 | medium | 2026-10-14
K11 | ToN: endpoint-GNN gain is host behavioural profile, not topology (5 seeds): GNN ip PR-AUC .903 < XGB host-ipport .954 in 5/5 seeds (gap −.051, block-bootstrap CI [−.115,−.007]), below even plain XGB (.930); F1@0.5 .883±.096 vs .931 (CI excl 0), val-tuned F1 −.023 (5/5). E008's seed-42 .937 was a favourable draw; GNN F1 seed noise (std .096) is threshold placement (ROC-AUC std .003). Shuffled-dst .940 (C2(d) fails, 1 seed); window context hurts (XGB .802, MLP .036/AUC .31); F1@0.5 fragile under drift (XGB host ip .20 with PR-AUC .93) | E008,E009,E013,E019 | high (5 seeds, identical flows) | 2026-10-21
K12 | CTU-13: host-ip context helps tabular (XGB .614, MLP .617 vs .531/.484), window hurts (XGB .405) | E011,E013 | medium | 2026-10-16
K13 | CTU-13: GNN ip cwbal F1 .855±.031 beats isolated .616 / ipport .656 / tabular host-ip ≤.617 in 5/5 seeds (+.199, floor .058), and test-time shuffle costs .36-.46; BUT AUC .993 ≈ XGB host-ip .991 < MLP host-ip .996 and val gap only +.02/.05 -> F1 gain may be threshold/calibration under drift on test scenarios 9/10/13, not topology. Topology claim NOT yet supported -> resolved by K14 | E013,E014 | medium | 2026-10-16
K14 | CTU-13: GNN ip's F1@0.5 gain (+.199) is threshold placement, not detection power: PR-AUC .855 < MLP host-ip .953 (5/5 seeds, every test scenario; block-bootstrap CI of gap [-.20,-.03]); at val-tuned thresholds GNN ip .477 < XGB host-ip .716, and val-tuned thresholds transfer badly for all models (val scenarios ≠ test). C2 fails on CTU-13 as on ToN (K11): endpoint-GNN gains are host context. Residual F1@0.5 advantage is mostly loss weighting: with class-weighted tabular (E018) the gap to MLP host-ip cw shrinks to +.051 (3/5 seeds positive, CI [−.035,+.139]), PR-AUC gap stays −.074 (CI [−.18,−.01]); GNN F1@0.5 edge lives only in test scenario 0, it is far worse in scenario 2 (.36 vs .82) | E014,E016,E018 | high (5 seeds, identical flows) | 2026-10-18
K15 | CTU-13 Part 3 (equal byte budget, 1% FPR, 5 training seeds): joint shaping+decoy is NOT superadditive on GNN ip (signed S β.5ρ.5 +.084 in seed 42 only, −.06..−.12 in 43-46; G≥.03 1/5), subadditive on MLP host-ip (S<0 5/5, shaping saturates Δ_A≈.5), ≈additive on XGB host-ip/plain (transfer non-monotone). Best single attack at equal budget ≈ joint → separate evaluation suffices. PGD converged (≤.004 at 100 steps/3 restarts); delay irrelevant (D-row Δ≤.005). Noise: attack seeds ≤.01; training-seed spread of GNN Δ_A (β .5) .08-.55 dominates. Decoys alarm 21-44% on GNN | E017, E020 | high (5 seeds, strength checked) | 2026-10-23
