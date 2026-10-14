# Import from conversation (2026-10-07 .. 2026-10-14; running-state checked 2026-10-14 13:55)

Terse, one fact per line. Not in the code. Times are server-local unless noted.

## Workflow / infrastructure
- Workflow: edit locally -> commit+push to origin (github.com/pedromamaral/GNN-nids, main) -> `git pull` on a GPU server -> run in container via `scripts/container.sh`. Never run experiments locally (laptop has no torch/data).
- Servers: `ssh GPUserver1` (10.26.110.15, CoShareStation1) and `ssh GPUserver2` (10.26.110.14, CoSHARE2), user pedroamaral, 1x RTX 2080 Ti 11 GB, 125 GB RAM, 16 cores each; repo at `~/GNN-nids`. Reachable only with VPN/campus network (VPN drops often: route goes via 192.168.1.1 when down).
- Pick server by headroom (`nvidia-smi`); GPUserver1 GPU is often 100% busy with other users' jobs.
- Disk is filling (shared): 2026-10-13 GPUserver2 19 GB free, GPUserver1 10 GB free. Graph caches for ToN are several GB; may need to delete old caches (e.g. k-NN ToN graphs) before the 5-seed grid.
- Servers were physically moved 2026-10-13 (rebooted: GPUserver1 12:35, GPUserver2 13:04); all containers and queue scripts died. Queue scripts (`logs/queue_*.sh`, setsid nohup) do not survive reboots.
- Launch pattern that works: write a queue script on the server via ssh heredoc, run with `setsid nohup ... &`. Nested quoting of `$var` inside `ssh "... container.sh run '...'"` broke once (empty `--node-key`).
- `container.sh test` already passes `-q`; adding another `-q` hides the pytest summary line.
- Local Python env for lit-review scripts: scratchpad venv (networkx, scipy, requests); not in repo.

## Data / protocol decisions
- Paper datasets: NetFlow-v3 (NF-UNSW-NB15-v3 dev, NF-ToN-IoT-v3), CTU-13 added 2026-10-13. NSL-KDD/CICIDS2017 dropped (2026-10-06).
- Chronological 60/20/20 split by FLOW_START_MILLISECONDS; windows of consecutive flows; scaler fit on train only.
- Features: 44 after dropping IPs, ports, DNS_QUERY_ID, timestamps, and TTL (MIN_TTL, MAX_TTL).
- TTL dropped (2026-10-07): on UNSW MIN_TTL alone gives test F1 0.9992; TTL 31 always benign, 62 always attack, 254 attack in 30,704/30,706. Rationale for paper: testbed hop-distance artefact, does not transfer, attacker controls its initial TTL. Without TTL XGBoost still 0.9995.
- k-NN ties: ~30% of flows in a 1000-flow window are exact duplicates; ties now broken by index (float64, 1e-9 quantisation) so rebuild is deterministic. Before the fix reconstruction churn was 0.65% with 0 exact windows; after: 0.0 on all 2,368 UNSW windows.
- UNSW split: attack fraction train 3.0%, val 9.3%, test 8.7%; all 9 classes in each split; val/test are ~4.6 h each at the end of 2015-02-18.
- ToN split: attack fraction train 27%, test 55% (temporal drift); Backdoor recall ~0 for XGBoost.
- CTU-13: downloaded on GPUserver2 only via wget from mcfp.felk.cvut.cz/publicDatasets/CTU-13-Dataset/CTU-13-Dataset.tar.bz2 (1,997,547,391 B). Archive contains live malware .exe samples: only *.binetflow + READMEs extracted to `data/raw/ctu13/CTU-13-Dataset/<n>/`, archive deleted. ~20M flows: Background ~19.1M, From-Botnet 444,699, Normal ~356k.
- CTU-13 choices: Background = benign by default (label noise; option drop); split train 1-8, val 11-12 (12 = unseen family NSIS.ay), test 9/10/13 (new runs of Neris/Rbot/Virut); windows per scenario. Infected IPs reused across scenarios (e.g. 147.32.84.165), so split separates captures not hosts; identity hidden from models instead.
- Endpoint graphs: nodes relabelled per window with constant features (no IP identity reaches the model); node_key ipport | ip | isolated (no-topology control); window 10,000 flows in pilots.

