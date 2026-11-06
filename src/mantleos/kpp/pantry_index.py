"""Pantry browsing and advisory matching of declared ingredient interfaces."""
import re
from urllib.parse import quote


ORGANS = {
    "heart": "Heart",
    "senses": "Senses",
    "nervous-system": "Nervous System",
    "immune-system": "Immune System",
    "limbs": "Limbs",
    "memory": "Memory",
}
CAPABILITY = re.compile(r"[a-z][a-z0-9-]{0,63}/[1-9][0-9]{0,8}")


def capability_id(value):
    return isinstance(value, str) and CAPABILITY.fullmatch(value) is not None


def validate_metadata(item):
    """Validate optional fields without requiring a contract on legacy entries."""
    for field in ("organs", "provides", "requires"):
        if field not in item:
            continue
        values = item[field]
        valid = (lambda value: isinstance(value, str) and value in ORGANS) if field == "organs" else capability_id
        if not isinstance(values, list) or not all(map(valid, values)) or len(values) != len(set(values)):
            raise ValueError(f"Invalid {field} in Pantry ingredient {item['id']}")
    if ("provides" in item) != ("requires" in item):
        raise ValueError(f"Ingredient {item['id']} must declare both provides and requires")


def shelf_views(manifests):
    """Render export paths from a mapping of root manifest filenames to contents."""
    root = "pantry/organs"
    heading = "Generated from the Pantry manifests. Edit the manifests to update these shelves."
    overview = ["# Pantry organ shelves", "", heading, "",
                "These are browsing categories. Each recipe chooses its organ composition.", ""]
    views = {}
    for organ, title in ORGANS.items():
        overview.append(f"- [{title}]({organ}/README.md)")
        lines = [f"# {title}", "", heading, "", "[All organ shelves](../README.md)", ""]
        lines += [f"- [{item['id']}](../../{quote(name)})" for name, item in sorted(manifests.items())
                  if organ in item.get("organs", ())]
        if lines[-1] == "":
            lines.append("No ingredients are currently classified on this shelf.")
        views[f"{root}/{organ}/README.md"] = ("\n".join(lines) + "\n").encode()
    overview += ["", "## Other Pantry ingredients", ""]
    overview += [f"- [{item['id']}](../{quote(name)})" for name, item in sorted(manifests.items())
                 if not item.get("organs")]
    views[f"{root}/README.md"] = ("\n".join(overview) + "\n").encode()
    return views


def _cycles(waits):
    """Group mutually reachable selected ingredients still waiting on declarations."""
    reachable = {}
    for ingredient, blockers in waits.items():
        seen = set()
        pending = list(blockers)
        while pending:
            blocker = pending.pop()
            if blocker not in seen:
                seen.add(blocker)
                pending.extend(waits.get(blocker, ()))
        reachable[ingredient] = seen
    return sorted({tuple(sorted(other for other in reachable[ingredient]
                                if ingredient in reachable.get(other, ())))
                   for ingredient in waits if ingredient in reachable[ingredient]})


def fit(catalog, *, recipe=None, ingredients=(), host_capabilities=()):
    """Compare metadata only. A ready declaration is not runtime evidence."""
    from .core import SLUG, digest, validate_recipe

    if recipe is None and not ingredients:
        raise ValueError("Select a recipe or at least one ingredient")
    if recipe is not None:
        validate_recipe(recipe)
    selected = sorted(set(recipe["ingredients"] if recipe is not None else ()) | set(ingredients))
    unknown_ids = sorted(set(selected) - catalog.keys())
    if unknown_ids:
        raise ValueError("Unknown Pantry ingredients: " + ", ".join(unknown_ids))
    if not all(map(capability_id, host_capabilities)):
        raise ValueError("Host capabilities must be versioned IDs such as notes-rows/1")
    host = set(host_capabilities)
    tissue = recipe["tissue"] if recipe is not None else "unspecified"

    def tissue_match(item):
        declared = item.get("compatible_tissues", ())
        if not declared or tissue in ("unspecified", "mixed"):
            return "review-needed"
        return "matches" if tissue in declared else "incompatible"

    def dependencies(name):
        return set(catalog[name].get("dependencies", ()))

    tissue_status = {name: tissue_match(catalog[name]) for name in selected}
    eligible = {name for name in selected if tissue_status[name] != "incompatible"}
    providers = {}
    for name, item in sorted(catalog.items()):
        validate_metadata(item)
        names = item.get("dependencies", [])
        if not isinstance(names, list) or not all(isinstance(dep, str) and SLUG.fullmatch(dep)
                                                 for dep in names):
            raise ValueError(f"Invalid dependencies in Pantry ingredient {name}")
        if tissue_match(item) != "incompatible":
            for capability in item.get("provides", ()):
                providers.setdefault(capability, []).append(name)

    ready = set()
    supplied = {}
    used_providers = {}
    while True:
        batch = sorted(name for name in eligible - ready if dependencies(name) <= ready
                       and set(catalog[name].get("requires", ())) <= host | supplied.keys())
        if not batch:
            break
        for name in batch:
            used_providers[name] = {capability: sorted(supplied[capability])
                                    for capability in catalog[name].get("requires", ())
                                    if capability not in host}
        for name in batch:
            ready.add(name)
            for capability in catalog[name].get("provides", ()):
                supplied.setdefault(capability, []).append(name)

    rows = []
    waits = {}
    for name in selected:
        item = catalog[name]
        missing_inputs = []
        bindings = {}
        waiting = dependencies(name) & (eligible - ready)
        for capability in sorted(item.get("requires", ())):
            if capability in host:
                bindings[capability] = {"kind": "host"}
                continue
            choices = (used_providers[name].get(capability, ()) if name in ready
                       else supplied.get(capability, ()))
            if choices:
                bindings[capability] = {"kind": "ingredient", "ids": sorted(choices)}
                continue
            candidates = providers.get(capability, ())
            waiting.update(set(candidates) & (eligible - ready))
            missing_inputs.append({
                "capability": capability,
                "waiting_for_selected": sorted(set(candidates) & (eligible - ready)),
                "suggestions": [{"id": candidate, "manifest_sha256": digest(catalog[candidate])}
                                for candidate in candidates if candidate not in selected],
            })
        if name in eligible - ready:
            waits[name] = waiting
        rows.append({
            "id": name,
            "manifest_sha256": digest(item),
            "interface_metadata": "declared" if "provides" in item else "unknown",
            "declared_inputs_satisfied": name in ready if "requires" in item else None,
            "tissue": tissue_status[name],
            "inputs": bindings,
            "missing_inputs": missing_inputs,
            "missing_dependencies": sorted(dependencies(name) - set(selected)),
            "unresolved_dependencies": sorted(dependencies(name) & (set(selected) - ready)),
        })
    return {
        "schema": "kpp.pantry-fit/1",
        "recipe_sha256": digest(recipe) if recipe is not None else None,
        "tissue": tissue,
        "host_capabilities": sorted(host),
        "ingredients": rows,
        "possible_wait_cycles": [list(cycle) for cycle in _cycles(waits)],
        "scope": "Advisory declarations only. Suggestions need their own inputs and recipe verification.",
    }
