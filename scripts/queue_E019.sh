#!/usr/bin/env bash
# E019: ToN-IoT-v3 endpoint E-GraphSAGE x {ip,ipport,isolated} x seeds 42-46 (E008 settings: L2, w10000, 50 epochs, unweighted CE),
# per-flow scores (06), tabular plain/host-ip/host-ipport scores (00, CPU XGB), then threshold-free comparison (07).
# Run on GPUserver1 (ToN cache ~5.5 GB per node key, only ~11 GB free): data/graphs is cleared after each node key (D09).
cd ~/GNN-nids
run() { GPU=0 scripts/container.sh run "$1"; }
DS=nf-ton-iot-v3
for k in ip ipport isolated; do
  for s in 42 43 44 45 46; do
    run "python experiments/01_baseline_training.py --dataset $DS --graph endpoint --model egraphsage --node-key $k --window-size 10000 --epochs 50 --seed $s --deterministic"
  done
  CK=$(ls results/runs/*_${DS}_egraphsage_endpoint_${k}_w10000_L2_seed_4[2-6]/best_checkpoint.pt | tr '\n' ' ')
  run "python experiments/06_graph_ablation.py --checkpoints $CK --save-scores --scores-only --output-dir results/E019_gnn_$k"
  run "rm -rf data/graphs/*"
done
COMMON="--dataset $DS --seeds 42 43 44 45 46 --save-scores --xgb-device cpu"
run "python experiments/00_tabular_baselines.py $COMMON --output-dir results/E019_tab_plain"
run "python experiments/00_tabular_baselines.py $COMMON --context host --node-key ip --output-dir results/E019_tab_hostip"
run "python experiments/00_tabular_baselines.py $COMMON --context host --node-key ipport --output-dir results/E019_tab_hostipport"
G=""; for k in ip ipport isolated; do f=$(ls results/E019_gnn_${k}/*/scores.npz | head -n 1); G="$G --gnn $k=$f"; done
T=""; for t in plain hostip hostipport; do f=$(ls results/E019_tab_${t}/*/scores.npz | head -n 1); T="$T --tab $t=$f"; done
run "python experiments/07_threshold_free.py $G $T --target ip --out results/E019_threshold_free.json"
echo E019_DONE