## Results (key numbers)
- Tabular, no TTL, 5 seeds, test F1: UNSW XGBoost 0.9995±0.0000, MLP 0.9985±0.0001. ToN XGBoost 0.8717±0.0029 (AUC 0.937), MLP 0.7345±0.0175 (AUC 0.849).
- Difficulty probe UNSW: LR 0.9907, depth-2 tree 0.9927; random ±0.05σ noise drops XGBoost to 0.78, ±0.5σ to 0.35. ToN: LR 0.66; ±0.1σ noise -> 0.20. Clean ease != robustness.
- k-NN GNN pilots (Phase 2 go/no-go, 1 training seed, 2 attack seeds, ε 0.05-0.5) all NO-GO: UNSW GCN (clean 0.976, 100 windows) structure effect ≤0.003, adaptive gain ≤0.009; UNSW GAT (clean 0.986) ≤0.001 / ≤0.004; ToN GCN (clean 0.81, 300 windows) ≤0.0004 / ≤0.019; feature effect large (UNSW GCN A=0.20 at ε=0.25, 0.79 at 0.5); NCR_mal 14-38%.
- k-NN graph ablation (`06_graph_ablation.py`, full test, F1 knn/none/random): UNSW GCN 0.975/0.995/0.21; UNSW GAT 0.986/0.995/0.15; ToN GCN 0.812/0.814/0.815. Removing edges changes 0.2-1.2% of predictions: k-NN neighbours are near-copies -> graph redundant.
- Endpoint E-GraphSAGE pilot (seed 42, w=10k, test F1): UNSW ipport 0.9973, ip 0.9388, isolated 0.9975. ToN ipport 0.899, ip 0.937, isolated 0.727. Runs: `results/runs/20261012_*_nf-{unsw-nb15,ton-iot}-v3_egraphsage_endpoint_{ipport,ip,isolated}_w10000_L2_seed_42` (UNSW on GPUserver1, ToN on GPUserver2).
- Endpoint ablation on trained models (F1 graph/none/random_dst/random_src/random): ToN ip 0.937/0.790/0.940/0.910/0.915; ToN ipport 0.899/0.745/0.902/0.911/0.895; UNSW ip 0.939/0.520/0.04/0.03/0.00 (brittle); UNSW ipport 0.997/0.990/0.43/0.906/0.36. ToN needs a neighbourhood but not the real one -> suspected window-composition confounder.
- Host-context tabular (UNSW, ip, 5 seeds): XGBoost 0.999998, MLP 0.9996 (`results/tabular/20261013_095833_nf-unsw-nb15-v3_host-ip-w10000/`, GPUserver1).
- UNSW window context (5 seeds): XGBoost 0.99939±0.00003, MLP 0.99820±0.00028. UNSW host context ipport: XGBoost 0.99966±0.00004, MLP 0.99815±0.00058. On UNSW every variant is ~0.998-1.000: no room for context/topology gains.
- CTU-13 tabular (5 seeds, scenario-disjoint test 9/10/13): plain XGBoost 0.5308±0.0004 (AUC 0.959), MLP 0.4840±0.0265 (AUC 0.937); window context XGBoost 0.4052±0.1677 (AUC 0.954, very unstable), MLP 0.2172±0.0203. CTU-13 is hard under this split and window context hurts.
- CTU-13 E-GraphSAGE ip (seed 42): test F1 0.0 (train 0.0002): degenerate, predicts all benign (botnet ~2% of flows, Background counted benign); needs class weighting / threshold tuning before any conclusion.
- Run-to-run noise: XGBoost seed std ≤0.003 F1; MLP ToN std 0.0175; GNN multi-seed noise not yet measured (only seed 42).

## Ideas tried / rejected
- Original paper claim (k-NN feature-structure coupling matters) rejected as main contribution: coupling real (rewires 14-38%) but inconsequential because k-NN graph is redundant. Kept as Part 1 (mechanism + adversarial consequence).
- CTU-13 as a rescue for k-NN graphs rejected: redundancy comes from feature-derived construction, not the dataset.
- Graph construction as defence for k-NN graphs rejected (graph is redundant); kept as optional for endpoint graphs.
- Address-graph direction alone rejected as overlapping GIANT; chosen framing is decomposition + own-flow-shaping attacker.

