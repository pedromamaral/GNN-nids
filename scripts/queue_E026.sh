#!/usr/bin/env bash
# E026: E024 grid on ToN at 5% FPR on logits (A037, D25; E024 was floored at 1% FPR, K18). GPUserver1.
# Reuses the results/E024_models caches (no refit); only --score-space logit --target-fpr 0.05 differ from E024.
# Reuses the E019 GNN-ip checkpoints (seeds 42-46, E008 settings, unweighted). Detectors: gnn_ip (white box), mlp_host_ip (white box),
# xgb_host_ip + xgb_plain (transfer). Delay off (K15), beta .1/.5, rho 0/.5/1 + budget-matched A/B for S, attack seeds 0,1.
# SMOKE=1: one seed, one beta, 2 chunks, 3 steps.
cd ~/GNN-nids
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "$1"; }
DS=nf-ton-iot-v3
ckpt() { ls -d results/runs/*_${DS}_egraphsage_endpoint_ip_w10000_L2_seed_$1/best_checkpoint.pt | head -n 1; }
if [ -n "$SMOKE" ]; then
  run "python experiments/08_context_decomposition.py --dataset $DS --seed 42 --model-cache results/E024_models/seed_42 --gnn-checkpoint $(ckpt 42) --attack-seeds 0 --betas 0.5 --rhos 0 0.5 1 --no-xgb --delay-modes off --score-space logit --target-fpr 0.05 --steps 3 --max-chunks 2 --output-dir results/E026_smoke"
  echo E026_SMOKE_DONE; exit 0
fi
for s in 42 43 44 45 46; do
  run "python experiments/08_context_decomposition.py --dataset $DS --seed $s --model-cache results/E024_models/seed_$s --gnn-checkpoint $(ckpt $s) --attack-seeds 0 1 --betas 0.1 0.5 --rhos 0 0.5 1 --delay-modes off --score-space logit --target-fpr 0.05 --output-dir results/E026/seed_$s"
done
echo E026_DONE
