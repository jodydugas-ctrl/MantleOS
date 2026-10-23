"""Logical comparison hints, separate from immutable byte-bound evidence IDs."""
from collections import defaultdict
from .common import digest

SCHEMA = "scan.symbol/1"


def annotate(nodes):
    """Owner chains and local disambiguators never assert runtime identity."""
    owners, counts, groups = {}, defaultdict(int), defaultdict(list)
    for node in nodes:
        parent = owners.get(node["owner"])
        scope = list(parent["scope"]) if parent else []
        logical_scope = list(parent["logical_scope"]) if parent else []
        if node["kind"] != "module":
            local = (node["owner"], node["kind"], node["name"])
            ordinal = counts[local]
            counts[local] += 1
            scope.append([node["kind"], node["name"], ordinal])
            logical_scope.append([node["kind"], node["name"]])
        logical = digest([node["path"], node["kind"], logical_scope])
        comparison = {"schema": SCHEMA, "scope": scope, "logical_scope": logical_scope,
                      "logical_key": "logical:" + logical,
                      "qualified_name": ".".join(item[1] for item in logical_scope),
                      "ambiguous": bool(node.get("name_truncated") and node["kind"] != "module"),
                      "authority": "COMPARISON_HINT_ONLY"}
        node["symbol_key"] = "symbol:" + digest([node["path"], node["kind"], scope])
        node["comparison"] = comparison
        owners[node["id"]] = comparison
        groups[logical].append(node)
    for group in groups.values():
        if len(group) > 1:
            for node in group:
                node["comparison"]["ambiguous"] = True
    for node in nodes:
        parent = owners.get(node["owner"])
        if parent and parent["ambiguous"]:
            node["comparison"]["ambiguous"] = True
    return nodes
