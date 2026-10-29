#!/usr/bin/env bash
# E023: k-NN decomposition full grid (A015, C1). UNSW GCN+GAT, 5 training x 5 attack seeds, eps .05/.10, k=5, L=1.
# Config-only: scripts/run_phase1.sh defaults; trains missing checkpoints, then 05 per checkpoint and 05b report.
cd ~/GNN-nids
GPU=0 TQDM_DISABLE=1 TRAIN_MISSING=1 DATASETS="nf-unsw-nb15-v3" MODELS="gcn gat" \
  TRAINING_SEEDS="42 43 44 45 46" ATTACK_SEEDS="42 43 44 45 46" EPSILONS="0.05 0.10" \
  REPORT_DIR=results/decomposition scripts/container.sh phase1
scripts/container.sh run "rm -rf data/graphs/*"
echo E023_DONE
