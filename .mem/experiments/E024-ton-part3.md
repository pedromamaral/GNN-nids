# E024 ToN port of Part 3 joint shaping+decoy attack (A033)
Status: ANALYSED 2026-11-02, INCONCLUSIVE (degenerate 1%-FPR operating point on ToN, K18) — was IMPLEMENTED 2026-10-29 (sha 12fab85), PLANNED (D22, needed-for-paper). Serves C4 generality, K15/K16.
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
## Results (2026-11-02, .mem/results/E024.json; per-flow white/transfer rows, mean of attack seeds 0/1, seeds 42-46)
| detector, β .5 | clean recall@1%FPR (tally) | Δ_A per seed | Δ_B per seed | S(ρ.5) | G≥.03 |
|---|---|---|---|---|---|
| GNN ip (white) | .076/.001/.011/.047/.000 | .035/.001/.000/.037/.000 (CV 1.34) | .071/.001/.010/−.037/.000 | −.016..+.000 | 0/5 |
| MLP host-ip (white) | ≈0 all seeds (thr 1.000) | ≤.002 | ≤.002 | ≈0 | 0/5 |
| XGB host-ip (transfer) | .056-.124 | ≤.008 | −.13..−.32 (recall UP) | +.003..+.027 | 0/5 |
| XGB plain (transfer) | .160-.192 | .011-.105 | 0 | −.007..+.039 | 1/5 (s44 .039) |
- Attack-seed noise ≤.003 (Δ), ≤.010 (S). Host-window rows show the same pattern (GNN Δ_A β.5 ≤.20, s45).
- Clean at threshold .5 is fine (GNN recall .58-.99, MLP .81-.94, XGB plain .80): the 1%-FPR point kills recall, not the models.
- Code check (subagent, 08:152-192): threshold = 0.99 quantile of float32 **sigmoid probabilities** of **test** benign flows; tally uses `>=`, clean_stats uses `>` (inconsistent); no tie handling; MLP thr saturates at 1.000, GNN .999-1.000; logit clip ±13.8.
## Interpretation
On ToN the test benign tail (>1% of benign flows, drift K10/K11) scores at or near probability saturation, above almost every malicious flow. At 1% FPR the clean recall is ≤.08 for both white-box detectors, so Δ_A/Δ_B/S are floored near 0 by construction. The low CVs and S≈0 measure the floor, not robustness. Negative Δ_B on XGB host-ip (decoys raise recall at a fixed threshold) is real but uninformative here.
## Verdict
- H(a) K15 replicates: INCONCLUSIVE. G≥.03 0/5 GNN is met nominally, but there is no recall left to attack. S<0 on host-ip 5/5 is NOT met (MLP ≈0, XGB >0).
- H(b) K16 replicates: INCONCLUSIVE. GNN CV 1.34 sits on a mean Δ_A of .014; MLP CV is undefined (Δ≈0).
- Operating-point artefact, not a dataset finding. Do not report it as 'dataset dependence'. Fix: A037 (E025).
