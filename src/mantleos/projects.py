#!/usr/bin/env python3
"""Git-shaped portable project objects for the Raven Engram body.

A project is NOT a cartridge and it is NOT an agent.  The Raven cartridge is the
single agent body.  Projects are ordinary Git-compatible repositories carried in
that body or saved as deterministic ``.rproj`` ZIP containers.

This module intentionally uses only Python's standard library.  It can therefore
be copied with a rebuilt Engram body and remain available immediately.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

PROJECT_SCHEMA = "mantle.project/1"
PROJECT_STATE_SCHEMA = "mantle.project-state/1"
PROJECT_MANIFEST_SCHEMA = "mantle.project-manifest/2"
PROJECT_CONTAINER_SUFFIX = ".rproj"
PROJECTS_DIR = "projects"
PROJECT_LIBRARY_DIR = "project-library"
FIXED_ZIP_TIME = (2026, 10, 6, 12, 0, 0)
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,79}\Z")

REQUIRED_PROJECT_FILES = (
    "PROJECT.json",
    "PROJECT-STATE.json",
    "README.md",
    "START-HERE.md",
    "HANDOFF.md",
    "AGENTS.md",
    "MANIFEST.json",
    ".gitignore",
)

_TRANSIENT_PARTS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".nox", ".venv", "venv", "node_modules",
    ".idea", ".vscode", "dist", "build",
}
_TRANSIENT_NAMES = {".DS_Store", "Thumbs.db"}
_SECRET_NAMES = {
    ".env", "credentials.json", "service-account.json", "id_rsa", "id_ed25519",
}
_SECRET_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
_SECRET_SAFE_SUFFIXES = {".example", ".sample", ".template"}


def _fail(message: str):
    raise ValueError(message)


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atomic_write(path: Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tmp-project-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _json_read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    if type(value) is not str or not value.strip():
        _fail("project name is required")
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    if not slug or not SLUG_RE.fullmatch(slug):
        _fail("project name cannot be converted to a safe slug")
    return slug


def _is_transient(rel: str) -> bool:
    path = PurePosixPath(rel)
    if any(part in _TRANSIENT_PARTS for part in path.parts):
        return True
    name = path.name
    return name in _TRANSIENT_NAMES or name.endswith((".pyc", ".pyo", "~")) or name.startswith(".tmp-")


def _is_secret_candidate(rel: str) -> bool:
    path = PurePosixPath(rel)
    name = path.name.lower()
    if any(name.endswith(safe) for safe in _SECRET_SAFE_SUFFIXES):
        return False
    if name in _SECRET_NAMES or name.startswith(".env."):
        return True
    return path.suffix.lower() in _SECRET_SUFFIXES


def portable_project_files(root: Path, *, include_manifest=True):
    """Return project files eligible for a portable project object.

    Git metadata and build/cache directories are deliberately excluded.  Secret-
    named files fail packaging rather than disappearing silently.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        _fail(f"project directory does not exist: {root}")
    result = []
    secret_hits = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_transient(rel):
            continue
        if rel == "MANIFEST.json" and not include_manifest:
            continue
        if _is_secret_candidate(rel):
            secret_hits.append(rel)
            continue
        result.append(path)
    if secret_hits:
        _fail("project contains secret-named files that must not be packaged: " + ", ".join(secret_hits))
    return result


_CANONICAL_PROJECT_FILE_MODES = {0o644, 0o755}


def _normalize_project_file_mode(mode: int) -> int:
    return 0o755 if (mode & 0o111) else 0o644


def _parse_project_manifest_mode(value, *, rel: str) -> int:
    if type(value) is not str or not re.fullmatch(r"0[0-7]{3}", value):
        _fail(f"invalid canonical project mode for {rel}")
    mode = int(value, 8)
    if mode not in _CANONICAL_PROJECT_FILE_MODES:
        _fail(f"unsupported canonical project mode for {rel}")
    return mode


def _declared_project_modes(root: Path):
    root = Path(root).resolve()
    path = root / "MANIFEST.json"
    if not path.is_file():
        return {}
    try:
        manifest = _json_read(path)
    except Exception:
        return {}
    if manifest.get("schema") != PROJECT_MANIFEST_SCHEMA or type(manifest.get("files")) is not dict:
        return {}
    modes = {}
    for rel, entry in manifest["files"].items():
        if type(rel) is not str or type(entry) is not dict:
            _fail("invalid project manifest mode declaration")
        modes[rel] = _parse_project_manifest_mode(entry.get("mode"), rel=rel)
    return modes


