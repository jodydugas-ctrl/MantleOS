from __future__ import annotations

from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"
MANIFEST_SCHEMA = "scan-source-manifest/0.1"
DEFAULT_MAX_BLOB_BYTES = 64 * 1024 * 1024


class JsonTransport(Protocol):
    def get_json(self, url: str) -> dict[str, Any]: ...


class UrlLibTransport:
    """Minimal read-only GitHub REST transport.

    The transport never performs a mutating request. A token is optional, but authenticated
    requests are strongly recommended for whole repositories because GitHub rate limits
    unauthenticated API traffic aggressively.
    """

    def __init__(self, token: str | None = None, timeout: float = 45.0):
        self.token = token
        self.timeout = timeout

    def get_json(self, url: str) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SCAN-software-body-acquirer/0.3",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                payload = resp.read()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"GitHub HTTP {exc.code} for {url}: {body[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub transport failure for {url}: {exc.reason}") from exc
        try:
            result = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"GitHub returned a non-JSON response for {url}") from exc
        if not isinstance(result, dict):
            raise RuntimeError(f"GitHub response is not an object for {url}")
        return result


def git_blob_sha1(data: bytes) -> str:
    """Return the canonical Git blob object id for exact bytes."""
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def _validate_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must be in owner/name form")
    owner, name = parts
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if any(ch not in allowed for ch in owner + name):
        raise ValueError("repository contains unsupported characters")
    return owner, name


def _safe_rel(path: str) -> str:
    p = PurePosixPath(path)
    if not path or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe GitHub tree path: {path!r}")
    return p.as_posix()


@dataclass(slots=True)
class BlobFetchResult:
    path: str
    ok: bool
    attributes: dict[str, Any]


class GitHubAcquirer:
    """Acquire an exact GitHub revision into scanner-owned storage.

    The repository is never cloned into a working Git checkout and no project code is executed.
    Source bytes are fetched from Git's object API, verified against their provider blob SHA-1,
    SHA-256 hashed by SCAN, and then copied into an inert scanner-owned content tree.
    """

    def __init__(self, transport: JsonTransport | None = None, token: str | None = None,
                 max_workers: int = 6, max_blob_bytes: int = DEFAULT_MAX_BLOB_BYTES):
        self.transport = transport or UrlLibTransport(token=token)
        self.max_workers = max(1, int(max_workers))
        self.max_blob_bytes = int(max_blob_bytes)
        if self.max_blob_bytes < 0:
            raise ValueError("max_blob_bytes must be >= 0")

    def acquire(self, repository: str, ref: str, out_dir: Path, *, strict: bool = False) -> dict[str, Any]:
        owner, name = _validate_repo(repository)
        if not ref:
            raise ValueError("ref is required; SCAN will not silently acquire a moving default branch")

        out_dir = out_dir.resolve()
        content_root = out_dir / "content"
        cache_root = out_dir / ".blob-cache"
        content_root.mkdir(parents=True, exist_ok=True)
        cache_root.mkdir(parents=True, exist_ok=True)

        ref_q = quote(ref, safe="")
        commit = self.transport.get_json(f"{API_ROOT}/repos/{owner}/{name}/commits/{ref_q}")
        commit_sha = str(commit.get("sha") or "")
        tree_sha = str(((commit.get("commit") or {}).get("tree") or {}).get("sha") or "")
        if len(commit_sha) != 40 or len(tree_sha) != 40:
            raise RuntimeError("GitHub commit response did not contain stable commit/tree SHA values")

        entries, tree_strategy = self._tree_entries(owner, name, tree_sha)
        manifest_items: list[dict[str, Any]] = []
        blobs: list[dict[str, Any]] = []

        for raw in entries:
            typ = raw.get("type")
            if typ not in {"blob", "commit"}:
                continue
            rel = _safe_rel(str(raw.get("path") or ""))
            item = {
                "path": rel,
                "size": int(raw.get("size") or 0),
                "sha": raw.get("sha"),
                "provider_object_id": raw.get("sha"),
                "provider_digest_algorithm": "git-object-sha1",
                "type": typ,
                "mode": raw.get("mode"),
            }
            if typ == "commit":
                item.update({
                    "content_available": False,
                    "acquisition_state": "EXTERNAL_REFERENCE",
                    "attributes": {"reference_type": "gitlink/submodule"},
                })
                manifest_items.append(item)
                continue
            if raw.get("mode") == "120000":
                # A Git symlink is a blob whose bytes are the link target. Do not create a live
                # filesystem symlink during ordinary acquisition because following it can escape
                # scanner-owned storage. Keep it explicit and non-parser-eligible instead.
                item.update({
                    "content_available": False,
                    "acquisition_state": "SYMLINK_REFERENCE",
                    "attributes": {"reference_type": "symlink", "blob_bytes_not_materialized_as_live_link": True},
                })
                manifest_items.append(item)
                continue
            if self.max_blob_bytes > 0 and item["size"] > self.max_blob_bytes:
                item.update({
                    "content_available": False,
                    "acquisition_state": "RESOURCE_LIMIT",
                    "attributes": {"max_blob_bytes": self.max_blob_bytes, "declared_size": item["size"]},
                })
                manifest_items.append(item)
                continue
            blobs.append(item)

        fetched: dict[str, BlobFetchResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            future_map = {
                pool.submit(self._fetch_blob, owner, name, item, content_root, cache_root): item
                for item in blobs
            }
            for future in as_completed(future_map):
                item = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:  # preserve the gap and continue mechanically
                    result = BlobFetchResult(item["path"], False, {
                        "acquisition_state": "BLOCKED",
                        "content_available": False,
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                fetched[item["path"]] = result

        for item in blobs:
            result = fetched[item["path"]]
            attrs = dict(item.get("attributes") or {})
            attrs.update(result.attributes.pop("attributes", {}))
            item.update(result.attributes)
            if attrs:
                item["attributes"] = attrs
            manifest_items.append(item)

        manifest_items.sort(key=lambda x: x["path"])
        blocked = sum(1 for x in manifest_items if x.get("acquisition_state") in {"BLOCKED", "RESOURCE_LIMIT"})
        materialized = sum(1 for x in manifest_items if x.get("content_available") is True)
        external = sum(1 for x in manifest_items if x.get("acquisition_state") in {"EXTERNAL_REFERENCE", "SYMLINK_REFERENCE"})

        specimen_id = f"{repository}@{commit_sha}"
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "specimen": {
                "specimen_id": specimen_id,
                "provider": "github",
                "repository": repository,
                "requested_ref": ref,
                "revision": commit_sha,
                "tree_sha": tree_sha,
                "tree_strategy": tree_strategy,
                "acquisition_method": "github-git-data-api",
                "content_root": "content",
            },
            "files": manifest_items,
        }
        report = {
            "schema_version": "scan-acquisition-report/0.1",
            "specimen_id": specimen_id,
            "revision": commit_sha,
            "tree_sha": tree_sha,
            "tree_strategy": tree_strategy,
            "object_count": len(manifest_items),
            "blob_count": len(blobs),
            "materialized_file_count": materialized,
            "blocked_file_count": blocked,
            "external_reference_count": external,
            "complete_for_provider_blobs": blocked == 0,
            "all_visible_entries_materialized": materialized == len(manifest_items),
        }

        (out_dir / "source_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        (out_dir / "acquisition_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        if strict and blocked:
            raise RuntimeError(f"GitHub acquisition incomplete: {blocked} blobs were blocked")
        return report

    def _tree_entries(self, owner: str, name: str, tree_sha: str) -> tuple[list[dict[str, Any]], str]:
        recursive_url = f"{API_ROOT}/repos/{owner}/{name}/git/trees/{tree_sha}?recursive=1"
        payload = self.transport.get_json(recursive_url)
        if not payload.get("truncated"):
            return list(payload.get("tree") or []), "recursive-tree"

        # GitHub may truncate very large recursive tree responses. Fall back to an explicit tree
        # walk so the whole visible body remains mechanically accountable.
        out: list[dict[str, Any]] = []
        stack: list[tuple[str, str]] = [("", tree_sha)]
        while stack:
            prefix, sha = stack.pop()
            tree = self.transport.get_json(f"{API_ROOT}/repos/{owner}/{name}/git/trees/{sha}")
            for entry in tree.get("tree") or []:
                name_part = str(entry.get("path") or "")
                full = f"{prefix}/{name_part}" if prefix else name_part
                clone = dict(entry)
                clone["path"] = full
                if entry.get("type") == "tree":
                    stack.append((full, str(entry.get("sha"))))
                else:
                    out.append(clone)
        out.sort(key=lambda x: str(x.get("path") or ""))
        return out, "explicit-tree-walk"

    def _fetch_blob(self, owner: str, name: str, item: dict[str, Any], content_root: Path,
                    cache_root: Path) -> BlobFetchResult:
        rel = _safe_rel(item["path"])
        expected = str(item.get("sha") or "")
        if len(expected) != 40:
            raise RuntimeError(f"missing Git blob SHA for {rel}")

        cache_path = cache_root / expected[:2] / expected[2:]
        data: bytes | None = None
        cache_hit = False
        if cache_path.is_file():
            if self.max_blob_bytes > 0 and cache_path.stat().st_size > self.max_blob_bytes:
                cache_path.unlink(missing_ok=True)
            else:
                candidate = cache_path.read_bytes()
                if git_blob_sha1(candidate) == expected:
                    data = candidate
                    cache_hit = True
                else:
                    cache_path.unlink(missing_ok=True)
        if data is not None and self.max_blob_bytes > 0 and len(data) > self.max_blob_bytes:
            raise RuntimeError(f"resource limit for {rel}: {len(data)} > {self.max_blob_bytes}")

        if data is None:
            payload = self.transport.get_json(f"{API_ROOT}/repos/{owner}/{name}/git/blobs/{expected}")
            encoding = payload.get("encoding")
            if encoding != "base64":
                raise RuntimeError(f"unsupported GitHub blob encoding {encoding!r} for {rel}")
            raw = str(payload.get("content") or "")
            try:
                data = b64decode(raw, validate=False)
            except Exception as exc:
                raise RuntimeError(f"invalid base64 blob for {rel}") from exc
            if self.max_blob_bytes > 0 and len(data) > self.max_blob_bytes:
                raise RuntimeError(f"resource limit for {rel}: {len(data)} > {self.max_blob_bytes}")
            actual_provider = git_blob_sha1(data)
            if actual_provider != expected:
                raise RuntimeError(f"Git blob hash mismatch for {rel}: expected {expected}, got {actual_provider}")
            declared = int(item.get("size") or 0)
            if declared and len(data) != declared:
                raise RuntimeError(f"Git blob size mismatch for {rel}: expected {declared}, got {len(data)}")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(cache_path, data)

        target = content_root.joinpath(*PurePosixPath(rel).parts)
        resolved_parent = target.parent.resolve()
        if content_root != resolved_parent and content_root not in resolved_parent.parents:
            raise ValueError(f"materialization path escapes scanner storage: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, data)
        return BlobFetchResult(rel, True, {
            "content_available": True,
            "acquisition_state": "PROVIDER_MATERIALIZED",
            "sha256": sha256(data).hexdigest(),
            "verified_provider_digest": True,
            "attributes": {"blob_cache_hit": cache_hit},
        })

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_name, path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
