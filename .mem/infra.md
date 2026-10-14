# Infrastructure (no secrets here; ssh keys in ~/.ssh, aliases in ~/.ssh/config)

## Hosts (user pedroamaral, repo ~/GNN-nids, both have NF-UNSW-NB15-v3 + NF-ToN-IoT-v3 raw)
| alias | IP | hostname | GPU | RAM/CPU | notes |
|---|---|---|---|---|---|
| GPUserver1 | 10.26.110.15 | CoShareStation1 | 1× RTX 2080 Ti 11 GB | 125 GB / 16 cores | GPU often ~99% busy (other users). Disk 11 GB free (10-14) |
| GPUserver2 | 10.26.110.14 | CoSHARE2 | 1× RTX 2080 Ti 11 GB | 125 GB / 16 cores | CTU-13 data ONLY here (data/raw/ctu13/CTU-13-Dataset/<n>/*.binetflow). Disk 32 GB free (10-14) |
- Reachable only on VPN/campus; VPN drops often (route via 192.168.1.1 when down). `server2`/`server3` unreachable — ignore.
- Laptop: no torch, no data. Never run experiments locally. Local python3 3.14 (tools only); servers python3 3.10 (outside container).
- Pick host by headroom: `tools/runs_status.sh` prints GPU util/mem + free disk for both.

## Workflow
edit locally → commit → `git push origin main` → `ssh <host> 'cd ~/GNN-nids && git pull'` → run in container. Push to origin only (D08).

## Container (docker/, compose project gnn-pedroamaral-gpu0)
- `scripts/container.sh [-d] JOB [ARGS]`; JOB ∈ build | shell | test | check-data | smoke | phase1 | report | run CMD...
- Name: `gnn_pedroamaral_<job>_gpu0_<YYYYmmdd_HHMMSS>`; log tees to `~/GNN-nids/logs/<name>.log`.
- Image built on both servers; `git pull` updates code without rebuild (rebuild only when docker/requirements.txt changes: `scripts/container.sh build`).
- `container.sh test` already passes `-q` (don't add another: it hides the summary).
- DATA_RAW defaults to ./data/raw (must contain netflow-v3/; ctu13/ for CTU-13). GPU=n selects GPU (always 0).

## Launch pattern (works; survives ssh disconnect, NOT reboots)
```
ssh GPUserver2 'cat > ~/GNN-nids/logs/queue_X.sh' <<'EOF'
#!/usr/bin/env bash
cd ~/GNN-nids
run() { GPU=0 scripts/container.sh run "$1"; }
run "python experiments/00_tabular_baselines.py --dataset nf-ton-iot-v3 --context window"
EOF
ssh GPUserver2 'cd ~/GNN-nids && chmod +x logs/queue_X.sh && setsid nohup logs/queue_X.sh > logs/queue_X.log 2>&1 < /dev/null &'
```
- `chmod +x` the queue script BEFORE launching (2026-10-14: "Permission denied", queue silently ended). The launching ssh does not return even when detached (setsid -f): run it with Bash run_in_background and verify with tools/runs_status.sh. Server clock ≈ laptop +4-5 h (container logs in UTC).
- Write scripts via heredoc: nested `$var` quoting inside `ssh "... container.sh run '...'"` broke once (empty --node-key).
- Register in .mem/runs.md as `E0xx | host | queue:queue_X.sh | ... | running`; then container names as they appear.

## Monitor / fetch
- Status: `tools/runs_status.sh` (one ssh per host, ≤20 lines). Never stream logs; `ssh h 'tail -n 30 ~/GNN-nids/logs/<name>.log'` at most.
- Results: `python3 tools/summarize_run.py E0xx GPUserverN:results/runs/<dir> ...` → .mem/results/E0xx.json (runs extraction server-side; no copying).
- Output dirs: results/runs/<ts>_<ds>_<model>_... (01: metrics.json, best_checkpoint.pt, training_log.txt); results/tabular/<ts>_<ds>[_ctx] (00: summary.csv, results.csv, per_class.csv, config.json); results/graph_ablation/<ts>/graph_ablation.csv (06); results/pilot/decomposition/ (05/05b: go_no_go.csv, decomposition_summary.csv).

## Gotchas
- Disk: shared, ≤32 GB free. Graph caches in data/graphs/ (ToN endpoint ~5.5 GB each, k-NN ToN 9.4 GB): delete after each batch (D09). Check `df -h ~` before GNN runs; a full disk kills checkpoint writes.
- XGBoost on GPU OOMs on context features (ToN/CTU-13 16.5M × 88/134): use CPU (A011). `--device` in 00 applies to both XGB and MLP.
- Servers were moved/rebooted 2026-10-13: queue scripts and containers die on reboot → check with runs_status.sh after any outage.
- Test suite writes nsl-kdd runs into results/runs on servers (artefact; delete).
- `--deterministic` warns (not aborts) on GAT scatter kernels.
- CTU-13 archive contained live malware .exe: only *.binetflow + READMEs extracted; never re-extract the full archive.
