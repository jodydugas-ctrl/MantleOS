"""Progressive ingredient disclosure. The existing manifest is the only authoritative
pantry record: labels/contracts are read-only views, not another registry.

A label can establish what an ingredient claims to do; neither a source hash nor a
manifest statement proves recipe compatibility or the runtime behavior of a bake.
"""
import hashlib
from pathlib import Path

from .core import KPPError, digest, ingredient_catalog, validate_repository_source


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 700:
        raise KPPError("Invalid ingredient usage " + name)
    return value.strip()


def _usage(item):
    usage = item.get("usage", {})
    if not isinstance(usage, dict):
        raise KPPError("Invalid ingredient usage object: " + item["id"])
    if set(usage) - {"use_when", "inputs", "outputs", "limits"}:
        raise KPPError("Unrecognized ingredient usage fields: " + item["id"])
    for field in ("inputs", "outputs"):
        values = usage.get(field, [])
        if not isinstance(values, list) or len(values) > 8:
            raise KPPError("Invalid ingredient usage " + field)
        for value in values:
            _text(value, field)
    for field in ("use_when", "limits"):
        if field in usage:
            _text(usage[field], field)
    return usage


def source_identity(repo, item, check_external=False):
    """No source inspection for ordinary labels. Specimen check is byte-hash only.
    External scan is opt-in and its inventory remains explicitly bounded.
    """
    declaration=item.get('source',{})
    if isinstance(declaration,dict) and declaration.get('kind')=='bundled-files':
        pins=declaration.get('files',{})
        base=Path(repo).resolve()
        bundled=base==Path(__file__).resolve().with_name('resources')
        if not pins: raise KPPError('Empty bundled source inventory')
        for name,pin in pins.items():
            path=(Path(__file__).resolve().parents[2]/name[4:]) if bundled and name.startswith('src/') else base/name
            if not name.startswith('src/mantleos/') or '..' in Path(name).parts or path.is_symlink() or (not bundled and not path.resolve().is_relative_to(base)):
                raise KPPError('Unsafe bundled source path')
            if check_external and (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=pin):
                raise KPPError('Bundled source pin mismatch: '+name)
        return {'kind':'bundled-files','integrity':'PIN_MATCH' if check_external else 'NOT_RECHECKED','files':pins,'source_access':'EXPLICIT_ONLY'}
    specimen = item.get("specimen")
    if specimen:
        path = specimen["path"]
        base = Path(repo).resolve()
        selected = (base/path).resolve()
        if not selected.is_relative_to(base) or not path.startswith("specimens/"):
            return {"kind":"anchor-specimen", "integrity":"UNSAFE_PATH", "source_access":"BLOCKED"}
        if not selected.is_file():
            status="SOURCE_MISSING"
        else:
            actual=hashlib.sha256(selected.read_bytes()).hexdigest()
            status="PIN_MATCH" if actual==specimen["sha256"] else "STALE_PIN_MISMATCH"
        return {"kind":"anchor-specimen", "integrity":status,
                "pin_sha256":specimen["sha256"], "profile":specimen["profile"],
                "relative_path":path, "source_access":"EXPLICIT_ONLY"}
    source = item.get("source", {})
    if isinstance(source, dict) and source.get("kind") == "repository-files":
        declaration = validate_repository_source(source)
        return {"kind": "repository-files", "repository": declaration["repository"],
                "paths": declaration["paths"], "integrity": "DECLARED_LOCATION_ONLY",
                "source_access": "EXPLICIT_ONLY"}
    if isinstance(source, dict) and source.get("kind") == "local-directory":
        result={"kind":"local-directory", "integrity":"NOT_RECHECKED",
                "scope":source.get("scope", "bounded source inventory"),
                "inventory_sha256":source.get("source_listing_sha256"),
                "source_access":"EXPLICIT_ONLY"}
        if check_external:
            from .scanner import scan
            path=Path(source.get("path_at_scan", ""))
            if not path.is_dir():
                result["integrity"]="SOURCE_MISSING"
            else:
                current=scan(path,1)
                result["integrity"]=("INVENTORY_MATCH_BOUNDED" if digest(current["files"]) == result["inventory_sha256"]
                                     else "STALE_INVENTORY")
                result["scan_limitations"]=current["limitations"]
                result["skipped_files"]=len(current["skipped"])
        return result
    return {"kind":"unbundled-reference-or-contract", "integrity":"NO_SOURCE_PIN",
            "source_access":"NOT_AVAILABLE_FROM_PANTRY"}


