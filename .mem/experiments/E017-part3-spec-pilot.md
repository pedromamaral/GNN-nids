# E017 Part 3 threat/cost model + A/B/C pilot on context detectors, CTU-13 (A012)
Status: DONE 2026-10-18 — GO (pilot criterion met; 1 training seed, no claim). IMPLEMENTED 2026-10-17 (8719ee5 + 2 test fixes; tests/test_context_attack.py 11 pass in container), smoke on GPUserver2 PASSED (end to end, 3 steps, chunk 1), pilot not run. Serves C4, G2, G3. Pilot = go/no-go for E020, no claim.

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

## Implementation (2026-10-17)
- src/attacks/context_attack.py: Chunk/Plan/Context, volume_features (torch twin of raw_features, float64 bytes), host_context_t (twin of 00 host_context), project/integerize shaping + decoys, build_plan, run_attack (projected sign-PGD, `--steps`, step_frac .2, random init per attack seed).
- experiments/08_context_decomposition.py: refits MLP/XGB host-ip + plain XGB (seed 42) via 00's trainers (00 train_mlp now exposes `.model`), loads GNN ip ckpt (`--gnn-checkpoint`), thresholds at 1% FPR on clean benign test, white-box on MLP host-ip + GNN ip, transfer MLP -> XGB host-ip/plain; grid incl. budget-matched A/B runs for S (`--no-superadd` to skip); `--replay` adds B_replay; writes rows.csv, summary.csv (delta_A/B/Cstar, G, S).
- Choices not in the spec: budget group = (window, bot host), base = that host's botnet-flow bytes; decoy slots <= #botnet flows of the group, accepted while cumulative cheapest-feasible cost (dst reply + 60 B) fits rho*budget; delay (Dur) shaping only when rho<1; per-detector window (tab 10000, GNN from ckpt); chunks of whole windows (400k flows).
- Not implemented: PR-AUC under attack (recall/FPR/F1 at 1% FPR and at 0.5 only).
- Checks built in: torch host context vs 00 numpy (assert <1e-3), test features == 00's, group costs <= budgets (assert), clean beta=0 row.
- GNN ckpt (GPUserver2): results/runs/20261015_000250_ctu13_egraphsage_endpoint_ip_w10000_cwbal_L2_seed_42/best_checkpoint.pt
- Smoke (no claim; chunk 1 has only ~61 botnet flows): MLP torch-vs-00 max|diff| 1e-6; budgets respected; plain XGB recall identical clean vs B (sanity OK); full-data run time dominated by fits (~1 h), 08 itself seconds per chunk-config.
## Results (.mem/results/E017.json; run results/E017_pilot/20261017_222359 on GPUserver2, ~1 h incl. refits; training seed 42, attack seeds 0/1)
Clean recall @1% FPR: GNN ip .904, MLP host-ip .928, XGB host-ip .624, XGB plain .617 (FPR .010 all).
Δ = clean − attacked recall @1% FPR, seed 0 | seed 1:
| detector | β | Δ_A | Δ_B | Δ_C* | G | S (ρ=.5) |
|---|---|---|---|---|---|---|
| GNN ip (white) | .05 | .029/.029 | .029/.035 | .064/.066 | .034/.031 | - |
| GNN ip | .10 | .041/.039 | .057/.056 | .109/.101 | .052/.046 | +.042/+.032 |
| GNN ip | .50 | .082/.085 | .149/.145 | .258/.252 | .109/.107 | +.070/+.082 (ρ=.75 +.086/+.080) |
| MLP host-ip (white) | .05 | .458/.458 | .036/.034 | .458/.458 | .000/.000 | - |
| MLP host-ip | .50 | .509/.510 | .167/.171 | .532/.530 | .023/.020 | −.085/−.085 (ρ=.75 −.118/−.115) |
| XGB host-ip (transfer) | .50 | .162/.162 | .044/.048 | .182/.181 | .020/.019 | −.056/−.054 |
| XGB plain (transfer) | .50 | .596/.599 | .000/.000 | .596/.599 | .000/.000 | −.000/−.002 |
- B_replay (benign flows replayed, β=.5): GNN .084/.083, MLP .014/.012, XGB host-ip .067/.062, plain .000.
- Decoy alarm rate @1% FPR (β=.5, ρ=1, seed 0): GNN .33 (replay .41), MLP .12 (replay .46), XGB host-ip .30 (replay .18). Benign FPR unchanged (.0097-.0100).
- Noise references: attack-seed spread ≤ .01 on G and S; plain XGB (B ≡ 0 by construction) |S| ≤ .015, G ≤ .014 → transfer/rounding floor ~.015. Training-seed noise UNKNOWN (1 seed).
## Interpretation
- GNN ip: joint attack is superadditive. G ≥ .03 at every β, both attack seeds (.031-.109); S ≥ +.03 for β ≥ .10. At β=.5 separate evaluation (best of A, B) reports Δ .149, joint Δ .258. Decoys work on the graph even unoptimised (replay ≈ 57% of optimised B).
- MLP host-ip: shaping dominates and saturates at the smallest budget (Δ_A .458 at β=.05 → .509 at .5); A and B overlap (S negative, down to −.118) → joint ≈ best separate (G ≤ .023 < .03). Decoys only hurt when optimised (replay ≈ 0).
- XGB host-ip (transfer): same subadditive pattern, weaker (G ≤ .020, S ≈ −.05). Plain XGB: B = 0 exactly (sanity passed); A transfer large (.30 → .60).
- Pattern: graph aggregation (message passing over flows of both endpoints) composes shaping and injection; mean host-context makes them substitutes.
## Anomalies / caveats (fix in E020)
1. Free delay: Δdur ≤ Dur costs nothing but is only allowed when shaping share > 0, so A and every C_ρ<1 get a budget-free component that B lacks. Likely cause of MLP Δ_A saturation at β=.05. Need a delay-only condition (β→0⁺) or a priced delay.
2. PGD strength unverified: 30 steps, sign steps of .2 × share. If A is under-optimised relative to C (C has more variables), G is inflated. Need a steps check (e.g. 30 vs 100, plus A restarts) before claims.
3. Decoys are conspicuous: 12-41% of decoys alarm at the 1% FPR point, far above benign 1%. A host-level view (host-window flagged if any flow or decoy alarms) could cancel B; E020 should report host-window recall.
4. 1 training seed; only CTU-13. The attack module is CTU-13-specific (Argus raw fields); ToN in E020 needs a NetFlow-v3 raw-feature twin (byte/packet/duration fields, more derived features).
## Verdict
GO (spec criterion): G ≥ .03 on GNN ip at every β in both attack seeds; |S| ≥ .03 on GNN ip, MLP host-ip, XGB host-ip; plain XGB B ≤ .01. C4 provisionally supported for the endpoint GNN only, opposite sign (subadditive, G < .03) for host-context tabular models. Not a claim: 1 training seed, caveats 1-3 open.
