"""Bounded, read-only Qt declarations and pinned GUI coverage; no execution."""
import hashlib
import re
from collections import Counter
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

from .core import KPPError, SLUG, digest, read_json

HEX = re.compile(r"[a-f0-9]{64}")
DISPOSITIONS = {"required", "deferred", "unknown", "unsupported", "excluded"}
KINDS = {"widget", "action", "action-group", "action-placement", "connection", "tab-order"}


def relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise KPPError("GUI evidence needs a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in (".", "..") for p in value.split("/")):
        raise KPPError("GUI evidence needs a safe relative path")
    return value


def text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048


def validate_contract(recipe):
    contract = recipe.get("reference_gui")
    if contract is None:
        return
    if not isinstance(contract, dict) or set(contract) != {"inventory", "coverage_anchor", "source_root"}:
        raise KPPError("reference_gui needs inventory, source_root and coverage_anchor")
    relative_path(contract["source_root"])
    pin = contract["inventory"]
    if not isinstance(pin, dict) or set(pin) != {"path", "sha256"}:
        raise KPPError("GUI inventory needs path and canonical JSON SHA-256")
    relative_path(pin["path"])
    if not pin["path"].startswith("references/") or not isinstance(pin["sha256"], str) or not HEX.fullmatch(pin["sha256"]):
        raise KPPError("GUI inventory needs references/ path and SHA-256")
    mandatory = {a["id"] for a in recipe["anchors"] if a["required"]}
    if not isinstance(contract["coverage_anchor"], str) or contract["coverage_anchor"] not in mandatory:
        raise KPPError("GUI coverage must link to a mandatory Anchor")
    target = recipe["target"]
    if not text(target.get("source")) or not isinstance(target.get("reference_version"), str) or not HEX.fullmatch(target["reference_version"]):
        raise KPPError("GUI target requires source identity and content snapshot revision")


def validate_inventory(obj, recipe=None):
    if not isinstance(obj, dict) or obj.get("schema") != "kpp.gui-inventory/2":
        raise KPPError("Unsupported GUI inventory schema")
    source = obj.get("source")
    if not isinstance(source, dict) or set(source) != {"identity", "revision", "files"} or not text(source["identity"]):
        raise KPPError("GUI inventory needs a content-pinned source")
    files = source["files"]
    if not isinstance(files, dict) or not files or len(files) > 256:
        raise KPPError("GUI source inventory must contain 1..256 files")
    for path, checksum in files.items():
        relative_path(path)
        if not path.endswith(".ui") or not isinstance(checksum, str) or not HEX.fullmatch(checksum):
            raise KPPError("Invalid Qt source file pin")
    if source["revision"] != digest(files):
        raise KPPError("GUI source revision disagrees with file pins")
    entries = obj.get("entries")
    unknowns = obj.get("uninspected")
    if not isinstance(unknowns, list) or not unknowns or any(not text(x) for x in unknowns):
        raise KPPError("Static GUI inventory must disclose uninspected runtime contexts")
    if not isinstance(entries, list) or not entries or len(entries) > 10000:
        raise KPPError("GUI inventory must contain 1..10000 entries")
    mandatory = {a["id"] for a in recipe["anchors"] if a["required"]} if recipe else None
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict) or not text(entry.get("id")) or entry["id"] in ids:
            raise KPPError("Invalid/duplicate GUI entry id")
        ids.add(entry["id"])
        if set(entry) & {"status", "represented", "functional", "tested", "accepted"}:
            raise KPPError("Stage labels and acceptance cannot be inventory status; use independent source-bound observations")
        if entry.get("kind") not in KINDS or entry.get("disposition") not in DISPOSITIONS or entry.get("observation") != "static":
            raise KPPError("Invalid GUI kind/disposition/observation")
        if entry.get("file") not in files or not text(entry.get("path")) or not text(entry.get("label")):
            raise KPPError("GUI entry missing source locator/label")
        if type(entry.get("depth")) is not int or not 1 <= entry["depth"] <= 32:
            raise KPPError("GUI entry needs behavioral depth in 1..32")
        links = entry.get("anchor_ids")
        if not isinstance(links, list) or any(not isinstance(x, str) or not SLUG.fullmatch(x) for x in links) or len(set(links)) != len(links):
            raise KPPError("Invalid GUI Anchor links")
        if mandatory is not None and any(x not in mandatory for x in links):
            raise KPPError("GUI entries must link to existing mandatory Anchors")
        if entry["disposition"] == "excluded":
            approval = entry.get("scope_approval")
            if not isinstance(approval, dict) or set(approval) != {"baker", "evidence"} or not all(text(x) for x in approval.values()):
                raise KPPError("GUI exclusion needs explicit Baker scope attestation")
    if recipe:
        target = recipe["target"]
        if source["identity"] != target["source"] or source["revision"] != target["reference_version"]:
            raise KPPError("GUI inventory and Chase target source pins disagree")
        if digest(obj) != recipe["reference_gui"]["inventory"]["sha256"]:
            raise KPPError("GUI inventory pin mismatch: new recipe/workspace required")
    return obj


