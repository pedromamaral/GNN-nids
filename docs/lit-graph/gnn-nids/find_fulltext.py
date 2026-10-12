"""Find open full-text locations for the core set (OpenAlex OA locations + arXiv title search)."""
import json, time, re, requests, xml.etree.ElementTree as ET
P = "https://api.openalex.org/works"; M = {"mailto": "pedro.m.amaral@gmail.com"}
CORE = [
 "R+R: From Claims to Crashes: A Systematic Re-evaluation of Graph-Based Network Intrusion",
 "Problem space structural adversarial attacks for Network Intrusion Detection Systems based on Graph Neural Networks",
 "Towards problem space-constrained adversarial attacks against graph neural network based network intrusion detection",
 "Defending Network Intrusion Detection Systems Based on Graph Neural Networks Against Structural Adversarial Attacks",
 "Unveiling the potential of Graph Neural Networks for robust Intrusion Detection",
 "Hierarchical Adversarial Attacks Against Graph-Neural-Network-Based IoT Network Intrusion Detection System",
 "E-GraphSAGE: A Graph Neural Network based Intrusion Detection System for IoT",
 "Anomal-E: A self-supervised network intrusion detection system based on graph neural networks",
 "Graph Neural Networks for Intrusion Detection: A Survey",
 "A survey on graph neural networks for intrusion detection systems: Methods, trends and challenges",
 "Graph neural networks for network intrusion detection systems: a comprehensive survey, taxonomy, and empirical",
 "From Flow Features to Communication Topology: Adaptive Graph Attention Network-Based IoMT Intrusion Detection",
 "Optimizing IoT Intrusion Detection—A Graph Neural Network Approach with Attribute-Based Graph Construction",
 "BS-GAT Behavior Similarity Based Graph Attention Network for Network Intrusion Detection",
 "Enhancing intrusion detection performance using GCN-LOF: A hybrid graph-based anomaly detection approach",
 "Efficient Network Representation for GNN-Based Intrusion Detection",
 "Unmasking Shortcut Learning in IoT Intrusion Detection: A Forensic, Multi-Paradigm Evaluation",
 "Dos and Don'ts of Machine Learning in Computer Security",
 "Applying self-supervised learning to network intrusion detection for network flows with graph neural network",
 "TCG-IDS: Robust Network Intrusion Detection via Temporal Contrastive Graph",
 "Towards realistic problem-space adversarial attacks against machine learning in network intrusion detection",
 "Temporal Analysis of NetFlow Datasets for Network Intrusion Detection Systems",
 "Edge weight concentration overcomes node degree blindness in graph based network intrusion detection",
 "Automating Botnet Detection with Graph Neural Networks",
 "Flow Topology-Based Graph Convolutional Network for Intrusion Detection in Label-Limited IoT Networks",
 "Establishing the Contaminating Effect of Metadata Feature Inclusion in Machine-Learned Network Intrusion Detection Models",
 "Application of a Dynamic Line Graph Neural Network for Intrusion Detection With Semisupervised Learning",
]
def arxiv(title):
    q = " AND ".join(f'ti:"{w}"' for w in re.findall(r"[A-Za-z]{5,}", title)[:6])
    for attempt in range(4):
        try:
            r = requests.get("https://export.arxiv.org/api/query", params={"search_query": q, "max_results": 3}, timeout=60)
            if r.status_code == 200: break
        except requests.RequestException:
            pass
        time.sleep(5 * (attempt + 1))
    else:
        return None, None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in ET.fromstring(r.text).findall("a:entry", ns):
        t = " ".join(e.find("a:title", ns).text.split())
        if len(set(re.findall(r"[a-z]{5,}", t.lower())) & set(re.findall(r"[a-z]{5,}", title.lower()))) >= 4:
            return e.find("a:id", ns).text.split("/abs/")[-1], t
    return None, None
import sys
res = []
def oa_search(t):
    for attempt in range(5):
        r = requests.get(P, params={**M, "search": t, "per-page": 1, "select": "id,doi,title,publication_year,primary_location,best_oa_location,locations"}, timeout=60)
        if r.status_code == 200 and "results" in r.json(): return r.json()["results"]
        time.sleep(5 * (attempt + 1))
    return []
for t in CORE[int(sys.argv[1]) if len(sys.argv) > 1 else 0:]:
    r = oa_search(t)
    w = r[0] if r else {}
    oa = [l.get("landing_page_url") for l in (w.get("locations") or []) if l.get("is_oa")]
    aid, at = arxiv(t); time.sleep(3)
    res.append({"query": t, "openalex": w.get("id"), "doi": w.get("doi"), "year": w.get("publication_year"),
                "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"), "oa": oa[:3], "arxiv": aid})
    print(f"{(w.get('title') or 'NONE')[:70]:70s} | {w.get('doi')} | arXiv={aid} | oa={oa[:2]}")
json.dump(res, open("raw/core_fulltext_part2.json" if len(sys.argv) > 1 else "raw/core_fulltext.json", "w"), indent=1)