def set_project_file_mode(body_root: Path, selector: str, rel: str, mode: str):
    """Explicitly change one manifest-bound project's canonical portable mode."""
    root = resolve_project(body_root, selector)
    if type(rel) is not str or not rel or "\\" in rel:
        _fail("project file must be a canonical relative POSIX path")
    rel_path = PurePosixPath(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts or rel_path.as_posix() != rel:
        _fail("project file must be a canonical relative POSIX path")
    if rel == "MANIFEST.json" or _is_transient(rel) or _is_secret_candidate(rel):
        _fail(f"project file is not eligible for canonical mode declaration: {rel}")

    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        _fail("project MANIFEST.json missing")
    manifest = _json_read(manifest_path)
    if manifest.get("schema") != PROJECT_MANIFEST_SCHEMA or type(manifest.get("files")) is not dict:
        _fail("unsupported project manifest schema")
    entry = manifest["files"].get(rel)
    if type(entry) is not dict:
        _fail(f"project file is not manifest-bound: {rel}")

    candidate = root.joinpath(*rel_path.parts)
    if candidate.is_symlink():
        _fail(f"project mode target may not be a symbolic link: {rel}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        _fail(f"project mode target escapes project root: {rel}")
    if not resolved.is_file():
        _fail(f"project mode target is not a file: {rel}")

    old_mode = _parse_project_manifest_mode(entry.get("mode"), rel=rel)
    new_mode = _parse_project_manifest_mode(mode, rel=rel)
    entry["mode"] = f"{new_mode:04o}"
    _atomic_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))

    host_mode_applied = True
    try:
        resolved.chmod(new_mode)
    except OSError:
        host_mode_applied = False
    return {
        "schema": "mantle.project-mode-change/1",
        "result": "PASS",
        "project": root.name,
        "file": rel,
        "old_mode": f"{old_mode:04o}",
        "new_mode": f"{new_mode:04o}",
        "authority": "MANIFEST.json",
        "host_mode_applied": host_mode_applied,
    }


def project_manifest_data(root: Path):
    root = Path(root).resolve()
    declared_modes = _declared_project_modes(root)
    files = {}
    for path in portable_project_files(root, include_manifest=False):
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        mode = declared_modes.get(rel)
        if mode is None:
            mode = _normalize_project_file_mode(path.stat().st_mode)
        files[rel] = {"bytes": len(raw), "mode": f"{mode:04o}", "sha256": _sha(raw)}
    return {"schema": PROJECT_MANIFEST_SCHEMA, "files": files}


