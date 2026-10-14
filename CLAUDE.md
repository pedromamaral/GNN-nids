# GNN adversarial NIDS (paper: Avenue #1, Computers & Security)

Decomposing feature vs structure adversarial effects in graph-based NIDS: k-NN flow graphs (Part 1), endpoint graphs vs XGBoost under a chronological protocol on NetFlow-v3 + CTU-13 (Part 2), A/B/C decomposition with a joint shaping+injection attacker (Part 3).

**Read `.mem/STATE.md` first, then `.mem/INDEX.md`; read only the files it routes to.**
Skills: research-memory (init/state/tidy), research-think (analyse, ideate, publishability, paper plan), research-do (implement, deploy, monitor, fetch, figures).

## Context rules
1. Start from STATE.md + INDEX.md. Read code by line range (`rg -n` first).
2. Recall by grep: `rg -i "<kw>" .mem/avenues.md .mem/experiments/LEDGER.md .mem/conclusions.md`. Never re-propose a `tried`/`dropped` avenue.
3. Raw outputs never enter context: `tools/runs_status.sh`, `tools/summarize_run.py`, `tail -n 30`, `rg -m 20`. Never cat logs or stream jobs.
4. Bulk reading (lit review, many files) → subagent returning ≤20 lines with file:line refs.
5. Replies ≤25 lines unless asked; tables over prose.
6. Write decisions / conclusions / avenues to .mem immediately, not at the end.
7. One phase per session; end with research-memory `state`, then `/clear`.
8. Think phases on the strongest model; do phases on a cheaper one.

## Hard rules
- Never run experiments locally (no torch/data). Edit → commit → `git push origin main` → `git pull` on GPUserver1/2 → `scripts/container.sh`. See .mem/infra.md.
- Push to `origin` only, never `student`.
- Numbers in .mem only from .mem/results/*.json or cited papers. No secrets in .mem.
- Fixed protocol: chronological 60/20/20, 44 features (no TTL, IPs, ports), identity hidden from models, 5 seeds for claims.
- Shared disks are nearly full: delete data/graphs/* caches after each batch.
