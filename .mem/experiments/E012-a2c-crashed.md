# E012 batch a2c remainder: crashed (A009, A010, A011)
Date 2026-10-13 · queue logs/queue_a2c.sh on both servers (died; servers also rebooted 10-13 12:35/13:04)
| run | host | container | failure |
|---|---|---|---|
| 00 ToN --context window | GPUserver2 | ..._20261013_132921 | XGBoost CUDA OOM (11.6 GB requested, 10.7 free) |
| 00 ToN --context host --node-key ip | GPUserver2 | ..._20261013_133321 | XGBoost CUDA OOM |
| 00 ToN --context host --node-key ipport | GPUserver1 | ..._20261013_131642 | XGBoost CUDA OOM |
| 00 ctu13 --context host --node-key ip | GPUserver2 | ..._20261013_141829 | XGBoost CUDA OOM |
| 01 ctu13 endpoint isolated | GPUserver2 | ? | no metrics.json (did not finish) |
| 01 ctu13 endpoint ipport | GPUserver2 | ..._20261013_145354 | PytorchStreamWriter failed = disk full |
Incomplete dirs deleted in the 2026-10-14 cleanup (D09).
Fixes before rerun (= E013): (1) `--xgb-device` option in 00 so XGBoost runs on CPU hist (n_jobs 16) while the MLP uses the GPU (A011); (2) class-weighted loss for endpoint GNN before CTU-13 GNN reruns (A010); (3) check `df -h ~` ≥ 15 GB before each GNN run.
