# E015 neighbour-aggregate XGB control (A027)
Status: PLANNED. Extends C2(a) control set (D12).
## Hypothesis
H: tabular XGB with 1-hop peer aggregates (mean/max/count per host in window) reaches >= GNN ip - 0.02 on CTU-13 => GNN gain is aggregation, not learned message passing.
## Change
Feature builder in 00 (e.g. --context neighbours --node-key ip). Same 44 features, identity hidden, chronological 60/20/20.
## Config
00 ctu13 and ToN, 5 seeds, --xgb-device cpu --n-jobs 16.
## Success criterion
Falsified (topology survives) if XGB-agg stays within noise of host-ip XGB (.614) while GNN ip ~.84.
## Results
(pending)
