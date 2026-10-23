from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .inventory import FileRecord
from .model import ExtractionResult


CURRENT_SCHEMA_VERSION = 1


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY, path TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT,
  language TEXT NOT NULL, is_binary INTEGER, line_count INTEGER, coverage TEXT NOT NULL,
  content_available INTEGER NOT NULL DEFAULT 1, acquisition_state TEXT NOT NULL DEFAULT 'LOCAL_BYTES',
  provider TEXT, provider_object_id TEXT, provider_digest_algorithm TEXT, attributes_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_sha ON files(sha256);
CREATE INDEX IF NOT EXISTS idx_files_acquisition ON files(content_available, acquisition_state);
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, file_id TEXT, path TEXT,
  coverage TEXT NOT NULL, attributes_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(path);
CREATE TABLE IF NOT EXISTS edges (
  id TEXT PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL,
  coverage TEXT NOT NULL, attributes_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, file_id TEXT NOT NULL, path TEXT NOT NULL, start_line INTEGER, end_line INTEGER,
  evidence_class TEXT NOT NULL, extractor TEXT NOT NULL, excerpt TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_path ON evidence(path);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL,
  attributes_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_kind ON findings(kind);
CREATE TABLE IF NOT EXISTS extraction_cache (
  file_sha256 TEXT NOT NULL, adapter TEXT NOT NULL, adapter_version TEXT NOT NULL,
  payload_json TEXT NOT NULL, PRIMARY KEY(file_sha256, adapter, adapter_version)
);

-- Canonical cross-object semantic/evidence graph. Extraction tables above remain optimized Stage-1 views;
-- these tables make files, evidence, anatomical objects, graph-relation claims, findings, interpretations,
-- behaviors and reconstruction anchors share one traversable identity space.
CREATE TABLE IF NOT EXISTS semantic_objects (
  id TEXT PRIMARY KEY, object_type TEXT NOT NULL, subtype TEXT NOT NULL, label TEXT NOT NULL,
  coverage TEXT NOT NULL, attributes_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_semantic_objects_type ON semantic_objects(object_type, subtype);
CREATE TABLE IF NOT EXISTS semantic_relations (
  id TEXT PRIMARY KEY, src TEXT NOT NULL, dst TEXT NOT NULL, kind TEXT NOT NULL,
  status TEXT NOT NULL, attributes_json TEXT NOT NULL DEFAULT '{}', evidence_ids_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_semantic_relations_src ON semantic_relations(src, kind);
CREATE INDEX IF NOT EXISTS idx_semantic_relations_dst ON semantic_relations(dst, kind);
CREATE INDEX IF NOT EXISTS idx_semantic_relations_kind ON semantic_relations(kind);
CREATE TABLE IF NOT EXISTS completeness_dimensions (
  id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, label TEXT NOT NULL, state TEXT NOT NULL,
  parent_id TEXT, attributes_json TEXT NOT NULL DEFAULT '{}', evidence_ids_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_completeness_state ON completeness_dimensions(state);
"""


class Store:
    def __init__(self, path: Path, *, recover_corrupt: bool = False, readonly: bool = False):
        self.path = Path(path)
        self.recover_corrupt = recover_corrupt
        self.readonly = bool(readonly)
        self.recovery_info: dict | None = None
        if self.readonly:
            if recover_corrupt:
                raise ValueError("readonly Store cannot recover/mutate a corrupt database")
            if not self.path.is_file():
                raise FileNotFoundError(self.path)
            uri = self.path.resolve().as_uri() + "?mode=ro&immutable=1"
            self.db = sqlite3.connect(uri, uri=True)
            self._validate_database()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.db = sqlite3.connect(self.path)
            self._validate_database()
        except sqlite3.DatabaseError as exc:
            if not recover_corrupt:
                try:
                    self.db.close()
                except Exception:
                    pass
                raise
            try:
                self.db.close()
            except Exception:
                pass
            backup = self._quarantine_existing("corrupt")
            self.recovery_info = {
                "state": "CLEAN_REBUILD", "reason": "DATABASE_CORRUPT",
                "error": str(exc), "quarantined_path": str(backup) if backup else None,
            }
            self.db = sqlite3.connect(self.path)
        self._migrate_if_needed()
        self.db.executescript(SCHEMA)
        self.db.execute(f"PRAGMA user_version={CURRENT_SCHEMA_VERSION}")
        self.db.commit()

    def _validate_database(self):
        # quick_check is intentionally run only at open; SCAN indexes are derived artifacts and
        # correctness outranks attempting to continue on a damaged canonical store.
        row = self.db.execute("PRAGMA quick_check").fetchone()
        if row and row[0] != "ok":
            raise sqlite3.DatabaseError(f"sqlite quick_check failed: {row[0]}")

    def _quarantine_existing(self, reason: str) -> Path | None:
        if not self.path.exists():
            return None
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.path.with_name(f"{self.path.stem}.{reason}.{stamp}{self.path.suffix}")
        self.path.replace(backup)
        for suffix in ("-wal", "-shm"):
            side = Path(str(self.path) + suffix)
            if side.exists():
                side.replace(Path(str(backup) + suffix))
        return backup

    def _migrate_if_needed(self):
        version = int(self.db.execute("PRAGMA user_version").fetchone()[0])
        if version > CURRENT_SCHEMA_VERSION:
            raise sqlite3.DatabaseError(
                f"scan index schema {version} is newer than supported {CURRENT_SCHEMA_VERSION}; use a newer SCAN engine"
            )
        row = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'").fetchone()
        if not row:
            return
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(files)").fetchall()}
        required = {"content_available", "acquisition_state", "provider", "provider_object_id", "provider_digest_algorithm", "attributes_json"}
        if not required.issubset(cols):
            # The index is derived. An incompatible legacy map is rebuilt deterministically rather
            # than guessed forward; the content-addressed extraction cache survives when its table is compatible.
            for table in ("files", "nodes", "edges", "evidence", "findings", "semantic_objects", "semantic_relations", "completeness_dimensions"):
                self.db.execute(f"DROP TABLE IF EXISTS {table}")
            self.db.commit()
            self.recovery_info = {
                "state": "SCHEMA_REBUILD", "from_version": version, "to_version": CURRENT_SCHEMA_VERSION,
                "reason": "incompatible derived-map schema",
            }

    def close(self):
        if not self.readonly:
            self.db.commit()
        self.db.close()

    def reset_current_map(self):
        for table in ("files", "nodes", "edges", "evidence", "findings", "semantic_objects", "semantic_relations", "completeness_dimensions"):
            self.db.execute(f"DELETE FROM {table}")

    def put_files(self, rows: Iterable[FileRecord]):
        self.db.executemany(
            """INSERT OR REPLACE INTO files
               (id,path,size,sha256,language,is_binary,line_count,coverage,content_available,acquisition_state,
                provider,provider_object_id,provider_digest_algorithm,attributes_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(
                r.id, r.path, r.size, r.sha256, r.language,
                None if r.is_binary is None else int(r.is_binary), r.line_count, r.coverage,
                int(r.content_available), r.acquisition_state, r.provider, r.provider_object_id,
                r.provider_digest_algorithm, json.dumps(r.attributes, ensure_ascii=False)
            ) for r in rows],
        )

    def get_cache(self, digest: str, adapter: str, version: str) -> ExtractionResult | None:
        row = self.db.execute(
            "SELECT payload_json FROM extraction_cache WHERE file_sha256=? AND adapter=? AND adapter_version=?",
            (digest, adapter, version),
        ).fetchone()
        return ExtractionResult.from_dict(json.loads(row[0])) if row else None

    def put_cache(self, digest: str, adapter: str, version: str, result: ExtractionResult):
        self.db.execute(
            "INSERT OR REPLACE INTO extraction_cache VALUES (?,?,?,?)",
            (digest, adapter, version, json.dumps(result.to_dict(), ensure_ascii=False)),
        )

    def put_result(self, result: ExtractionResult):
        # Stable IDs intentionally let declarations and references converge on the same canonical
        # object (notably QAction). Merge duplicate rows instead of silently letting the final adapter
        # occurrence erase earlier evidence or richer declaration attributes.
        kind_rank = {
            "human_surface": 100, "surface_factory_output": 90, "surface_reference": 80,
            "handler_reference": 70, "symbol": 70, "event": 60, "event_source": 50,
            "ui_widget": 40, "translation_unit": 30,
        }
        coverage_rank = {"MAPPED": 5, "PARTIAL": 4, "UNKNOWN": 3, "NOT_APPLICABLE": 2, "BLOCKED": 1}

        nodes = {}
        for x in result.nodes:
            prev = nodes.get(x.id)
            if prev is None:
                nodes[x.id] = x
                continue
            prefer_new = kind_rank.get(x.kind, 0) > kind_rank.get(prev.kind, 0)
            preferred, other = (x, prev) if prefer_new else (prev, x)
            attrs = dict(other.attributes)
            attrs.update(preferred.attributes)
            preferred.attributes = attrs
            preferred.evidence_ids = sorted(set(prev.evidence_ids + x.evidence_ids))
            if coverage_rank.get(x.coverage, 0) > coverage_rank.get(prev.coverage, 0):
                preferred.coverage = x.coverage
            nodes[x.id] = preferred

        edges = {}
        for x in result.edges:
            prev = edges.get(x.id)
            if prev is None:
                edges[x.id] = x
                continue
            prev.evidence_ids = sorted(set(prev.evidence_ids + x.evidence_ids))
            prev.attributes = {**prev.attributes, **x.attributes}
            if coverage_rank.get(x.coverage, 0) > coverage_rank.get(prev.coverage, 0):
                prev.coverage = x.coverage
            edges[x.id] = prev

        evidence = {x.id: x for x in result.evidence}
        findings = {x.id: x for x in result.findings}
        self.db.executemany(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?,?)",
            [(x.id, x.kind, x.name, x.file_id, x.path, x.coverage, json.dumps(x.attributes), json.dumps(x.evidence_ids)) for x in nodes.values()],
        )
        self.db.executemany(
            "INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?,?,?)",
            [(x.id, x.src, x.dst, x.kind, x.coverage, json.dumps(x.attributes), json.dumps(x.evidence_ids)) for x in edges.values()],
        )
        self.db.executemany(
            "INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?,?)",
            [(x.id, x.file_id, x.path, x.start_line, x.end_line, x.evidence_class, x.extractor, x.excerpt) for x in evidence.values()],
        )
        self.db.executemany(
            "INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?)",
            [(x.id, x.kind, x.title, x.status, json.dumps(x.attributes), json.dumps(x.evidence_ids)) for x in findings.values()],
        )
        self.db.commit()

    def put_semantic_bundle(self, objects: Iterable[dict], relations: Iterable[dict], completeness: Iterable[dict] = ()): 
        """Atomically commit one semantic promotion/overlay bundle."""
        objects = list(objects)
        relations = list(relations)
        completeness = list(completeness)
        with self.db:
            if objects:
                self.db.executemany(
                    "INSERT OR REPLACE INTO semantic_objects VALUES (?,?,?,?,?,?)",
                    [(r["id"], r["object_type"], r["subtype"], r["label"], r.get("coverage", "UNKNOWN"), json.dumps(r.get("attributes") or {}, ensure_ascii=False)) for r in objects],
                )
            if relations:
                self.db.executemany(
                    "INSERT OR REPLACE INTO semantic_relations VALUES (?,?,?,?,?,?,?)",
                    [(r["id"], r["src"], r["dst"], r["kind"], r.get("status", "MAPPED"),
                      json.dumps(r.get("attributes") or {}, ensure_ascii=False), json.dumps(r.get("evidence_ids") or [], ensure_ascii=False)) for r in relations],
                )
            if completeness:
                self.db.executemany(
                    "INSERT OR REPLACE INTO completeness_dimensions VALUES (?,?,?,?,?,?,?)",
                    [(r["id"], r["key"], r["label"], r["state"], r.get("parent_id"),
                      json.dumps(r.get("attributes") or {}, ensure_ascii=False), json.dumps(r.get("evidence_ids") or [], ensure_ascii=False)) for r in completeness],
                )

    def put_semantic_objects(self, rows: Iterable[dict]):
        self.db.executemany(
            "INSERT OR REPLACE INTO semantic_objects VALUES (?,?,?,?,?,?)",
            [(r["id"], r["object_type"], r["subtype"], r["label"], r.get("coverage", "UNKNOWN"), json.dumps(r.get("attributes") or {}, ensure_ascii=False)) for r in rows],
        )
        self.db.commit()

    def put_semantic_relations(self, rows: Iterable[dict]):
        self.db.executemany(
            "INSERT OR REPLACE INTO semantic_relations VALUES (?,?,?,?,?,?,?)",
            [(r["id"], r["src"], r["dst"], r["kind"], r.get("status", "MAPPED"),
              json.dumps(r.get("attributes") or {}, ensure_ascii=False), json.dumps(r.get("evidence_ids") or [], ensure_ascii=False)) for r in rows],
        )
        self.db.commit()

    def put_completeness(self, rows: Iterable[dict]):
        self.db.executemany(
            "INSERT OR REPLACE INTO completeness_dimensions VALUES (?,?,?,?,?,?,?)",
            [(r["id"], r["key"], r["label"], r["state"], r.get("parent_id"),
              json.dumps(r.get("attributes") or {}, ensure_ascii=False), json.dumps(r.get("evidence_ids") or [], ensure_ascii=False)) for r in rows],
        )
        self.db.commit()

    def _decode_semantic_object(self, row: dict) -> dict:
        row = dict(row)
        row["attributes"] = json.loads(row.pop("attributes_json") or "{}")
        return row

    def _decode_semantic_relation(self, row: dict) -> dict:
        row = dict(row)
        row["attributes"] = json.loads(row.pop("attributes_json") or "{}")
        row["evidence_ids"] = json.loads(row.pop("evidence_ids_json") or "[]")
        return row

    def semantic_objects(self) -> list[dict]:
        return [self._decode_semantic_object(r) for r in self.query("SELECT * FROM semantic_objects ORDER BY object_type,subtype,label,id")]

    def semantic_relations(self) -> list[dict]:
        return [self._decode_semantic_relation(r) for r in self.query("SELECT * FROM semantic_relations ORDER BY kind,src,dst,id")]

    def semantic_object(self, object_id: str) -> dict | None:
        rows = self.query("SELECT * FROM semantic_objects WHERE id=?", (object_id,))
        return self._decode_semantic_object(rows[0]) if rows else None

    def incoming_semantic_relations(self, object_id: str) -> list[dict]:
        return [self._decode_semantic_relation(r) for r in self.query("SELECT * FROM semantic_relations WHERE dst=? ORDER BY kind,src,id", (object_id,))]

    def outgoing_semantic_relations(self, object_id: str) -> list[dict]:
        return [self._decode_semantic_relation(r) for r in self.query("SELECT * FROM semantic_relations WHERE src=? ORDER BY kind,dst,id", (object_id,))]

    def completeness_dimensions(self) -> list[dict]:
        rows = self.query("SELECT * FROM completeness_dimensions ORDER BY key")
        out = []
        for row in rows:
            row = dict(row)
            row["attributes"] = json.loads(row.pop("attributes_json") or "{}")
            row["evidence_ids"] = json.loads(row.pop("evidence_ids_json") or "[]")
            out.append(row)
        return out

    def query(self, sql: str, args=()):
        self.db.row_factory = sqlite3.Row
        return [dict(row) for row in self.db.execute(sql, args).fetchall()]
