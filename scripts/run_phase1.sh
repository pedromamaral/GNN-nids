#!/usr/bin/env bash
# Phase 1 of docs/PAPER_ROADMAP.md: the decomposition go/no-go experiment.
#
# For every dataset x model x training seed, find the trained checkpoint in
# results/runs/ (training it first if TRAIN_MISSING=1), run
# experiments/05_decomposition.py with all attack seeds, then aggregate with
# experiments/05b_decomposition_report.py.
#
# Usage (from the repository root, inside the Docker container or venv):
#   scripts/run_phase1.sh
#   DATASETS="cicids2017-patator" MODELS="gcn" TRAINING_SEEDS="42 43" scripts/run_phase1.sh
#   TRAIN_MISSING=1 scripts/run_phase1.sh
#   EXTRA_ARGS="--max-windows 20" scripts/run_phase1.sh     # quick smoke run
set -euo pipefail

DATASETS=${DATASETS:-"cicids2017-selected cicids2017-patator"}
MODELS=${MODELS:-"gcn gat"}
TRAINING_SEEDS=${TRAINING_SEEDS:-"42 43 44 45 46"}
ATTACK_SEEDS=${ATTACK_SEEDS:-"42 43 44 45 46"}
EPSILONS=${EPSILONS:-"0.05 0.10"}
K=${K:-5}
LAYERS=${LAYERS:-1}
TRAIN_MISSING=${TRAIN_MISSING:-0}
EXTRA_ARGS=${EXTRA_ARGS:-}      # extra arguments for 05_decomposition.py
TRAIN_ARGS=${TRAIN_ARGS:-}      # extra arguments for 01_baseline_training.py (e.g. "--epochs 3" for smoke runs)
REPORT_DIR=${REPORT_DIR:-results/decomposition}
PYTHON=${PYTHON:-python}

layers_tag=""
if [ "$LAYERS" != "1" ]; then layers_tag="_L${LAYERS}"; fi

find_checkpoint() {  # dataset model seed -> newest matching checkpoint, or empty
  ls -1d results/runs/*_"$1"_"$2"_k_"${K}${layers_tag}"_seed_"$3" 2>/dev/null \
    | sort | tail -n 1 | sed 's|$|/best_checkpoint.pt|' | while read -r f; do [ -f "$f" ] && echo "$f"; done \
    || true
}

for dataset in $DATASETS; do
  for model in $MODELS; do
    for seed in $TRAINING_SEEDS; do
      ckpt=$(find_checkpoint "$dataset" "$model" "$seed")
      if [ -z "$ckpt" ]; then
        if [ "$TRAIN_MISSING" = "1" ]; then
          echo ">>> training $dataset $model seed=$seed (L=$LAYERS)"
          # shellcheck disable=SC2086
          $PYTHON experiments/01_baseline_training.py --dataset "$dataset" --model "$model" --k "$K" \
            --hidden-layers "$LAYERS" --seed "$seed" --deterministic $TRAIN_ARGS
          ckpt=$(find_checkpoint "$dataset" "$model" "$seed")
        else
          echo "!!! no checkpoint for $dataset $model k=$K L=$LAYERS seed=$seed (set TRAIN_MISSING=1 to train)" >&2
          continue
        fi
      fi
      echo ">>> decomposition $dataset $model seed=$seed  ($ckpt)"
      # shellcheck disable=SC2086
      $PYTHON experiments/05_decomposition.py --dataset "$dataset" --model "$model" --k "$K" \
        --checkpoint "$ckpt" --training-seed "$seed" --attack-seeds $ATTACK_SEEDS \
        --epsilons $EPSILONS --deterministic $EXTRA_ARGS
    done
  done
done

$PYTHON experiments/05b_decomposition_report.py --results-dir "$REPORT_DIR"