def scan_qt(source, identity):
    """Compatibility entry point over canonical SCAN interface extraction."""
    import time
    from ..scan.discovery import scan_qt as native
    try:
        return native(source, identity, deadline=time.monotonic() + 30)
    except (ValueError, OSError) as error:
        raise KPPError(str(error)) from error


def read_inventory(recipe, repo):
    if "reference_gui" not in recipe:
        return None
    root = Path(repo).resolve()
    path = root / recipe["reference_gui"]["inventory"]["path"]
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file() or path.stat().st_size > 5_000_000:
        raise KPPError("Missing/unsafe/oversized GUI inventory")
    inventory=validate_inventory(read_json(path), recipe)
    source_path=root/recipe["reference_gui"]["source_root"]
    if source_path.is_symlink() or not source_path.resolve().is_relative_to(root):
        raise KPPError("Unsafe GUI source root")
    from .scanner import scan
    observed = scan(source_path, filters=['interface'], identity=inventory['source']['identity'],
                    max_files=1000, max_bytes=2_000_000)['interface_inventory']
    if observed is None:
        raise KPPError('Interface inventory requires .ui files with supported declarations')
    if observed["source"] != inventory["source"]:
        raise KPPError("GUI source bytes changed; revise source/recipe pins")
    fields=("id", "kind", "file", "path", "label", "class", "shortcut", "properties", "observation", "confidence", "declaration")
    def projection(entries):
        return {e["id"]:{key:e.get(key) for key in fields} for e in entries}
    if projection(observed["entries"]) != projection(inventory["entries"]):
        raise KPPError("GUI inventory omitted or changed discovered declarations")
    return inventory


def coverage(inventory, accepted=()):
    """Accountability over the observed surface; labels do not prove behavior."""
    excluded = [e for e in inventory["entries"] if e["disposition"] == "excluded"]
    required = [e for e in inventory["entries"] if e["disposition"] != "excluded"]
    unaccounted = [e["id"] for e in required if not e["anchor_ids"]]
    return {"schema": "kpp.gui-coverage/1", "source": inventory["source"],
            "observed_entries": len(inventory["entries"]),
            "by_kind": dict(sorted(Counter(e["kind"] for e in inventory["entries"]).items())),
            "by_disposition": dict(sorted(Counter(e["disposition"] for e in inventory["entries"]).items())),
            "by_observation": {"static": len(inventory["entries"])},
            "unaccounted": unaccounted, "accounted_for": not unaccounted,
            "scope_exclusions": [{"id": e["id"], "attestation": e["scope_approval"]} for e in excluded],
            "unaccepted_entries": [e["id"] for e in required if not e["anchor_ids"] or not all(a in accepted for a in e["anchor_ids"])],
            "uninspected": inventory["uninspected"],
            "visual_conformance": "NOT_MEASURED", "runtime_behavior": "NOT_OBSERVED",
            "scope": "Inventory coverage of static declarations only; not exhaustive GUI discovery or parity"}
