# E018 Class-weighted tabular on CTU-13 (A030)
Status: PLANNED (D16). Closes the F1@0.5 confound in K14.
## Hypothesis
With a matched training prior (XGB scale_pos_weight = n_neg/n_pos, MLP BCE pos_weight = n_neg/n_pos, as GNN cwbal), tabular host-ip F1@0.5 reaches ≥ GNN ip − .058; i.e. the GNN's F1@0.5 edge is the loss weighting, not the graph.
## Change
00_tabular_baselines.py `--class-weight balanced` (default off); plain + host-ip, XGB+MLP, seeds 42-46, `--save-scores`; rerun 07 with the E016 GNN npz.
## Success criterion
Supported if gap GNN ip − best class-weighted tabular < .058 on F1@0.5. Refuted (GNN keeps a real fixed-threshold advantage, report it as calibration robustness) otherwise.
## Results
(pending)
