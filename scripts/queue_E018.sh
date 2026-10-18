#!/usr/bin/env bash
# E018: class-weighted tabular on CTU-13 (CPU XGB as E013), then threshold-free comparison vs E016 GNN scores.
cd ~/GNN-nids
run() { GPU=0 scripts/container.sh run "$1"; }
COMMON="--dataset ctu13 --seeds 42 43 44 45 46 --class-weight balanced --save-scores --xgb-device cpu"
run "python experiments/00_tabular_baselines.py $COMMON --output-dir results/E018_tab_plain"
run "python experiments/00_tabular_baselines.py $COMMON --context host --node-key ip --output-dir results/E018_tab_hostip"
G=""; for k in ip ipport isolated; do f=$(ls results/E016_gnn_${k}/*/scores.npz 2>/dev/null | head -n 1); [ -n "$f" ] && G="$G --gnn $k=$f"; done
P=$(ls results/E018_tab_plain/*/scores.npz | head -n 1); H=$(ls results/E018_tab_hostip/*/scores.npz | head -n 1)
run "python experiments/07_threshold_free.py $G --tab plain_cw=$P --tab hostip_cw=$H --target ip --out results/E018_threshold_free.json"
echo E018_DONE
