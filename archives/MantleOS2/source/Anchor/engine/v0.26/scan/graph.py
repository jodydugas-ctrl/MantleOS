from __future__ import annotations

from collections import defaultdict


def graph_metrics(nodes: list[dict], edges: list[dict]) -> dict:
    ids = {n["id"] for n in nodes}
    outdeg = defaultdict(int)
    indeg = defaultdict(int)
    adjacency = defaultdict(list)
    for e in edges:
        if e["src"] in ids and e["dst"] in ids:
            outdeg[e["src"]] += 1
            indeg[e["dst"]] += 1
            adjacency[e["src"]].append(e["dst"])

    # Tarjan SCC, deterministic node order.
    index = 0
    stack: list[str] = []
    onstack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str):
        nonlocal index
        indexes[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)
        for w in sorted(adjacency.get(v, [])):
            if w not in indexes:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in onstack:
                lowlink[v] = min(lowlink[v], indexes[w])
        if lowlink[v] == indexes[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                onstack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(sorted(comp))

    for v in sorted(ids):
        if v not in indexes:
            strongconnect(v)

    hubs = sorted(
        ({"id": nid, "in_degree": indeg[nid], "out_degree": outdeg[nid], "degree": indeg[nid] + outdeg[nid]} for nid in ids),
        key=lambda x: (-x["degree"], x["id"]),
    )[:50]
    return {
        "node_count": len(nodes), "edge_count": len(edges),
        "scc_count": len(sccs), "nontrivial_scc_count": sum(1 for c in sccs if len(c) > 1),
        "largest_scc": max((len(c) for c in sccs), default=0), "top_hubs": hubs,
    }
