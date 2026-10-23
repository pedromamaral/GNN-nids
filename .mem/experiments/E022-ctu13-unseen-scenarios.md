# E022 CTU-13 unseen infected scenarios: identity-leakage control (A028)
Status: PLANNED 2026-10-23 (D20). Serves C3.
## Hypothesis
Host-context gain (GNN ip, XGB/MLP host-ip vs plain) observed on the CTU-13 chronological split shrinks below .02 PR-AUC when the test contains infected captures (bot hosts/families) unseen in training — i.e. the gain is partly identity/scenario memorisation.
## Change
- New split mode for CTU-13: scenario-disjoint test of infected captures not in train (exact scenario assignment fixed in implement; record in D# if it deviates from the 60/20/20 protocol).
- Run GNN ip cwbal, XGB/MLP plain + host-ip, 5 seeds, 07 threshold-free metrics (PR-AUC, block bootstrap).
## Config
scripts/queue_E022.sh (GPUserver1, after cache cleanup; disk 7.6 GB).
## Success criterion
- Supported (leakage): context gain (host-ip − plain, PR-AUC) on unseen scenarios < .02 or CI includes 0, 5 seeds.
- Refuted: gain ≥ .02 in 5/5 seeds, CI excludes 0 → context gain generalises.
## Results
(pending)
