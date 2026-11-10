#!/usr/bin/env bash
# E027: k-NN graph ablation over 5 training seeds (A038, D24, C1/K04). UNSW GCN+GAT, k=5, L=1.
# Config-only: experiments/06_graph_ablation.py on the E023 checkpoints (knn / none / random x3 graph seeds 0,1,2).
cd ~/GNN-nids
CK=$(ls results/runs/*_nf-unsw-nb15-v3_{gcn,gat}_k_5_seed_4[2-6]/best_checkpoint.pt | tr '\n' ' ')
echo "checkpoints: $(echo $CK | wc -w)"
[ "$(echo $CK | wc -w)" = 10 ] || { echo "E027_FAILED: expected 10 checkpoints"; exit 1; }
GPU=0 TQDM_DISABLE=1 scripts/container.sh run "python experiments/06_graph_ablation.py --checkpoints $CK --random-seeds 0 1 2 --save-window-counts --output-dir results/graph_ablation/E027"
scripts/container.sh run "rm -rf data/graphs/*"
echo E027_DONE
