"""Phase 4: citation-graph analysis (communities, influence, bridges, main paths, momentum)."""
import json, re, collections, itertools
import networkx as nx, numpy as np
C = {w["id"]: w for w in json.load(open("raw/candidates.json"))}
ids = set(C)
G = nx.DiGraph()
for i, w in C.items():
    G.add_node(i)
    for r in w["refs"]:
        if r in ids and r != i: G.add_edge(i, r)
print("nodes", G.number_of_nodes(), "edges", G.number_of_edges())
# bibliographic coupling (shared references, all refs not only within set)
refsets = {i: set(w["refs"]) for i, w in C.items()}
B = nx.Graph(); B.add_nodes_from(ids)
inv = collections.defaultdict(set)
for i, rs in refsets.items():
    for r in rs: inv[r].add(i)
cw = collections.Counter()
for r, citers in inv.items():
    if 2 <= len(citers) <= 150:
        for a, b in itertools.combinations(sorted(citers), 2): cw[(a, b)] += 1
for (a, b), n in cw.items():
    if n >= 2: B.add_edge(a, b, weight=n / np.sqrt(len(refsets[a]) * len(refsets[b])))
iso = [n for n in B.nodes if B.degree(n) == 0]
Bc = B.subgraph([n for n in B.nodes if B.degree(n) > 0]).copy()
comms = nx.community.louvain_communities(Bc, weight="weight", seed=42, resolution=1.0)
comms = sorted(comms, key=len, reverse=True)
cid = {n: k for k, c in enumerate(comms) for n in c}
pr = nx.pagerank(G, alpha=0.85)
indeg = dict(G.in_degree())
btw = nx.betweenness_centrality(Bc, k=min(300, len(Bc)), seed=42, weight=None)
def short(w): return f"{(w['title'] or '')[:85]} ({w['publication_year']}, {(w['venue'] or '-')[:22]}, cites={w['cited_by_count']})"
out = {"communities": []}
for k, c in enumerate(comms):
    if len(c) < 5: continue
    years = [C[n]["publication_year"] or 0 for n in c]
    top = sorted(c, key=lambda n: -pr[n])[:12]
    words = collections.Counter(t for n in c for t in re.findall(r"[a-z][a-z\-]{3,}", (C[n]["title"] or "").lower())
                                if t not in {"network","networks","based","detection","intrusion","using","with","approach","system","systems","learning","graph","neural","model","models","from","towards","novel","method","deep"})
    recent = np.mean([y >= 2025 for y in years])
    print(f"\n=== Community {k}: {len(c)} papers, median year {int(np.median(years))}, share 2025-26: {recent:.0%}")
    print("   top words:", ", ".join(w for w, _ in words.most_common(12)))
    for n in top: print(f"   PR={pr[n]*1000:5.1f} in={indeg[n]:3d} | {short(C[n])}")
    out["communities"].append({"k": k, "size": len(c), "median_year": int(np.median(years)), "recent_share": float(recent),
                               "top_words": [w for w, _ in words.most_common(12)], "top": top, "members": sorted(c)})
print("\nunclustered (no coupling):", len(iso))
print("\n=== Global PageRank top 25")
for n in sorted(ids, key=lambda n: -pr[n])[:25]: print(f"  PR={pr[n]*1000:5.1f} in={indeg[n]:3d} c={cid.get(n,'-')} | {short(C[n])}")
print("\n=== Bridges (betweenness on coupling graph) top 12")
for n in sorted(btw, key=lambda n: -btw[n])[:12]: print(f"  btw={btw[n]:.3f} c={cid.get(n)} | {short(C[n])}")
# structural holes: community pairs with few cross-citations relative to size
print("\n=== Cross-citation density between communities (edges per 100 node pairs)")
big = [c for c in comms if len(c) >= 5]
for (a, ca), (b, cb) in itertools.combinations(enumerate(big), 2):
    e = sum(1 for u in ca for v in G.successors(u) if v in cb) + sum(1 for u in cb for v in G.successors(u) if v in ca)
    print(f"  C{a}-C{b}: {100*e/(len(ca)*len(cb)):.2f}  ({e} edges)")
# main path (SPC) on DAG
D = G.copy(); D.remove_edges_from([e for e in nx.find_cycle(D)] if not nx.is_directed_acyclic_graph(D) else [])
while not nx.is_directed_acyclic_graph(D):
    D.remove_edges_from(nx.find_cycle(D))
src = [n for n in D if D.in_degree(n) == 0]; snk = [n for n in D if D.out_degree(n) == 0]
order = list(nx.topological_sort(D))
nfrom = {n: 1 if D.in_degree(n) == 0 else 0 for n in D}
for n in order:
    for v in D.successors(n): nfrom[v] += nfrom[n]
nto = {n: 1 if D.out_degree(n) == 0 else 0 for n in D}
for n in reversed(order):
    for v in D.successors(n): nto[n] += nto[v]
spc = {(u, v): nfrom[u] * nto[v] for u, v in D.edges}
start = max((e for e in spc if D.in_degree(e[0]) == 0), key=lambda e: spc[e])
path = [start[0], start[1]]
while D.out_degree(path[-1]) > 0:
    path.append(max(D.successors(path[-1]), key=lambda v: spc[(path[-1], v)]))
print("\n=== Global main path (citing -> cited)")
for n in path: print("  ", short(C[n]))
out.update({"pagerank": {n: pr[n] for n in ids}, "indegree": indeg, "betweenness": btw, "community_of": cid, "main_path": path})
json.dump(out, open("analysis.json", "w"))
nx.write_graphml(nx.relabel_nodes(G, {n: n.split("/")[-1] for n in G}), "citation_graph.graphml")
