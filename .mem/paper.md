# Paper plan (Computers & Security). Outline: docs/PAPER_ROADMAP.md (Direction + Phases). Writing: research-paper-writer skill.
# claim → figure/table → experiments → status

| claim | figure / table | experiments | status |
|---|---|---|---|
| protocol | T1 datasets, splits, attack fractions, dropped features (TTL evidence) | E001,E002 | data in hand |
| baselines | T2 test F1/AUC: XGB, MLP, k-NN GCN/GAT, E-GraphSAGE ipport/ip/isolated, context controls × UNSW/ToN/CTU-13 | E002,E005,E008,E010,E011,E013+ | partial (ToN controls missing; GNN 1 seed) |
| C1 k-NN redundant | F1 graph ablation bars (knn/none/random) | E007 | 1 seed; needs A015 grid |
| C1 coupling inconsequential | F2 A/B/C vs ε, neighbour churn | E006 | pilot only; needs A015 |
| C2 endpoint vs tabular | F3 ablation (graph/none/shuffled) + controls | E008,E009,E013 | OPEN (K06) |
| C3 CTU-13 | rows of T2 | E011,E013 | GNN degenerate (K09) |
| C4 decomposition + joint attacker | F4 A/B/C/interaction vs budget; T3 separate vs injection-only vs joint | - | not started (A012) |
| C5 construction as defence | F5 clean F1 vs robust F1 Pareto | - | parked (A013) |

Figure scripts: paper/figs/*.py reading .mem/results/*.json only (none yet).
