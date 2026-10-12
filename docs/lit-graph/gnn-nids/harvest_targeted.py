"""Phase 2b: targeted seed discovery (title+abstract filters) for the three research questions."""
import json, time, requests
F = {
 "gnn_nids": '"graph neural network" AND ("intrusion detection" OR "network intrusion")',
 "gnn_flow": '("graph neural network" OR "graph convolutional" OR "graph attention") AND ("network flow" OR netflow OR "flow-based")',
 "knn_graph_ids": '("k-nearest" OR knn OR "similarity graph" OR "feature similarity") AND graph AND "intrusion detection" AND (GCN OR "graph neural" OR "graph convolutional")',
 "adv_gnn_ids": '(adversarial OR evasion) AND ("graph neural network" OR GNN) AND ("intrusion detection" OR NIDS)',
 "problem_space_nids": '"problem space" AND adversarial AND ("intrusion detection" OR "network traffic")',
 "pitfalls": '(pitfalls OR "dataset flaws" OR "spurious correlations" OR shortcut OR artefact OR artifact) AND ("intrusion detection" OR "network security" OR "machine learning for security")',
 "gnn_tabular_baseline": '("graph neural network" OR GNN) AND ("intrusion detection") AND (XGBoost OR "gradient boosting" OR "random forest") AND (comparison OR baseline OR benchmark)',
}
SEL = "id,doi,title,publication_year,cited_by_count,primary_location,type"
out = {}
for tag, q in F.items():
    for sort in ("cited_by_count:desc", "publication_date:desc"):
        r = requests.get("https://api.openalex.org/works", params={
            "filter": f"title_and_abstract.search:{q},from_publication_date:2018-01-01", "sort": sort,
            "per-page": 50, "select": SEL, "mailto": "pedro.m.amaral@gmail.com"}, timeout=60)
        if r.status_code != 200:
            print(tag, sort, r.status_code, r.text[:200]); continue
        for w in r.json()["results"]:
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
            e = out.setdefault(w["id"], {"id": w["id"], "doi": w["doi"], "title": w["title"], "year": w["publication_year"],
                                         "cites": w["cited_by_count"], "venue": src, "type": w["type"], "tags": []})
            if tag not in e["tags"]: e["tags"].append(tag)
        time.sleep(0.3)
json.dump(list(out.values()), open("raw/targeted_candidates.json", "w"), indent=1)
print(len(out), "unique works")
for tag in F:
    xs = sorted([x for x in out.values() if tag in x["tags"]], key=lambda x: -x["cites"])
    print(f"\n### {tag} ({len(xs)})")
    for x in xs[:40]: print(f"{x['cites']:5d} {x['year']} {(x['venue'] or '-')[:26]:26s} | {(x['title'] or '')[:100]}")
