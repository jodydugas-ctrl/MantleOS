"""Byte-bound evidence envelopes. Hash consistency is not provider authenticity."""
import copy
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import tokenize
from .common import ScanError, canonical, digest, identity, sha, source_paths
from .investigator import _report
from .providers import HEX, fields, relative

SCHEMA = "scan.evidence/1"
CLASSES = {"STATIC_SYNTAX", "INFERRED_STATIC_BINDING", "RUNTIME_OBSERVED", "UNKNOWN"}
SCOPE = "Reference and receipt consistency only; no provider authenticity, behavior equivalence or promotion authority"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ScanError("Invalid evidence timestamp")
    try: result = datetime.fromisoformat(value)
    except ValueError as error: raise ScanError("Invalid evidence timestamp") from error
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ScanError("Evidence timestamps must specify UTC")
    return result


def provider(value):
    fields(value, ("name", "version", "revision"))
    for key in ("name", "version"):
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 200:
            raise ScanError("Evidence provider identity missing")
    if not isinstance(value["revision"], str) or not HEX.fullmatch(value["revision"]):
        raise ScanError("Evidence provider revision must be hash-bound")


def context(report):
    graph = _report(report)
    if len(graph["files"]) > 1000:
        raise ScanError("Evidence inventory file budget exceeded")
    inventory = []
    paths = set()
    for entry in graph["files"]:
        path = relative(entry["path"])
        if path in paths: raise ScanError("Duplicate evidence inventory path")
        paths.add(path)
        value = entry.get("sha256")
        if value is not None and (not isinstance(value, str) or not HEX.fullmatch(value)):
            raise ScanError("Invalid source inventory hash")
        inventory.append([path, value, entry["status"]])
    root = report.get("source_root")
    if not isinstance(root, str) or not Path(root).is_absolute():
        raise ScanError("Evidence requires an absolute source root")
    body = {"schema": "scan.context/1", "source_root": str(Path(root).resolve()),
            "graph_sha256": report["graph_digest"], "inventory_sha256": digest(inventory)}
    return dict(body, id="context:" + digest(body))


def seal(body):
    if len(canonical(body).encode("utf-8")) > 8_000_000:
        raise ScanError("Evidence envelope byte budget exceeded")
    return dict(body, id="evidence:" + digest(body))


def base(report, evidence_class, method, provider_identity, *, parents=(), created_at=None, validity_seconds=86400):
    if evidence_class not in CLASSES or method not in ("core-static-export", "untrusted-provider-capture", "controlled-observation"):
        raise ScanError("Unknown evidence class or method")
    if type(validity_seconds) is not int or not 1 <= validity_seconds <= 30 * 86400:
        raise ScanError("Evidence validity must be 1 second to 30 days")
    provider(provider_identity)
    if not isinstance(parents, (list, tuple)) or len(parents) > 16 or len(set(parents)) != len(parents) or any(
            not isinstance(value, str) or not value.startswith("evidence:") or not HEX.fullmatch(value[9:]) for value in parents):
        raise ScanError("Invalid evidence lineage parents")
    created = timestamp(created_at or utc_now())
    ctx = context(report)
    return {"schema": SCHEMA, "target_sha256": ctx["inventory_sha256"], "evidence_class": evidence_class,
            "provider": copy.deepcopy(provider_identity), "method": method, "context": ctx,
            "lineage": {"schema": "scan.lineage/1", "parent_ids": list(parents)},
            "created_at": created.isoformat(timespec="seconds"),
            "expires_at": (created + timedelta(seconds=validity_seconds)).isoformat(timespec="seconds"),
            "assertions": [], "source_spans": [], "limitations": [SCOPE]}


