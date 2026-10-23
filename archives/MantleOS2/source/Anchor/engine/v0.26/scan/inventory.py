from __future__ import annotations

from dataclasses import dataclass, asdict, field
from hashlib import sha1, sha256
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from .model import stable_id


LANG_BY_EXT = {
    ".c": "C", ".h": "C/C++ Header", ".cc": "C++", ".cpp": "C++", ".cxx": "C++", ".hpp": "C++ Header",
    ".py": "Python", ".rs": "Rust", ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go", ".cs": "C#", ".swift": "Swift", ".lua": "Lua", ".rb": "Ruby", ".php": "PHP",
    ".sh": "Shell", ".ps1": "PowerShell", ".xml": "XML", ".ui": "Qt UI XML", ".qrc": "Qt Resource XML",
    ".json": "JSON", ".toml": "TOML", ".yaml": "YAML", ".yml": "YAML", ".ini": "INI", ".cfg": "Config",
    ".md": "Markdown", ".cmake": "CMake", ".pro": "QMake", ".pri": "QMake", ".prf": "QMake", ".gradle": "Gradle", ".properties": "Properties",
}
SPECIAL_NAMES = {"CMakeLists.txt": "CMake", "Makefile": "Make", "Dockerfile": "Dockerfile"}
TEXT_EXTS = set(LANG_BY_EXT) | {".txt", ".desktop", ".plist", ".rc", ".in", ".css", ".html", ".htm", ".sql"}
DEFAULT_MAX_FILE_BYTES = 64 * 1024 * 1024


@dataclass(slots=True)
class FileRecord:
    id: str
    path: str
    size: int
    sha256: str | None
    language: str
    is_binary: bool | None
    line_count: int | None
    coverage: str
    content_available: bool = True
    acquisition_state: str = "LOCAL_BYTES"
    provider: str | None = None
    provider_object_id: str | None = None
    provider_digest_algorithm: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def language_for_path(path: str) -> str:
    p = PurePosixPath(path)
    return SPECIAL_NAMES.get(p.name, LANG_BY_EXT.get(p.suffix.lower(), "Unknown"))


def _is_binary(data: bytes, suffix: str, name: str) -> bool:
    if b"\x00" in data[:8192]:
        return True
    if suffix.lower() in TEXT_EXTS or name in SPECIAL_NAMES:
        return False
    try:
        data[:8192].decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def record_from_bytes(rel: str, data: bytes, *, provider: str | None = None,
                      provider_object_id: str | None = None,
                      provider_digest_algorithm: str | None = None,
                      acquisition_state: str = "LOCAL_BYTES",
                      attributes: dict[str, Any] | None = None) -> FileRecord:
    p = PurePosixPath(rel)
    digest = sha256(data).hexdigest()
    binary = _is_binary(data, p.suffix.lower(), p.name)
    line_count = None if binary else data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return FileRecord(
        id=stable_id("file", rel, digest), path=rel, size=len(data), sha256=digest,
        language=language_for_path(rel), is_binary=binary, line_count=line_count,
        coverage="PARTIAL" if binary else "MAPPED", content_available=True,
        acquisition_state=acquisition_state, provider=provider,
        provider_object_id=provider_object_id, provider_digest_algorithm=provider_digest_algorithm,
        attributes=attributes or {},
    )


def _blocked_local_record(rel: str, *, size: int, state: str, attributes: dict[str, Any] | None = None) -> FileRecord:
    identity = stable_id("local-blocked", rel, size, state, attributes or {})
    return FileRecord(
        id=stable_id("file", rel, identity), path=rel, size=size, sha256=None,
        language=language_for_path(rel), is_binary=None, line_count=None,
        coverage="PARTIAL" if state == "SYMLINK_REFERENCE" else "BLOCKED",
        content_available=False, acquisition_state=state, attributes=attributes or {},
    )


def _safe_local_candidate(root: Path, rel: str) -> Path:
    """Return a local path only when every existing component is non-symlink and contained by root."""
    rel = _validate_manifest_path(rel)
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            return current
        if stat.S_ISLNK(st.st_mode):
            raise RuntimeError(f"SYMLINK_REFERENCE:{rel}:{os.readlink(current)}")
    try:
        resolved_parent = current.parent.resolve(strict=True)
    except FileNotFoundError:
        resolved_parent = current.parent.resolve(strict=False)
    if resolved_parent != root and root not in resolved_parent.parents:
        raise RuntimeError(f"PATH_ESCAPE:{rel}")
    return current


