#!/usr/bin/env bash
# E022: CTU-13 unseen-family split (D21, A028). Needs CTU-13 raw data (GPUserver2 only) and waits for queue_E021 so the shared
# data/graphs cache is not clobbered. Train 1-5,9,10,13 / val 11 / test 6,7,8,12 via CTU13_SPLIT=unseen.
# GNN ip + isolated cwbal (window 10000, 50 ep), plain + host-ip XGB/MLP cwbal, 5 seeds, then 07 threshold-free.
cd ~/GNN-nids
while ! grep -q E021_DONE logs/queue_E021.log 2>/dev/null; do sleep 300; done
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "CTU13_SPLIT=unseen $1"; }
run "rm -rf data/graphs/*"
for k in ip isolated; do
  CK=""
  for s in 42 43 44 45 46; do
    run "python experiments/01_baseline_training.py --dataset ctu13 --graph endpoint --model egraphsage --node-key $k --window-size 10000 --epochs 50 --class-weight balanced --seed $s --deterministic"
    CK="$CK $(ls -td results/runs/*_ctu13_egraphsage_endpoint_${k}_w10000_cwbal_L2_seed_$s | head -n 1)/best_checkpoint.pt"
  done
  run "python experiments/06_graph_ablation.py --checkpoints $CK --save-scores --scores-only --output-dir results/E022_gnn_$k"
  run "rm -rf data/graphs/*"
done
COMMON="--dataset ctu13 --seeds 42 43 44 45 46 --class-weight balanced --save-scores --xgb-device cpu"
run "python experiments/00_tabular_baselines.py $COMMON --output-dir results/E022_tab_plain"
run "python experiments/00_tabular_baselines.py $COMMON --context host --node-key ip --output-dir results/E022_tab_hostip"
G=""; for k in ip isolated; do f=$(ls results/E022_gnn_${k}/*/scores.npz | head -n 1); G="$G --gnn $k=$f"; done
P=$(ls results/E022_tab_plain/*/scores.npz | head -n 1); H=$(ls results/E022_tab_hostip/*/scores.npz | head -n 1)
run "python experiments/07_threshold_free.py $G --tab plain_cw=$P --tab hostip_cw=$H --target ip --out results/E022_threshold_free.json"
echo E022_DONE
