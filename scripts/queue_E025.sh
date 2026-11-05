#!/usr/bin/env bash
# E025: ToN clean operating-point diagnostic (A037, D23). GPUserver1. No attack, no retraining: reuses E019 GNN-ip checkpoints and
# the E024 model caches (results/E024_models/seed_s); scores on logits / XGB margins, writes clean_op.json per seed.
# SMOKE=1: one seed, 2 chunks.
cd ~/GNN-nids
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "$1"; }
DS=nf-ton-iot-v3
ckpt() { ls -d results/runs/*_${DS}_egraphsage_endpoint_ip_w10000_L2_seed_$1/best_checkpoint.pt | head -n 1; }
if [ -n "$SMOKE" ]; then
  run "python experiments/08_context_decomposition.py --dataset $DS --seed 42 --model-cache results/E024_models/seed_42 --gnn-checkpoint $(ckpt 42) --clean-only --max-chunks 2 --output-dir results/E025_smoke"
  echo E025_SMOKE_DONE; exit 0
fi
for s in 42 43 44 45 46; do
  run "python experiments/08_context_decomposition.py --dataset $DS --seed $s --model-cache results/E024_models/seed_$s --gnn-checkpoint $(ckpt $s) --clean-only --output-dir results/E025/seed_$s"
done
echo E025_DONE