def write_project_manifest(root: Path):
    data = project_manifest_data(root)
    _atomic_write(Path(root) / "MANIFEST.json", (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return data


def verify_project(root: Path):
    root = Path(root).resolve()
    missing = [name for name in REQUIRED_PROJECT_FILES if not (root / name).is_file()]
    if missing:
        _fail("project missing required files: " + ", ".join(missing))
    descriptor = _json_read(root / "PROJECT.json")
    state_doc = _json_read(root / "PROJECT-STATE.json")
    manifest = _json_read(root / "MANIFEST.json")
    if descriptor.get("schema") != PROJECT_SCHEMA:
        _fail("unsupported PROJECT.json schema")
    if state_doc.get("schema") != PROJECT_STATE_SCHEMA:
        _fail("unsupported PROJECT-STATE.json schema")
    slug = descriptor.get("slug")
    if type(slug) is not str or not SLUG_RE.fullmatch(slug):
        _fail("invalid project slug")
    if manifest != project_manifest_data(root):
        _fail("project manifest mismatch")
    return {
        "schema": "mantle.project-verification/1",
        "result": "PASS",
        "name": descriptor.get("name"),
        "slug": slug,
        "files": len(manifest["files"]),
        "status": state_doc.get("status"),
        "current_goal": state_doc.get("current_goal"),
    }


def _default_project_descriptor(name: str, slug: str):
    return {
        "schema": PROJECT_SCHEMA,
        "format_version": "1.0",
        "name": name,
        "slug": slug,
        "kind": "git-compatible-project",
        "agent_body": "external-owner",
        "portable_container": PROJECT_CONTAINER_SUFFIX,
        "git": {"required": False, "github_required": False},
    }


def _default_project_state(name: str):
    return {
        "schema": PROJECT_STATE_SCHEMA,
        "project": name,
        "status": "active",
        "current_goal": "Define the next project task.",
        "current_phase": "bootstrap",
        "last_completed": ["Created portable Git-compatible project structure."],
        "next_actions": ["Replace bootstrap placeholders with project-specific context."],
        "known_issues": [],
        "important_constraints": [
            "This project is not an agent cartridge.",
            "Keep the repository usable without GitHub.",
            "Do not store secrets in the portable project object.",
        ],
    }


def _skeleton_files(name: str, slug: str):
    readme = f"""# {name}\n\nThis is a Git-compatible project owned or used by an Engram body. It is a **project**, not another cartridge.\n\nStart with `START-HERE.md`, then read `PROJECT-STATE.json`, `HANDOFF.md`, and `AGENTS.md`.\n"""
    start = f"""# Start Here — {name}\n\nThis repository is a portable project object.\n\n1. Read `PROJECT-STATE.json` for current truth.\n2. Read `HANDOFF.md` for interpreted context.\n3. Read `AGENTS.md` before making significant changes.\n4. Inspect the source/tests relevant to the requested task.\n5. After meaningful work, update durable project context and regenerate `MANIFEST.json`.\n\nGit and GitHub are optional history/synchronization layers; this repository must remain understandable without them.\n"""
    handoff = f"""# Handoff — {name}\n\n## What We Are Building\n\nDescribe the project here.\n\n## What the User Ultimately Wants\n\nRecord durable user intent, not chat transcript.\n\n## Where We Are Now\n\nBootstrap structure created.\n\n## What Was Just Completed\n\nPortable project structure initialized.\n\n## Important Decisions\n\n- This is a project object carried by an Engram body, not a nested cartridge.\n- Git/GitHub are optional.\n\n## Things You Must Not Accidentally Change\n\nRecord project invariants here.\n\n## Known Problems\n\nNone recorded.\n\n## Most Likely Next Step\n\nReplace bootstrap placeholders with project-specific state.\n"""
    agents = f"""# Coding Agent Contract — {name}\n\nThis directory is a project repository, not an agent body. The Engram/Raven cartridge that owns or opens it is the single body/persona boundary.\n\nBefore significant edits, read `START-HERE.md`, `PROJECT-STATE.json`, `HANDOFF.md`, and relevant docs/tests. Preserve existing user intent and settled decisions. Make the smallest coherent change, run relevant verification, then update only durable context that actually changed.\n\nDo not depend on a previous chat. Do not put credentials or secrets in this repository. Git and GitHub may be used for history and synchronization, but project continuity must not depend on either.\n"""
    gitignore = """# Local / generated\n__pycache__/\n*.py[cod]\n.pytest_cache/\n.mypy_cache/\n.ruff_cache/\n.venv/\nvenv/\nnode_modules/\nbuild/\ndist/\n.DS_Store\n.env\n.env.*\n*.key\n*.pem\n\n# Portable project containers\n*.rproj\n"""
    verifier = r'''#!/usr/bin/env python3
"""Verify the portable project manifest; checks apply even under python -O."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
if not isinstance(manifest, dict) or manifest.get("schema") != "mantle.project-manifest/2":
    raise SystemExit("FAIL: unsupported project manifest")
files = manifest.get("files")
if not isinstance(files, dict):
    raise SystemExit("FAIL: missing project file index")
for rel, meta in files.items():
    if not isinstance(rel, str) or not rel or not isinstance(meta, dict):
        raise SystemExit("FAIL: invalid manifest entry")
    name = PurePosixPath(rel)
    path = (ROOT / rel).resolve()
    if (name.as_posix() != rel or name.is_absolute() or ".." in name.parts
            or "\\" in rel or ":" in rel or not path.is_relative_to(ROOT)
            or (ROOT / rel).is_symlink() or not path.is_file()):
        raise SystemExit("FAIL: unsafe or missing project file: " + rel)
    raw = path.read_bytes()
    if (len(raw) != meta.get("bytes") or meta.get("mode") not in {"0644", "0755"}
            or hashlib.sha256(raw).hexdigest() != meta.get("sha256")):
        raise SystemExit("FAIL: project file integrity mismatch: " + rel)
print("PASS", len(files), "files")
'''
    workflow = """name: project-health\n\non:\n  push:\n  pull_request:\n\njobs:\n  verify-portable-project:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.x'\n      - run: python tools/verify_project.py\n"""
    return {
        "README.md": readme,
        "START-HERE.md": start,
        "HANDOFF.md": handoff,
        "AGENTS.md": agents,
        ".gitignore": gitignore,
        "tools/verify_project.py": verifier,
        ".github/workflows/project-health.yml": workflow,
        "docs/.gitkeep": "",
        "src/.gitkeep": "",
        "tests/.gitkeep": "",
    }


def _write_bootstrap_metadata(root: Path, name: str, slug: str, *, preserve_existing=True):
    root.mkdir(parents=True, exist_ok=True)
    descriptor_path = root / "PROJECT.json"
    state_path = root / "PROJECT-STATE.json"
    if not preserve_existing or not descriptor_path.exists():
        _atomic_write(descriptor_path, (json.dumps(_default_project_descriptor(name, slug), indent=2, sort_keys=True) + "\n").encode("utf-8"))
    if not preserve_existing or not state_path.exists():
        _atomic_write(state_path, (json.dumps(_default_project_state(name), indent=2, sort_keys=True) + "\n").encode("utf-8"))
    for rel, text in _skeleton_files(name, slug).items():
        path = root / rel
        if preserve_existing and path.exists():
            continue
        _atomic_write(path, text.encode("utf-8"))
        if rel == "tools/verify_project.py":
            path.chmod(0o755)


def resolve_project(body_root: Path, selector: str | Path):
    """Resolve an owned active project by slug only.

    External directories enter the body exclusively through ``add_project``. This
    keeps save/inspect/verify operations from silently escaping the body workspace.
    """
    body_root = Path(body_root).resolve()
    value = str(selector)
    if not SLUG_RE.fullmatch(value):
        _fail("project selector must be an owned project slug")
    path = (body_root / PROJECTS_DIR / value).resolve()
    projects_root = (body_root / PROJECTS_DIR).resolve()
    try:
        path.relative_to(projects_root)
    except ValueError:
        _fail("project selector escapes the body project workspace")
    if not path.is_dir():
        _fail(f"project not found: {selector}")
    return path


def create_project(body_root: Path, name: str, *, slug: str | None = None):
    body_root = Path(body_root).resolve()
    slug = slugify(name) if slug is None else slugify(slug)
    root = body_root / PROJECTS_DIR / slug
    if root.exists():
        _fail(f"project already exists: {slug}")
    _write_bootstrap_metadata(root, name.strip(), slug, preserve_existing=False)
    write_project_manifest(root)
    result = verify_project(root)
    result["path"] = str(root)
    return result


def _copy_portable_tree(source: Path, destination: Path):
    source = Path(source).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    declared_modes = _declared_project_modes(source)
    for src in portable_project_files(source, include_manifest=False):
        rel = src.relative_to(source)
        rel_text = rel.as_posix()
        dst = destination / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mode = declared_modes.get(rel_text, _normalize_project_file_mode(src.stat().st_mode))
        dst.chmod(mode)
    # Preserve canonical mode declarations on hosts without POSIX execute bits.
    if (source / 'MANIFEST.json').is_file():
        shutil.copy2(source / 'MANIFEST.json', destination / 'MANIFEST.json')


def add_project(body_root: Path, source: Path, *, name: str | None = None, slug: str | None = None):
    """Adopt an existing repository/directory into the Engram project workspace."""
    body_root = Path(body_root).resolve()
    source = Path(source).resolve()
    if not source.is_dir():
        _fail(f"source project directory not found: {source}")
    project_name = (name or source.name).strip()
    project_slug = slugify(slug or project_name)
    destination = body_root / PROJECTS_DIR / project_slug
    if destination.exists():
        _fail(f"project already exists: {project_slug}")
    try:
        _copy_portable_tree(source, destination)
        _write_bootstrap_metadata(destination, project_name, project_slug, preserve_existing=True)
        # PROJECT.json is authoritative for body lookup. If an imported project
        # already used the Raven schema, preserve its name but bind the owned slug.
        descriptor = _json_read(destination / "PROJECT.json")
        if descriptor.get("schema") != PROJECT_SCHEMA:
            _fail("existing PROJECT.json uses an incompatible schema")
        descriptor["slug"] = project_slug
        descriptor.setdefault("name", project_name)
        _atomic_write(destination / "PROJECT.json", (json.dumps(descriptor, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        write_project_manifest(destination)
        result = verify_project(destination)
        result["path"] = str(destination)
        result["source"] = str(source)
        return result
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def list_projects(body_root: Path):
    body_root = Path(body_root).resolve()
    workspace = body_root / PROJECTS_DIR
    library = body_root / PROJECT_LIBRARY_DIR
    active = []
    if workspace.exists():
        for child in sorted(workspace.iterdir()):
            if child.is_dir() and (child / "PROJECT.json").is_file():
                try:
                    item = verify_project(child)
                    item["path"] = str(child)
                except Exception as exc:
                    item = {"slug": child.name, "path": str(child), "result": "FAIL", "error": str(exc)}
                active.append(item)
    saved = []
    if library.exists():
        for archive in sorted(library.glob(f"*{PROJECT_CONTAINER_SUFFIX}")):
            saved.append({"name": archive.name, "bytes": archive.stat().st_size, "sha256": _sha(archive.read_bytes())})
    return {"schema": "mantle.project-list/1", "active": active, "saved": saved}


def inspect_project(root: Path):
    result = verify_project(root)
    descriptor = _json_read(Path(root) / "PROJECT.json")
    state_doc = _json_read(Path(root) / "PROJECT-STATE.json")
    result["descriptor"] = descriptor
    result["state"] = state_doc
    result["path"] = str(Path(root).resolve())
    return result


def _zip_write_file(z: zipfile.ZipFile, root: Path, path: Path, *, declared_modes=None):
    rel = path.relative_to(root).as_posix()
    info = zipfile.ZipInfo(rel, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    if rel == "MANIFEST.json":
        mode = 0o644
    else:
        if declared_modes is None:
            declared_modes = _declared_project_modes(root)
        if rel not in declared_modes:
            _fail(f"project archive file lacks canonical mode declaration: {rel}")
        mode = declared_modes[rel]
    info.external_attr = (stat.S_IFREG | mode) << 16
    z.writestr(info, path.read_bytes())


def save_project(body_root: Path, selector: str, *, output: Path | None = None):
    body_root = Path(body_root).resolve()
    root = resolve_project(body_root, selector)
    write_project_manifest(root)
    verification = verify_project(root)
    slug = verification["slug"]
    if output is None:
        output = body_root / PROJECT_LIBRARY_DIR / f"{slug}{PROJECT_CONTAINER_SUFFIX}"
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    files = portable_project_files(root, include_manifest=True)
    declared_modes = _declared_project_modes(root)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            _zip_write_file(z, root, path, declared_modes=declared_modes)
    archive_check = verify_project_archive(output)
    return {
        "schema": "mantle.project-save/1",
        "result": "PASS",
        "project": slug,
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": _sha(output.read_bytes()),
        "archive_verification": archive_check,
    }


def _safe_member_name(name: str):
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or "" in path.parts:
        _fail(f"unsafe archive member: {name}")
    return path


def _extract_project_archive(archive: Path, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            path = _safe_member_name(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                _fail("project archives may not contain symbolic links")
            if info.is_dir():
                (destination / Path(*path.parts)).mkdir(parents=True, exist_ok=True)
                continue
            target = destination / Path(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(target, z.read(info))
            file_mode = (info.external_attr >> 16) & 0o777
            if file_mode:
                target.chmod(file_mode)


def verify_project_archive(archive: Path):
    archive = Path(archive).resolve()
    if not archive.is_file():
        _fail(f"project archive not found: {archive}")
    with tempfile.TemporaryDirectory(prefix="raven-project-verify-") as td:
        root = Path(td) / "project"
        _extract_project_archive(archive, root)
        result = verify_project(root)
    return result


def load_project(body_root: Path, archive: Path, *, slug: str | None = None, replace=False):
    body_root = Path(body_root).resolve()
    archive = Path(archive).resolve()
    with tempfile.TemporaryDirectory(prefix="raven-project-load-") as td:
        staged = Path(td) / "project"
        _extract_project_archive(archive, staged)
        verified = verify_project(staged)
        target_slug = slugify(slug or verified["slug"])
        # Rebind slug only when explicitly renamed during load.
        if target_slug != verified["slug"]:
            descriptor = _json_read(staged / "PROJECT.json")
            descriptor["slug"] = target_slug
            _atomic_write(staged / "PROJECT.json", (json.dumps(descriptor, indent=2, sort_keys=True) + "\n").encode("utf-8"))
            write_project_manifest(staged)
            verified = verify_project(staged)
        target = body_root / PROJECTS_DIR / target_slug
        if target.exists():
            if not replace:
                _fail(f"project already exists: {target_slug}")
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staged, target)
    result = verify_project(target)
    result["path"] = str(target)
    result["source_archive"] = str(archive)
    return result


def git_status(body_root: Path, selector: str):
    root = resolve_project(body_root, selector)
    if not (root / ".git").exists():
        return {"schema": "mantle.project-git-status/1", "project": root.name, "git": False, "status": "NOT_INITIALIZED"}
    proc = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "--branch"], text=True, capture_output=True)
    if proc.returncode != 0:
        _fail("git status failed: " + proc.stderr.strip())
    return {"schema": "mantle.project-git-status/1", "project": root.name, "git": True, "status": proc.stdout.rstrip("\n")}
