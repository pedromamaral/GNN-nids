"""Phase 3: 1-hop backward + forward expansion from seeds, then keyword-relevance pruning."""
import json, re, time, requests
P = "https://api.openalex.org/works"; M = {"mailto": "pedro.m.amaral@gmail.com"}
SEL = "id,doi,title,publication_year,cited_by_count,primary_location,type,referenced_works,abstract_inverted_index"
seeds = [s for s in json.load(open("raw/seeds.json")) if "Time Matters" not in s["title"]]
seed_ids = {s["id"] for s in seeds}
def get(params):
    for attempt in range(5):
        r = requests.get(P, params={**M, **params}, timeout=90)
        if r.status_code == 200: return r.json()
        time.sleep(2 + 3 * attempt)
    r.raise_for_status()
works = {}
def add(w, how):
    e = works.setdefault(w["id"], {**{k: w.get(k) for k in ("id","doi","title","publication_year","cited_by_count","type")},
         "venue": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
         "refs": w.get("referenced_works") or [], "abstract": "", "seed_links": set()})
    inv = w.get("abstract_inverted_index")
    if inv and not e["abstract"]:
        pos = sorted((p, t) for t, ps in inv.items() for p in ps); e["abstract"] = " ".join(t for _, t in pos)
    e["seed_links"].add(how)
# seeds themselves (with abstracts)
ids = [s["id"].split("/")[-1] for s in seeds]
for i in range(0, len(ids), 50):
    for w in get({"filter": "openalex_id:" + "|".join(ids[i:i+50]), "per-page": 50, "select": SEL})["results"]: add(w, "seed")
# backward
back = {}
for s in seeds:
    for r in s["refs"]: back.setdefault(r, set()).add(s["id"])
bids = [b.split("/")[-1] for b in back]
for i in range(0, len(bids), 50):
    for w in get({"filter": "openalex_id:" + "|".join(bids[i:i+50]), "per-page": 50, "select": SEL})["results"]:
        for sid in back[w["id"]]: add(w, "ref_of:" + sid)
    time.sleep(0.3)
# forward (citing), top 200 by citations + 100 most recent
for s in seeds:
    if (s["cites"] or 0) == 0: continue
    sid = s["id"].split("/")[-1]
    for sort, n in (("cited_by_count:desc", 200), ("publication_date:desc", 100)):
        for w in get({"filter": f"cites:{sid}", "sort": sort, "per-page": n, "select": SEL})["results"]: add(w, "cites:" + s["id"])
        time.sleep(0.3)
print("harvested", len(works))
# relevance score
KW = [(r"graph", 2), (r"intrusion|nids|ids\b", 2), (r"network (flow|traffic)|netflow|flow", 1), (r"adversarial|evasion|attack", 1),
      (r"gnn|graph neural|graph convolution|graph attention|graphsage", 2), (r"robust", 1), (r"problem[- ]space", 2), (r"k-?nn|nearest neighbo|similarity graph", 1)]
for w in works.values():
    txt = ((w["title"] or "") + " " + w["abstract"]).lower()
    w["rel"] = sum(wt for pat, wt in KW if re.search(pat, txt))
    w["n_seed_links"] = len({l.split(":",1)[-1] for l in w["seed_links"]})
keep = {k: w for k, w in works.items() if k in seed_ids or (w["rel"] >= 5 and (w["n_seed_links"] >= 2 or (w["cited_by_count"] or 0) >= 30 or (w["publication_year"] or 0) >= 2024))}
print("kept", len(keep))
for w in keep.values(): w["seed_links"] = sorted(w["seed_links"])
json.dump(list(keep.values()), open("raw/candidates.json", "w"))
for w in works.values(): w["seed_links"] = sorted(w["seed_links"]) if isinstance(w["seed_links"], set) else w["seed_links"]
json.dump(list(works.values()), open("raw/harvest_all.json", "w"))
