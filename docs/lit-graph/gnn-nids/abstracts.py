"""Abstract-level records (OpenAlex) for papers read at abstract level only."""
import json, time, requests
P = "https://api.openalex.org/works"; M = {"mailto": "pedro.m.amaral@gmail.com"}
T = [
 "Hierarchical Adversarial Attacks Against Graph-Neural-Network-Based IoT Network Intrusion Detection System",
 "A survey on graph neural networks for intrusion detection systems: Methods, trends and challenges",
 "Graph neural networks for network intrusion detection systems: a comprehensive survey, taxonomy, and empirical",
 "Graph Neural Networks for Intrusion Detection: A Survey",
 "Towards problem space-constrained adversarial attacks against graph neural network based network intrusion detection",
 "Unmasking Shortcut Learning in IoT Intrusion Detection: A Forensic, Multi-Paradigm Evaluation",
 "Edge weight concentration overcomes node degree blindness in graph based network intrusion detection",
 "From Flows to Graphs: Benchmarking Centrality Metrics in ML-Based Intrusion Detection Systems",
 "Detecting Unknown Encrypted Malicious Traffic in Real Time via Flow Interaction Graph Analysis",
 "Modeling realistic adversarial attacks against network intrusion detection systems",
 "Intriguing properties of adversarial ML attacks in the problem space",
 "Dos and Don'ts of Machine Learning in Computer Security",
 "BS-GAT: a network intrusion detection system based on graph neural network for edge computing",
 "Enhancing intrusion detection performance using GCN-LOF: A hybrid graph-based anomaly detection approach",
 "Flow Topology-Based Graph Convolutional Network for Intrusion Detection in Label-Limited IoT Networks",
 "A new concatenated Multigraph Neural Network for IoT intrusion detection",
 "Practical Evaluation of Graph Neural Networks in Network Intrusion Detection",
 "TCG-IDS: Robust Network Intrusion Detection via Temporal Contrastive Graph Learning",
 "Towards a Standard Feature Set for Network Intrusion Detection System Datasets",
 "Temporal Analysis of NetFlow Datasets for Network Intrusion Detection Systems",
 "Establishing the Contaminating Effect of Metadata Feature Inclusion in Machine-Learned Network Intrusion Detection Models",
 "When Adversarial Perturbations meet Concept Drift: An Exploratory Analysis on ML-NIDS",
 "Efficient Network Representation for GNN-Based Intrusion Detection",
 "Application of a Dynamic Line Graph Neural Network for Intrusion Detection With Semisupervised Learning",
 "Automating Botnet Detection with Graph Neural Networks",
 "Adversarial Machine Learning for Network Intrusion Detection Systems: A Comprehensive Survey",
 "Graph Structure Learning for Robust Graph Neural Networks",
 "GNNGuard: Defending Graph Neural Networks against Adversarial Attacks",
 "Adversarial Attacks on Neural Networks for Graph Data",
 "Sometimes Simpler is Better: A Comprehensive Analysis of State-of-the-Art Provenance-Based Intrusion Detection Systems",
]
out = []
for t in T:
    for attempt in range(6):
        r = requests.get(P, params={**M, "search": t, "per-page": 1, "select": "id,doi,title,publication_year,cited_by_count,primary_location,authorships,abstract_inverted_index"}, timeout=60)
        if r.status_code == 200 and "results" in r.json(): break
        time.sleep(6 * (attempt + 1))
    res = r.json().get("results", []) if r.status_code == 200 else []
    if not res: print("MISSING", t); continue
    w = res[0]; inv = w.get("abstract_inverted_index") or {}
    ab = " ".join(x for _, x in sorted((p, x) for x, ps in inv.items() for p in ps))
    out.append({"query": t, "id": w["id"], "doi": w["doi"], "title": w["title"], "year": w["publication_year"], "cites": w["cited_by_count"],
                "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
                "authors": [a["author"]["display_name"] for a in w["authorships"]][:6], "abstract": ab})
    print(f"{w['publication_year']} {w['cited_by_count']:4d} {(w['title'] or '')[:80]} | abs={len(ab)}")
    time.sleep(2)
json.dump(out, open("raw/abstracts.json", "w"), indent=1)
