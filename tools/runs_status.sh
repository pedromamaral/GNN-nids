#!/usr/bin/env bash
# One call -> <=20-line status of all active runs (rows of .mem/runs.md whose
# last field is running or queued), plus GPU and disk headroom per server.
#
#   tools/runs_status.sh [HOST ...]     default hosts: those in active rows, else GPUserver1 GPUserver2
#
# Row format (.mem/runs.md):
#   E013-ton-window | GPUserver1 | gnn_pedroamaral_run_gpu0_20261014_150000 | cmd | started .. | ETA .. | where | running
# The container field may be `queue:<script name>` (a logs/queue_*.sh driver):
# then the script is checked with pgrep and the live containers are listed.
# One ssh per host. Flags: RUN (alive), DONE (container gone, clean log end),
# CRASH (container gone, error in log tail), NOLOG, QUEUE alive/ended.
set -uo pipefail
cd "$(dirname "$0")/.."
RUNS=.mem/runs.md

rows=$(grep -E '\|[[:space:]]*(running|queued)[[:space:]]*$' "$RUNS" 2>/dev/null || true)
if [ $# -gt 0 ]; then hosts="$*"
else
  hosts=$(printf '%s\n' "$rows" | awk -F'|' 'NF>2{gsub(/ /,"",$2); print $2}' | sort -u)
  [ -z "$hosts" ] && hosts="GPUserver1 GPUserver2"
fi

for h in $hosts; do
  ctrs=$(printf '%s\n' "$rows" | awk -F'|' -v h="$h" 'NF>2{gsub(/ /,"",$2); gsub(/ /,"",$3); if($2==h) print $3}' | tr '\n' ' ')
  ssh -o ConnectTimeout=8 -o BatchMode=yes "$h" "CTRS='$ctrs' bash -s" <<'REMOTE' 2>&1 | head -n 9 | sed "s/^/$h /" || echo "$h UNREACHABLE (VPN?)"
cd ~/GNN-nids 2>/dev/null || exit 1
me=$(id -un)
gpu=$(nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | awk -F', ' '{printf "%s%% %s/%sMiB", $1, $2, $3}')
echo "gpu $gpu | disk free $(df -h ~ | awk 'NR==2{print $4}')"
live=$(docker ps --filter "name=gnn_${me}_" --format '{{.Names}}|{{.RunningFor}}')
lastline() { tail -c 4000 "logs/$1.log" 2>/dev/null | tr '\r' '\n' | grep -v '^[[:space:]]*$' | tail -n 1 | cut -c1-100; }
while IFS= read -r x; do [ -n "$x" ] || continue; n=${x%%|*}; echo "RUN   $n (${x#*|}) :: $(lastline "$n")"; done <<< "$live"
for c in $CTRS; do
  case $c in
    queue:*) q=${c#queue:}; if pgrep -f "$q" >/dev/null; then echo "QUEUE $q alive"; else echo "QUEUE $q ended"; fi ;;
    *) printf '%s\n' "$live" | grep -q "^$c|" && continue
       if [ ! -f "logs/$c.log" ]; then echo "NOLOG $c"
       elif tail -n 40 "logs/$c.log" | grep -qiE 'traceback|error|out of memory|killed'; then
         echo "CRASH $c :: $(tail -n 40 "logs/$c.log" | grep -iE 'error|out of memory|killed' | tail -n 1 | cut -c1-100)"
       else echo "DONE  $c :: $(lastline "$c")"; fi ;;
  esac
done
REMOTE
done
