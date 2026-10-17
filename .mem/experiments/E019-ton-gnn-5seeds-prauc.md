# E019 ToN endpoint GNN 5 seeds + threshold-free comparison (A016, A026-ToN)
Status: PLANNED (D16). Makes K11 a 5-seed claim (hard rule).
## Hypothesis
On ToN the GNN ip gain is host context: GNN ip − max(XGB/MLP host-ipport, host-ip, plain) < max(.02, 2× GNN seed std) on PR-AUC and F1@0.5.
## Change
01 ToN endpoint E-GraphSAGE ip/ipport/isolated (cwbal as CTU-13? decide: keep E008 settings for comparability, record) seeds 42-46 (seed 42 reuse if settings equal); 06 --save-scores --scores-only; 00 ToN plain/host-ip/host-ipport --save-scores; 07. GPUserver1 (ToN cache ~5.5 GB each, delete after: D09).
## Success criterion
Supported (C2 negative on ToN, 5 seeds) if gap < floor on PR-AUC; if GNN > floor on PR-AUC, reopen C2 for ToN (D15 reopen condition).
## Results
(pending)