def static_evidence(report, node_ids=(), edge_ids=(), **kwargs):
    graph = _report(report)
    if not isinstance(node_ids, (list, tuple)) or not isinstance(edge_ids, (list, tuple)) or not 1 <= len(node_ids) + len(edge_ids) <= 1000:
        raise ScanError("Select 1-1000 source records for the evidence dossier")
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {edge["id"]: edge for edge in graph["edges"]}
    if any(value not in nodes for value in node_ids) or any(value not in edges for value in edge_ids):
        raise ScanError("Unknown evidence record reference")
    if len(set(node_ids)) != len(node_ids) or len(set(edge_ids)) != len(edge_ids):
        raise ScanError("Duplicate evidence record selection")
    classes = {"STATIC_SYNTAX"}
    assertions, referenced = [], set(node_ids)
    for nid in node_ids:
        node = nodes[nid]
        if node.get("evidence") != "STATIC_SYNTAX":
            raise ScanError("Static source records cannot claim runtime observation")
        assertions.append({"record_type": "node", "evidence_class": "STATIC_SYNTAX", "record": copy.deepcopy(node)})
    for eid in edge_ids:
        edge = edges[eid]
        klass = edge_class(edge)
        classes.add(klass)
        assertions.append({"record_type": "edge", "evidence_class": klass, "record": copy.deepcopy(edge)})
        referenced.update((edge["src"], edge["dst"]))
        if edge.get("occurrence"): referenced.add(edge["occurrence"])
    klass = "INFERRED_STATIC_BINDING" if "INFERRED_STATIC_BINDING" in classes else "STATIC_SYNTAX"
    body = base(report, klass, "core-static-export", core_provider(graph), **kwargs)
    body["assertions"] = assertions
    body["source_spans"] = spans([nodes[nid] for nid in sorted(referenced)])
    return seal(body)


def core_provider(graph):
    return {"name": "mantleos-static", "version": "scan.report/1",
            "revision": digest([graph.get("adapter_revisions", {}), sha(Path(__file__).read_bytes())])}


def edge_class(edge):
    mapping = {"contains": "STATIC_SYNTAX", "inside_loop": "STATIC_SYNTAX", "possible_call": "INFERRED_STATIC_BINDING",
               "possible_import": "INFERRED_STATIC_BINDING"}
    if edge.get("kind") not in mapping: raise ScanError("Unknown evidence relationship kind")
    klass = mapping[edge["kind"]]
    expected = {"contains": "STATIC_SYNTAX", "inside_loop": "STATIC_SYNTAX", "possible_call": "INFERRED_STATIC_BINDING",
                "possible_import": "INFERRED_PATH_BINDING"}[edge["kind"]]
    if edge.get("evidence") != expected: raise ScanError("Relationship evidence class mismatch")
    return klass


def spans(nodes):
    result = []
    for node in nodes:
        if not isinstance(node.get("source_sha256"), str) or not HEX.fullmatch(node["source_sha256"]):
            raise ScanError("Source record is not byte-bound")
        line, end = node.get("line"), node.get("end_line")
        if (line is None) != (end is None) or (line is not None and (type(line) is not int or type(end) is not int or not 1 <= line <= end)):
            raise ScanError("Invalid evidence source span")
        result.append({"path": relative(node["path"]), "line_start": line, "line_end": end,
                       "source_sha256": node["source_sha256"], "node_id": node["id"]})
    if len(result) > 100: raise ScanError("Evidence source span budget exceeded (100)")
    return result


def external_evidence(report, observation, provider_identity, **kwargs):
    if len(canonical(observation).encode()) > 1_000_000:
        raise ScanError("External observation byte budget exceeded")
    body = base(report, "UNKNOWN", "untrusted-provider-capture", provider_identity, **kwargs)
    body["assertions"] = [{"record_type": "unknown", "evidence_class": "UNKNOWN", "observation": copy.deepcopy(observation)}]
    body["limitations"].append("Provider narratives, proposed commands and claimed runtime classes are inert unverified data.")
    return seal(body)


def source_bytes(root, path, expected):
    relative(path)
    raw = Path(root) / path
    target = raw.resolve()
    if raw.is_symlink() or not target.is_relative_to(Path(root).resolve()) or target != raw.absolute():
        raise ScanError("Evidence source path redirected or escaped its root")
    before = target.stat()
    if before.st_size > 2_000_000: raise ScanError("Evidence source byte budget exceeded")
    with target.open("rb") as stream: data = stream.read(2_000_001)
    after = target.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or len(data) > 2_000_000 or sha(data) != expected:
        raise ScanError("Evidence source bytes changed or mismatch")
    return data


