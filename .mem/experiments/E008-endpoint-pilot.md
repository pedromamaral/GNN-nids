# E008 endpoint E-GraphSAGE pilot (A008, claim C2)
Date 2026-10-12/13 · seed 42 · results .mem/results/E008.json
Cmd: `python experiments/01_baseline_training.py --dataset <ds> --graph endpoint --model egraphsage --node-key {ipport,ip,isolated} --window-size 10000 --epochs 50 --seed 42 --deterministic`
Dirs: GPUserver1 results/runs/20261012_18*_nf-unsw-nb15-v3_egraphsage_endpoint_* ; GPUserver2 results/runs/2026101{2,3}_*_nf-ton-iot-v3_egraphsage_endpoint_*

| test F1 | ipport | ip | isolated | XGB (E002) |
|---|---|---|---|---|
| UNSW | 0.9973 | 0.9388 | 0.9975 | 0.9995 |
| ToN | 0.8990 | 0.9372 | 0.7270 | 0.8717 |

- UNSW: topology adds nothing (isolated = ipport ≈ XGB).
- ToN: ip beats XGB by 0.066 and isolated by 0.21 — but E009 ablation: shuffled endpoints keep 0.91-0.94, no edges 0.79 → window-composition confounder suspected (K06).
- Val→test drift on ToN: isolated best val 0.961, test 0.727 (K10).
- Single seed: GNN seed noise unknown (A022).
Next: E013 controls (ToN --context window / host) decide the Part 2 framing (A023).
