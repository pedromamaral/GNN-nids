# Decisions (also in docs/PAPER_ROADMAP.md "Decision log")
# D# | date | decision | why | alternatives rejected

D01 | 2026-10-05 | Decomposition (A/B/C) first, go/no-go at week 3; random edge perturbations only as upper bound | edges of a feature-derived graph are not attacker-editable | Nettack/Metattack (A007)
D02 | 2026-10-06 | Datasets: NetFlow-v3 only (+CTU-13 optional); experiments in containers via scripts/container.sh | paper relevance; reproducibility on shared servers | NSL-KDD, CICIDS2017 (A020)
D03 | 2026-10-07 | Drop TTL (MIN_TTL, MAX_TTL; ARTEFACT_COLUMNS in src/data/netflow_v3.py) → 44 features | testbed hop-distance artefact, attacker sets own TTL, does not transfer (K01) | keep TTL
D04 | 2026-10-07 | Protocol: sort by FLOW_START_MILLISECONDS, chronological 60/20/20, windows of consecutive flows, scaler on train; k-NN ties broken by index (float64, 1e-9 quantisation); DNS_QUERY_ID dropped | no temporal leakage; deterministic graphs (churn 0.65% → 0) | random splits (as in lit)
D05 | 2026-10-12 | Paper direction = Avenue #1, target Computers & Security; Parts: (1) k-NN mechanism, (2) endpoint vs XGBoost + CTU-13, (3) decomposition with joint attacker | k-NN NO-GO everywhere; endpoint graphs carry structure; GIANT does injection only | Avenues #2/#3 standalone (A013, A014), address-graph alone (A004)
D06 | 2026-10-13 | CTU-13: Background = benign by default (option to drop); train 1-8, val 11-12 (12 = unseen family NSIS.ay), test 9/10/13; windows per scenario; identity hidden from models (infected IPs reused across scenarios, e.g. 147.32.84.165) | scenario-disjoint captures as identity-leakage control | host-disjoint split (impossible: IP reuse)
D07 | 2026-10-13 | Endpoint graphs: nodes relabelled per window, constant node features (no IP identity reaches the model); node_key ∈ ipport | ip | isolated (no-topology control); pilot window 10,000 flows | prevents identity leakage; isolated = clean topology ablation | IP-feature nodes
D08 | 2026-10-07 | Push to `origin` (github.com/pedromamaral/GNN-nids), never to `student` (jcaeiro02) | student remote is separate | -
D09 | 2026-10-14 | Disk policy: graph caches (data/graphs/*) deleted after each batch; keep raw data, finished results, checkpoints, logs | shared disks ≤32 GB free; ToN endpoint cache ~5.5 GB each, k-NN ToN 9.4 GB | keep all caches
D10 | 2026-10-14 | Memory workflow: .mem/ (research-memory skill) replaces long conversations; E ids E001-E012 reconstructed from .mem/_import.md + server result dirs | credit cost of long context | -
