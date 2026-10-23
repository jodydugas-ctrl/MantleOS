import hashlib
import json
import os
from pathlib import Path
import tempfile


class ScanError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(kind, *parts):
    return kind + ":" + digest(parts)[:24]


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ScanError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ScanError("Non-finite JSON number: " + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def read_json(path, limit=64_000_000):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ScanError("JSON file exceeds limit")
    return strict_json(data.decode("utf-8"))


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".scan-write-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def outside(path, root):
    if Path(path).resolve().is_relative_to(Path(root).resolve()):
        raise ScanError("Output/workspace must be outside the scanned source")


EXCLUDES = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv", "vendor", "dist", "build", ".scan-optimizer"}


def source_paths(root):
    """No symlink traversal; exclusions are declared in reports."""
    root = Path(root).resolve()
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDES and not (Path(folder) / d).is_symlink())
        for name in sorted(files):
            path = Path(folder) / name
            if name.startswith(".env") or name.endswith((".pyc", ".pyo")):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            yield path


def tree_identity(root):
    root = Path(root).resolve()
    return digest([(p.relative_to(root).as_posix(), sha(p.read_bytes())) for p in source_paths(root)])
