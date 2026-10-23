"""Deterministic resident Body creation, verified reload, and atomic persistence."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import errno
import fcntl
import hmac
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from threading import RLock
from typing import Any, Iterator, NamedTuple

from .config import ResidentConfig
from .primer import build_primer
from .storage import ResidentStorage
from .vendor import vendored_symbol


class BodyDisabledError(RuntimeError):
    """Resident Body startup was disabled by configuration."""


class ResidencyError(RuntimeError):
    """Resident state cannot be loaded or persisted safely."""


class ResidentHandle(NamedTuple):
    organism: Any
    path: Path
    created: bool


_UMASK_LOCK = RLock()
_RENAME_EXCHANGE = 2


def _validate_owned_node(path: Path, *, directory: bool | None = None) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ResidencyError(f"resident node is missing: {path.name}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise ResidencyError(f"resident state contains a symbolic link: {path.name}")
    if directory is True and not stat.S_ISDIR(info.st_mode):
        raise ResidencyError(f"resident node is not a directory: {path.name}")
    if directory is False and not stat.S_ISREG(info.st_mode):
        raise ResidencyError(f"resident node is not a regular file: {path.name}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ResidencyError(f"resident node has unexpected ownership: {path.name}")
    return info


def _secure_tree(path: Path) -> None:
    _validate_owned_node(path, directory=True)
    os.chmod(path, 0o700, follow_symlinks=False)
    for node in path.rglob("*"):
        info = _validate_owned_node(node)
        if stat.S_ISDIR(info.st_mode):
            os.chmod(node, 0o700, follow_symlinks=False)
        elif stat.S_ISREG(info.st_mode):
            os.chmod(node, 0o600, follow_symlinks=False)
        else:
            raise ResidencyError(f"unsupported resident node type: {node.name}")


def _assert_safe_tree(path: Path, *, trusted_fd_root: bool = False) -> None:
    if trusted_fd_root:
        root_info = path.stat()
        if not stat.S_ISDIR(root_info.st_mode) or (
            hasattr(os, "getuid") and root_info.st_uid != os.getuid()
        ):
            raise ResidencyError("resident directory has unsafe type or ownership")
    else:
        root_info = _validate_owned_node(path, directory=True)
    if root_info.st_mode & 0o077:
        raise ResidencyError("resident directory permissions are not owner-only")
    for node in path.rglob("*"):
        info = _validate_owned_node(node)
        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise ResidencyError(f"unsupported resident node type: {node.name}")
        if info.st_mode & 0o077:
            raise ResidencyError(f"resident node permissions are not owner-only: {node.name}")


def _fsync_tree(path: Path) -> None:
    for node in path.rglob("*"):
        info = node.lstat()
        if stat.S_ISREG(info.st_mode):
            fd = os.open(node, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    for directory in sorted(
        (node for node in path.rglob("*") if node.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ) + [path]:
        fd = os.open(
            directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _fd_path(fd: int) -> Path:
    return Path(f"/proc/self/fd/{fd}")


def _atomic_exchange(parent_fd: int, old_name: str, new_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise ResidencyError("atomic resident replacement is unsupported on this platform")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        old_name.encode(),
        parent_fd,
        new_name.encode(),
        _RENAME_EXCHANGE,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
            raise ResidencyError(
                "atomic resident replacement is unsupported on this filesystem"
            )
        raise OSError(error, os.strerror(error))
    os.fsync(parent_fd)


def _remove_entry(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        shutil.rmtree(path)
    else:
        path.unlink()


@contextmanager
def _resident_lock(path: Path) -> Iterator[int]:
    parent = path.parent
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    parent_fd = os.open(parent, directory_flags)
    lock_dir_fd = -1
    lock_fd = -1
    try:
        parent_info = os.fstat(parent_fd)
        if not stat.S_ISDIR(parent_info.st_mode) or (
            hasattr(os, "getuid") and parent_info.st_uid != os.getuid()
        ):
            raise ResidencyError("resident parent has unsafe type or ownership")
        os.fchmod(parent_fd, 0o700)
        try:
            os.mkdir(".locks", 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        lock_dir_fd = os.open(".locks", directory_flags, dir_fd=parent_fd)
        lock_dir_info = os.fstat(lock_dir_fd)
        if not stat.S_ISDIR(lock_dir_info.st_mode) or (
            hasattr(os, "getuid") and lock_dir_info.st_uid != os.getuid()
        ):
            raise ResidencyError("resident lock directory has unsafe type or ownership")
        os.fchmod(lock_dir_fd, 0o700)
        lock_flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open(
            path.name + ".lock",
            lock_flags,
            0o600,
            dir_fd=lock_dir_fd,
        )
        lock_info = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_info.st_mode) or (
            hasattr(os, "getuid") and lock_info.st_uid != os.getuid()
        ):
            raise ResidencyError("resident lock has unsafe type or ownership")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield parent_fd
    finally:
        if lock_fd >= 0:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)
        if lock_dir_fd >= 0:
            os.close(lock_dir_fd)
        os.close(parent_fd)


def _save_resident_locked(organism: Any, path: Path, parent_fd: int) -> None:
    parent_view = _fd_path(parent_fd)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{path.name}.stage-", dir=parent_view)
    )
    os.chmod(stage, 0o700)
    try:
        with _UMASK_LOCK:
            previous_umask = os.umask(0o077)
            try:
                organism.save(str(stage))
            finally:
                os.umask(previous_umask)
        _secure_tree(stage)
        _fsync_tree(stage)
        try:
            target_info = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            target_info = None
        if target_info is not None:
            if not stat.S_ISDIR(target_info.st_mode) or stat.S_ISLNK(target_info.st_mode):
                raise ResidencyError("resident target has unsafe type")
            if hasattr(os, "getuid") and target_info.st_uid != os.getuid():
                raise ResidencyError("resident target has unexpected ownership")
            _atomic_exchange(parent_fd, path.name, stage.name)
            _remove_entry(stage)
        else:
            os.rename(
                stage.name,
                path.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
        _assert_safe_tree(parent_view / path.name)
    except Exception:
        _remove_entry(stage)
        raise


def save_resident(organism: Any, path: Path) -> None:
    """Publish a complete owner-only snapshot under an interprocess lock."""
    with _resident_lock(path) as parent_fd:
        _save_resident_locked(organism, path, parent_fd)


class ResidentBodyFactory:
    """Create one Body per Hermes profile, or load its verified sealed identity."""

    def __init__(self, config: ResidentConfig, *, hermes_home: str | Path | None = None):
        self.config = config
        self.storage = ResidentStorage(config, hermes_home=hermes_home)

    @staticmethod
    def _load_verified(organism_type: Any, path: Path) -> Any:
        _assert_safe_tree(path, trusted_fd_root=True)
        seal_path = path / "self_seal.json"
        if not seal_path.is_file() or seal_path.is_symlink():
            raise ResidencyError("resident self seal is missing")
        try:
            seal = json.loads(seal_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ResidencyError("resident self seal is malformed") from exc
        if (
            not isinstance(seal, dict)
            or set(seal) != {"fingerprint", "mac"}
            or not isinstance(seal.get("fingerprint"), str)
            or not isinstance(seal.get("mac"), str)
            or len(seal["fingerprint"]) != 16
            or len(seal["mac"]) != 64
            or any(character not in "0123456789abcdef" for character in seal["fingerprint"])
            or any(character not in "0123456789abcdef" for character in seal["mac"])
        ):
            raise ResidencyError("resident self seal has invalid fields")
        try:
            organism = organism_type.load(str(path), verify_seals=True)
        except Exception as exc:
            raise ResidencyError(
                f"resident self seal or identity verification failed: {type(exc).__name__}"
            ) from exc
        if not hmac.compare_digest(
            seal["fingerprint"],
            organism.body.key_fingerprint,
        ):
            raise ResidencyError("resident self seal fingerprint mismatch")
        if any(event.get("kind") == "autoimmune_risk" for event in organism.immune.log):
            raise ResidencyError("resident self seal verification failed")
        return organism

    def get_or_create(self, profile_id: str) -> ResidentHandle:
        if not self.config.body_enabled:
            raise BodyDisabledError("resident Body is disabled by configuration")
        path = self.storage.organism_path(profile_id)
        organism_type = vendored_symbol("core.organism", "Organism")
        with _resident_lock(path) as parent_fd:
            try:
                target_info = os.stat(
                    path.name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                target_info = None
            if target_info is not None:
                if not stat.S_ISDIR(target_info.st_mode) or stat.S_ISLNK(
                    target_info.st_mode
                ):
                    raise ResidencyError("resident path has unsafe type")
                resident_fd = os.open(
                    path.name,
                    os.O_RDONLY
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=parent_fd,
                )
                try:
                    organism = self._load_verified(
                        organism_type,
                        _fd_path(resident_fd),
                    )
                finally:
                    os.close(resident_fd)
                return ResidentHandle(organism, path, False)
            primer = build_primer(self.config)
            organism = organism_type.birth(
                identity=dict(primer.identity),
                truths=list(primer.truths),
                commandments=list(primer.commandments),
            )
            _save_resident_locked(organism, path, parent_fd)
            return ResidentHandle(organism, path, True)
