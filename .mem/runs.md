# Run registry. Active rows on top; tools/runs_status.sh reads rows ending in `running` or `queued`.
# id | host | container (or queue:<script>) | cmd | started | ETA | output | status
# container = gnn_pedroamaral_<job>_gpu0_<YYYYmmdd_HHMMSS> (printed by scripts/container.sh); log = ~/GNN-nids/logs/<container>.log

## Active
E018 | GPUserver2 | queue:queue_E018.sh | 00 ctu13 --class-weight balanced plain + host-ip (CPU XGB, seeds 42-46, --save-scores), then 07 vs E016 GNN npz | 10-18 ~(server clock) | ~2-3 h (est., unmeasured) | results/E018_tab_{plain,hostip}/, results/E018_threshold_free.json; log logs/queue_E018.log (ends E018_DONE) | running
E017 | GPUserver2 | queue:queue_E017.sh | 08 pilot: seed 42, attack seeds 0 1, betas .05 .1 .25 .5, rhos 0-1, steps 30, --replay (refit ~1 h first) | 10-17 ~23:00 WEST | ~4-8 h (est., unmeasured) | results/E017_pilot/<ts>/{rows,summary}.csv; log logs/queue_E017.log (ends E017_DONE) | done (ran 22:2x-23:20 WEST, ~1 h; fetched -> .mem/results/E017.json)
E017-smoke | GPUserver2 | queue:queue_E017smoke.sh | 08 --max-chunks 1 --steps 3 --betas 0.1 --rhos 0 .5 1 --replay (refits MLP/XGB seed 42, CPU XGB: slow) | 10-17 | ~30-60 min (est.) | results/E017_smoke/; log logs/queue_E017smoke.log | done (ran ~1 h 20 min incl. fits)
E016 | GPUserver2 | queue:queue_E016.sh (first container gnn_pedroamaral_run_gpu0_20261017_172202) | 06 --save-scores --scores-only x3 node_keys (15 ckpts), 00 ctu13 plain + host-ip --save-scores, 07 threshold-free, rm data/graphs/* | 10-17 ~16:22 server clock (log time) | ~1-3 h (est., unmeasured) | results/E016_gnn_*/, results/E016_tab_*/, results/E016_threshold_free.json; log logs/queue_E016.log (ends E016_DONE) | done (fetched -> .mem/results/E016.json)
E014 | GPUserver2 | queue:queue_E014.sh | pytest test_graph_ablation, then 01 ctu13 endpoint cwbal {ip,isolated,ipport} x seeds 43-46 (12 runs; seed 42 reused from E013), then 06 --save-window-counts on 15 ckpts, then rm data/graphs/* | 10-15 ~21:54 (server clock) | ~several h (est., unmeasured) | results/runs/*_cwbal_L2_seed_4[3-6], results/graph_ablation/<ts>/ ; log logs/queue_E014.log (ends 'E014_DONE') | 01 x12 done; 06 rerun via queue:queue_E014b.sh (fix 3ec549a), started 10-16 ~13:22 server clock, log logs/queue_E014b.log (ends E014_DONE) | done (fetched -> .mem/results/E014.json)

## Recently ended
E012-a2c | GPUserver1+2 | queue:queue_a2c.sh | 00 ToN/ctu13 context controls + 01 ctu13 endpoint ×3 | 10-13 ~12:40 | - | logs/queue_a2c.log | crashed (XGB OOM ×4, disk full ×1, isolated unfinished)
