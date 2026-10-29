# E024 ToN port of Part 3 joint shaping+decoy attack (A033)
Status: IMPLEMENTED 2026-10-29 (sha 12fab85; smoke running GPUserver1, logs/queue_E024_smoke.log) — was PLANNED (D22, needed-for-paper). Serves C4 generality, K15/K16.
## Hypothesis
On NF-ToN-IoT-v3, as on CTU-13 (K15, K16): (a) at equal byte budget the joint attack ≈ best single attack on GNN ip (G ≥ .03 in ≤ 1/5 seeds) and is subadditive on host-context tabular; (b) GNN-ip shaping vulnerability Δ_A varies across training seeds far more than attack noise (CV ≥ .3), while MLP/XGB host-ip stays tight.
## Change
- Port the 08 joint attack (E017/E020 spec D17) to NetFlow-v3 features: map the raw controllable fields (bytes, packets, duration twins of Dur/TotPkts/SrcBytes) with increase-only shaping in raw space; decoys from bot hosts to popular benign destinations; operating point 1% FPR.
- Detectors: GNN ip (E019 settings), MLP host-ip, XGB host-ip (transfer). Delay off (K15). β .1/.5, ρ 0/.5/1. 5 training seeds (10 if the ToN spread is ambiguous) × 2 attack seeds; signed S, clean_stats.json.
## Config
scripts/queue_E024.sh (GPUserver1; `SMOKE=1` = 1 seed, beta .5, 2 chunks, 5 steps, no XGB). Code: `08 --dataset nf-ton-iot-v3` + `Space` in src/attacks/context_attack.py (CTU-13 path unchanged: default CTU13_SPACE). Reuses E019 GNN-ip ckpts seeds 42-46; MLP/XGB fitted+cached in results/E024_models/seed_s; out results/E024/seed_s. Grid: beta .1/.5, rho 0/.5/1 (+budget-matched A/B), delay off, attack seeds 0,1.
Spec: raw Dur=FLOW_DURATION_MILLISECONDS, TotPkts=IN+OUT_PKTS, TotBytes=IN+OUT_BYTES, SrcBytes=IN_BYTES (added bytes/pkts are client->server; OUT_* fixed). Driven columns: IN_BYTES, OUT_BYTES, IN_PKTS, FLOW_DURATION_MS, DURATION_IN (+dur delta), SRC_TO_DST_SECOND_BYTES and SRC_TO_DST_AVG_THROUGHPUT (x bytes-ratio / dur-ratio; assumption, definitions not checked against data).
**L1 limitation:** packet-size histograms (NUM_PKTS_*), LONGEST/SHORTEST/MIN/MAX pkt len and IATs are NOT recomputed after shaping/decoys (attacker flows are only partly self-consistent). State in the paper; if reviewers push, add a histogram update (added pkts at avg size dsrc/dpkts).
## Success criterion
- K15 replicates: G ≥ .03 in ≤ 1/5 GNN seeds, S < 0 on host-ip 5/5.
- K16 replicates: GNN CV(Δ_A, β .5) ≥ .3 and MLP CV < .15.
- Either fails → report a dataset dependence (no claim of generality).
## Results
(pending)
