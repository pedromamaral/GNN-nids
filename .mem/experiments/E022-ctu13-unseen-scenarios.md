# E022 CTU-13 unseen infected scenarios: identity-leakage control (A028)
Status: IMPLEMENTED 2026-10-23 (D20, D21); not launched. Serves C3.
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
## Results
(pending)
