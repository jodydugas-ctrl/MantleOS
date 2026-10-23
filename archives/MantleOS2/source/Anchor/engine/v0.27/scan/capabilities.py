from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def _loads(value: str | None, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def build_nest_capability_map(store) -> dict[str, Any]:
    """Build a conservative BODY<->NEST/capability projection from the canonical scan tables.

    This projection does not invent capabilities from provider names alone. Effects and boundaries retain
    their extractor coverage/provenance; dynamic factories are POTENTIAL until a concrete payload is known.
    """
    rows = store.query(
        "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes "
        "WHERE kind IN ('nest_boundary','effect','extension_receptor','extension_receptor_candidate',"
        "'capability_factory','persistence_provider','persistence_operation','guard','error_path',"
        "'control_exit','retry_path_candidate') ORDER BY path,kind,name,id"
    )
    effects = []
    boundaries = []
    extensions = []
    persistence = []
    control = []
    by_capability: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "capability": None, "effects": [], "boundaries": [], "directions": set(), "provenance": set(),
    })

    for row in rows:
        attrs = _loads(row.get("attributes_json"), {})
        base = {
            "id": row["id"], "kind": row["kind"], "name": row["name"], "path": row.get("path"),
            "coverage": row["coverage"], "attributes": attrs,
            "evidence_ids": _loads(row.get("evidence_ids_json"), []),
        }
        if row["kind"] == "effect":
            provenance = attrs.get("capability_provenance") or ("COUPLED" if attrs.get("classification") == "compiler_typed_api" else "UNKNOWN")
            base["capability_provenance"] = provenance
            effects.append(base)
            capability = attrs.get("capability") or "unknown"
            item = by_capability[str(capability)]
            item["capability"] = capability
            item["effects"].append(row["id"])
            if attrs.get("direction"):
                item["directions"].add(str(attrs["direction"]))
            item["provenance"].add(provenance)
        elif row["kind"] == "nest_boundary":
            provenance = "COUPLED" if attrs.get("classification") == "compiler_typed_api" else "UNKNOWN"
            base["capability_provenance"] = provenance
            boundaries.append(base)
            capability = attrs.get("boundary_type") or row["name"]
            item = by_capability[str(capability)]
            item["capability"] = capability
            item["boundaries"].append(row["id"])
            if attrs.get("direction"):
                item["directions"].add(str(attrs["direction"]))
            item["provenance"].add(provenance)
        elif row["kind"] in {"extension_receptor", "extension_receptor_candidate", "capability_factory"}:
            if row["kind"] == "capability_factory":
                base["capability_provenance"] = "POTENTIAL"
            elif row["kind"] == "extension_receptor" and attrs.get("classification") == "compiler_typed_extension_api":
                base["capability_provenance"] = "COUPLED"
            else:
                base["capability_provenance"] = "UNKNOWN"
            extensions.append(base)
        elif row["kind"] in {"persistence_provider", "persistence_operation"}:
            persistence.append(base)
        else:
            control.append(base)

    capabilities = []
    for key in sorted(by_capability):
        item = by_capability[key]
        capabilities.append({
            "capability": item["capability"],
            "effect_ids": sorted(set(item["effects"])),
            "boundary_ids": sorted(set(item["boundaries"])),
            "directions": sorted(item["directions"]),
            "provenance_states": sorted(item["provenance"]),
        })

    return {
        "schema_version": "scan-nest-capability-map/0.1",
        "state": "PARTIAL" if rows else "UNKNOWN",
        "capability_count": len(capabilities),
        "effect_count": len(effects),
        "boundary_count": len(boundaries),
        "extension_receptor_count": sum(1 for x in extensions if x["kind"] != "capability_factory"),
        "capability_factory_count": sum(1 for x in extensions if x["kind"] == "capability_factory"),
        "persistence_object_count": len(persistence),
        "control/error_object_count": len(control),
        "capabilities": capabilities,
        "effects": effects,
        "boundaries": boundaries,
        "extensions": extensions,
        "persistence": persistence,
        "guards_errors_retries": control,
        "invariant": "NEST feature != BODY coupling != authorization != current use != observed runtime success",
    }


def write_nest_capability_map(store, output: Path) -> dict[str, Any]:
    payload = build_nest_capability_map(store)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