def _stat_identity(value: os.stat_result, *, platform_name: str | None = None) -> tuple[int, ...]:
    """Return fields that are comparable for path and descriptor stat calls.

    Windows does not promise identical creation/change-time semantics for ``lstat`` and
    ``fstat``. Comparing ``st_ctime_ns`` there made unchanged files fail closed as
    ``SOURCE_CHANGED``. Device, inode/file index, size, and modification time retain the
    path-to-handle identity guard; POSIX also includes ctime to detect metadata races.
    """
    platform_name = os.name if platform_name is None else platform_name
    identity = (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if platform_name != "nt":
        identity += (value.st_ctime_ns,)
    return identity


def _read_regular_bytes(path: Path, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> bytes:
    st0 = os.lstat(path)
    if stat.S_ISLNK(st0.st_mode):
        raise RuntimeError(f"SYMLINK_REFERENCE:{path}")
    if not stat.S_ISREG(st0.st_mode):
        raise RuntimeError(f"SPECIAL_FILE:{path}")
    if max_file_bytes > 0 and st0.st_size > max_file_bytes:
        raise RuntimeError(f"RESOURCE_LIMIT:{st0.st_size}:{max_file_bytes}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        st1 = os.fstat(fd)
        if not stat.S_ISREG(st1.st_mode):
            raise RuntimeError(f"SPECIAL_FILE:{path}")
        before = _stat_identity(st0)
        opened = _stat_identity(st1)
        if before != opened:
            raise RuntimeError(f"SOURCE_CHANGED:{path}")
        chunks: list[bytes] = []
        remaining = st1.st_size
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        st2 = os.fstat(fd)
        after = _stat_identity(st2)
        if before != after or len(data) != st0.st_size:
            raise RuntimeError(f"SOURCE_CHANGED:{path}")
        return data
    finally:
        os.close(fd)


def read_verified_local(root: Path, rel: str, expected_sha256: str | None,
                        *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> bytes:
    root = root.resolve(strict=True)
    path = _safe_local_candidate(root, rel)
    data = _read_regular_bytes(path, max_file_bytes=max_file_bytes)
    if expected_sha256 and sha256(data).hexdigest() != expected_sha256:
        raise RuntimeError(f"SOURCE_CHANGED_DIGEST:{rel}")
    return data


def inventory(root: Path, excludes: set[str] | None = None,
              *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_total_bytes: int = 0,
              max_materialized_files: int = 0) -> list[FileRecord]:
    raw_root = Path(root)
    if raw_root.is_symlink():
        raise ValueError(f"scan root must not be a symlink: {raw_root}")
    root = raw_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"scan root is not a directory: {root}")
    if max_total_bytes < 0 or max_materialized_files < 0:
        raise ValueError("aggregate inventory budgets must be >= 0")
    excludes = excludes or {".git", ".scan", "__pycache__", ".pytest_cache", ".mypy_cache"}
    rows: list[FileRecord] = []
    total_bytes = 0
    materialized_files = 0
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        # Keep traversal deterministic and never descend through excluded or symlinked directories.
        kept_dirs: list[str] = []
        for name in sorted(dirs):
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if any(part in excludes for part in PurePosixPath(rel).parts):
                continue
            try:
                st = os.lstat(path)
            except OSError as exc:
                rows.append(_blocked_local_record(rel, size=0, state="READ_ERROR", attributes={"error": str(exc)}))
                continue
            if stat.S_ISLNK(st.st_mode):
                rows.append(_blocked_local_record(rel, size=st.st_size, state="SYMLINK_REFERENCE",
                                                  attributes={"target": os.readlink(path), "entry_type": "directory_symlink"}))
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in sorted(files):
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if any(part in excludes for part in PurePosixPath(rel).parts):
                continue
            try:
                st = os.lstat(path)
            except OSError as exc:
                rows.append(_blocked_local_record(rel, size=0, state="READ_ERROR", attributes={"error": str(exc)}))
                continue
            if stat.S_ISLNK(st.st_mode):
                rows.append(_blocked_local_record(rel, size=st.st_size, state="SYMLINK_REFERENCE",
                                                  attributes={"target": os.readlink(path), "entry_type": "file_symlink"}))
                continue
            if not stat.S_ISREG(st.st_mode):
                rows.append(_blocked_local_record(rel, size=st.st_size, state="SPECIAL_FILE",
                                                  attributes={"mode": st.st_mode}))
                continue
            if max_file_bytes > 0 and st.st_size > max_file_bytes:
                rows.append(_blocked_local_record(rel, size=st.st_size, state="RESOURCE_LIMIT",
                                                  attributes={"max_file_bytes": max_file_bytes}))
                continue
            if max_materialized_files > 0 and materialized_files >= max_materialized_files:
                rows.append(_blocked_local_record(rel, size=st.st_size, state="RESOURCE_LIMIT_TOTAL_FILES",
                                                  attributes={"max_materialized_files": max_materialized_files,
                                                              "materialized_files_before_limit": materialized_files}))
                continue
            if max_total_bytes > 0 and total_bytes + st.st_size > max_total_bytes:
                rows.append(_blocked_local_record(rel, size=st.st_size, state="RESOURCE_LIMIT_TOTAL_BYTES",
                                                  attributes={"max_total_bytes": max_total_bytes,
                                                              "bytes_materialized_before_limit": total_bytes}))
                continue
            try:
                data = _read_regular_bytes(path, max_file_bytes=max_file_bytes)
            except RuntimeError as exc:
                message = str(exc)
                state = message.split(":", 1)[0] if ":" in message else "READ_ERROR"
                rows.append(_blocked_local_record(rel, size=st.st_size, state=state,
                                                  attributes={"error": message, "max_file_bytes": max_file_bytes}))
                continue
            except OSError as exc:
                rows.append(_blocked_local_record(rel, size=st.st_size, state="READ_ERROR", attributes={"error": str(exc)}))
                continue
            rows.append(record_from_bytes(rel, data))
            total_bytes += len(data)
            materialized_files += 1
    return sorted(rows, key=lambda r: r.path)

def _validate_manifest_path(value: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe manifest path: {value!r}")
    return p.as_posix()


def _blocked_record(rel: str, *, size: int, data: bytes | None, provider: str | None,
                    provider_object_id: str | None, provider_digest_algorithm: str | None,
                    state: str, attributes: dict[str, Any]) -> FileRecord:
    p = PurePosixPath(rel)
    digest = sha256(data).hexdigest() if data is not None else None
    binary = _is_binary(data, p.suffix.lower(), p.name) if data is not None else None
    line_count = None if data is None or binary else data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    identity = provider_object_id or digest or stable_id("manifest-entry", rel, size, state)
    return FileRecord(
        id=stable_id("file", rel, provider or "manifest", identity, state),
        path=rel, size=size, sha256=digest, language=language_for_path(rel),
        is_binary=binary, line_count=line_count, coverage="BLOCKED", content_available=False,
        acquisition_state=state, provider=provider, provider_object_id=provider_object_id,
        provider_digest_algorithm=provider_digest_algorithm, attributes=attributes,
    )


def inventory_from_manifest(manifest_path: Path, content_root: Path | None = None, *,
                            max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_total_bytes: int = 0,
                            max_materialized_files: int = 0) -> tuple[list[FileRecord], dict[str, Any]]:
    """Build a verified file ledger from a scanner-source manifest.

    A manifest can describe provider-visible files before their bytes are local. When a matching
    local path exists, SCAN verifies provider and scanner digests before making the file parser-
    eligible. Wrong bytes and aggregate-budget exclusions remain explicit and are never parsed.
    """
    if max_total_bytes < 0 or max_materialized_files < 0:
        raise ValueError("aggregate inventory budgets must be >= 0")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = manifest.get("schema_version")
    if schema != "scan-source-manifest/0.1":
        raise ValueError(f"unsupported source manifest schema: {schema!r}")
    specimen = dict(manifest.get("specimen") or {})
    provider = specimen.get("provider") or manifest.get("provider")
    rows: list[FileRecord] = []
    if content_root and Path(content_root).is_symlink():
        raise ValueError(f"content root must not be a symlink: {content_root}")
    content_root = content_root.resolve(strict=True) if content_root else None
    total_bytes = 0
    materialized_files = 0

    for item in manifest.get("files", []):
        rel = _validate_manifest_path(str(item["path"]))
        provider_object_id = item.get("provider_object_id") or item.get("sha")
        provider_digest_algorithm = item.get("provider_digest_algorithm")
        if provider_object_id and not provider_digest_algorithm and provider == "github":
            provider_digest_algorithm = "git-object-sha1"

        manifest_size = int(item.get("size") or 0)
        item_type = item.get("type")
        item_state = item.get("acquisition_state")
        base_attributes = {
            "manifest_size": item.get("size"),
            "manifest_mode": item.get("mode"),
            "manifest_type": item_type,
            **dict(item.get("attributes") or {}),
        }

        if item_type == "commit" or item_state in {"EXTERNAL_REFERENCE", "SYMLINK_REFERENCE"}:
            state = item_state or "EXTERNAL_REFERENCE"
            identity = provider_object_id or stable_id("manifest-entry", rel, manifest_size, state)
            rows.append(FileRecord(
                id=stable_id("file", rel, provider or "manifest", identity),
                path=rel, size=manifest_size, sha256=None, language=language_for_path(rel),
                is_binary=None, line_count=None, coverage="PARTIAL", content_available=False,
                acquisition_state=state, provider=provider, provider_object_id=provider_object_id,
                provider_digest_algorithm=provider_digest_algorithm, attributes=base_attributes,
            ))
            continue

        materialized = content_root.joinpath(*PurePosixPath(rel).parts) if content_root else None
        if materialized and materialized.exists():
            if max_materialized_files > 0 and materialized_files >= max_materialized_files:
                rows.append(_blocked_record(
                    rel, size=manifest_size, data=None, provider=provider, provider_object_id=provider_object_id,
                    provider_digest_algorithm=provider_digest_algorithm, state="RESOURCE_LIMIT_TOTAL_FILES",
                    attributes={**base_attributes, "max_materialized_files": max_materialized_files,
                                "materialized_files_before_limit": materialized_files},
                ))
                continue
            if max_total_bytes > 0 and total_bytes + manifest_size > max_total_bytes:
                rows.append(_blocked_record(
                    rel, size=manifest_size, data=None, provider=provider, provider_object_id=provider_object_id,
                    provider_digest_algorithm=provider_digest_algorithm, state="RESOURCE_LIMIT_TOTAL_BYTES",
                    attributes={**base_attributes, "max_total_bytes": max_total_bytes,
                                "bytes_materialized_before_limit": total_bytes},
                ))
                continue
            try:
                safe_path = _safe_local_candidate(content_root, rel)
                data = _read_regular_bytes(safe_path, max_file_bytes=max_file_bytes)
            except (RuntimeError, OSError) as exc:
                message = str(exc)
                state = message.split(":", 1)[0] if ":" in message else "READ_ERROR"
                rows.append(_blocked_record(
                    rel, size=manifest_size, data=None, provider=provider,
                    provider_object_id=provider_object_id, provider_digest_algorithm=provider_digest_algorithm,
                    state=state, attributes={**base_attributes, "verification_error": message,
                                             "max_file_bytes": max_file_bytes},
                ))
                continue
            actual_sha256 = sha256(data).hexdigest()
            verification = {
                **base_attributes, "actual_size": len(data), "manifest_sha256": item.get("sha256"),
                "provider_digest_verified": None, "manifest_sha256_verified": None,
            }
            mismatch_reason = None
            expected_sha256 = item.get("sha256")
            if expected_sha256:
                verification["manifest_sha256_verified"] = actual_sha256 == expected_sha256
                if actual_sha256 != expected_sha256:
                    mismatch_reason = f"sha256 expected {expected_sha256}, got {actual_sha256}"
            if provider_object_id and provider_digest_algorithm == "git-object-sha1":
                actual_git = git_blob_sha1(data)
                verification["provider_digest_verified"] = actual_git == provider_object_id
                verification["actual_provider_object_id"] = actual_git
                if actual_git != provider_object_id:
                    mismatch_reason = f"git blob expected {provider_object_id}, got {actual_git}"
            if mismatch_reason:
                verification["verification_error"] = mismatch_reason
                rows.append(_blocked_record(
                    rel, size=manifest_size or len(data), data=data, provider=provider,
                    provider_object_id=provider_object_id, provider_digest_algorithm=provider_digest_algorithm,
                    state="HASH_MISMATCH", attributes=verification,
                ))
                continue
            rec = record_from_bytes(
                rel, data, provider=provider, provider_object_id=provider_object_id,
                provider_digest_algorithm=provider_digest_algorithm, acquisition_state="MANIFEST_MATERIALIZED",
                attributes=verification,
            )
            rows.append(rec)
            total_bytes += len(data)
            materialized_files += 1
            continue

        size = manifest_size
        identity = provider_object_id or stable_id("manifest-entry", rel, size)
        state = item_state or ("BLOCKED" if item.get("error") else "METADATA_ONLY")
        coverage = "BLOCKED" if state == "BLOCKED" else "PARTIAL"
        attrs = {**base_attributes}
        if item.get("error"):
            attrs["acquisition_error"] = item.get("error")
        rows.append(FileRecord(
            id=stable_id("file", rel, provider or "manifest", identity, state),
            path=rel, size=size, sha256=item.get("sha256"), language=language_for_path(rel),
            is_binary=None, line_count=None, coverage=coverage, content_available=False, acquisition_state=state,
            provider=provider, provider_object_id=provider_object_id, provider_digest_algorithm=provider_digest_algorithm,
            attributes=attrs,
        ))

    rows.sort(key=lambda r: r.path)
    return rows, specimen
