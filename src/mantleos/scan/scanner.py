"""Incremental extraction, with fresh graph binding on every source snapshot."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from .adapters import adapter_revision, extract
from .common import EXCLUDES, ScanError, canonical, digest, identity, outside, sha, source_paths, write_json
from .graph import graph_metrics
from .registry import Registry, select_filters, source_filter


class Cache:
    def __init__(self, workspace):
        Path(workspace).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(Path(workspace) / "analysis.sqlite")
        self.db.execute("CREATE TABLE IF NOT EXISTS analysis (key TEXT PRIMARY KEY, body TEXT NOT NULL, sha TEXT NOT NULL, touched REAL NOT NULL)")

    def get(self, key):
        row = self.db.execute("SELECT body, sha FROM analysis WHERE key=?", (key,)).fetchone()
        if row and len(row[0]) <= 15_000_000 and sha(row[0].encode()) == row[1]:
            try:
                value = json.loads(row[0])
                if isinstance(value.get("nodes"), list) and isinstance(value.get("edges"), list):
                    self.db.execute("UPDATE analysis SET touched=? WHERE key=?", (time.time(), key))
                    return value
            except (ValueError, AttributeError):
                pass
        return None

    def put(self, key, value):
        body = canonical(value)
        self.db.execute("INSERT OR REPLACE INTO analysis VALUES (?,?,?,?)", (key, body, sha(body.encode()), time.time()))

    def close(self):
        # Bound retained history by entry count and encoded record size, not just age.
        self.db.execute("DELETE FROM analysis WHERE key NOT IN (SELECT key FROM analysis ORDER BY touched DESC LIMIT 2000)")
        total = 0
        for key, size in self.db.execute("SELECT key, length(CAST(body AS BLOB)) FROM analysis ORDER BY touched DESC").fetchall():
            total += size
            if total > 64_000_000:
                self.db.execute("DELETE FROM analysis WHERE key=?", (key,))
        self.db.commit()
        self.db.close()


def connect_graph(nodes):
    """Rebind relationships from current records; never reuse old cross-file edges."""
    modules = {n["path"]: n["id"] for n in nodes if n["kind"] == "module"}
    top_functions = defaultdict(list)
    for n in nodes:
        if n["kind"] == "function" and n["owner"] == modules.get(n["path"]) and n["attributes"].get("analysis_origin") != "optional-provider":
            top_functions[(n["path"], n["name"])].append(n["id"])
    edges = []
    for n in nodes:
        if n["kind"] == "call" and not n["attributes"].get("shadowed", True):
            targets = top_functions[(n["path"], n["name"])]
            if len(targets) == 1:
                edges.append({"id": identity("edge", n["id"], targets[0]), "src": n["owner"], "dst": targets[0],
                              "occurrence": n["id"], "kind": "possible_call", "evidence": "INFERRED_STATIC_BINDING"})
        if n["kind"] == "import":
            name = n["attributes"].get("module", "")
            if n["path"].endswith((".py", ".pyi", ".pyw")):
                level = n["attributes"].get("level", 0)
                parent = Path(n["path"]).parent
                if level:
                    for _ in range(level - 1): parent = parent.parent
                    base = parent / name.replace(".", "/")
                else:
                    base = Path(name.replace(".", "/"))
                candidates = [str(base).replace("\\", "/") + ".py", (base / "__init__.py").as_posix()]
            elif name.startswith("."):
                base = os.path.normpath(str(Path(n["path"]).parent / name)).replace("\\", "/")
                candidates = [base] + [base + x for x in (".ts", ".tsx", ".js", ".jsx")] + [base + "/index.ts", base + "/index.js"]
            else:
                candidates = []
            for path in candidates:
                if path in modules:
                    edges.append({"id": identity("edge", n["id"], modules[path]), "src": modules[n["path"]], "dst": modules[path],
                                  "occurrence": n["id"], "kind": "possible_import", "evidence": "INFERRED_PATH_BINDING"})
                    break
    return edges


def scan(root, workspace, *, node=None, provider_policy=None, allow_external=False, max_files=1000, max_bytes=16_000_000, max_file_bytes=512_000, max_seconds=60, max_nodes=100000, filters=None, execution='serial'):
    root, workspace = Path(root).resolve(), Path(workspace).resolve()
    if not root.is_dir(): raise ScanError("Source must be a directory")
    outside(workspace, root)
    if any(type(v) is not int or v <= 0 for v in (max_files, max_bytes, max_file_bytes, max_seconds, max_nodes)):
        raise ScanError("Scan limits must be positive integers")
    if max_files > 1000 or max_file_bytes > 2_000_000 or max_bytes > 64_000_000 or max_nodes > 500000:
        raise ScanError("Requested limits exceed this release's bounded profile")
    selected = select_filters(filters)
    if execution not in ('serial', 'parallel'):
        raise ScanError('Unsupported scan execution mode')
    from .providers import Providers
    providers = Providers(provider_policy, allow_external=allow_external, source=root)
    registry, cache = Registry(workspace), Cache(workspace)
    started = time.monotonic()
    inventory, facts, gaps, jobs = [], {}, [], []
    enhancement_jobs = []
    enhancement_hits, enhancement_misses, enhancement_attempts = 0, 0, 0
    total, hits, misses = 0, 0, 0
    revisions = {}
    stopped = False
    admitted = 0
    def admit(entry, value):
        nonlocal admitted
        count = len(value["nodes"]) + len(value["edges"])
        if admitted + count > max_nodes:
            entry["status"] = "LIMIT"
            gaps.append({"path": entry["path"], "reason": "Combined graph record budget"})
            return False
        admitted += count
        facts[entry["path"]] = value
        return True
    try:
        for path in source_paths(root):
            if len(inventory) >= max_files or time.monotonic() - started >= max_seconds:
                stopped = True
                gaps.append({"path": "*", "reason": "Inventory stopped at file/time budget; remainder uninspected"})
                break
            relative = path.relative_to(root).as_posix()
            family = registry.family(path)
            entry = {"path": relative, "family": family, "sha256": None, "status": "INVENTORIED"}
            inventory.append(entry)
            try:
                before = path.stat()
                entry["bytes"] = before.st_size
                if before.st_size > max_file_bytes or total + before.st_size > max_bytes:
                    entry["status"] = "LIMIT"
                    gaps.append({"path": relative, "reason": "Source byte budget; contents not inspected"})
                    continue
                with path.open("rb") as stream: data = stream.read(max_file_bytes + 1)
                after = path.stat()
                if len(data) > max_file_bytes or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ScanError("Source changed while being read, or exceeds byte budget")
                total += len(data)
                entry["sha256"] = sha(data)
                if source_filter(family) not in selected:
                    entry["status"] = "FILTERED"
                    continue
                if family == "inventory":
                    entry["status"] = "UNSUPPORTED"
                    gaps.append({"path": relative, "reason": "No qualified syntax adapter; use research or map a compatible extension"})
                    continue
                if family not in revisions:
                    revisions[family] = adapter_revision(family)
                if family == "typescript" and providers.config is not None:
                    enhancement_jobs.append((entry,data))
                elif family == "typescript" and allow_external:
                    entry["enhancement_status"] = "UNAVAILABLE"
                    gaps.append({"path":relative,"reason":providers.error})
                key = digest([relative, entry["sha256"], revisions[family]])
                value = cache.get(key)
                if value:
                    hits += 1
                    admit(entry, value)
                else:
                    misses += 1
                    jobs.append((entry, data, key))
            except (OSError, ValueError) as exc:
                entry["status"] = "ERROR"
                gaps.append({"path": relative, "reason": str(exc)[:500]})
        def extract_job(job):
            entry, data, _ = job
            if time.monotonic() - started >= max_seconds:
                return None, 'Extraction time budget'
            try:
                value = extract(entry['path'], data, entry['family'], deadline=started + max_seconds)
                if time.monotonic() - started >= max_seconds:
                    return None, 'Extraction time budget'
                return value, None
            except (ValueError, SyntaxError, RecursionError, UnicodeError, MemoryError) as exc:
                return None, type(exc).__name__ + ': ' + str(exc)[:300]

        # Only captured-byte extraction runs in workers. Cache access and graph
        # admission stay on the owning thread, in deterministic inventory order.
        pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='scan') if execution == 'parallel' else None
        try:
            results = pool.map(extract_job, jobs) if pool else map(extract_job, jobs)
            for (entry, data, key), (value, error) in zip(jobs, results):
                if error:
                    entry['status'] = 'LIMIT' if error == 'Extraction time budget' else 'ERROR'
                    gaps.append({'path': entry['path'], 'reason': error})
                else:
                    admit(entry, value)
                    cache.put(key, value)
        finally:
            if pool:
                pool.shutdown(wait=True, cancel_futures=True)
        # Admit the native graph first. Optional records cannot consume its budget
        # or replace its evidence, even when an enhancement fails.
        native_nodes = [node for entry in inventory for node in facts.get(entry['path'],{}).get('nodes',[])]
        native_derived = connect_graph(native_nodes)[:max(0,max_nodes - admitted)]
        if enhancement_jobs: revisions["typescript-specialist"] = providers.revision
        from .providers import enhance
        for entry,data in enhancement_jobs:
            native = facts.get(entry["path"])
            if native is None: continue
            try:
                remaining = max_seconds - (time.monotonic() - started)
                if remaining <= 0: raise ScanError("Provider extraction time budget")
                key = digest(["specialist",entry["path"],entry["sha256"],providers.revision])
                specialist = cache.get(key)
                if specialist is None:
                    enhancement_misses += 1; enhancement_attempts += 1
                    specialist = providers.extract(entry["path"],data,timeout=min(30,remaining))
                    cache.put(key,specialist)
                else: enhancement_hits += 1
                value = enhance(native,specialist)
                extra = len(value["nodes"]) + len(value["edges"]) - len(native["nodes"]) - len(native["edges"])
                if admitted + len(native_derived) + extra > max_nodes: raise ScanError("Optional enhancement exceeds remaining graph budget; native records retained")
                admitted += extra; facts[entry["path"]] = value
                entry["enhancement_status"] = "APPLIED"
            except (ValueError,OSError,UnicodeError,RecursionError,KeyError,subprocess.TimeoutExpired) as exc:
                entry["enhancement_status"] = "UNAVAILABLE"
                gaps.append({"path":entry["path"],"reason":"Native fallback retained; optional provider: " + str(exc)[:400]})
    finally:
        cache.close()
    nodes, edges = [], []
    for entry in inventory:
        value = facts.get(entry["path"])
        if value:
            if len(nodes) + len(value["nodes"]) > max_nodes:
                entry["status"] = "LIMIT"
                gaps.append({"path": entry["path"], "reason": "Graph record budget"})
                continue
            entry["status"] = value["coverage"]
            entry["limitations"] = value.get("gaps", [])
            if entry["family"] in ("anchor", "typescript", "pe", "interface"):
                gaps.extend({"path": entry["path"], "reason": reason} for reason in entry["limitations"])
            if "provider" in value:
                entry["provider"] = value["provider"]
                entry["enhancement_coverage"] = value["enhancement_coverage"]
            nodes.extend(value["nodes"])
            edges.extend(value["edges"])
    native_edge_ids = {edge['id'] for edge in native_derived}
    derived = native_derived + [edge for edge in connect_graph(nodes) if edge['id'] not in native_edge_ids]
    remaining = max(0, max_nodes - len(nodes) - len(edges))
    if len(derived) > remaining:
        gaps.append({"path": "*", "reason": "Inferred relationships truncated by combined graph record budget"})
    edges.extend(derived[:remaining])
    graph = {"schema": "scan.graph/1", "files": inventory, "nodes": nodes, "edges": edges, "gaps": gaps,
             "adapter_revisions": revisions, "limits": {"files": max_files, "bytes": max_bytes, "file_bytes": max_file_bytes, "nodes": max_nodes},
             "scope": {"filters": selected, "modality": "STATIC", "specimen_executed": False, "runtime_observed": False,
                       "excluded_directory_names": sorted(EXCLUDES), "excluded_files": "symlinks, .env*, .pyc, .pyo",
                       "inventory_exhausted_within_exclusions": not stopped, "behavioral_verification": "NOT_RUN",
                       "limitations": ["Bounded structural and partial flow analysis, not a complete semantic model.",
                                       "Inferred bindings may be overridden dynamically; no actual traffic or runtime causality claimed.",
                                       "Source files are captured individually, not as an atomic filesystem snapshot."]}}
    if any(n["attributes"].get("analysis_origin") == "optional-provider" for n in nodes):
        graph["node_identity_scheme"] = "scan.native-plus-specialist/1"
    report = {"schema": "scan.report/1", "source_root": str(root), "graph": graph, "graph_digest": digest(graph),
              "run": {"execution": execution, "cache_hits": hits, "cache_misses": misses, "seconds": time.monotonic() - started,
                      "source_bytes": total, "typescript_batches": int(bool(enhancement_attempts)),
                      "enhancement_cache_hits":enhancement_hits,"enhancement_cache_misses":enhancement_misses},
              "metrics": graph_metrics(nodes, [e for e in edges if e["kind"] in ("possible_call", "possible_import")])}
    write_json(workspace / "latest-scan.json", report)
    verify_report(report)
    return report


def verify_report(report):
    if report.get("schema") != "scan.report/1" or digest(report["graph"]) != report.get("graph_digest"):
        raise ScanError("Scan report identity mismatch")
    nodes = {n["id"] for n in report["graph"]["nodes"]}
    if len(nodes) != len(report["graph"]["nodes"]): raise ScanError("Duplicate node IDs")
    for edge in report["graph"]["edges"]:
        if edge["src"] not in nodes or edge["dst"] not in nodes:
            raise ScanError("Dangling graph edge")
    return report
