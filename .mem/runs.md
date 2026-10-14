# Run registry. Active rows on top; tools/runs_status.sh reads rows ending in `running` or `queued`.
# id | host | container (or queue:<script>) | cmd | started | ETA | output | status
# container = gnn_pedroamaral_<job>_gpu0_<YYYYmmdd_HHMMSS> (printed by scripts/container.sh); log = ~/GNN-nids/logs/<container>.log

## Active
E013-q2 | GPUserver2 | queue:queue_e013.sh | 00 ToN window, ToN host ip, ctu13 host ip (xgb cpu); 01 ctu13 endpoint ip/isolated/ipport cwbal | started 10-14 ~18:00 | ETA ? (several h) | results/tabular, results/runs; logs/queue_e013.log | running
E013-q1 | GPUserver1 | queue:queue_e013.sh | 00 ToN host ipport (xgb cpu) | started 10-14 ~18:00 | ETA ? | results/tabular; logs/queue_e013.log | running

## Recently ended
E012-a2c | GPUserver1+2 | queue:queue_a2c.sh | 00 ToN/ctu13 context controls + 01 ctu13 endpoint ×3 | 10-13 ~12:40 | - | logs/queue_a2c.log | crashed (XGB OOM ×4, disk full ×1, isolated unfinished)
