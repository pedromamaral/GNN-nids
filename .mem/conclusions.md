# Conclusions (what we currently believe)

## Reference numbers (test F1 unless stated; mean±std over 5 seeds)
REF | UNSW XGBoost (44 feat, no TTL) | 0.9995±0.0000, AUC 1.000 | E002
REF | UNSW MLP | 0.9985±0.0001 | E002
REF | ToN XGBoost | 0.8717±0.0029, AUC 0.937 | E002
REF | ToN MLP | 0.7345±0.0175, AUC 0.849 | E002
REF | CTU-13 XGBoost (test 9/10/13) | 0.5308±0.0004, AUC 0.959 | E011
REF | CTU-13 MLP | 0.4840±0.0265, AUC 0.937 | E011
REF | UNSW with TTL: XGBoost / MLP | 0.9999 / 0.9992 | E001
REF | k-NN GNN seed 42: UNSW GCN / UNSW GAT / ToN GCN | 0.975 / 0.986 / 0.812 | E005
REF | E-GraphSAGE w10k seed 42, UNSW ipport/ip/isolated | 0.9973 / 0.9388 / 0.9975 | E008
REF | E-GraphSAGE w10k seed 42, ToN ipport/ip/isolated | 0.8990 / 0.9372 / 0.7270 | E008
REF | seed noise XGBoost | std ≤0.003 F1 | E002,E010,E011
REF | seed noise MLP ToN | std 0.0175 | E002
REF | seed noise GNN | NOT MEASURED (only seed 42) | A022

## Conclusions
K01 | TTL is a testbed artefact on UNSW: MIN_TTL alone F1 0.9992; TTL 31 always benign, 62 always attack; dropped (D03). Without it XGBoost still 0.9995 | E001,E002 | high | 2026-10-07
K02 | UNSW is saturated: every variant (tabular, host ip/ipport, window context, endpoint GNN) is 0.998-1.000 → no room to show context/topology gains on UNSW | E002,E008,E010 | high | 2026-10-13
K03 | Clean ease ≠ robustness: random ±0.05σ noise drops UNSW XGBoost to 0.78 (±0.5σ → 0.35); ToN ±0.1σ → 0.20; UNSW LR 0.9907, depth-2 tree 0.9927 | E003 | medium (numbers from import, no json) | 2026-10-07
K04 | k-NN graph is redundant: removing edges changes 0.2-1.2% of predictions and never lowers F1 (UNSW GCN knn/none/random 0.975/0.995/0.21; GAT 0.986/0.995/0.15; ToN GCN 0.812/0.814/0.815) — neighbours are near-copies | E007 | high | 2026-10-08
K05 | k-NN feature-structure coupling is real (14-38% malicious neighbours rewired) but inconsequential: structure effect ≤0.005, adaptive gain ≤0.019, feature effect large (UNSW GCN 0.20 at ε=0.25) → k-NN go/no-go NO-GO on all 3 pilots | E006 | high (1 training seed, 2 attack seeds) | 2026-10-08
K06 | ToN endpoint GNN ip (0.937) > XGBoost (0.872), but ablation shows it needs a neighbourhood, not the real one (none 0.790, shuffled dst 0.940, src 0.910, both 0.915) → suspected window-composition confounder; untested on ToN because the controls crashed | E008,E009,E012 | open | 2026-10-13
K07 | UNSW ip endpoint model is brittle: any shuffle → F1 0.00-0.04, no edges 0.52; ipport model survives src shuffle (0.906) but not dst (0.43) | E009 | medium | 2026-10-13
K08 | CTU-13 scenario-disjoint split is hard (XGBoost 0.53) and window context hurts (XGBoost 0.405±0.168, MLP 0.217, MLP AUC 0.65) | E011 | medium | 2026-10-13
K09 | CTU-13 E-GraphSAGE ip collapses to all-benign (val F1 0 at every epoch, test F1 0, AUC 0.82): imbalance (~2% botnet), not evidence against GNNs; needs class weighting | E011 | low | 2026-10-13
K10 | ToN val F1 does not rank test F1 (isolated best val 0.961 → test 0.727; ip 0.939 → 0.937): temporal drift val→test; model selection on val is unreliable on ToN | E008 | medium | 2026-10-14
