"""Phase 2: seed discovery via OpenAlex search (sorted by citations and by relevance)."""
import json, time, requests
Q = [
 "graph neural network intrusion detection survey",
 "graph neural network network intrusion detection",
 "graph neural network intrusion detection netflow",
 "E-GraphSAGE intrusion detection",
 "k-nearest neighbor graph intrusion detection graph convolutional network",
 "similarity graph network flows graph neural network intrusion detection",
 "graph attention network intrusion detection flows",
 "adversarial attack graph neural network intrusion detection",
 "problem space adversarial attack network intrusion detection graph",
 "adversarial robustness graph-based network intrusion detection",
 "adversarial attacks machine learning network intrusion detection survey",
 "pitfalls machine learning network intrusion detection evaluation dataset",
 "netflow standard feature set intrusion detection datasets",
 "self-supervised graph neural network network intrusion detection",
]
SEL = "id,doi,title,publication_year,cited_by_count,primary_location,type"
out = {}
for q in Q:
    for sort in ("cited_by_count:desc", "relevance_score:desc"):
        r = requests.get("https://api.openalex.org/works", params={
            "search": q, "filter": "from_publication_date:2017-01-01", "sort": sort,
            "per-page": 25, "select": SEL, "mailto": "pedro.m.amaral@gmail.com"}, timeout=60)
        r.raise_for_status()
        for w in r.json()["results"]:
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
            e = out.setdefault(w["id"], {"id": w["id"], "doi": w["doi"], "title": w["title"],
                 "year": w["publication_year"], "cites": w["cited_by_count"], "venue": src, "type": w["type"], "queries": []})
            e["queries"].append(q)
        time.sleep(0.3)
json.dump(list(out.values()), open("raw/seed_candidates.json", "w"), indent=1)
print(len(out), "unique works")
