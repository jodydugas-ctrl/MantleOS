#!/usr/bin/env python3
"""Small persistence primitives shared by Mantle Body checkpoints."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
from typing import Any


OWNER_DIRECTORY_MODE = 0o700
OWNER_FILE_MODE = 0o600
_STAGE_PREFIX = ".mantle-stage-"
_PROC_FD_PREFIX = ("/", "proc", "self", "fd")


def _secure_dirfd_available() -> bool:
    required = (os.open, os.mkdir, os.stat, os.unlink, os.rename)
    return (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "fchmod")
        and all(operation in os.supports_dir_fd for operation in required)
    )


def _path_anchor(path: str) -> tuple[int, list[str], bool]:
    """Return a trusted directory descriptor and lexical descendants."""
    raw = os.fspath(path)
    if not isinstance(raw, str):
        raise TypeError("persistence path must be text")
    if "\x00" in raw:
        raise ValueError("persistence path contains a null byte")

    lexical = Path(raw).parts
    if any(component in {".", ".."} for component in lexical):
        raise OSError("persistence path contains a traversal component")

    if lexical[:4] == _PROC_FD_PREFIX:
        if len(lexical) < 5 or not lexical[4].isdigit():
            raise OSError("persistence descriptor anchor is invalid")
        descriptor = int(lexical[4])
        info = os.fstat(descriptor)
        if not stat.S_ISDIR(info.st_mode):
            raise NotADirectoryError(
                f"persistence descriptor is not a directory: {descriptor}"
            )
        return os.dup(descriptor), list(lexical[5:]), True

    absolute = Path(os.path.abspath(raw))
    parts = list(absolute.parts)
    if not parts or parts[0] != os.sep:
        raise OSError("persistence path must resolve beneath a filesystem root")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    return os.open(os.sep, flags), parts[1:], False


def _open_directory(path: str, *, create: bool) -> int:
    """Open a directory without following a mutable pathname after validation."""
    descriptor, components, descriptor_anchor = _path_anchor(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        for index, component in enumerate(components):
            created = False
            if create:
                try:
                    os.mkdir(
                        component,
                        OWNER_DIRECTORY_MODE,
                        dir_fd=descriptor,
                    )
                    created = True
                except FileExistsError:
                    pass
            child = os.open(component, flags, dir_fd=descriptor)
            info = os.fstat(child)
            if not stat.S_ISDIR(info.st_mode):
                os.close(child)
                raise NotADirectoryError(component)
            if created or index == len(components) - 1:
                os.fchmod(child, OWNER_DIRECTORY_MODE)
            os.close(descriptor)
            descriptor = child
        if descriptor_anchor and not components and create:
            os.fchmod(descriptor, OWNER_DIRECTORY_MODE)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_parent(path: str, *, create: bool) -> tuple[int, str]:
    raw = os.fspath(path)
    lexical = Path(raw).parts
    if not lexical or raw.endswith(os.sep):
        raise OSError("persistence artifact path is invalid")
    name = lexical[-1]
    if name in {"", ".", ".."}:
        raise OSError("persistence artifact name is invalid")

    parent = os.path.dirname(raw) or os.curdir
    descriptor = _open_directory(parent, create=create)
    return descriptor, name


def _refuse_artifact(descriptor: int, name: str) -> None:
    try:
        info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode):
        raise OSError(f"persistence artifact is a symbolic link: {name}")
    if not stat.S_ISREG(info.st_mode):
        raise OSError(f"persistence artifact is not a regular file: {name}")


def _new_stage(descriptor: int) -> tuple[int, str]:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    for _ in range(128):
        name = _STAGE_PREFIX + secrets.token_hex(12)
        try:
            return (
                os.open(name, flags, OWNER_FILE_MODE, dir_fd=descriptor),
                name,
            )
        except FileExistsError:
            continue
    raise FileExistsError("unable to allocate a persistence staging artifact")


def _refuse_symbolic_links(path: str) -> None:
    """Portable fallback: reject symlinks and descriptor traversal lexically."""
    raw = os.fspath(path)
    lexical = Path(raw).parts
    if any(component in {".", ".."} for component in lexical):
        raise OSError("persistence path contains a traversal component")

    if lexical[:4] == _PROC_FD_PREFIX:
        if len(lexical) < 5 or not lexical[4].isdigit():
            raise OSError("persistence descriptor anchor is invalid")
        descriptor = int(lexical[4])
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise NotADirectoryError(
                f"persistence descriptor is not a directory: {descriptor}"
            )
        current = Path(*lexical[:5])
        nodes = []
        for component in lexical[5:]:
            current /= component
            nodes.append(current)
    else:
        absolute = Path(os.path.abspath(raw))
        nodes = [*reversed(absolute.parents), absolute]

    for node in nodes:
        try:
            info = node.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise OSError(f"persistence path contains a symbolic link: {node}")


def ensure_owner_directory(path: str) -> None:
    """Create or harden a state directory so only its owner can traverse it."""
    if _secure_dirfd_available():
        descriptor = _open_directory(path, create=True)
        os.close(descriptor)
        return

    _refuse_symbolic_links(path)
    os.makedirs(path, mode=OWNER_DIRECTORY_MODE, exist_ok=True)
    _refuse_symbolic_links(path)
    os.chmod(path, OWNER_DIRECTORY_MODE)


def harden_owner_file(path: str) -> None:
    """Remove group/world permissions from a persisted artifact."""
    if _secure_dirfd_available():
        descriptor, name = _open_parent(path, create=False)
        try:
            _refuse_artifact(descriptor, name)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise OSError(
                        f"persisted artifact is not a regular file: {path}"
                    )
                os.fchmod(fd, OWNER_FILE_MODE)
            finally:
                os.close(fd)
        finally:
            os.close(descriptor)
        return

    _refuse_symbolic_links(path)
    os.chmod(path, OWNER_FILE_MODE)


def _atomic_write_json_secure(path: str, value: Any) -> None:
    descriptor, name = _open_parent(path, create=True)
    stage_name = ""
    try:
        _refuse_artifact(descriptor, name)
        stage_fd, stage_name = _new_stage(descriptor)
        try:
            with os.fdopen(stage_fd, "w", encoding="utf-8") as stream:
                json.dump(value, stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), OWNER_FILE_MODE)
        except BaseException:
            try:
                os.unlink(stage_name, dir_fd=descriptor)
            except FileNotFoundError:
                pass
            stage_name = ""
            raise

        _refuse_artifact(descriptor, name)
        os.replace(
            stage_name,
            name,
            src_dir_fd=descriptor,
            dst_dir_fd=descriptor,
        )
        stage_name = ""
        final_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
        try:
            if not stat.S_ISREG(os.fstat(final_fd).st_mode):
                raise OSError(f"persisted artifact is not a regular file: {path}")
            os.fchmod(final_fd, OWNER_FILE_MODE)
            os.fsync(final_fd)
        finally:
            os.close(final_fd)
        os.fsync(descriptor)
    finally:
        if stage_name:
            try:
                os.unlink(stage_name, dir_fd=descriptor)
            except FileNotFoundError:
                pass
        os.close(descriptor)


def _atomic_write_json_fallback(path: str, value: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    ensure_owner_directory(directory)
    _refuse_symbolic_links(path)
    fd, staged = tempfile.mkstemp(prefix=_STAGE_PREFIX, dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, OWNER_FILE_MODE)
        _refuse_symbolic_links(path)
        os.replace(staged, path)
        harden_owner_file(path)
    except BaseException:
        try:
            os.unlink(staged)
        except FileNotFoundError:
            pass
        raise


def atomic_write_json(path: str, value: Any) -> None:
    """Serialize, fsync, and atomically replace JSON without path races."""
    if _secure_dirfd_available():
        _atomic_write_json_secure(path, value)
    else:
        _atomic_write_json_fallback(path, value)
