# E022 CTU-13 unseen infected scenarios: identity-leakage control (A028)
Status: ANALYSED 2026-10-29 (leakage refuted; GNN host aggregation does not transfer). Serves C3.
## Hypothesis
Host-context gain (GNN ip, XGB/MLP host-ip vs plain) observed on the CTU-13 chronological split shrinks below .02 PR-AUC when the test contains infected captures (bot hosts/families) unseen in training — i.e. the gain is partly identity/scenario memorisation.
## Change
- New split mode for CTU-13: scenario-disjoint test of infected captures not in train (exact scenario assignment fixed in implement; record in D# if it deviates from the 60/20/20 protocol).
- Run GNN ip cwbal, XGB/MLP plain + host-ip, 5 seeds, 07 threshold-free metrics (PR-AUC, block bootstrap).
## Implementation
src/data/ctu13.py: `CTU13_SPLITS` + env `CTU13_SPLIT=unseen` switches CTU13_DEFAULT_SPLIT for 00/01/06/08 (no other code change; default unchanged). Split D21: train 1-5,9,10,13 / val 11 / test 6,7,8,12. Verified on GPUserver2: train 15,916,752 flows (423,547 bot), val 107,251 (8,164), test 3,952,697 (12,988). Commit 4952d01.
Queue waits for E021_DONE (shared data/graphs). Runs GNN ip + isolated (not ipport) and tab plain/host-ip, all cwbal. Still unsmoked end to end (GPU/graph path).

## Config
scripts/queue_E022.sh on GPUserver2 (CTU-13 data only there; GPUserver1 has none).
## Success criterion
- Supported (leakage): context gain (host-ip − plain, PR-AUC) on unseen scenarios < .02 or CI includes 0, 5 seeds.
- Refuted: gain ≥ .02 in 5/5 seeds, CI excludes 0 → context gain generalises.
## Results (2026-10-29, .mem/results/E022.json = results/E022_threshold_free.json; 5 seeds, block 10, 10k resamples; 0 val/test row mismatches)
| model | PR-AUC | ROC-AUC | F1@.5 | F1 val-tuned |
|---|---|---|---|---|
| XGB host-ip cw | .670 (sd .019) | .944 | .612 | .681 |
| MLP host-ip cw | .501 (sd .121) | .890 | .575 | .558 |
| GNN ip cwbal | .129 (sd .028) | .909 | .213 | .056 |
| MLP plain cw | .134 | .906 | .086 | 0 |
| XGB plain cw | .117 | .902 | .104 | 0 |
| GNN isolated | .080 | .877 | .131 | 0 |
Paired per seed (PR-AUC): XGB host-ip − plain +.552 [.527,.579] 5/5; MLP host-ip − plain +.367 [.179,.484] 5/5; GNN ip − isolated +.048 [.001,.077] 5/5; GNN ip − XGB plain +.011 [−.032,.037] 4/5; GNN ip − XGB host-ip −.541 [−.559,−.507] 0/5.
Per test scenario (PR-AUC, scenario order 6/7/8/12): XGB host-ip .98/.10/.63/.02; GNN ip .53/.01/.05/.02; XGB plain .48/.01/.06/.01. Scenario 12 (NSIS.ay) is undetected by every model; scenario 6 carries most of the pooled PR-AUC.
Bootstrap CI keys not in the JSON (summary gives means/min-seed only) → verdict on per-seed signs and ranges.
## Interpretation
The tabular host-context gain is not identity or family memorisation: it survives unseen families with a larger margin than on the default split (K12, K14). The GNN-ip host aggregation does **not** transfer: it is ≈ plain XGB and far below XGB host-ip on unseen families. Val-tuned thresholds (val 11) fail on new families for all non-context models (F1 0).
## Verdict
- H (leakage: host-ip − plain < .02 or CI ∋ 0): REFUTED for XGB and MLP (+.55 / +.37, 5/5).
- C3 closed: context gain generalises to unseen infected families for tabular host context, not for the endpoint GNN.
- Caveat (D21): infected host IPs are reused across scenarios. Identity is hidden from the models, so this is family-disjoint, not host-disjoint.
