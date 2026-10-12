import json, time, requests
F = {
 "giant": 'GIANT AND "graph" AND injection AND "intrusion detection"',
 "critique1": '"graph neural network" AND "intrusion detection" AND (reproducibility OR "re-evaluation" OR "critical")',
 "critique2": '"graph neural network" AND "intrusion detection" AND (leakage OR "data leakage" OR "IP address")',
 "critique3": '("graph-based" OR GNN) AND "intrusion detection" AND ("simple baseline" OR "do we need")',
 "venturi": 'Venturi AND graph AND adversarial',
 "injection": '"node injection" AND "intrusion detection"',
 "netflow_temporal": 'NetFlow AND datasets AND temporal AND "intrusion detection"',
 "realistic_eval": '"intrusion detection" AND ("temporal split" OR "chronological" OR "time-based split")',
 "knn_graph2": '"graph convolutional network" AND "intrusion detection" AND "k-nearest"',
 "topk_sim": '"similarity" AND "graph construction" AND "intrusion detection"',
}
SEL = "id,doi,title,publication_year,cited_by_count,primary_location,type"
out = {}
for tag, q in F.items():
    r = requests.get("https://api.openalex.org/works", params={"filter": f"title_and_abstract.search:{q},from_publication_date:2018-01-01",
        "sort": "cited_by_count:desc", "per-page": 30, "select": SEL, "mailto": "pedro.m.amaral@gmail.com"}, timeout=60)
    time.sleep(1.0)
    if r.status_code != 200: print(tag, r.status_code, r.text[:150]); continue
    print(f"\n### {tag}")
    for w in r.json()["results"]:
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
        out[w["id"]] = {"id": w["id"], "doi": w["doi"], "title": w["title"], "year": w["publication_year"], "cites": w["cited_by_count"], "venue": src, "tag": tag}
        print(f"{w['cited_by_count']:5d} {w['publication_year']} {(src or '-')[:26]:26s} | {(w['title'] or '')[:105]}")
json.dump(list(out.values()), open("raw/extra_candidates.json", "w"), indent=1)
