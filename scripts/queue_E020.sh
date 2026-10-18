#!/usr/bin/env bash
# E020: Part 3 on CTU-13, D18. GPUserver2 (CTU-13 data). Per training seed: refit MLP/XGB once (model cache), then the
# full A/B/C grid with free and no delay, replay baseline, 2 attack seeds. First: PGD-strength check on seed 42.
cd ~/GNN-nids
run() { GPU=0 TQDM_DISABLE=1 scripts/container.sh run "$1"; }
ckpt() { ls -d results/runs/*_ctu13_egraphsage_endpoint_ip_w10000_cwbal_L2_seed_$1/best_checkpoint.pt | head -n 1; }
COMMON="--ctu13-dir data/raw/ctu13/CTU-13-Dataset"
for s in 42 43 44 45 46; do
  MC="--model-cache results/E020_models/seed_$s"
  G="--gnn-checkpoint $(ckpt $s)"
  if [ "$s" = 42 ]; then
    # strength check (D18b): same configs as the main run's attack seed 0, more steps / restarts
    SC="--seed 42 $COMMON $MC $G --attack-seeds 0 --betas 0.1 0.5 --rhos 0 0.5 1 --no-superadd --delay-modes free"
    run "python experiments/08_context_decomposition.py $SC --steps 100 --output-dir results/E020_strength_steps100"
    run "python experiments/08_context_decomposition.py $SC --steps 30 --restarts 3 --output-dir results/E020_strength_restarts3"
  fi
  run "python experiments/08_context_decomposition.py --seed $s $COMMON $MC $G --attack-seeds 0 1 --delay-modes free off --replay --output-dir results/E020_main/seed_$s"
done
echo E020_DONE
