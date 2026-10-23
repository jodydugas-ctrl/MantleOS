"""Append-only Engram continuity primitives for MantleOS.

This module intentionally stays small, but it now exposes the exact-head operations
needed by the generic hosted transaction protocol.  Derived retrieval may be rebuilt
at an historical head; canonical truth remains the append-only ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

ZERO = "0" * 64
TOKEN = re.compile(r"[A-Za-z0-9_'-]+")
HEX64 = re.compile(r"[0-9a-f]{64}")


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def hash_record(value: dict) -> str:
    unsigned = {k: v for k, v in value.items() if k != "sha256"}
    return hashlib.sha256(canonical(unsigned).encode("utf-8")).hexdigest()


def read(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    records = []
    prev = ZERO
    physical = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        physical += 1
        rec = json.loads(raw)
        if rec.get("seq") != physical:
            raise ValueError("Engram sequence mismatch")
        if rec.get('schema') not in {'mantle.engram-record/1', 'raven.engram-record/1'}:
            raise ValueError('Unsupported Engram schema')
        previous_key = 'prev' if rec['schema'] == 'raven.engram-record/1' else 'prev_sha256'
        if rec.get(previous_key) != prev:
            raise ValueError("Engram chain mismatch")
        if rec.get("sha256") != hash_record(rec):
            raise ValueError("Engram record hash mismatch")
        prev = rec["sha256"]
        records.append(rec)
    return records


def head(path: str | Path) -> str:
    records = read(path)
    return records[-1]["sha256"] if records else ZERO


def read_at_head(path: str | Path, ledger_head: str) -> list[dict]:
    """Return the exact canonical prefix ending at *ledger_head*.

    ZERO denotes the empty pre-history.  Unknown hashes are rejected rather than
    silently falling back to the current ledger.
    """
    if not isinstance(ledger_head, str) or not HEX64.fullmatch(ledger_head):
        raise ValueError("Invalid Engram ledger head")
    records = read(path)
    if ledger_head == ZERO:
        return []
    for index, rec in enumerate(records):
        if rec["sha256"] == ledger_head:
            return records[: index + 1]
    raise ValueError("Engram historical head not found")


def append(path: str | Path, rec_type: str, source: str, body: dict, *, expected_head: str | None = None) -> dict:
    from .transactions import body_lock, ensure_clean
    with body_lock(Path(path).parent):
        ensure_clean(Path(path).parent)
        return _append_locked(path,rec_type,source,body,expected_head=expected_head)


def _append_locked(path: str | Path, rec_type: str, source: str, body: dict, *, expected_head: str | None = None) -> dict:
    """Append one canonical record, optionally refusing a stale writer.

    The public wrapper serializes writers across processes. ``expected_head``
    additionally refuses a request prepared against an older ledger.
    """
    path = Path(path)
    records = read(path)
    current = records[-1]["sha256"] if records else ZERO
    if expected_head is not None:
        if not isinstance(expected_head, str) or not HEX64.fullmatch(expected_head):
            raise ValueError("Invalid expected Engram head")
        if current != expected_head:
            raise ValueError("Stale Engram head")
    rec = {
        "schema": "mantle.engram-record/1",
        "seq": len(records) + 1,
        "id": uuid.uuid4().hex,
        "type": rec_type,
        "source": source,
        "body": body,
        "prev_sha256": current,
    }
    rec["sha256"] = hash_record(rec)
    from .cells import append_segment
    append_segment(rec)
    path.parent.mkdir(parents=True, exist_ok=True)
    from .transactions import atomic_bytes
    prefix=path.read_bytes() if path.exists() else b''
    if prefix and not prefix.endswith(b'\n'):prefix+=b'\n'
    atomic_bytes(path,prefix+(canonical(rec)+'\n').encode('utf-8'))
    manifest_path=path.parent/'MANIFEST.json'
    if manifest_path.is_file():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        for item in manifest.get('files',[]):
            if item['path']==path.name:
                data=path.read_bytes()
                item.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        atomic_bytes(manifest_path,(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        if (path.parent/'COMPILED.json').exists():
            from .compiled import compile_body
            compile_body(path.parent)
    return rec


def _query_records(records: list[dict], text: str, *, limit=8, types=None) -> list[dict]:
    from .projection import build, rank
    return [records[row[3]] for row in rank(records,build(records),text,limit=limit,types=types)]


def query(path: str | Path, text: str, *, limit=8, types=None) -> list[dict]:
    return _query_records(read(path), text, limit=limit, types=types)


def query_at_head(path: str | Path, text: str, *, ledger_head: str, limit=8, types=None) -> list[dict]:
    return _query_records(read_at_head(path, ledger_head), text, limit=limit, types=types)


def find_request(path: str | Path, request_id: str) -> dict | None:
    """Find the newest committed hosted turn for an idempotency request id."""
    for rec in reversed(read(path)):
        if rec.get("type") != "turn":
            continue
        body = rec.get("body") or {}
        if body.get("turn_schema") == "mantle.host-turn/1" and body.get("request_id") == request_id:
            return rec
    return None
