# E017 Part 3 threat/cost model + A/B/C pilot on context detectors, CTU-13 (A012)
Status: SPEC FIXED 2026-10-17 (D16, D17), not implemented. Serves C4, G2, G3. Pilot = go/no-go for E020, no claim.

## Hypothesis
At equal traffic-cost budget β, separate evaluation misjudges context detectors:
joint gain G = Δ(C*) − max(Δ(A,β), Δ(B,β)) ≥ .03, or |superadditivity S| ≥ .03 with
S = Δ(C_ρ) − Δ(A,(1−ρ)β) − Δ(B,ρβ) (D17). Δ = drop in bot-flow recall at the fixed operating point (S5).
Predictions: B > 0 on MLP host-ip and GNN ip (decoys dilute host mean context); B ≈ 0 on plain XGB (sanity check).

## Threat model
Attacker = every infected host in test scenarios 9/10/13 at once. Controls its own flows' own direction and may emit decoy flows from itself. Cannot touch benign hosts' flows, labels, or the window definition. White-box on MLP host-ip and GNN ip; XGB host-ip and plain XGB attacked by transfer from MLP host-ip (same features).

## Features (src/data/ctu13.py Ctu13Preprocessor, 36)
log1p Dur, TotPkts, TotBytes, SrcBytes, DstBytes(=Tot−Src), BytesPerPkt(=Tot/Pkts); sTos, dTos; one-hot proto(4), dir(5), tcp src/dst flags(16), non-TCP state(3).
- S2 shaping: raw Δdur, Δpkts, ΔSrcBytes ≥ 0 only (padding, extra packets, delay); DstBytes, ToS, all one-hots fixed. Derived features recomputed via a differentiable copy of raw_features + frozen train scaler. Projection: 60·Δpkts ≤ ΔSrcBytes ≤ 1500·(pkts+Δpkts) − SrcBytes; Δdur ≤ Dur (≤2×, free); integers at evaluation (metrics on rounded flows).
- S3 decoys: src = bot, dst = popular benign destinations in the window (sampled by frequency), categorical combo + start features copied from a random benign flow to that dst; volume features optimised (PGD, same projection); baseline B_replay = benign flows replayed unchanged.

## Cost (S1)
Currency = extra bytes. Shaping cost = Σ ΔSrcBytes (extra packets priced by their bytes); decoy cost = its TotBytes. Budget β ∈ {.05, .10, .25, .50} × the bot host's clean bytes per window. ρ = share of β spent on decoys; ρ ∈ {0, .25, .5, .75, 1}: A = ρ0, B = ρ1, C_ρ, C* = argmax over ρ.

## Evaluation
- S5 operating point: per detector, threshold at 1% FPR on clean benign test flows, fixed before attack; also report F1@0.5 (continuity with K14).
- S6 metrics: recall on bots' original flows (primary), decoy alarm rate, PR-AUC, F1.
- S7 windows: original windows by flow id + inserted decoys (no recount); decoys also enter the dst host's context (collateral on benign flows reported as FPR change).
- S8 context recomputation: torch host_context (window, src/dst endpoint mean + log1p count) for MLP gradients and for XGB evaluation; GNN ip: decoys = new edges in the rebuilt endpoint graph.
- S9 pilot: CTU-13, training seed 42 (E014/E016 GNN ip ckpt; 00 MLP/XGB host-ip and plain refit seed 42), 2 attack seeds (PGD init + decoy destination sampling), 4 budgets × 5 ρ; PGD steps fixed in config. ~3 GPU-h.

## Success criterion (pilot)
GO to E020 if any detector shows G ≥ .03 or |S| ≥ .03 at some β in both attack seeds; else E020 at reduced size, framing 'separate evaluation suffices'. Sanity: plain XGB B ≤ .01, else bug (context leak).

## Implementation notes (for research-do)
New module src/attacks/context_attack.py (raw-space shaping, decoy insertion, projection, cost accounting) + experiments/08_context_decomposition.py (detectors × β × ρ × attack seed → csv); 00 needs a way to save/reload MLP + XGB models (or refit inside 08 for seed 42). Tests for projection validity, cost accounting, and B=0 on a context-free model.

## Results
(pending)
