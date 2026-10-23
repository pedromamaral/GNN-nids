#!/usr/bin/env bash
# E021: training-seed variance of adversarial robustness, CTU-13 (A031, D20). GPUserver2 (CTU-13 data).
# Seeds 42-46 reuse the E014 GNN checkpoints and E020 MLP caches; seeds 47-56 are trained here (E014 settings).
# MLP unweighted (as E020 caches). Reduced 08 grid: gnn_ip + mlp_host_ip only, delay off (K15), beta .1/.5, rho 0/.5/1 + budget-matched A/B for S, attack seeds 0,1.
cd ~/GNN-nids
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "$1"; }
ckpt() { ls -d results/runs/*_ctu13_egraphsage_endpoint_ip_w10000_cwbal_L2_seed_$1/best_checkpoint.pt | head -n 1; }
COMMON="--ctu13-dir data/raw/ctu13/CTU-13-Dataset"
for s in 47 48 49 50 51 52 53 54 55 56; do
  run "python experiments/01_baseline_training.py --dataset ctu13 --graph endpoint --model egraphsage --node-key ip --window-size 10000 --epochs 50 --class-weight balanced --seed $s --deterministic"
done
run "rm -rf data/graphs/*"
for s in 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56; do
  if [ "$s" -le 46 ]; then MC="--model-cache results/E020_models/seed_$s"; else MC="--model-cache results/E021_models/seed_$s"; fi
  run "python experiments/08_context_decomposition.py --seed $s $COMMON $MC --gnn-checkpoint $(ckpt $s) --no-xgb --attack-seeds 0 1 --betas 0.1 0.5 --rhos 0 0.5 1 --delay-modes off --output-dir results/E021/seed_$s"
done
echo E021_DONE
