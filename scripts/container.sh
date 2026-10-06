#!/usr/bin/env bash
# Run project jobs inside the experiment container on a GPU server.
#
#   scripts/container.sh [-d] JOB [ARGS...]
#
# JOB is one of:
#   build        build (or rebuild) the image
#   shell        interactive shell in the container
#   test         run the test suite
#   check-data   check that the raw files needed by the experiments are present
#   smoke        5-minute end-to-end check of Phase 1 (throwaway seed 99, writes to results/smoke/)
#   phase1       full Phase 1 grid (scripts/run_phase1.sh; trains missing checkpoints)
#   report       aggregate Phase 1 results and print the go/no-go verdict
#   run CMD...   any other command, e.g. run python experiments/05_decomposition.py --help
#
# Options / environment:
#   -d           run in the background; follow with: docker logs -f <name>  (also logs/<name>.log)
#   GPU=n        host GPU index to use (default 0). One job per GPU is the intended pattern.
#   DATA_RAW=... host directory holding the raw datasets (default: ./data/raw)
#   Any variable read by scripts/run_phase1.sh (DATASETS, MODELS, TRAINING_SEEDS, ...) is passed through.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT=$(pwd)

DETACH=0
if [ "${1:-}" = "-d" ]; then DETACH=1; shift; fi
JOB=${1:-shell}
shift || true

export GPU=${GPU:-0}
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)
export DATA_RAW=${DATA_RAW:-$REPO_ROOT/data/raw}
mkdir -p "$DATA_RAW" results logs data/graphs

PROJECT="gnn-$(id -un)-gpu${GPU}"
COMPOSE=(docker compose -f docker/docker-compose.yml -p "$PROJECT")

# Variables forwarded into the container for scripts/run_phase1.sh.
PASS_VARS=(DATASETS MODELS TRAINING_SEEDS ATTACK_SEEDS EPSILONS K LAYERS TRAIN_MISSING TRAIN_ARGS EXTRA_ARGS REPORT_DIR PYTHON)
ENV_ARGS=()
for v in "${PASS_VARS[@]}"; do
  if [ -n "${!v:-}" ]; then ENV_ARGS+=(-e "$v=${!v}"); fi
done

case "$JOB" in
  build)
    exec "${COMPOSE[@]}" build "$@" ;;
  shell)
    exec "${COMPOSE[@]}" run --rm "${ENV_ARGS[@]}" gnn bash ;;
  test)
    CMD="python -m pytest -q $*" ;;
  check-data)
    CMD="python scripts/check_data.py $*" ;;
  smoke)
    ENV_ARGS+=(-e "DATASETS=${DATASETS:-nf-unsw-nb15-v3}" -e "MODELS=${MODELS:-gcn}" \
               -e "TRAINING_SEEDS=99" -e "ATTACK_SEEDS=42 43" -e "TRAIN_MISSING=1" \
               -e "TRAIN_ARGS=${TRAIN_ARGS:---epochs 3}" \
               -e "EXTRA_ARGS=--max-windows 20 --output-dir results/smoke/decomposition" \
               -e "REPORT_DIR=results/smoke/decomposition")
    CMD="python -m pytest -q tests/test_decomposition.py && scripts/run_phase1.sh" ;;
  phase1)
    ENV_ARGS+=(-e "TRAIN_MISSING=${TRAIN_MISSING:-1}")
    CMD="scripts/run_phase1.sh" ;;
  report)
    CMD="python experiments/05b_decomposition_report.py $*" ;;
  run)
    CMD="$*" ;;
  *)
    echo "Unknown job: $JOB (see the header of $0)" >&2; exit 2 ;;
esac

NAME="gnn_$(id -un)_${JOB}_gpu${GPU}_$(date +%Y%m%d_%H%M%S)"
WRAPPED="set -o pipefail; nvidia-smi -L || true; ($CMD) 2>&1 | tee logs/${NAME}.log"

if [ "$DETACH" = "1" ]; then
  "${COMPOSE[@]}" run -d --rm --name "$NAME" "${ENV_ARGS[@]}" gnn bash -c "$WRAPPED"
  echo "Started $NAME on GPU $GPU."
  echo "Follow:  docker logs -f $NAME     (log file: logs/${NAME}.log)"
else
  "${COMPOSE[@]}" run --rm --name "$NAME" "${ENV_ARGS[@]}" gnn bash -c "$WRAPPED"
fi
