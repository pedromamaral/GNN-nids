#!/usr/bin/env bash
# E024: ToN port of the Part 3 joint shaping+decoy attack (A033, D22). GPUserver1 (ToN data + E019 checkpoints).
# Reuses the E019 GNN-ip checkpoints (seeds 42-46, E008 settings, unweighted). Detectors: gnn_ip (white box), mlp_host_ip (white box),
# xgb_host_ip + xgb_plain (transfer). Delay off (K15), beta .1/.5, rho 0/.5/1 + budget-matched A/B for S, attack seeds 0,1.
# SMOKE=1: one seed, one beta/rho, 2 chunks, 5 steps.
cd ~/GNN-nids
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "$1"; }
DS=nf-ton-iot-v3
ckpt() { ls -d results/runs/*_${DS}_egraphsage_endpoint_ip_w10000_L2_seed_$1/best_checkpoint.pt | head -n 1; }
if [ -n "$SMOKE" ]; then
  run "python experiments/08_context_decomposition.py --dataset $DS --seed 42 --model-cache results/E024_models/smoke --gnn-checkpoint $(ckpt 42) --attack-seeds 0 --betas 0.5 --rhos 0 0.5 1 --no-xgb --delay-modes off --steps 5 --max-chunks 2 --output-dir results/E024_smoke"
  echo E024_SMOKE_DONE; exit 0
fi
for s in 42 43 44 45 46; do
  run "python experiments/08_context_decomposition.py --dataset $DS --seed $s --model-cache results/E024_models/seed_$s --gnn-checkpoint $(ckpt $s) --attack-seeds 0 1 --betas 0.1 0.5 --rhos 0 0.5 1 --delay-modes off --output-dir results/E024/seed_$s"
done
echo E024_DONE
