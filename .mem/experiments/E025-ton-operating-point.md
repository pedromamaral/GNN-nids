# E025 ToN operating-point diagnostic for Part 3 (A037, D23)
Status: PLANNED 2026-11-04. Serves C4 generality, K15/K16 (unblocks the ToN Part 3 rerun after K18).
## Hypothesis
The E024 floor (clean recall@1%FPR GNN ≤.08, MLP ≈0) is mainly float32 sigmoid saturation: ≥1% of test benign flows tie at p≈1.0. Ranking on logits gives GNN-ip recall@1%FPR ≥.3. Alternative: a genuinely drifted benign tail (K10/K11), so the logit recall@1%FPR also stays <.3.
## Change
- Clean scoring only (no attack), no retraining: E019 GNN-ip ckpts and E024 MLP host-ip / XGB host-ip / XGB plain caches (results/E024_models/seed_s), seeds 42-46, ToN test + val.
- Per detector and seed, report:
  - (i) fraction of test benign flows with p ≥ 1−1e-7 (ties);
  - (ii) recall at 1% and 5% FPR with thresholds on logits / XGB margins, set on TEST benign;
  - (iii) the same with thresholds set on VAL benign, plus the realised test FPR;
  - (iv) recall at a val-set threshold matched to clean recall .9.
- Fix in 08 (needed for the rerun anyway): score with logits; `>=` in both tally and clean_stats.
## Config
Small script or 08 `--clean-only` flag; GPUserver1; ~1 GPU-h. Output clean_op.json per seed → summarize_run → .mem/results/E025.json.
## Success criterion / decision rule
- GNN-ip logit recall@1%FPR (test-benign threshold) ≥.3 in ≥4/5 seeds → saturation: rerun E024 grid at 1% FPR on logits (E026, ~6 GPU-h); the CTU-13 setting stays comparable.
- Otherwise, if recall@5%FPR or the matched-recall point is ≥.3 → rerun there, labelled as a different operating point from CTU-13.
- Otherwise → ToN Part 3 is not evaluable at low FPR; report it as a limitation (no generality claim for K15/K16).
- Val-benign thresholds with realised test FPR ≫ target → record as a drift caveat (K10).
## Implementation (2026-11-05)
- 08: `--clean-only` (NetFlow-v3 only; writes clean_op.json, no attack) and `--score-space {prob,logit}` (default prob = E017-E024 unchanged). Detectors get `use_logit` (MLP/GNN logits, XGB `output_margin`); logit mode: thr_logit = thr, half = 0. `>=` now in clean_stats too (was `>`; only differs on exact ties). `clean_operating_points()` computes (i)-(iv) plus the E024 prob-space point for reference. `load_test(part="val")`.
- Queue: scripts/queue_E025.sh (SMOKE=1 -> seed 42, 2 chunks -> results/E025_smoke). Out: results/E025/seed_s/clean_op.json. tools/summarize_run.py reads clean_op.json.
- Not smoke-tested yet (no torch locally): first deploy step is `SMOKE=1 scripts/queue_E025.sh`. Reuses E024_models/seed_s caches (must still be on GPUserver1).
## Results
(pending)