## Literature (docs/LITERATURE_REVIEW.md, docs/lit-graph/gnn-nids/)
- k-NN redundancy partly pre-empted by preprint "From Flow Features to Communication Topology" (Preprints.org 2026, CICIoMT2024, window-level, RF baseline, no mechanism, no attacks).
- GIANT (WWW 2026, doi 10.1145/3774904.3792601) already does joint injection (endpoints + features of injected flows), injection-only, no decomposition, random 80/20 split, no tabular baselines, no k-NN graphs.
- Venturi et al. 2024 (arXiv 2403.11830) evaluate feature and structural attacks separately (GNN robust to features, one injected flow collapses E-GraphSAGE); Venturi 2025 (NCA) adversarial-training defence.
- R+R ACSAC 2025 and arXiv 2609.12263 critique unsupervised temporal host-graph GIDS (encoder-free control ranks first on 2/4 datasets; 2 crafted edges evade).
- E-GraphSAGE (random 70/30, reported baselines, source IPs remapped because few IPs source attacks); Pujol-Perich 2022 (accuracy only similar to MLP/RF; robust to packet-size/IAT shifts).
- Open gaps: no feature/structure/interaction decomposition anywhere; no own-flow-shaping + injection attacker; construction-as-defence untested in NIDS; no chronological + same-split XGBoost comparison for endpoint GNNs.

## Decisions
- 2026-10-12: Paper direction = Avenue #1. Working title "Robust to Features, Fragile to Structure? Decomposing Adversarial Effects in Graph-Based Network Intrusion Detection". Target Computers & Security. Parts: (1) k-NN mechanism, (2) endpoint graphs vs XGBoost under same protocol + CTU-13, (3) A/B/C decomposition with joint attacker (own-flow shaping + injection, traffic-cost budget).
- Push to `origin`, not `student` remote (jcaeiro02).

## Running now (checked 2026-10-14 ~13:30-13:55): NOTHING running on either server
- Both queues (`logs/queue_a2c.sh`) have ended; no gnn_pedroamaral containers alive.
- GPUserver2 finished: 00 ctu13 plain (`results/tabular/20261013_124122_ctu13/`), 00 ctu13 --context window (`results/tabular/20261013_130000_ctu13_window-w10000/`), 01 ctu13 egraphsage ip (`results/runs/20261013_132610_ctu13_egraphsage_endpoint_ip_w10000_L2_seed_42`).
- GPUserver2 FAILED: 00 ToN --context window (container ..._20261013_132921) and 00 ToN --context host ip (..._133321) and 00 ctu13 --context host ip (..._141829): XGBoost CUDA OOM (requested 11.6 GB, 10.7 GB free). 01 ctu13 isolated: run dir exists, no metrics.json (did not finish). 01 ctu13 ipport (..._145354): "PytorchStreamWriter failed writing file" = disk full.
- GPUserver1 finished: 00 UNSW --context host ipport (`results/tabular/20261013_120237_nf-unsw-nb15-v3_host-ipport-w10000/`), 00 UNSW --context window (`results/tabular/20261013_120953_nf-unsw-nb15-v3_window-w10000/`). FAILED: 00 ToN --context host ipport (..._131642): XGBoost CUDA OOM.

## Open problems / next steps
- 2026-10-14 cleanup: deleted all graph caches (data/graphs/* on both servers), incomplete run/tabular dirs, test-suite nsl-kdd runs. Kept raw data, finished results, checkpoints, logs. Disk after: GPUserver2 32 GB free (95%), GPUserver1 11 GB free (99%). Next endpoint runs rebuild caches (ToN endpoint ~5.5 GB each, k-NN ToN 9.4 GB): keep only the caches in use and delete after each batch.
- XGBoost GPU OOM on context features (16.5M x 88/134): use CPU hist (n_jobs 16) or lower max_bin / external memory for xgboost only; needs a separate --xgb-device option in 00 (current --device applies to both models). Then rerun: ToN window (the key test), ToN host ip, ToN host ipport, ctu13 host ip.
- CTU-13 GNN all-benign collapse: add class-weighted loss (or focal) in Trainer for endpoint models; rerun ip / isolated / ipport after freeing disk.
- Decide Part 2 framing from ToN window-context vs host-context vs E-GraphSAGE ip (0.937): window ≈ GNN -> temporal confounder finding; host ≈ GNN -> host behavioural profile; GNN > both -> topology real.
- CTU-13 results (tabular + 3 GNN variants) not yet seen.
- A4: implement attacker (own-flow shaping + decoy injection, traffic-cost budget) and decomposition adapter for endpoint graphs; start after window-context result.
- A5: 5-seed grid for endpoint GNNs and controls; optional construction-as-defence sweep (node key, window, degree cap).
- Known artefact: test suite writes nsl-kdd runs into results/runs on servers.
- Phase 2 k-NN full seed grid (5x5) still not run; needed only for Part 1 robustness of claims.
