# Run registry. Active rows on top; tools/runs_status.sh reads rows ending in `running` or `queued`.
# id | host | container (or queue:<script>) | cmd | started | ETA | output | status
# container = gnn_pedroamaral_<job>_gpu0_<YYYYmmdd_HHMMSS> (printed by scripts/container.sh); log = ~/GNN-nids/logs/<container>.log

## Active
(none — checked 2026-10-14 17:20; both servers idle on our side)

## Recently ended
E012-a2c | GPUserver1+2 | queue:queue_a2c.sh | 00 ToN/ctu13 context controls + 01 ctu13 endpoint ×3 | 10-13 ~12:40 | - | logs/queue_a2c.log | crashed (XGB OOM ×4, disk full ×1, isolated unfinished)
E011 | GPUserver2 | queue_a2c.sh | 00 ctu13 plain/window, 01 ctu13 ip | 10-13 12:41 | - | results/tabular/20261013_124122_ctu13, _130000_ctu13_window-w10000, results/runs/20261013_132610_* | finished
E010 | GPUserver1 | queue_a2b.sh | 00 UNSW host ip/ipport/window | 10-13 09:58 | - | results/tabular/20261013_{095833,120237,120953}_* | finished
