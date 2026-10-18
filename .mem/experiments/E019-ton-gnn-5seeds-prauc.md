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
## Results
(pending)
