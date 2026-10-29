# Strategy plan — gnn-nids (GNN adversarial NIDS)

<!-- DIGEST START -->
- 2026-10-29 · topic gnn-nids · status: revision 1 (first saved plan; supersedes the D22 strategy note in .mem/strategy.md) · chosen: AVENUE #1 as reframed by D22 (evaluation-methodology paper)
- Verdict: PUBLISHABLE in Computers & Security after 4 closers (below). Not yet submittable: one claim rests on 1 training seed, two on one dataset, one on an uncontrolled host overlap.
- RQ: when GNN-NIDS are evaluated under a chronological split, with identity hidden, same-split tabular host-context controls, ≥5 seeds and threshold-free metrics, which reported benefits (graph, topology, robustness) survive?
- C1 feature-derived k-NN graphs are redundant; attack-induced rewiring has no effect (K04, K05; 1 training seed → E023)
- C2 endpoint-GNN gains are host context, not topology: tabular host context ≥ GNN on PR-AUC on ToN and CTU-13 (K11, K14)
- C3 host context transfers to unseen botnet families; the GNN does not (K17; family- not host-disjoint → A035)
- C4 equal-budget joint shaping+decoy attack ≈ best single attack → separate evaluation suffices (K15; CTU-13 only → E024)
- C5 GNN shaping robustness is a training-seed lottery (CV .46 vs MLP .10, ×30 range) that no clean/val metric predicts (K16; CTU-13 only → E024)
- Gaps addressed: G1 (C1), G5 (C2, C3), G2+G3 (C4), G6 (C5). G4 left to AVENUE #2.
- Novelty (one line): first same-protocol audit of supervised flow-level GNN-NIDS that separates graph, host context and seed effects, for both clean detection and adversarial robustness.
- Novelty threats, positioned: underspecification (D'Amour et al., JMLR 23, 2022); init scheme changes GNN robustness at similar clean accuracy (Ennadir et al., NeurIPS 2024); seed variance of certified robustness (Le & Cao, arXiv 2601.13303, 2026) → C5 is an NIDS instance of a known phenomenon; claim the magnitude, the GNN-vs-tabular contrast and the consequence for single-seed GNN-NIDS robustness papers, not the phenomenon.
- Evaluation-critique line: R+R (ACSAC 2025); Zhao & Hassan "First-Principles Evaluation of GIDS" (arXiv 2609.12263, CCS '26 format) — unsupervised temporal GIDS, PCA control, single-run attacks, no host-context control, no seed variance of robustness → we differ on supervised flow GNNs, host-context controls, attack decomposition, seeds.
- Venue precedent: Berhili et al., "How evaluation protocol choices inflate intrusion detection accuracy", Computers & Security 2026 (tabular only, no GNN) → C&S takes protocol papers.
- Target venues: Computers & Security (main). Stretch (needs A034 + E024 positive replication): ACSAC / RAID. Not TIFS/TDSC (negative-result framing).
- Baselines (our protocol; literature numbers are random-split and not comparable): ToN XGB host-ipport PR-AUC .954 vs GNN ip .903 (E019) · CTU-13 MLP host-ip PR-AUC .953 vs GNN ip .855 (E016) · CTU-13 unseen families XGB host-ip .670 vs GNN ip .129 vs plain .117 (E022)
- Data (in hand): NetFlow-v3 (UQ, https://staff.itee.uq.edu.au/marius/NIDS_datasets/ ; licence "Other", UQ deposit terms, open access) · CTU-13 (Stratosphere, https://www.stratosphereips.org/datasets-ctu13 ; free use with citation per FAQ)
- Kill 1 E024 (ToN Part 3): GNN CV(Δ_A β.5) < .3 → C5 becomes a CTU-13 observation, drop "lottery" from the title; G ≥ .03 in ≥2/5 seeds → C4 becomes dataset-dependent.
- Kill 2 A035 (host-disjoint subset of E022 test): host-ip PR-AUC gain over plain < .10 on flows of never-seen infected IPs → C3 is host reuse, not transfer; rewrite C3.
- Kill 3 E023: k-NN structure effect ≥ .05 or adaptive gain ≥ .03 in ≥2/5 seeds → C1 flips (unlikely, K04).
- Do-not-pursue: AVENUE #3 standalone k-NN paper (A014, pre-empted by #10) · k-NN edge attacks (A007) · adversarial training (A019; Venturi 2025 / Galli et al. NCA 2025 on CTU-13+ToN) · 4th dataset (A021) unless asked · neighbour-aggregate XGB (A027) · stealthy decoys (A032) before submission · AVENUE #2 (A013) before submission.
- Constraints: 2× shared RTX 2080 Ti 11 GB (GPU often busy), disks nearly full (delete graph caches), no local runs; 5 seeds per claim.
<!-- DIGEST END -->

## 1. Executive summary
The results support a methodology paper, and Computers & Security is the right venue. Two of the four findings are strong and new: host context, not topology, explains endpoint-GNN gains, and that context transfers to unseen botnet families while the GNN does not. The other two are reportable but need replication. "Separate evaluation suffices" (C4) and the seed lottery (C5) are measured on CTU-13 only. C5 is also the general underspecification phenomenon, so it must be presented as its NIDS instance and consequence. Close four items (E023, E024, the E022 bootstrap CIs, a host-disjoint check A035), then freeze experiments and write. A second GNN architecture (A034) is what would lift it toward ACSAC/RAID.

## 2. Lab conditions used
- Compute: GPUserver1/2, 1× RTX 2080 Ti 11 GB each, shared with other users; CTU-13 only on GPUserver2; disks nearly full (infra.md).
- People: Pedro (PI), origin in João Caeiro's MSc thesis; implementation via Claude Code (research-do).
- Data: NF-UNSW-NB15-v3, NF-ToN-IoT-v3, CTU-13 on servers. No proprietary data needed.
- Time: no hard deadline stated; C&S has rolling submission. Planned: ~2 weeks of runs + writing.
- Risk appetite: safe main paper; constraint "5 seeds per claim" (CLAUDE.md).
- lab-profile.md in the OneDrive lit-graph root was not reachable from this session (folder not connected), so these come from .mem/infra.md and CLAUDE.md.

## 3. Feasibility matrix
| id | avenue | equip | compute | data | expertise | budget | time | verdict |
|---|---|---|---|---|---|---|---|---|
| AVENUE #1 (A005, D22) | methodology paper C1–C5 | ✅ | ✅ (~25 GPU-h left) | ✅ | ✅ | ✅ | ✅ | GREEN |
| A015 / E023 | k-NN 5×5 grid | ✅ | ✅ running | ✅ | ✅ | ✅ | ✅ | GREEN |
| A033 / E024 | ToN port of joint attack | ✅ | 🟡 ~10 GPU-h on a busy GPU | ✅ | ✅ | ✅ | 🟡 2–3 d code | GREEN |
| A035 (new) | host-disjoint subset of E022 test | ✅ | ✅ CPU | 🟡 needs per-flow scores + IPs of the test flows | ✅ | ✅ | ✅ | GREEN if per-flow outputs exist, else re-score the checkpoints (~1 GPU-h) |
| A034 | 2nd endpoint GNN (E-ResGAT / GAT-edge) on CTU-13 | ✅ | 🟡 ~8 GPU-h | ✅ | ✅ | ✅ | 🟡 ~1 d code | YELLOW (optional, stretch venue) |
| A036 (new) | seed-ensemble mitigation for C5 (attack the 5-seed mean logit) | ✅ | ✅ reuses E021 checkpoints | ✅ | ✅ | ✅ | 🟡 ~1 d code | YELLOW (optional) |
| AVENUE #2 (A013) | construction / robust host-context aggregation as defence | ✅ | ✅ | ✅ | ✅ | ✅ | 🔴 for this paper | GREEN as follow-up paper |
| A032 | stealthy decoys | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 | park |
| AVENUE #3 (A014) | standalone k-NN negative paper | — | — | — | — | — | — | RED (pre-empted by #10, folded into C1) |
| AVENUE #4 | CTU-13 cross-scenario | — | — | — | — | — | — | DONE (E022 → C3) |

## 4. Open-source unlocks
None needed: all data and code are in hand. One check before artefact release: NetFlow-v3 is under UQ deposit terms (licence "Other", open access, https://researchdata.edu.au/nf-ton-iot-v3/3485175) and CTU-13 asks for citation (https://www.stratosphereips.org/datasets-faq). Release code and configs, not the data.

## 5. Strategic ranking (weights F .3 · I .3 · S .2 · T .2)
| rank | option | F | I | S | T | score | role |
|---|---|---|---|---|---|---|---|
| 1 | AVENUE #1 + closers (E023, E024, E022 CIs, A035) → C&S | 5 | 4 | 4 | 4 | 4.3 | safe bet |
| 2 | rank 1 + A034 (2nd GNN) (+ A036) → ACSAC/RAID or a stronger C&S paper | 4 | 5 | 4 | 3 | 4.1 | stretch |
| 3 | AVENUE #2: robust host-context aggregation vs decoy injection (A013) | 4 | 3 | 4 | 3 | 3.5 | strategic follow-up (Computer Networks / TNSM) |
| 4 | A036 seed-ensemble mitigation alone | 4 | 3 | 3 | 4 | 3.5 | strengthener for C5 |
| 5 | A032 stealthy decoys | 4 | 2 | 2 | 4 | 3.0 | park |

Portfolio: submit rank 1 first. Add A034 only if E024 replicates and the GPU is free. Start rank 3 after submission; it reuses the Part 3 attack and fits the C2 finding (defend the host context, not the graph).

## 6. Per-finding publishability
| finding | evidence | novelty vs literature | what is missing |
|---|---|---|---|
| C1 k-NN redundant | K04, K05 (1 training seed, 3 pilots) | #10 (preprint) states redundancy without mechanism or attacks | E023 seeds; it stays a supporting section |
| C2 host context, not topology | K11 (ToN, CI excl 0), K14 (CTU-13, CI excl 0), 5 seeds | none found: E-GraphSAGE/Pujol-Perich use random splits and plain baselines; R+R/First-Principles are unsupervised GIDS without host-context controls | nothing |
| C3 transfer to unseen families | K17, 5 seeds, gap ≫ seed sd | AVENUE #4 gap; no GNN-NIDS paper tests unseen families with context controls | E022 bootstrap CIs; A035 host-disjoint subset |
| C4 separate suffices | K15, 15 seeds, PGD converged | GIANT injection-only; Venturi 2024 separate; Mouzaoui et al. (SECRYPT 2026) list combined feature+structure as future work | E024 (ToN) |
| C5 seed lottery | K16, 15 seeds, 7 predictors | general phenomenon known (D'Amour 2022; Ennadir 2024; Le & Cao 2026); in GNN-NIDS, none of the robustness papers checked (Venturi 2024, GIANT, Mouzaoui 2026 [slides only], Galli 2025 [abstract only], Zhao & Hassan 2026) reports robustness over training seeds; verify the first four in full text before writing it | E024 replication; position against the three papers; A036 optional |

## 7. Recommended plans
### RECOMMENDED AVENUE #1 (D22): Pitfalls in evaluating graph-based NIDS
- Verdict: GREEN. RQ and claims C1–C5 as in the digest.
- Why here: the fixed protocol (D03/D04/D06), host-context controls and the Part 3 attacker already exist; nobody else has the same-split tabular controls.
- Have: all code, datasets, results E001–E022. Unlock: none. Acquire: nothing.
- Milestones: M1 (week 1) fetch E023, implement E024, re-export E022 CIs, run A035. M2 (week 2) E024 runs, analyse, research-think paper-plan (paper.md is stale). M3 (weeks 3–6) write with research-paper-writer; figures from .mem/results only; release code.
- Framing: lead with C2/C3 (strongest, new), then C5 and C4 as robustness-evaluation pitfalls, C1 as the k-NN case. End with a checklist (chronological split, same-split host-context tabular control, threshold-free metrics, ≥5 training seeds for any robustness claim, joint-attack sanity check).
- Key risks: (1) "negative results" reviewer → frame as actionable protocol + checklist + code; (2) "one GNN architecture" → A034 or argue E-GraphSAGE is the reference design used by Venturi, GIANT and Galli; (3) C5 seen as known → cite and position as above; (4) host reuse in C3 → A035.
- Building on: #1 E-GraphSAGE, #3 Pujol-Perich, #4 Venturi, #6 GIANT, #8 R+R, #9 First-Principles, #10, Arp et al. 2022.

### STRETCH: + A034 (and A036)
- Adds a second endpoint GNN on CTU-13 (C2 + C5 for 2 architectures) and a seed-ensemble result that turns C5 into a recommendation. ~2 d code, ~10 GPU-h. Do only after E024.
- Kill: if the 2nd architecture beats tabular host context on PR-AUC in 5/5 seeds, C2 becomes "E-GraphSAGE-specific" — still publishable, but the title changes.

### FOLLOW-UP: AVENUE #2 (A013), robust host-context aggregation
- Since gains are host context, defend the context: per-host median/trimmed aggregation, minimum flows per host, against the Part 3 decoy injection. Success as in A013. After submission.

## 8. What to avoid (for now)
- New attack variants (A032) or defences (A013, A019) before submission: scope creep on a paper whose message is evaluation.
- A 4th dataset (A021) unless a reviewer asks.
- Claiming C5 as a discovery; claiming C3 as host-disjoint before A035.
- Comparing to literature F1 numbers: all random-split.

## 9. Revision log
- 2026-10-29 · rev 1 · first saved plan. Adopts D22 reframe; verdict publishable after closers; adds A035 (host-disjoint check) and A036 (seed ensemble); positions C5 against D'Amour 2022, Ennadir 2024, Le & Cao 2026; adds Mouzaoui (SECRYPT 2026), Galli et al. (NCA 2025), Berhili et al. (C&S 2026); corrects .mem/strategy.md, which conflated R+R (ACSAC 2025) with arXiv 2609.12263 (Zhao & Hassan, CCS '26 format).

## References added in this revision
- D'Amour et al., Underspecification Presents Challenges for Credibility in Modern ML, JMLR 23 (2022). https://www.jmlr.org/beta/papers/v23/20-1335.html
- Ennadir et al., If You Want to Be Robust, Be Wary of Initialization, NeurIPS 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/2a6fc6774932e7835349089b0287ed2c-Abstract.html
- Le & Cao, On the Extreme Variance of Certified Local Robustness Across Model Seeds, arXiv 2601.13303 (2026). https://arxiv.org/abs/2601.13303
- Zhao & Hassan, A First-Principles Evaluation of Graph-Based NIDS, arXiv 2609.12263 (2026). https://arxiv.org/abs/2609.12263
- Mouzaoui et al., Robustness Evaluation of GNN-based NIDS against Adversarial Flow Injection, SECRYPT 2026. https://mouzaouimatthieu.github.io/files/SECRYPT2026-slides.pdf
- Galli, Venturi et al., Defending GNN-based NIDS Against Structural Adversarial Attacks, arXiv 2608.24454 (NCA 2025). https://arxiv.org/abs/2608.24454
- Berhili et al., How evaluation protocol choices inflate intrusion detection accuracy, Computers & Security (2026). https://www.sciencedirect.com/science/article/abs/pii/S0167404826003949 · code https://github.com/mberhili/ids-evaluation-protocol-bias
- Ngo et al., Adversarial GNN Benchmarks: Towards Practical and Fair Evaluation, arXiv 2605.05534 (2026). https://arxiv.org/abs/2605.05534
- Apruzzese et al., SoK: Pragmatic Assessment of ML for Network Intrusion Detection, EuroS&P 2023. https://arxiv.org/abs/2305.00550
