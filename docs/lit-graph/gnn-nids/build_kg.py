"""Phase 5-6: curated core-paper extraction -> knowledge graph (JSONL) + gap matrix.

Every property below was read in this session from the source indicated in
`access` (oa = open full text, institutional = full text via b-on/NOVA,
abstract = abstract or landing page only). `evidence` holds a short quote or
a pointer to the section where the property was read.
Values: True / False / None (not reported or not determinable from what was read).
"""
import json

# Graph families
KNN = "feature-similarity (k-NN / top-k) graph"
ENDPOINT = "endpoint/host flow graph (supervised)"
LINE = "line graph of endpoint flows"
TEMPORAL = "temporal host graph (unsupervised GIDS)"
TOPO_PCAP = "PCAP communication-topology graph"

P = [
 dict(key="egraphsage", title="E-GraphSAGE: A Graph Neural Network based Intrusion Detection System for IoT", year=2022,
      venue="IEEE/IFIP NOMS", doi="10.1109/noms54207.2022.9789878", access="oa (arXiv:2103.16329)", family=ENDPOINT,
      datasets=["NF-BoT-IoT", "NF-ToN-IoT", "BoT-IoT", "ToN-IoT"], split="random 70/30 of flow records",
      same_split_tabular=False, edge_ablation=False, identity_control=True, feature_attack=False, structural_attack=False,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Sec. IV: '70% of the flow records ... for training'; source IPs randomly remapped because few IPs source attacks; Table III compares with numbers reported by other papers."),
 dict(key="anomale", title="Anomal-E: A self-supervised network intrusion detection system based on graph neural networks", year=2022,
      venue="Knowledge-Based Systems", doi="10.1016/j.knosys.2022.110030", access="oa (arXiv:2207.06819)", family=ENDPOINT,
      datasets=["NF-UNSW-NB15-v2", "NF-CSE-CIC-IDS2018-v2"], split=None,
      same_split_tabular=True, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=False,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Sec. 5: anomaly detectors on Anomal-E embeddings vs. on raw features, same data."),
 dict(key="pujol", title="Unveiling the potential of Graph Neural Networks for robust Intrusion Detection", year=2022,
      venue="ACM SIGMETRICS PER", doi="10.1145/3543146.3543171", access="oa (arXiv:2107.14756)", family=ENDPOINT,
      datasets=["CIC-IDS2017"], split="random 80/20 of graph samples",
      same_split_tabular=True, edge_ablation=False, identity_control=True, feature_attack=True, structural_attack=False,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Sec. 5.2: accuracy 'similar' to MLP, AdaBoost, RF, ID3; Sec. 5.3: packet-size and IAT perturbations leave the GNN unaffected; host states initialised to ones (no IPs)."),
 dict(key="venturi24", title="Problem space structural adversarial attacks for Network Intrusion Detection Systems based on Graph Neural Networks", year=2024,
      venue="arXiv preprint", doi="10.48550/arxiv.2403.11830", access="oa", family=ENDPOINT + "; " + LINE,
      datasets=["CTU-13", "ToN-IoT"], split="80:20 per attack, 1:10 malicious:benign",
      same_split_tabular=True, edge_ablation=False, identity_control=None, feature_attack=True, structural_attack=True,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Sec. 3.4: only addition operations feasible; Sec. 5.2-5.5: feature attacks (RF collapses, GNNs robust) and C2x/add-node attacks evaluated separately; one injected benign flow per compromised node collapses E-GraphSAGE."),
 dict(key="venturi25", title="Defending Network Intrusion Detection Systems Based on Graph Neural Networks Against Structural Adversarial Attacks", year=2025,
      venue="IEEE NCA 2025", doi="10.1109/nca67271.2025.00043", access="oa (arXiv:2608.24454)", family=ENDPOINT,
      datasets=["CTU-13", "ToN-IoT"], split=None,
      same_split_tabular=None, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=True,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: adversarial training with benign flows re-wired to low-degree endpoints; threat model excludes feature-space perturbations."),
 dict(key="giant", title="GIANT: Structure-Agnostic Practical Adversarial Attacks for Graph-based Network Intrusion Detection Systems", year=2026,
      venue="ACM Web Conference (WWW)", doi="10.1145/3774904.3792601", access="oa (ACM Open, reader)", family=ENDPOINT + "; " + LINE,
      datasets=["ToN-IoT", "CIC-IDS2018-v2"], split="random 80/20 per attack, 1:15",
      same_split_tabular=False, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=True,
      joint_attack="injection-only", decomposition=False, construction_defence=False,
      evidence="Sec. 1: injects flows 'to jointly manipulate topology and flow attributes' without altering existing traffic; Sec. 4.1: targets E-GraphSAGE, TS-IDS, Anomal-E, E-ResGAT (+ homophily filter); ablation is component-wise only."),
 dict(key="mouzaoui", title="Towards problem space-constrained adversarial attacks against graph neural network based network intrusion detection systems", year=2025,
      venue="RESSI 2025 (workshop)", doi=None, url="https://hal.science/hal-05478056", access="abstract", family=ENDPOINT,
      datasets=None, split=None, same_split_tabular=None, edge_ablation=False, identity_control=None, feature_attack=False,
      structural_attack=True, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: attackers 'can only create new communications'; weakly submodular, greedy; raises false alarms."),
 dict(key="rr", title="R+R: From Claims to Crashes: A Systematic Re-evaluation of Graph-Based Network Intrusion Detection Systems", year=2025,
      venue="ACSAC 2025", doi="10.1109/acsac67867.2025.00050", access="institutional", family=TEMPORAL,
      datasets=["LANL", "OpTC", "CIC-IDS2017", "CTU-13", "enterprise (new)"], split="train on pre-attack logs",
      same_split_tabular=True, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=True,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="RQ2: IF/LOF/OC-SVM baselines; RQ3: high FPR on enterprise traffic; RQ5: two adversarial edges cover all attack events on LANL."),
 dict(key="firstprinciples", title="A First-Principles Evaluation of Graph-Based Network Intrusion Detection Systems", year=2026,
      venue="arXiv preprint", doi=None, url="https://arxiv.org/abs/2609.12263", access="oa", family=TEMPORAL,
      datasets=["Campus", "LANL", "OpTC", "CIC-IDS2017"], split="chronological",
      same_split_tabular=True, edge_ablation=True, identity_control=None, feature_attack=True, structural_attack=True,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: encoder-free GIDS-Lite 'ranks first by AP on two of the four datasets'; Sec. 5.5: covering edges vs. minimum-perturbation feature attack on the control."),
 dict(key="iomt", title="From Flow Features to Communication Topology: Adaptive Graph Attention Network-Based IoMT Intrusion Detection", year=2026,
      venue="Preprints.org (not peer reviewed)", doi="10.20944/preprints202604.1972.v1", access="oa", family=KNN + "; " + TOPO_PCAP,
      datasets=["CICIoMT2024"], split="session-aware PCAP-level splits (window-level labels)",
      same_split_tabular=True, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=False,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: 'feature-similarity graphs provide no reliable advantage over Random Forest'; topology graphs competitive on topology-heavy attacks (0.800 vs 0.784 macro-F1)."),
 dict(key="tksgf", title="Optimizing IoT Intrusion Detection—A Graph Neural Network Approach with Attribute-Based Graph Construction", year=2025,
      venue="Information (MDPI)", doi="10.3390/info16060499", access="oa (browser)", family=KNN,
      datasets=["NF-BoT-IoT", "NF-ToN-IoT"], split="60-70% train, rest val/test (ordering not stated)",
      same_split_tabular=False, edge_ablation=False, identity_control=None, feature_attack=False, structural_attack=False,
      joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Sec. 4.4: Table 2 compares with results 'from previous research'; Sec. 4.5: ablation over similarity metric/threshold only."),
 dict(key="bsgat", title="BS-GAT: a network intrusion detection system based on graph neural network for edge computing", year=2025,
      venue="Cybersecurity", doi="10.1186/s42400-024-00296-8", access="abstract", family=KNN,
      datasets=None, split=None, same_split_tabular=None, edge_ablation=None, identity_control=None, feature_attack=False,
      structural_attack=False, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: flows as nodes, behaviour-similarity rules as edges."),
 dict(key="gcnlof", title="Enhancing intrusion detection performance using GCN-LOF: A hybrid graph-based anomaly detection approach", year=2025,
      venue="Computer Networks", doi="10.1016/j.comnet.2025.111606", access="abstract", family=KNN,
      datasets=None, split=None, same_split_tabular=None, edge_ablation=None, identity_control=None, feature_attack=False,
      structural_attack=False, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Title/abstract: k-NN graph + GCN embeddings scored by LOF."),
 dict(key="temporalknn", title="An Explainable and Interpretable GNN Based on Temporal Time Series: An IDS Approach", year=2026,
      venue="Electronics (MDPI)", doi="10.3390/electronics15173764", access="abstract", family=KNN,
      datasets=None, split="chronological (abstract)", same_split_tabular=None, edge_ablation=None, identity_control=None,
      feature_attack=False, structural_attack=False, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: flow nodes, edges by conversation chains and temporal k-NN by IP; matched pipeline, chronological split."),
 dict(key="zhou21", title="Hierarchical Adversarial Attacks Against Graph-Neural-Network-Based IoT Network Intrusion Detection System", year=2021,
      venue="IEEE Internet of Things Journal", doi="10.1109/jiot.2021.3130434", access="secondary (described in Venturi 2024, Sec. 6)", family=ENDPOINT,
      datasets=None, split=None, same_split_tabular=None, edge_ablation=False, identity_control=None, feature_attack=True,
      structural_attack=False, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Venturi 2024 Sec. 6: shadow-model transfer, feature perturbations only."),
 dict(key="itasec23", title="Practical Evaluation of Graph Neural Networks in Network Intrusion Detection", year=2023,
      venue="ITASEC 2023 (CEUR Vol-3488)", doi=None, url="https://ceur-ws.org/Vol-3488/paper29.pdf", access="abstract", family=ENDPOINT,
      datasets=None, split="online constraints", same_split_tabular=None, edge_ablation=False, identity_control=None,
      feature_attack=False, structural_attack=False, joint_attack=False, decomposition=False, construction_defence=False,
      evidence="Abstract: literature 'overestimates detection performance' under real-world constraints."),
]

# The repository's own pilot (docs/PAPER_ROADMAP.md, Phase 2) for comparison in the matrix.
OURS = dict(key="this-repo-pilot", title="This repository: k-NN flow GNN on NF-UNSW-NB15-v3 / NF-ToN-IoT-v3 (Phase 2 pilot)", family=KNN,
            same_split_tabular=True, edge_ablation=True, identity_control=True, feature_attack=True, structural_attack="induced (rebuild)",
            joint_attack=False, decomposition=True, construction_defence=False, split="chronological 60/20/20")

PROPS = ["same_split_tabular", "edge_ablation", "identity_control", "feature_attack", "structural_attack", "joint_attack", "decomposition", "construction_defence"]


def write_kg():
    nodes, edges = [], []
    seen = set()
    def node(nid, ntype, **kw):
        if nid not in seen:
            seen.add(nid); nodes.append({"id": nid, "type": ntype, **kw})
    for p in P:
        pid = "paper:" + p["key"]
        node(pid, "Paper", title=p["title"], year=p["year"], venue=p["venue"], doi=p.get("doi"), url=p.get("url"), access=p["access"])
        for fam in p["family"].split("; "):
            node("method:" + fam, "Method", name=fam)
            edges.append({"src": pid, "rel": "USES", "dst": "method:" + fam, "source_paper": p["key"], "evidence": p["evidence"], "access": p["access"]})
        for d in p.get("datasets") or []:
            node("dataset:" + d, "Dataset", name=d)
            edges.append({"src": pid, "rel": "EVALUATED_ON", "dst": "dataset:" + d, "source_paper": p["key"], "evidence": p["evidence"], "access": p["access"]})
        for prop in PROPS:
            if p.get(prop) not in (None, False):
                node("task:" + prop, "Task/Problem", name=prop)
                edges.append({"src": pid, "rel": "ADDRESSES", "dst": "task:" + prop, "value": p[prop], "source_paper": p["key"], "evidence": p["evidence"], "access": p["access"]})
        if p.get("split"):
            edges.append({"src": pid, "rel": "REPORTS", "dst": "metric:split_protocol", "value": p["split"], "source_paper": p["key"], "access": p["access"]})
    node("metric:split_protocol", "Metric", name="train/test split protocol")
    with open("kg_nodes.jsonl", "w") as f:
        for n in nodes: f.write(json.dumps(n) + "\n")
    with open("kg_edges.jsonl", "w") as f:
        for e in edges: f.write(json.dumps(e) + "\n")
    return len(nodes), len(edges)


def gap_matrix():
    fams = [KNN, ENDPOINT, LINE, TEMPORAL, TOPO_PCAP]
    rows = []
    for fam in fams:
        ps = [p for p in P if fam in p["family"]]
        row = {"family": fam, "papers": len(ps)}
        for prop in PROPS:
            row[prop] = sum(1 for p in ps if p.get(prop) not in (None, False))
        rows.append(row)
    return rows


if __name__ == "__main__":
    n, e = write_kg()
    print(f"kg: {n} nodes, {e} edges")
    rows = gap_matrix()
    json.dump(rows, open("gap_matrix.json", "w"), indent=1)
    print("family | papers | " + " | ".join(PROPS))
    for r in rows:
        print(f"{r['family']} | {r['papers']} | " + " | ".join(str(r[p]) for p in PROPS))
