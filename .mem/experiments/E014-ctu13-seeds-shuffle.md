# E014 CTU-13 topology test: 5 seeds + shuffled-endpoint ablation (A022, A025)
Status: PLANNED. Decides C2 on CTU-13 (project.md C2, D12).
## Hypothesis
H: the E013 CTU-13 GNN ip gain (.844 vs isolated .639 / ipport .675, seed 42) is topology: GNN ip - max(controls) >= max(0.02, 2x pooled seed std), 5/5 seeds positive, block-bootstrap CI excludes 0, shuffle costs >= 0.02.
## Change
No code change expected for the seed runs (01 --seed). 06 shuffle on ip checkpoint (test-time); train-time shuffle only if borderline.
## Config
01 ctu13 --graph endpoint --model egraphsage --node-key {ip,isolated,ipport} --window-size 10000 --epochs 50 --class-weight balanced --seed {42,43,44,45,46} --deterministic (GPUserver2, as E013).
06 modes: none / random_dst / random_src / random on each ip checkpoint; label test-time.
Controls for the max: XGB/MLP host ip (E013, 5 seeds), window, plus E015 neighbour-aggregate XGB.
Bootstrap block length N: TO FIX BEFORE RUNNING (>= 1 CTU-13 scenario or >= N windows): N = ___
Disk: df -h ~ >= 15 GB before; delete data/graphs/* after (D09).
## Success criterion
C2(a)-(d) per project.md, CTU-13 only. Record GNN seed std here (first measurement).
## Results
(pending)
