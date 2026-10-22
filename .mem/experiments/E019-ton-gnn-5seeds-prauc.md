# E019 ToN endpoint GNN 5 seeds + threshold-free comparison (A016, A026-ToN)
Status: IMPLEMENTED 2026-10-18 (scripts/queue_E019.sh, config-only: no new Python), not deployed (D16). Makes K11 a 5-seed claim (hard rule).
## Hypothesis
On ToN the GNN ip gain is host context: GNN ip − max(XGB/MLP host-ipport, host-ip, plain) < max(.02, 2× GNN seed std) on PR-AUC and F1@0.5.
## Change
01 ToN endpoint E-GraphSAGE ip/ipport/isolated (cwbal as CTU-13? decide: keep E008 settings for comparability, record) seeds 42-46 (seed 42 reuse if settings equal); 06 --save-scores --scores-only; 00 ToN plain/host-ip/host-ipport --save-scores; 07. GPUserver1 (ToN cache ~5.5 GB each, delete after: D09).
## Success criterion
Supported (C2 negative on ToN, 5 seeds) if gap < floor on PR-AUC; if GNN > floor on PR-AUC, reopen C2 for ToN (D15 reopen condition).
## Implementation
- scripts/queue_E019.sh (GPUserver1; bash -n ok, no smoke possible locally): per node key {ip, ipport, isolated}: 01 seeds 42-46 with E008 settings (L2, w10000, 50 ep, unweighted CE, --deterministic; seed 42 retrained on this server so all 5 seeds are co-located and uniform), 06 --save-scores --scores-only (results/E019_gnn_<k>/), then `rm -rf data/graphs/*` (disk 11 GB free, D09); then 00 ToN plain / host-ip / host-ipport (5 seeds, CPU XGB, --save-scores) and 07 (--target ip) -> results/E019_threshold_free.json.
- 15 GNN trainings; time unmeasured (CTU-13 equivalents not comparable). Existing seed-42 ckpts are on GPUserver2 and are not reused.
- Risk: 07 aborts if GNN and tabular ToN test flows differ in label order (identity check); GPUserver1 GPU was often 99% busy with other users (infra.md).
## Results (fetched 2026-10-21, .mem/results/E019.json; 07 under key threshold_free; block 10 windows, 10k resamples)
| model (ToN test, 5 seeds) | F1@0.5 | PR-AUC | ROC-AUC | F1 val-tuned |
|---|---|---|---|---|
| GNN ip | .883±.096 (s45 .714) | .903 | .946±.003 | .947 |
| GNN ipport | .909±.017 | .900 | .927 | .915 |
| GNN isolated | .789±.110 | .877 | .922 | .918 |
| XGB host-ipport (best competitor) | .931 | .954 | .971 | .970 |
| XGB host-ip / plain | .201 / .869 | .927 / .930 | .955 / .928 | .859 / .934 |
| MLP host-ipport / host-ip / plain | .917 / .906 / .735 | .915 / .900 / .882 | .959 / .950 / .849 | .953 / .915 / .811 |
Gap GNN ip − XGB host-ipport: PR-AUC −.051 (all 5 seeds −.043..−.056, CI [−.115,−.007]); F1@0.5 −.048 (CI [−.067,−.025], min seed −.217); F1 tuned −.023 (5/5 negative, CI [−.036,−.016]).
Identity check: 0 label mismatches on every key/seed reported; ip/42 is absent from the mismatch dict (its point scores exist) - check in 07 if this table goes into the paper.
## Interpretation
- No metric favours GNN ip on ToN: it loses to XGB host-ipport on PR-AUC in 5/5 seeds, with the CI excluding 0, and its PR-AUC (.903) is even below plain XGB (.930). C2(a) fails clearly (gap negative, not just below the floor).
- E008's seed 42 (F1 .937) was a favourable draw: GNN ip F1@0.5 seed std .096 (seed 45 .714), but ROC-AUC std only .003 -> on ToN, GNN seed noise lives in threshold placement, not ranking (as K14 found for CTU-13).
- The XGB host-ip F1@0.5 collapse (.20 with PR-AUC .93) is the same calibration-under-drift effect (K10/K11).
## Verdict
SUPPORTED: C2 negative on ToN with 5 seeds. Endpoint-GNN gains are host context on both datasets; K11 upgraded to high. A016 closed.
