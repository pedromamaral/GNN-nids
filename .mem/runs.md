# Run registry. Active rows on top; tools/runs_status.sh reads rows ending in `running` or `queued`.
# id | host | container (or queue:<script>) | cmd | started | ETA | output | status
# container = gnn_pedroamaral_<job>_gpu0_<YYYYmmdd_HHMMSS> (printed by scripts/container.sh); log = ~/GNN-nids/logs/<container>.log

## Active
E014 | GPUserver2 | queue:queue_E014.sh | pytest test_graph_ablation, then 01 ctu13 endpoint cwbal {ip,isolated,ipport} x seeds 43-46 (12 runs; seed 42 reused from E013), then 06 --save-window-counts on 15 ckpts, then rm data/graphs/* | 10-15 ~21:54 (server clock) | ~several h (est., unmeasured) | results/runs/*_cwbal_L2_seed_4[3-6], results/graph_ablation/<ts>/ ; log logs/queue_E014.log (ends 'E014_DONE') | 01 x12 done; 06 rerun via queue:queue_E014b.sh (fix 3ec549a), started 10-16 ~13:22 server clock, log logs/queue_E014b.log (ends E014_DONE) | running

## Recently ended
E012-a2c | GPUserver1+2 | queue:queue_a2c.sh | 00 ToN/ctu13 context controls + 01 ctu13 endpoint ×3 | 10-13 ~12:40 | - | logs/queue_a2c.log | crashed (XGB OOM ×4, disk full ×1, isolated unfinished)
