"""Resolve the seed list (titles / DOIs) to OpenAlex works."""
import json, time, requests
P = "https://api.openalex.org/works"
M = {"mailto": "pedro.m.amaral@gmail.com"}
SEEDS = [
 ("doi", "10.1145/3774904.3792601"),  # GIANT, WWW 2026
 ("title", "E-GraphSAGE: A Graph Neural Network based Intrusion Detection System for IoT"),
 ("title", "Anomal-E: A self-supervised network intrusion detection system based on graph neural networks"),
 ("title", "Unveiling the potential of Graph Neural Networks for robust Intrusion Detection"),
 ("title", "Hierarchical Adversarial Attacks Against Graph-Neural-Network-Based IoT Network Intrusion Detection System"),
 ("title", "Graph Neural Networks for Intrusion Detection: A Survey"),
 ("title", "A survey on graph neural networks for intrusion detection systems: Methods, trends and challenges"),
 ("title", "Graph neural networks for network intrusion detection systems: a comprehensive survey, taxonomy, and empirical"),
 ("title", "Problem space structural adversarial attacks for Network Intrusion Detection Systems based on Graph Neural Networks"),
 ("title", "Towards problem space-constrained adversarial attacks against graph neural network based network intrusion detection"),
 ("title", "Defending Network Intrusion Detection Systems Based on Graph Neural Networks Against Structural Adversarial Attacks"),
 ("title", "ARGANIDS: a novel Network Intrusion Detection System based on adversarially Regularized Graph Autoencoder"),
 ("title", "Application of a Dynamic Line Graph Neural Network for Intrusion Detection With Semisupervised Learning"),
 ("title", "TCG-IDS: Robust Network Intrusion Detection via Temporal Contrastive Graph"),
 ("title", "Applying self-supervised learning to network intrusion detection for network flows with graph neural network"),
 ("title", "Efficient Network Representation for GNN-Based Intrusion Detection"),
 ("title", "Optimizing IoT Intrusion Detection—A Graph Neural Network Approach with Attribute-Based Graph Construction"),
 ("title", "Enhancing intrusion detection performance using GCN-LOF: A hybrid graph-based anomaly detection approach"),
 ("title", "BS-GAT: a network intrusion detection system based on graph neural network for edge computing"),
 ("title", "From Flow Features to Communication Topology: Adaptive Graph Attention Network-Based IoMT Intrusion Detection"),
 ("title", "Euler: Detecting Network Lateral Movement via Scalable Temporal Graph Link Prediction"),
 ("title", "Dos and Don'ts of Machine Learning in Computer Security"),
 ("title", "Adversarial Machine Learning for Network Intrusion Detection Systems: A Comprehensive Survey"),
 ("title", "Towards realistic problem-space adversarial attacks against machine learning in network intrusion detection"),
 ("title", "Towards a Standard Feature Set for Network Intrusion Detection System Datasets"),
 ("title", "Establishing the Contaminating Effect of Metadata Feature Inclusion in Machine-Learned Network Intrusion Detection Models"),
 ("title", "Unmasking Shortcut Learning in IoT Intrusion Detection"),
 ("title", "Are TGNN-Based Intrusion Detection Results Trustworthy? A Dataset Audit and Evaluation Framework"),
 ("title", "Temporal Analysis of NetFlow Datasets for Network Intrusion Detection Systems"),
 ("title", "Edge weight concentration overcomes node degree blindness in graph based network intrusion detection"),
 ("title", "Network intrusion detection with edge-directed graph Multi-Head Attention Networks"),
 ("title", "When Adversarial Perturbations meet Concept Drift: An Exploratory Analysis on ML-NIDS"),
]
SEL = "id,doi,title,publication_year,cited_by_count,primary_location,type,referenced_works,open_access,best_oa_location"
res = []
for kind, v in SEEDS:
    if kind == "doi":
        r = requests.get(f"{P}/https://doi.org/{v}", params={**M, "select": SEL}, timeout=60)
        w = r.json() if r.status_code == 200 else None
    else:
        r = requests.get(P, params={**M, "search": v, "per-page": 3, "select": SEL}, timeout=60)
        hits = r.json().get("results", []) if r.status_code == 200 else []
        w = hits[0] if hits else None
    time.sleep(0.4)
    if not w:
        print("MISSING", v); continue
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
    oa = (w.get("best_oa_location") or {}).get("landing_page_url") or (w.get("best_oa_location") or {}).get("pdf_url")
    res.append({"query": v, "id": w["id"], "doi": w["doi"], "title": w["title"], "year": w["publication_year"],
                "cites": w["cited_by_count"], "venue": src, "nrefs": len(w.get("referenced_works") or []),
                "refs": w.get("referenced_works") or [], "oa_url": oa})
    print(f"{w['cited_by_count']:4d} {w['publication_year']} refs={len(w.get('referenced_works') or []):3d} {(src or '-')[:24]:24s} | {w['title'][:90]}")
json.dump(res, open("raw/seeds.json", "w"), indent=1)
