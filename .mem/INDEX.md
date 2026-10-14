# Routing: task → read (always start with STATE.md). Never read by default: *-archive.md, _import.md, docs/LITERATURE_REVIEW.md (use strategy.md), data/, results/ on servers.

| task | read | skip |
|---|---|---|
| analyse results (research-think) | conclusions.md, LEDGER.md, relevant results/E###.json, card | infra, codebase |
| ideate next experiment | project.md, `rg` avenues.md + conclusions.md, strategy.md | infra, codebase, runs |
| publishability / novelty | strategy.md, project.md, conclusions.md; lit graph docs/lit-graph/gnn-nids/ via subagent | code |
| implement (research-do) | codebase.md, the card, then code by `rg -n` + line ranges | strategy, paper |
| deploy / launch | infra.md, runs.md | strategy, avenues |
| status of runs | `tools/runs_status.sh` only | everything else |
| fetch results | runs.md, `tools/summarize_run.py`; then LEDGER + card | code |
| figures / tables | paper.md, results/*.json | logs |
| paper writing | paper.md, project.md, conclusions.md, strategy.md, docs/PAPER_ROADMAP.md | infra, code |
| decision history | `rg` decisions.md; docs/PAPER_ROADMAP.md "Decision log" | |
| tidy | all .mem files (wc -l first) | |
