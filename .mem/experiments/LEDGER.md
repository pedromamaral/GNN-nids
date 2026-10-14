# Experiment ledger. id | date | sha | change | config | key result | verdict | avenue
# Test F1; "s42" = seed 42 only. sha = first commit containing the code (runs before 10-14 often used code committed later; approximate, "~"). Results: .mem/results/E###.json (where present).

E001 | 2026-10-07 | ~7f583ff | TTL artefact probe, UNSW with all 46 features | 00, 5 seeds; depth-2 XGB on MIN_TTL | XGB 0.9999, MLP 0.9992; MIN_TTL alone 0.9992 | TTL dropped | A006
E002 | 2026-10-07 | ~2654ad9 | tabular baselines, no TTL (44 feat) | 00, UNSW+ToN, 5 seeds | UNSW XGB 0.9995 MLP 0.9985; ToN XGB 0.8717±0.0029 MLP 0.7345±0.0175 | reference | A005
E003 | 2026-10-07 | ~2654ad9 | difficulty / random-noise probe (no json; ad hoc) | LR, depth-2 tree, ±σ noise | UNSW LR 0.9907; ±0.05σ → XGB 0.78; ToN ±0.1σ → 0.20 | clean ease ≠ robustness | -
E004 | 2026-10-07 | ~7f583ff | k-NN tie-breaking by index | rebuild 2,368 UNSW windows | reconstruction churn 0.65% → 0.0 | fixed | -
E005 | 2026-10-07 | ~2654ad9 | k-NN GNN checkpoints (training) | 01 k=5 w1000 s42: UNSW GCN, ToN GCN, UNSW GAT | 0.975 / 0.812 / 0.986 | checkpoints for E006/E007 | A001
E006 | 2026-10-08 | ~9eba80a | Phase 2 decomposition pilots (05+05b) | s42, 2 attack seeds, ε .05-.5; UNSW GCN 100w, ToN GCN 300w, UNSW GAT 100w | structure effect ≤0.005, adaptive gain ≤0.019 | NO-GO all 3 | A001
E007 | 2026-10-08 | ~4081f38 | k-NN graph ablation (06) | knn / none / random(3 seeds) | UNSW GCN .975/.995/.21; GAT .986/.995/.15; ToN .812/.814/.815 | graph redundant | A001
E008 | 2026-10-12 | ~27ce19d | endpoint E-GraphSAGE pilot | 01 --graph endpoint w10k L2 s42 50ep; ipport/ip/isolated | UNSW .9973/.9388/.9975; ToN .8990/.9372/.7270 | UNSW no-go; ToN ip > XGB (confounded?) | A008
E009 | 2026-10-13 | ~f42b2fd | endpoint ablation on E008 checkpoints (06) | graph/none/random_dst/random_src/random | ToN ip .937/.790/.940/.910/.915; UNSW ip .939/.520/.04/.03/.00 | needs a neighbourhood, not the real one | A008
E010 | 2026-10-13 | ~f42b2fd | UNSW context controls (00 --context host ip / host ipport / window) | 5 seeds, w10k | XGB 1.0000 / 0.9997 / 0.9994; MLP .9996/.9981/.9982 | UNSW saturated | A009
E011 | 2026-10-13 | ~542b225 | CTU-13: tabular plain + window, E-GraphSAGE ip | 00 5 seeds; 01 w10k s42 | XGB .5308 (window .405±.168); MLP .484 (window .217); GNN ip 0.0 (all benign) | hard; GNN degenerate | A009,A010
E012 | 2026-10-13 | ~730be34 | batch a2c rest: ToN --context window, host ip, host ipport; ctu13 host ip; ctu13 GNN isolated, ipport | queue_a2c.sh on both servers | XGB CUDA OOM (4 runs); GNN isolated unfinished, ipport disk full | CRASHED → rerun | A009,A011