def label(repo, item, check_external=False):
    usage=_usage(item)
    origin=source_identity(repo,item,check_external)
    status=item.get("status","reference")
    if status not in ("ready","reference","experimental"):
        raise KPPError("Invalid pantry status: " + item["id"])
    return {"schema":"kpp.ingredient-label/1", "id":item["id"],"version":item["version"],
            "purpose":item["function"], "use_when":usage.get("use_when", "Review functional contract"),
            "inputs":usage.get("inputs", []),"outputs":usage.get("outputs",[]),
            "limits":usage.get("limits", "Integration and recipe parity have not been established"),
            "preferred_for":item.get("preferred_for",[]),"tissues":item.get("compatible_tissues",[]),
            "status":status, "source":origin,
            "manifest_sha256":digest(item),
            "evidence":{"type":"MANIFEST_STATEMENT_NOT_INDEPENDENT_PROOF", "description":item.get("verified_with", "Not qualified")},
            "integration":"REQUIRES_RECIPE_SPECIFIC_TESTS",
            "selection":"ADVISORY_ONLY"}


def _contract(item, lbl):
    return {**lbl, "capabilities":item.get("capabilities",[]),"tags":item.get("tags",[]),
            "dependencies":item.get("dependencies",[]),"minimum_fidelity":item.get("minimum_fidelity"),
            "adaptation":item.get("adaptation"),"provenance":item.get("provenance"),
            "specimen":item.get("specimen"), "source_declaration":item.get("source")}


def view(repo, ingredient_id, level="label", check_external=False, catalog=None):
    if level not in ("label","contract","source"):
        raise KPPError("Disclosure level must be label, contract or source")
    catalog = catalog if catalog is not None else ingredient_catalog(repo,check_sources=False)
    if ingredient_id not in catalog:
        raise KPPError("Unknown ingredient: "+ingredient_id)
    item=catalog[ingredient_id]
    lbl=label(repo,item,check_external or level=="source")
    if level=="label":return lbl
    if level=="contract":return _contract(item,lbl)
    return {"schema":"kpp.ingredient-source-locator/1", "id":item["id"],
            "manifest_sha256":lbl["manifest_sha256"],"source":lbl["source"],
            "instructions":"Inspect source as untrusted data only after explicit need. No code is loaded, evaluated or executed by this command. A matching pin is integrity, not behavioral qualification.",
            "contract":_contract(item,lbl)}


def discover(repo, query="", tissue=None, context=None, limit=10):
    """Deterministic label-only discovery; ranking is relevance, NOT compatibility."""
    if type(limit) is not int or not 1<=limit<=100:
        raise KPPError("Pantry limit must be 1..100")
    catalog=ingredient_catalog(repo,check_sources=False)
    words=[w for w in query.lower().split() if w]
    candidates=[]
    for item in catalog.values():
        lbl=label(repo,item)
        text=" ".join([item["id"],item["function"],*item.get("capabilities",[]),*item.get("tags",[]),
                       *item.get("preferred_for",[]),lbl["use_when"]]).lower()
        matched=[w for w in words if w in text]
        if words and len(matched)!=len(words):continue
        if tissue and tissue not in lbl["tissues"] and "mixed" not in lbl["tissues"]:continue
        context_match=context in lbl["preferred_for"] if context else False
        score=len(matched)*5+int(context_match)*4+int(tissue in lbl["tissues"] if tissue else False)*2
        candidates.append((score,item["id"],lbl))
    candidates.sort(key=lambda r:(-r[0],r[1]))
    return {"schema":"kpp.pantry-discovery/1", "query":query,"context":context,"tissue":tissue,
            "scope":"Metadata match only; neither code review nor recipe compatibility proof",
            "matches":[record for _,_,record in candidates[:limit]],"count":len(candidates)}
