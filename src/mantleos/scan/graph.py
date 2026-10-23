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

    # Iterative Tarjan SCC: source call chains can exceed Python's recursion limit.
    index = 0
    stack: list[str] = []
    onstack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sccs: list[list[str]] = []

    def enter(v: str):
        nonlocal index
        indexes[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)
        return iter(sorted(adjacency.get(v, [])))

    for v in sorted(ids):
        if v in indexes:
            continue
        frames = [(v, enter(v))]
        while frames:
            current, children = frames[-1]
            child = next(children, None)
            if child is not None:
                if child not in indexes:
                    frames.append((child, enter(child)))
                elif child in onstack:
                    lowlink[current] = min(lowlink[current], indexes[child])
                continue
            frames.pop()
            if lowlink[current] == indexes[current]:
                comp: list[str] = []
                while True:
                    member = stack.pop()
                    onstack.remove(member)
                    comp.append(member)
                    if member == current:
                        break
                sccs.append(sorted(comp))
            if frames:
                parent = frames[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[current])

    hubs = sorted(
        ({"id": nid, "in_degree": indeg[nid], "out_degree": outdeg[nid], "degree": indeg[nid] + outdeg[nid]} for nid in ids),
        key=lambda x: (-x["degree"], x["id"]),
    )[:50]
    return {
        "node_count": len(nodes), "edge_count": len(edges),
        "scc_count": len(sccs), "nontrivial_scc_count": sum(1 for c in sccs if len(c) > 1),
        "largest_scc": max((len(c) for c in sccs), default=0), "top_hubs": hubs,
    }