def _verify(receipt, report, source_root, *, now=None, parent_ids=(), runtime_receipts=None, authorized_runs=None):
    fields(receipt, ("schema", "id", "target_sha256", "evidence_class", "provider", "method", "context", "lineage",
                     "created_at", "expires_at", "assertions", "source_spans", "limitations"), ("runtime_receipt_id",))
    body = {key: value for key, value in receipt.items() if key != "id"}
    if receipt["schema"] != SCHEMA or seal(body)["id"] != receipt["id"]:
        raise ScanError("Evidence envelope identity mismatch")
    ctx = context(report)
    if receipt["context"] != ctx or str(Path(source_root).resolve()) != ctx["source_root"] or receipt["target_sha256"] != ctx["inventory_sha256"]:
        raise ScanError("Evidence context or source location mismatch; relocate only by explicit rescan")
    provider(receipt["provider"])
    fields(receipt["lineage"], ("schema", "parent_ids"))
    parents = receipt["lineage"]["parent_ids"]
    if receipt["lineage"]["schema"] != "scan.lineage/1" or not isinstance(parents, list) or len(parents) > 16 or parents != list(parent_ids):
        raise ScanError("Evidence lineage is not bound to the expected parents")
    if len(set(parents)) != len(parents) or any(not isinstance(value, str) or not value.startswith("evidence:") or not HEX.fullmatch(value[9:]) for value in parents):
        raise ScanError("Invalid evidence lineage identity")
    created, expiry, current = timestamp(receipt["created_at"]), timestamp(receipt["expires_at"]), timestamp(now or utc_now())
    if not created <= current < expiry or not timedelta(0) < expiry - created <= timedelta(days=30):
        raise ScanError("Evidence expired, future-dated or outside its validity budget")
    klass = receipt["evidence_class"]
    if not isinstance(klass, str) or klass not in CLASSES: raise ScanError("Unknown evidence class")
    assertions, locations, limitations = receipt["assertions"], receipt["source_spans"], receipt["limitations"]
    if not isinstance(assertions, list) or not 1 <= len(assertions) <= 1000 or not isinstance(locations, list) or len(locations) > 100:
        raise ScanError("Evidence assertion/span budget exceeded")
    if not isinstance(limitations, list) or not 1 <= len(limitations) <= 100 or SCOPE not in limitations or any(
            not isinstance(item, str) or len(item) > 2000 for item in limitations):
        raise ScanError("Evidence limitations must preserve the verification scope")
    graph = _report(report)
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {edge["id"]: edge for edge in graph["edges"]}
    inventory = {entry["path"]: entry for entry in graph["files"]}
    if klass == "RUNTIME_OBSERVED":
        from .observations import verify_observation
        if receipt["method"] != "controlled-observation" or not isinstance(runtime_receipts, dict) or not isinstance(authorized_runs, dict):
            raise ScanError("Runtime claims need an independently authorized local observation receipt")
        run_id = receipt.get("runtime_receipt_id")
        if not isinstance(run_id, str) or run_id not in runtime_receipts or run_id not in authorized_runs:
            raise ScanError("Runtime receipt is not independently authorized")
        run = runtime_receipts[run_id]
        verify_observation(run, report, source_root, expected_sha256=authorized_runs[run_id])
        if run["run_id"] != run_id or timestamp(run["finished_at"]) > created:
            raise ScanError("Runtime observation identity/time differs from its envelope")
        expected = [{"record_type": "runtime", "evidence_class": "RUNTIME_OBSERVED", "observation": run["result"]}]
        if assertions != expected or locations or receipt["provider"] != run["provider"]:
            raise ScanError("Runtime assertions extend beyond the authorized observation")
    elif klass == "UNKNOWN":
        if receipt["method"] != "untrusted-provider-capture" or len(assertions) != 1 or locations or "runtime_receipt_id" in receipt:
            raise ScanError("Unknown provider captures cannot carry observation authority")
        fields(assertions[0], ("record_type", "evidence_class", "observation"))
        if assertions[0]["record_type"] != "unknown" or assertions[0]["evidence_class"] != "UNKNOWN" or len(canonical(assertions[0]["observation"]).encode()) > 1_000_000:
            raise ScanError("Invalid unknown provider capture")
    else:
        if receipt["method"] != "core-static-export" or "runtime_receipt_id" in receipt or receipt["provider"] != core_provider(graph):
            raise ScanError("Static receipt method/provider mismatch")
        node_ids, edge_ids = [], []
        for assertion in assertions:
            fields(assertion, ("record_type", "evidence_class", "record"))
            record = assertion["record"]
            if assertion["record_type"] == "node":
                if not isinstance(record, dict) or record.get("id") not in nodes or record != nodes[record["id"]] or record.get("evidence") != "STATIC_SYNTAX" or assertion["evidence_class"] != "STATIC_SYNTAX":
                    raise ScanError("Evidence syntax assertion differs from its source graph")
                node_ids.append(record["id"])
            elif assertion["record_type"] == "edge":
                if not isinstance(record, dict) or record.get("id") not in edges or record != edges[record["id"]] or assertion["evidence_class"] != edge_class(record):
                    raise ScanError("Evidence relationship assertion differs from its source graph")
                edge_ids.append(record["id"])
            else: raise ScanError("Unadmitted static assertion type")
        expected = static_evidence(report, node_ids, edge_ids, created_at=receipt["created_at"],
                                   validity_seconds=int((expiry - created).total_seconds()), parents=parents)
        if locations != expected["source_spans"] or klass != expected["evidence_class"]:
            raise ScanError("Evidence spans or aggregate class differ from referenced records")
    # Check every hashed file in the declared snapshot, not just the selected
    # lines. Files outside the scanner's declared coverage remain UNKNOWN.
    total = 0
    file_bytes = {}
    if graph["scope"].get("inventory_exhausted_within_exclusions") is True:
        current_paths = set()
        for path in source_paths(source_root):
            current_paths.add(path.relative_to(Path(source_root).resolve()).as_posix())
            if len(current_paths) > 1000: raise ScanError("Evidence current inventory budget exceeded")
        if current_paths != set(inventory):
            raise ScanError("Evidence file inventory changed; rescan required")
    for entry in inventory.values():
        if entry.get("sha256") is None: continue
        data = source_bytes(source_root, entry["path"], entry["sha256"])
        total += len(data)
        if total > 64_000_000: raise ScanError("Evidence snapshot byte budget exceeded")
        if any(span["path"] == entry["path"] for span in locations): file_bytes[entry["path"]] = data
    # Recompute node identities from exact bytes and per-file extraction order.
    ordinals = {}
    for node in graph["nodes"]:
        path = relative(node["path"])
        ordinal = ordinals.get(path, 0)
        entry = inventory.get(path)
        if entry is None or not entry.get("sha256") or node.get("source_sha256") != entry["sha256"] or node.get("evidence") != "STATIC_SYNTAX":
            raise ScanError("Graph syntax evidence is not bound to its inventoried bytes")
        attrs = node["attributes"]
        if attrs.get("analysis_origin") == "optional-provider":
            if graph.get("node_identity_scheme") != "scan.native-plus-specialist/1":
                raise ScanError("Specialist node identity scheme missing")
            provider_ordinal = attrs.get("provider_record_ordinal")
            specialist_provider = entry.get("provider")
            if (type(provider_ordinal) is not int or not 1 <= provider_ordinal < 12000 or
                    not isinstance(specialist_provider,dict) or attrs.get("provider") != specialist_provider):
                raise ScanError("Specialist source identity not bound to its provider")
            original = identity("node",path,node["source_sha256"],node["kind"],node["line"],provider_ordinal)
            expected_identity = identity("node-provider",specialist_provider,original)
        else:
            ordinals[path] = ordinal + 1
            expected_identity = identity("node",path,node["source_sha256"],node["kind"],node["line"],ordinal)
        if node["id"] != expected_identity:
            raise ScanError("Source node identity mismatch")
    for span in locations:
        fields(span, ("path", "line_start", "line_end", "source_sha256", "node_id"))
        if span["path"] not in file_bytes or span["source_sha256"] != inventory[span["path"]]["sha256"]:
            raise ScanError("Evidence span byte binding mismatch")
        if span["line_start"] is not None:
            data = file_bytes[span["path"]]
            if inventory[span["path"]]["family"] == "python":
                encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
                text = data.decode(encoding)
            else: text = data.decode("utf-8-sig")
            if not 1 <= span["line_start"] <= span["line_end"] <= len(text.splitlines()) + 1:
                raise ScanError("Evidence source line span exceeds captured bytes")
    return {"schema": "scan.evidence-verification/1", "result": "PASS", "evidence_id": receipt["id"],
            "evidence_class": klass, "scope": SCOPE, "provider_authenticity": "NOT_ESTABLISHED",
            "unhashed_inventory_files": sum(entry.get("sha256") is None for entry in inventory.values()),
            "behavioral_equivalence": "UNKNOWN", "promotion_authority": False}


def verify_evidence(receipt, report, source_root, **kwargs):
    try: return _verify(receipt, report, source_root, **kwargs)
    except ScanError: raise
    except (OSError, KeyError, TypeError, AttributeError, ValueError, RecursionError, IndexError) as error:
        raise ScanError("Malformed or unavailable evidence: " + str(error)[:300]) from error


def migrate_evidence(receipt):
    # The earlier proposal was never an accepted receipt. No default values can
    # supply missing source context, timestamps or runtime authorization.
    if not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA or "context" not in receipt:
        raise ScanError("Unsupported/unbound evidence; create a new source-bound receipt by explicit rescan")
    return copy.deepcopy(receipt)
