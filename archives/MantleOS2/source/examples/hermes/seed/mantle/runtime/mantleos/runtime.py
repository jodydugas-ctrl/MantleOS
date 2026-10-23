"""Small, host-independent MantleOS 2 Body runtime.

The module deliberately does not import Hermes. Hermes is the native NEST and
remains usable without this runtime or an AppAI MIND.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import math
import os
import secrets
import subprocess
import time
import uuid
from collections.abc import Callable, Iterable
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import PhysiologyState
from .nutrition import NutritionError, openrouter_completion, parse_openrouter_food, verify_openrouter_food
from .organs import redact_semantic_data

SCHEMA = "mantle.body.v2"
DEFAULT_LAYER_CAPACITY = 1_048_576
COMMUNICATION_NAME = "COMMUNICATION.TXT"


class MantleError(RuntimeError):
    """A gate or integrity condition prevented a Mantle operation."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


@contextmanager
def _exclusive_file(path: Path, *, timeout: float = 10.0):
    """Portable advisory lock for append and Heartbeat critical sections."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    started = time.monotonic()
    while True:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.monotonic() - started >= timeout:
                handle.close()
                raise MantleError(f"Timed out waiting for Body lock: {path.name}") from None
            time.sleep(0.05)
    try:
        yield
    finally:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _restrict_identity_key(path: Path, *, platform_name: str | None = None) -> None:
    """Restrict a Body identity key to the creating OS account."""

    platform_name = platform_name or os.name
    try:
        os.chmod(path, 0o600)
    except OSError as exc:
        raise MantleError("The Body identity key could not be restricted to its owner") from exc
    if platform_name != "nt":
        return

    try:
        identity = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        row = next(csv.reader(identity.stdout.splitlines()))
        principal_sid = row[1].strip()
    except (OSError, IndexError, StopIteration, csv.Error) as exc:
        raise MantleError("Windows did not identify the account creating the Body identity key") from exc
    if identity.returncode != 0 or not principal_sid.startswith("S-1-"):
        raise MantleError("Windows did not identify the account creating the Body identity key")
    command = [
        "icacls",
        str(path),
        "/inheritance:r",
        "/grant:r",
        f"*{principal_sid}:(F)",
        "*S-1-5-18:(F)",
        "*S-1-5-32-544:(F)",
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise MantleError("Windows could not apply a private ACL to the Body identity key") from exc
    if result.returncode != 0:
        raise MantleError("Windows could not apply a private ACL to the Body identity key")


@dataclass(frozen=True)
class BodyPaths:
    nest: Path

    @property
    def public(self) -> Path:
        return self.nest / "mantle"

    @property
    def private(self) -> Path:
        return self.nest / ".mantle"

    @property
    def key(self) -> Path:
        return self.private / "keys" / "body.key"

    @property
    def born(self) -> Path:
        return self.private / "self" / "born.enc"

    @property
    def primer(self) -> Path:
        return self.private / "self" / "primer.enc"

    @property
    def personality_candidate(self) -> Path:
        return self.private / "construction" / "PERSONALITY.CANDIDATE.md"

    @property
    def personality_evidence(self) -> Path:
        return self.private / "construction" / "personality-evidence.json"

    @property
    def personality_origin(self) -> Path:
        return self.private / "state" / "personality-origin.enc"

    @property
    def birth_candidate(self) -> Path:
        return self.private / "self" / "birth-candidate.enc"

    @property
    def birth_receipt(self) -> Path:
        return self.private / "self" / "first-heartbeat.enc"

    @property
    def prebirth(self) -> Path:
        return self.private / "prebirth.json"

    @property
    def vcw(self) -> Path:
        return self.private / "vcw"

    @property
    def snapshot(self) -> Path:
        return self.private / "state" / "nest-snapshot.enc"

    @property
    def communication_state(self) -> Path:
        return self.private / "state" / "communication.enc"

    @property
    def mind_frontier(self) -> Path:
        return self.private / "state" / "mind-frontier.enc"

    @property
    def mind_pending(self) -> Path:
        return self.private / "state" / "mind-pending"

    @property
    def host_heartbeats(self) -> Path:
        return self.private / "state" / "host-heartbeats"

    @property
    def openrouter_provider(self) -> Path:
        return self.private / "providers" / "openrouter.enc"

    @property
    def physiology(self) -> Path:
        return self.private / "state" / "physiology.enc"

    @property
    def communication(self) -> Path:
        return self.nest / COMMUNICATION_NAME


class BodyCipher:
    """Authenticated encryption owned by the Body and never exposed to a MIND."""

    MAGIC = b"MANTLE2-AESGCM\0"

    @staticmethod
    def require_available():
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError as exc:
            raise MantleError(
                "Birth requires the host's cryptography dependency. "
                "Install Hermes in its supported Python environment before birth."
            ) from exc
        return AESGCM

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise MantleError("Body key must be exactly 32 bytes")
        AESGCM = self.require_available()
        self._aead = AESGCM(key)

    def seal(self, value: bytes, *, purpose: str) -> bytes:
        nonce = secrets.token_bytes(12)
        ciphertext = self._aead.encrypt(nonce, value, purpose.encode("utf-8"))
        return self.MAGIC + nonce + ciphertext

    def open(self, value: bytes, *, purpose: str) -> bytes:
        if not value.startswith(self.MAGIC):
            raise MantleError("Encrypted Body data has an unknown format")
        offset = len(self.MAGIC)
        nonce = value[offset : offset + 12]
        return self._aead.decrypt(nonce, value[offset + 12 :], purpose.encode("utf-8"))


def _save_sealed_json(path: Path, cipher: BodyCipher, purpose: str, value: Any) -> None:
    _atomic_write(path, cipher.seal(canonical_json(value), purpose=purpose))


def _load_sealed_json(path: Path, cipher: BodyCipher, purpose: str, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(cipher.open(path.read_bytes(), purpose=purpose).decode("utf-8"))


@dataclass(frozen=True)
class Book:
    logical_id: str
    application: str
    book_id: str
    capacity: int = DEFAULT_LAYER_CAPACITY
    tome: str = "STATE_EVENT"
    dialect: str = "canonical-json-v2"


DEFAULT_BOOKS = (
    Book("layer-0", "Default Body / NEST", "book:default-body:v2"),
    Book("heart", "HEART", "book:heart:v2", tome="PHYSIOLOGY"),
    Book("communication", "User communication", "book:communication:v2", tome="COMMUNICATION"),
    Book("mind", "MIND interface", "book:mind:v2", tome="AGENT"),
    Book("senses", "Semantic sensory ingress", "book:senses:v2", tome="SENSORY"),
    Book("immune", "Immune findings", "book:immune:v2", tome="AUTHORITY"),
    Book("authority", "Capability grants", "book:authority:v2", tome="AUTHORITY"),
    Book("actions", "Admitted Limb actions", "book:actions:v2", tome="TOOLS"),
    Book("lineage", "Identity and lifecycle", "book:lineage:v2", tome="LINEAGE"),
)


class VCW:
    """Encrypted append-only memories grouped into extensible logical layers."""

    def __init__(self, root: Path, cipher: BodyCipher, books: Iterable[Book] = DEFAULT_BOOKS):
        self.root = root
        self.cipher = cipher
        self.books = {book.logical_id: book for book in books}

    def initialize(self) -> None:
        for book in self.books.values():
            if not self._physical_files(book):
                self._create_physical(book, 1, None, None)

    def _directory(self, book: Book) -> Path:
        return self.root / book.logical_id

    def _physical_files(self, book: Book) -> list[Path]:
        directory = self._directory(book)
        return sorted(directory.glob("*.jsonl")) if directory.exists() else []

    def _header(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        except (OSError, IndexError, json.JSONDecodeError) as exc:
            raise MantleError(f"Invalid VCW physical layer: {path}") from exc

    def _tail(self, path: Path) -> tuple[int, str]:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) == 1:
            header = json.loads(lines[0])
            return 0, header["header_hash"]
        record = json.loads(lines[-1])
        return int(record["sequence"]), str(record["hash"])

    def _create_physical(
        self, book: Book, sequence: int, extension_of: str | None, previous_tail_hash: str | None
    ) -> Path:
        directory = self._directory(book)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{sequence:06d}.jsonl"
        if path.exists():
            return path
        header = {
            "schema": "mantle.vcw.physical-layer.v2",
            "logical_layer": book.logical_id,
            "application": book.application,
            "book_id": book.book_id,
            "tome": book.tome,
            "dialect": book.dialect,
            "physical_sequence": sequence,
            "extension_of": extension_of,
            "previous_tail_hash": previous_tail_hash,
            "created_at": utc_now(),
        }
        header["header_hash"] = sha256_bytes(canonical_json(header))
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(header, sort_keys=True, ensure_ascii=False) + "\n")
        return path

    def append(self, logical_id: str, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        with _exclusive_file(self.root / ".append.lock"):
            return self._append_unlocked(logical_id, kind, redact_semantic_data(data))

    def _append_unlocked(self, logical_id: str, kind: str, data: dict[str, Any]) -> dict[str, Any]:
        if logical_id not in self.books:
            raise MantleError(f"No Book exists for logical VCW layer {logical_id!r}")
        book = self.books[logical_id]
        files = self._physical_files(book)
        if not files:
            self.initialize()
            files = self._physical_files(book)
        path = files[-1]
        local_sequence, previous_hash = self._tail(path)
        timestamp = utc_now()
        payload = canonical_json({"kind": kind, "data": data})
        aad = f"{logical_id}|{path.stem}|{local_sequence + 1}|{timestamp}|{previous_hash}"
        sealed = self.cipher.seal(payload, purpose=aad)
        envelope = {
            "sequence": local_sequence + 1,
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "nonce_and_ciphertext": base64.b64encode(sealed).decode("ascii"),
        }
        envelope["hash"] = sha256_bytes(canonical_json(envelope))
        encoded = json.dumps(envelope, sort_keys=True, ensure_ascii=False) + "\n"
        if path.stat().st_size + len(encoded.encode("utf-8")) > book.capacity and local_sequence:
            path = self._create_physical(book, len(files) + 1, files[-1].name, previous_hash)
            local_sequence, previous_hash = self._tail(path)
            timestamp = utc_now()
            aad = f"{logical_id}|{path.stem}|1|{timestamp}|{previous_hash}"
            sealed = self.cipher.seal(payload, purpose=aad)
            envelope = {
                "sequence": 1,
                "timestamp": timestamp,
                "previous_hash": previous_hash,
                "nonce_and_ciphertext": base64.b64encode(sealed).decode("ascii"),
            }
            envelope["hash"] = sha256_bytes(canonical_json(envelope))
            encoded = json.dumps(envelope, sort_keys=True, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return {"logical_layer": logical_id, "physical_layer": path.name, "hash": envelope["hash"]}

    def verify(self) -> dict[str, Any]:
        physical_count = 0
        record_count = 0
        for book in self.books.values():
            previous_physical_tail: str | None = None
            for index, path in enumerate(self._physical_files(book), start=1):
                physical_count += 1
                lines = path.read_text(encoding="utf-8").splitlines()
                if not lines:
                    raise MantleError(f"Empty VCW physical layer: {path}")
                header = json.loads(lines[0])
                claimed_header_hash = header.pop("header_hash")
                if sha256_bytes(canonical_json(header)) != claimed_header_hash:
                    raise MantleError(f"VCW header hash failed: {path}")
                if (
                    header["book_id"] != book.book_id
                    or header.get("tome") != book.tome
                    or header.get("dialect") != book.dialect
                    or header["physical_sequence"] != index
                ):
                    raise MantleError(f"VCW Book or extension sequence mismatch: {path}")
                if index > 1 and header["previous_tail_hash"] != previous_physical_tail:
                    raise MantleError(f"VCW extension does not continue its parent: {path}")
                previous_hash = claimed_header_hash
                for expected_sequence, line in enumerate(lines[1:], start=1):
                    record_count += 1
                    envelope = json.loads(line)
                    claimed_hash = envelope.pop("hash")
                    if (
                        envelope["sequence"] != expected_sequence
                        or envelope["previous_hash"] != previous_hash
                    ):
                        raise MantleError(f"VCW record chain failed: {path}:{expected_sequence + 1}")
                    if sha256_bytes(canonical_json(envelope)) != claimed_hash:
                        raise MantleError(f"VCW record hash failed: {path}:{expected_sequence + 1}")
                    aad = (
                        f"{book.logical_id}|{path.stem}|{expected_sequence}|"
                        f"{envelope['timestamp']}|{previous_hash}"
                    )
                    self.cipher.open(base64.b64decode(envelope["nonce_and_ciphertext"]), purpose=aad)
                    previous_hash = claimed_hash
                previous_physical_tail = previous_hash
        return {"ok": True, "physical_layers": physical_count, "records": record_count}

    def events_after(
        self, frontier: dict[str, str] | None = None, *, limit: int = 20
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Return a bounded chronological batch and its proposed frontier.

        A frontier stores the last acknowledged record hash per logical layer.
        It advances only over events included in the returned batch.
        """
        frontier = dict(frontier or {})
        events: list[dict[str, Any]] = []
        for book in self.books.values():
            marker = frontier.get(book.logical_id)
            marker_found = marker is None
            for path in self._physical_files(book):
                lines = path.read_text(encoding="utf-8").splitlines()
                previous_hash = json.loads(lines[0])["header_hash"]
                for line in lines[1:]:
                    envelope = json.loads(line)
                    record_hash = envelope["hash"]
                    if not marker_found:
                        if record_hash == marker:
                            marker_found = True
                        previous_hash = record_hash
                        continue
                    aad = (
                        f"{book.logical_id}|{path.stem}|{envelope['sequence']}|"
                        f"{envelope['timestamp']}|{previous_hash}"
                    )
                    payload = json.loads(
                        self.cipher.open(
                            base64.b64decode(envelope["nonce_and_ciphertext"]), purpose=aad
                        ).decode("utf-8")
                    )
                    events.append(
                        {
                            "logical_layer": book.logical_id,
                            "physical_layer": path.name,
                            "sequence": envelope["sequence"],
                            "timestamp": envelope["timestamp"],
                            "hash": record_hash,
                            "kind": payload["kind"],
                            "data": payload["data"],
                        }
                    )
                    previous_hash = record_hash
            if not marker_found:
                raise MantleError(f"MIND frontier is not present in VCW layer {book.logical_id!r}")
        events.sort(
            key=lambda event: (
                event["timestamp"],
                event["logical_layer"],
                event["physical_layer"],
                event["sequence"],
            )
        )
        selected = events[: max(0, limit)]
        proposed = dict(frontier)
        for event in selected:
            proposed[event["logical_layer"]] = event["hash"]
        return selected, proposed


class MantleBody:
    """The autonomic Body. A MIND is an optional caller, never a prerequisite."""

    def __init__(self, nest: str | Path):
        resolved = Path(nest).resolve()
        self.paths = BodyPaths(resolved)
        if not self.paths.public.is_dir():
            raise MantleError(f"No Mantle public delta found in NEST: {resolved}")

    @property
    def is_born(self) -> bool:
        return self.paths.key.is_file() and self.paths.born.is_file()

    def _cipher(self) -> BodyCipher:
        if not self.paths.key.exists():
            raise MantleError("This organism has not been born")
        return BodyCipher(self.paths.key.read_bytes())

    def _vcw(self) -> VCW:
        return VCW(self.paths.vcw, self._cipher())

    @staticmethod
    def _receipt_name(*parts: str) -> str:
        return sha256_bytes("\0".join(parts).encode("utf-8")) + ".enc"

    def _construction_proof(self) -> dict[str, Any]:
        """Verify that reviewed prebirth tissue still matches construction evidence."""
        if not self.paths.prebirth.is_file():
            raise MantleError("Assimilation construction has no prebirth checkpoint")
        try:
            prebirth = json.loads(self.paths.prebirth.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MantleError("The prebirth checkpoint is unreadable") from exc
        if prebirth.get("schema") != "mantle.prebirth.v2":
            raise MantleError("The prebirth checkpoint has an unknown schema")

        manifest_path = self.paths.public / "ASSIMILATION.json"
        if not manifest_path.is_file():
            raise MantleError("The public assimilation manifest is missing")
        expected_manifest = prebirth.get("public_manifest_sha256")
        if not isinstance(expected_manifest, str) or len(expected_manifest) != 64:
            raise MantleError("The prebirth checkpoint does not bind the public manifest")
        actual_manifest = sha256_file(manifest_path)
        if actual_manifest != expected_manifest:
            raise MantleError("The public assimilation manifest changed after construction")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MantleError("The public assimilation manifest is unreadable") from exc
        if manifest.get("schema") != "mantle.assimilation.v2":
            raise MantleError("The public assimilation manifest has an unknown schema")
        if manifest.get("status") != "constructed-not-born":
            raise MantleError("The public assimilation manifest is not a prebirth construction")

        primer_candidate = prebirth.get("primer_candidate")
        if isinstance(primer_candidate, dict):
            expected_personality = primer_candidate.get("personality_sha256")
            expected_evidence = primer_candidate.get("evidence_sha256")
            if expected_personality and (
                not self.paths.personality_candidate.is_file()
                or sha256_file(self.paths.personality_candidate) != expected_personality
            ):
                raise MantleError("The private Personality candidate changed after construction")
            if expected_evidence and (
                not self.paths.personality_evidence.is_file()
                or sha256_file(self.paths.personality_evidence) != expected_evidence
            ):
                raise MantleError("The private Personality evidence changed after construction")

        delta = manifest.get("delta")
        if not isinstance(delta, dict):
            raise MantleError("The public assimilation manifest has no delta proof")
        declared = delta.get("paths")
        checksums = delta.get("sha256")
        if not isinstance(declared, list) or not isinstance(checksums, dict):
            raise MantleError("The public assimilation manifest has an invalid delta proof")
        declared_paths = set()
        for value in declared:
            if not isinstance(value, str):
                raise MantleError("The public delta contains a non-path declaration")
            candidate = (self.paths.nest / value).resolve()
            try:
                candidate.relative_to(self.paths.public.resolve())
            except ValueError as exc:
                raise MantleError(f"Public delta path escapes mantle/: {value}") from exc
            declared_paths.add(value)
        if len(declared_paths) != len(declared):
            raise MantleError("The public delta contains duplicate path declarations")

        manifest_relative = "mantle/ASSIMILATION.json"
        expected_hashed = declared_paths - {manifest_relative}
        if set(checksums) != expected_hashed:
            raise MantleError("The public delta path and checksum declarations disagree")
        for relative in sorted(expected_hashed):
            path = self.paths.nest / relative
            expected = checksums.get(relative)
            if not path.is_file():
                raise MantleError(f"Public candidate tissue is missing: {relative}")
            if not isinstance(expected, str) or sha256_file(path) != expected:
                raise MantleError(f"Public candidate tissue changed after construction: {relative}")

        actual_paths = {
            path.relative_to(self.paths.nest).as_posix()
            for path in self.paths.public.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        }
        undeclared = sorted(actual_paths - declared_paths)
        missing = sorted(declared_paths - actual_paths)
        if undeclared:
            raise MantleError(f"Undeclared public candidate tissue is present: {undeclared[0]}")
        if missing:
            raise MantleError(f"Declared public candidate tissue is missing: {missing[0]}")

        # Direct nerve bytes are candidate tissue too. Before birth, every
        # mapped seam must still match its final construction hash.
        nerve_map = manifest.get("nerve_map", [])
        final_by_path: dict[str, str] = {}
        for nerve in nerve_map:
            if not isinstance(nerve, dict):
                raise MantleError("The Nerve Map contains an invalid record")
            anchor = nerve.get("anchor", {})
            path = anchor.get("path") if isinstance(anchor, dict) else None
            after = nerve.get("after_sha256")
            if not isinstance(path, str) or not isinstance(after, str):
                raise MantleError("The Nerve Map does not bind a source seam")
            final_by_path[path] = after
        for relative, expected in final_by_path.items():
            path = self.paths.nest / relative
            if not path.is_file() or sha256_file(path) != expected:
                raise MantleError(f"Direct nerve tissue changed after construction: {relative}")

        gitignore = self.paths.nest / ".gitignore"
        gitignore_text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
        required_ignores = ("/.mantle/", "/COMMUNICATION.TXT", "/Food.txt")
        if any(line not in gitignore_text.splitlines() for line in required_ignores):
            raise MantleError("The NEST no longer excludes private Mantle surfaces from Git")
        return {
            "ok": True,
            "status": "constructed-not-born",
            "manifest_sha256": actual_manifest,
            "declared_files": len(declared_paths),
            "verified_files": len(expected_hashed),
            "verified_nerve_files": len(final_by_path),
            "birth_authorized": False,
        }

    def status(self) -> dict[str, Any]:
        prebirth = None
        if self.paths.prebirth.exists():
            with suppress(OSError, UnicodeDecodeError, json.JSONDecodeError):
                prebirth = json.loads(self.paths.prebirth.read_text(encoding="utf-8"))
        result: dict[str, Any] = {
            "schema": SCHEMA,
            "nest": str(self.paths.nest),
            "public_delta": str(self.paths.public),
            "status": "born" if self.is_born else "constructed-not-born",
            "prebirth": prebirth,
            "mind": "not-configured",
        }
        if not self.is_born:
            try:
                result["construction_integrity"] = self._construction_proof()
            except MantleError as exc:
                result["status"] = "construction-invalid"
                result["construction_integrity"] = {"ok": False, "error": str(exc)}
        if self.is_born:
            cipher = self._cipher()
            result["identity"] = _load_sealed_json(
                self.paths.born,
                cipher,
                "body-identity",
                {},
            )
            provider = _load_sealed_json(
                self.paths.openrouter_provider,
                cipher,
                "provider:openrouter",
                {},
            )
            if provider:
                result["mind"] = {
                    "provider": "openrouter",
                    "model": provider.get("model"),
                    "status": provider.get("status"),
                }
            result["physiology"] = _load_sealed_json(
                self.paths.physiology,
                cipher,
                "physiology",
                {"state": PhysiologyState.ACTIVE.value},
            )
        return result

    def set_physiology(self, state: PhysiologyState | str, *, reason: str) -> dict[str, Any]:
        if not self.is_born:
            raise MantleError("Physiology cannot change before birth")
        try:
            resolved = state if isinstance(state, PhysiologyState) else PhysiologyState(state)
        except ValueError as exc:
            raise MantleError(f"Unknown physiology state: {state}") from exc
        if resolved is PhysiologyState.CONSTRUCTION or resolved is PhysiologyState.UNBORN:
            raise MantleError("A born organism cannot return to a prebirth physiology state")
        record = {"state": resolved.value, "reason": reason, "changed_at": utc_now()}
        _save_sealed_json(self.paths.physiology, self._cipher(), "physiology", record)
        self._vcw().append("heart", "physiology.changed", record)
        return record

    def primer_context(self, events: list[dict[str, Any]]) -> str:
        """Build the Body-owned, Primer-first context for an AppAI MIND call.

        The identity key is used only to open SELF inside the Body.  It and the
        encrypted source records are never returned to the MIND.
        """
        if not self.is_born:
            raise MantleError("Primer context is unavailable before birth")
        commandments, personality = self._primer_components()
        safe_events = [
            {
                "logical_layer": event.get("logical_layer"),
                "kind": event.get("kind"),
                "recorded_at": event.get("recorded_at"),
                "data": event.get("data"),
                "hash": event.get("hash"),
            }
            for event in events
        ]
        return (
            "<APPAI_PRIMER>\n"
            + commandments
            + "\n\n"
            + personality
            + "\n</APPAI_PRIMER>\n\n"
            + "<BODY_CONTINUITY>\n"
            + json.dumps(safe_events, sort_keys=True, ensure_ascii=False)
            + "\n</BODY_CONTINUITY>"
        )

    def _primer_components(self) -> tuple[str, str]:
        """Load the permanent two-component Primer, including legacy envelopes."""
        primer = _load_sealed_json(self.paths.primer, self._cipher(), "primer", {})
        if not isinstance(primer, dict):
            raise MantleError("The sealed Primer has an invalid format")
        commandments = primer.get("commandments")
        personality = primer.get("personality")
        if not isinstance(commandments, str) or not commandments.strip():
            raise MantleError("The sealed Primer is missing Commandments")
        if not isinstance(personality, str) or not personality.strip():
            raise MantleError("The sealed Primer is missing Personality")
        return commandments, personality

    def _verify_primer_origin(self) -> dict[str, Any]:
        commandments, personality = self._primer_components()
        origin = _load_sealed_json(
            self.paths.personality_origin,
            self._cipher(),
            "personality-origin",
            {},
        )
        if not origin:
            return {"ok": True, "origin": "legacy-unavailable"}
        if not isinstance(origin, dict) or origin.get("schema") != "mantle.personality-origin.v2":
            raise MantleError("The sealed Personality origin has an unknown format")
        if origin.get("personality_sha256") != sha256_bytes(personality.encode("utf-8")):
            raise MantleError("The permanent Personality no longer matches its origin")
        if origin.get("commandments_sha256") != sha256_bytes(commandments.encode("utf-8")):
            raise MantleError("The sealed Commandments no longer match the Primer origin")
        return {"ok": True, "origin": "verified"}

    def birth(self, name: str, *, approved: bool = False) -> dict[str, Any]:
        if not approved:
            raise MantleError("Birth requires a separate explicit approval")
        if self.is_born:
            raise MantleError("This organism is already born")
        if not self.paths.prebirth.exists():
            raise MantleError("Assimilation construction has no prebirth checkpoint")
        if not name.strip():
            raise MantleError("Birth requires a confirmed identity name")
        construction_proof = self._construction_proof()
        prebirth = json.loads(self.paths.prebirth.read_text(encoding="utf-8"))
        if prebirth.get("gates", {}).get("primer") != "ready-for-birth-review":
            raise MantleError("The Primer candidate is not ready for a separate birth review")
        commandments_path = self.paths.public / "primer" / "COMMANDMENTS.md"
        if not commandments_path.is_file() or not commandments_path.read_text(encoding="utf-8").strip():
            raise MantleError("Primer candidate is missing COMMANDMENTS.md")
        if not self.paths.personality_candidate.is_file():
            raise MantleError("The unique Personality candidate is missing")
        primer_candidate = prebirth.get("primer_candidate", {})
        if primer_candidate.get("personality_sha256") != sha256_file(self.paths.personality_candidate):
            raise MantleError("The approved Personality candidate changed after review")
        try:
            personality_bytes = self.paths.personality_candidate.read_bytes()
            personality = personality_bytes.decode("utf-8")
            commandments_bytes = commandments_path.read_bytes()
            commandments = commandments_bytes.decode("utf-8")
            evidence_bytes = self.paths.personality_evidence.read_bytes()
            personality_evidence = json.loads(evidence_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MantleError("The approved Primer construction material is unreadable") from exc

        # Preflight before creating even a candidate key. Construction may be
        # inspected on machines that cannot safely birth the organism.
        BodyCipher.require_available()
        self.paths.key.parent.mkdir(parents=True, exist_ok=True)
        created_key = False
        if not self.paths.key.exists():
            with self.paths.key.open("xb") as handle:
                handle.write(secrets.token_bytes(32))
            created_key = True
        try:
            _restrict_identity_key(self.paths.key)
        except MantleError:
            if created_key:
                with suppress(OSError):
                    self.paths.key.unlink()
            raise
        cipher = self._cipher()
        identity = _load_sealed_json(self.paths.birth_candidate, cipher, "birth-candidate", {})
        if identity and identity.get("name") != name.strip():
            raise MantleError(
                f"An interrupted birth already prepared identity {identity.get('name')!r}; "
                "resume with the same confirmed name"
            )
        if not identity:
            identity = {
                "schema": "mantle.identity.v2",
                "organism_id": str(uuid.uuid4()),
                "name": name.strip(),
                "prepared_at": utc_now(),
                "default_body": "Layer 0 / NEST",
                "construction_manifest_sha256": construction_proof["manifest_sha256"],
            }
            _save_sealed_json(self.paths.birth_candidate, cipher, "birth-candidate", identity)
        expected_origin = {
            "schema": "mantle.personality-origin.v2",
            "personality_sha256": sha256_bytes(personality_bytes),
            "commandments_sha256": sha256_bytes(commandments_bytes),
            "evidence_sha256": sha256_bytes(evidence_bytes),
            "evidence": personality_evidence,
        }
        existing_origin = _load_sealed_json(
            self.paths.personality_origin,
            cipher,
            "personality-origin",
            {},
        )
        if existing_origin and existing_origin != expected_origin:
            raise MantleError("An interrupted birth has conflicting Personality origin evidence")
        if not existing_origin:
            _save_sealed_json(
                self.paths.personality_origin,
                cipher,
                "personality-origin",
                expected_origin,
            )

        primer = {"commandments": commandments, "personality": personality}
        existing_primer = _load_sealed_json(self.paths.primer, cipher, "primer", {})
        if existing_primer != primer:
            if existing_primer:
                legacy_components = {
                    "commandments": existing_primer.get("commandments"),
                    "personality": existing_primer.get("personality"),
                } if isinstance(existing_primer, dict) else {}
                if legacy_components != primer:
                    raise MantleError("An interrupted birth has a conflicting sealed Primer")
            _save_sealed_json(self.paths.primer, cipher, "primer", primer)

        heartbeat = _load_sealed_json(self.paths.birth_receipt, cipher, "first-heartbeat", {})
        if not heartbeat:
            heartbeat = self.heartbeat(
                reason="birth",
                _allow_unsealed_identity=True,
                _birth_identity={"organism_id": identity["organism_id"], "name": identity["name"]},
            )
            # This recovery receipt closes the narrow crash window between a
            # completed first Heartbeat and the final born-state write.
            _save_sealed_json(self.paths.birth_receipt, cipher, "first-heartbeat", heartbeat)
        identity["born_at"] = heartbeat["completed_at"]
        identity["first_heartbeat"] = heartbeat
        _save_sealed_json(self.paths.born, cipher, "body-identity", identity)
        with suppress(OSError):
            self.paths.personality_candidate.unlink()
        with suppress(OSError):
            self.paths.personality_evidence.unlink()
        return identity

    def _ensure_communication_file(self) -> None:
        if self.paths.communication.exists():
            return
        text = (
            "MantleOS 2 universal communication surface\n"
            "This file is intentionally unencrypted. Do not place secrets here.\n"
            "Write a single message after USER>, then save the file.\n\n"
            "USER> \n"
        )
        self.paths.communication.write_text(text, encoding="utf-8", newline="\n")

    def speak(self, message: str) -> dict[str, Any]:
        """Commit one user message and run the same full unscheduled Heartbeat."""
        if not self.is_born:
            raise MantleError("Communication cannot begin before birth")
        if not message.strip():
            raise MantleError("Communication requires a non-empty message")
        self._ensure_communication_file()
        with self.paths.communication.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"USER> {message.strip()}\n")
        return self.heartbeat(reason="direct-user-message")

    def _snapshot_nest(self, cipher: BodyCipher) -> dict[str, Any]:
        previous = _load_sealed_json(self.paths.snapshot, cipher, "nest-snapshot", {"files": {}})
        previous_files = previous.get("files", {})
        current: dict[str, dict[str, Any]] = {}
        for root, directories, files in os.walk(self.paths.nest):
            directories[:] = sorted(d for d in directories if d not in {".git", ".mantle", "__pycache__"})
            for filename in sorted(files):
                path = Path(root) / filename
                relative = path.relative_to(self.paths.nest).as_posix()
                if relative == COMMUNICATION_NAME or path.is_symlink():
                    continue
                try:
                    stat = path.stat()
                    old = previous_files.get(relative)
                    if old and old.get("size") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns:
                        digest = old["sha256"]
                    else:
                        digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    current[relative] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
                except OSError:
                    continue
        added = sorted(set(current) - set(previous_files))
        removed = sorted(set(previous_files) - set(current))
        changed = sorted(
            path
            for path in set(current) & set(previous_files)
            if current[path]["sha256"] != previous_files[path]["sha256"]
        )
        snapshot = {"captured_at": utc_now(), "files": current}
        _save_sealed_json(self.paths.snapshot, cipher, "nest-snapshot", snapshot)
        summary = {
            "file_count": len(current),
            "aggregate_sha256": sha256_bytes(canonical_json({k: v["sha256"] for k, v in current.items()})),
            "added_count": len(added),
            "changed_count": len(changed),
            "removed_count": len(removed),
            "added_sample": added[:100],
            "changed_sample": changed[:100],
            "removed_sample": removed[:100],
            "sample_truncated": any(len(group) > 100 for group in (added, changed, removed)),
        }
        return summary

    def _communication_turn(
        self, cipher: BodyCipher, responder: Callable[[str], str] | None
    ) -> dict[str, Any] | None:
        self._ensure_communication_file()
        lines = self.paths.communication.read_text(encoding="utf-8").splitlines()
        candidates = [
            (index, line[5:].strip())
            for index, line in enumerate(lines)
            if line.startswith("USER>") and line[5:].strip()
        ]
        if not candidates:
            return None
        index, message = candidates[-1]
        signature = sha256_bytes(f"{index}:{message}".encode())
        state = _load_sealed_json(self.paths.communication_state, cipher, "communication-state", {})
        if state.get("last_user_signature") == signature:
            return None

        self._vcw().append(
            "communication",
            "user.message",
            {"message": message, "semantic_commit": "file-save"},
        )
        if responder is None:
            response = (
                "Received and recorded. The AppAI MIND is not configured; "
                "the Body will carry this message forward."
            )
            mind_state = "not-configured"
        else:
            try:
                response = responder(message)
                mind_state = "responded"
            except Exception as exc:
                response = "Received and recorded. The configured MIND is temporarily unavailable."
                mind_state = "unavailable"
                self._vcw().append(
                    "mind",
                    "mind.call.failed",
                    {"error_type": type(exc).__name__, "message_preserved": True},
                )
        with self.paths.communication.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"APPAI> {response}\n\nUSER> \n")
        self._vcw().append("communication", "appai.response", {"response": response, "mind": mind_state})
        _save_sealed_json(
            self.paths.communication_state,
            cipher,
            "communication-state",
            {"last_user_signature": signature, "processed_at": utc_now()},
        )
        return {"user_message_recorded": True, "mind": mind_state}

    def digest_food(
        self,
        path: str | Path,
        *,
        probe: Callable[[Any], dict[str, Any]] = verify_openrouter_food,
        retry: bool = False,
    ) -> dict[str, Any]:
        """Securely store and verify an OpenRouter Food delivery."""
        if not self.is_born:
            raise MantleError("Food cannot be digested before birth")
        source = Path(path).resolve()
        try:
            food = parse_openrouter_food(source.read_bytes())
        except (OSError, NutritionError) as exc:
            raise MantleError(str(exc)) from exc
        cipher = self._cipher()
        previous = _load_sealed_json(
            self.paths.openrouter_provider,
            cipher,
            "provider:openrouter",
            {},
        )
        if previous.get("source_sha256") == food.source_sha256 and not retry:
            return {
                "status": previous.get("status", "unknown"),
                "provider": "openrouter",
                "model": previous.get("model", food.model),
                "already_digested": True,
            }
        provider = {
            "schema": "mantle.provider.openrouter.v2",
            "provider": "openrouter",
            "api_key": food.api_key,
            "key_fingerprint": food.key_fingerprint,
            "model": food.model,
            "source_sha256": food.source_sha256,
            "status": "stored-unverified",
            "stored_at": utc_now(),
        }
        _save_sealed_json(
            self.paths.openrouter_provider,
            cipher,
            "provider:openrouter",
            provider,
        )
        self._vcw().append(
            "heart",
            "nutrition.stored",
            {
                "kind": "openrouter-credential",
                "source_sha256": food.source_sha256,
                "key_fingerprint": food.key_fingerprint,
                "model": food.model,
            },
        )
        try:
            verification = probe(food)
        except Exception as exc:
            provider["status"] = "verification-failed"
            provider["verified_at"] = utc_now()
            provider["failure_type"] = type(exc).__name__
            _save_sealed_json(
                self.paths.openrouter_provider,
                cipher,
                "provider:openrouter",
                provider,
            )
            self._vcw().append(
                "mind",
                "provider.verification-failed",
                {
                    "provider": "openrouter",
                    "model": food.model,
                    "key_fingerprint": food.key_fingerprint,
                    "failure_type": type(exc).__name__,
                },
            )
            self._scrub_consumed_food(source, food.source_sha256, "verification-failed")
            raise MantleError("OpenRouter Food was stored securely but verification failed") from exc

        provider["status"] = "active"
        provider["verified_at"] = utc_now()
        provider["selected_model"] = verification.get("selected_model", food.model)
        _save_sealed_json(
            self.paths.openrouter_provider,
            cipher,
            "provider:openrouter",
            provider,
        )
        allowed = {
            "ok",
            "requested_model",
            "selected_model",
            "response_id",
            "response_chars",
            "usage",
        }
        safe_verification = {key: value for key, value in verification.items() if key in allowed}
        self._vcw().append(
            "mind",
            "provider.verified",
            {
                "provider": "openrouter",
                "key_fingerprint": food.key_fingerprint,
                **safe_verification,
            },
        )
        self._scrub_consumed_food(source, food.source_sha256, "active")
        return {"status": "active", "provider": "openrouter", **safe_verification}

    def _scrub_consumed_food(self, source: Path, source_sha256: str, status: str) -> None:
        """Remove plaintext secret only for the conventional in-NEST Food file."""
        if source != (self.paths.nest / "Food.txt").resolve():
            return
        receipt = (
            "MantleOS Food receipt\n"
            f"Consumed: {utc_now()}\n"
            f"Source SHA-256: {source_sha256}\n"
            f"Status: {status}\n"
            "The credential is stored in encrypted private Body state.\n"
        )
        _atomic_write(source, receipt.encode("utf-8"))

    def _default_mind_responder(self) -> Callable[[str], str] | None:
        if not self.is_born or not self.paths.openrouter_provider.exists():
            return None
        provider = _load_sealed_json(
            self.paths.openrouter_provider,
            self._cipher(),
            "provider:openrouter",
            {},
        )
        if provider.get("status") != "active":
            return None

        def respond(message: str) -> str:
            result = openrouter_completion(provider["api_key"], provider["model"], message)
            self._vcw().append(
                "mind",
                "mind.call.completed",
                {
                    "provider": "openrouter",
                    "requested_model": provider["model"],
                    "selected_model": result["selected_model"],
                    "response_id": result["response_id"],
                    "usage": result["usage"],
                },
            )
            return result["content"]

        return respond

    def _auto_digest_food(self) -> dict[str, Any] | None:
        source = self.paths.nest / "Food.txt"
        if not self.is_born or not source.is_file():
            return None
        try:
            if source.read_bytes().startswith(b"MantleOS Food receipt"):
                return None
            return self.digest_food(source)
        except Exception as exc:
            self._vcw().append(
                "heart",
                "nutrition.failed",
                {"error_type": type(exc).__name__, "source": "Food.txt"},
            )
            return {"status": "failed", "error_type": type(exc).__name__}

    def heartbeat(
        self,
        *,
        reason: str = "scheduled",
        responder: Callable[[str], str] | None = None,
        _allow_unsealed_identity: bool = False,
        _birth_identity: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        with _exclusive_file(self.paths.private / "state" / ".heartbeat.lock"):
            return self._heartbeat_unlocked(
                reason=reason,
                responder=responder,
                _allow_unsealed_identity=_allow_unsealed_identity,
                _birth_identity=_birth_identity,
            )

    def _heartbeat_unlocked(
        self,
        *,
        reason: str,
        responder: Callable[[str], str] | None,
        _allow_unsealed_identity: bool,
        _birth_identity: dict[str, str] | None,
    ) -> dict[str, Any]:
        if not self.is_born and not _allow_unsealed_identity:
            raise MantleError("Heartbeat cannot begin before the birth gate")
        cipher = self._cipher()
        vcw = VCW(self.paths.vcw, cipher)
        vcw.initialize()
        heartbeat_id = str(uuid.uuid4())
        started = utc_now()
        vcw.append(
            "heart",
            "heartbeat.started",
            {"heartbeat_id": heartbeat_id, "reason": reason, "started_at": started},
        )
        if _birth_identity is not None:
            vcw.append(
                "layer-0",
                "assimilation.baseline",
                json.loads(self.paths.prebirth.read_text(encoding="utf-8")),
            )
            vcw.append("heart", "birth.prepared", _birth_identity)
        nest = self._snapshot_nest(cipher)
        vcw.append("layer-0", "nest.state", nest)
        nutrition = self._auto_digest_food()
        if responder is None:
            responder = self._default_mind_responder()
        communication = self._communication_turn(cipher, responder)
        if communication is not None:
            mind_state = communication["mind"]
        elif responder is not None:
            mind_state = "configured-idle"
        else:
            mind_state = "not-configured"
        physiology = _load_sealed_json(
            self.paths.physiology,
            cipher,
            "physiology",
            {},
        )
        if not physiology:
            physiology = {
                "state": PhysiologyState.ACTIVE.value,
                "reason": "birth" if _birth_identity is not None else "heartbeat",
                "changed_at": utc_now(),
            }
            _save_sealed_json(self.paths.physiology, cipher, "physiology", physiology)
            vcw.append("heart", "physiology.changed", physiology)
        proof = vcw.verify()
        completed = utc_now()
        result = {
            "heartbeat_id": heartbeat_id,
            "reason": reason,
            "started_at": started,
            "completed_at": completed,
            "phases": ["sense", "record", "digest", "communicate", "mind", "verify", "checkpoint"],
            "nest": nest,
            "communication": communication,
            "nutrition": nutrition,
            "mind": mind_state,
            "physiology": physiology,
            "proof": proof,
        }
        vcw.append("heart", "heartbeat.completed", result)
        return result

    def record_observation(self, logical_id: str, kind: str, data: dict[str, Any]) -> dict[str, Any] | None:
        if not self.is_born:
            return None
        return self._vcw().append(logical_id, kind, data)

    def prepare_mind_update(
        self, session_id: str, turn_id: str, *, max_events: int = 8
    ) -> dict[str, Any]:
        """Prepare but do not acknowledge a bounded MIND continuity update."""
        if not self.is_born:
            raise MantleError("A MIND cannot attach before birth")
        cipher = self._cipher()
        frontier = _load_sealed_json(self.paths.mind_frontier, cipher, "mind-frontier", {})
        events, proposed = self._vcw().events_after(frontier, limit=max_events)
        rendered = []
        for event in events:
            data_text = json.dumps(event["data"], sort_keys=True, ensure_ascii=False, default=str)
            if len(data_text) > 1_200:
                data_text = json.dumps(
                    {
                        "truncated": True,
                        "original_chars": len(data_text),
                        "sha256": sha256_bytes(data_text.encode("utf-8")),
                        "prefix": data_text[:800],
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
            rendered.append(
                {
                    "layer": event["logical_layer"],
                    "at": event["timestamp"],
                    "kind": event["kind"],
                    "data": json.loads(data_text),
                }
            )
        receipt = {
            "schema": "mantle.mind-update.v2",
            "session_id": session_id,
            "turn_id": turn_id,
            "prepared_at": utc_now(),
            "base_frontier": frontier,
            "proposed_frontier": proposed,
            "event_count": len(rendered),
            "events": rendered,
            "status": "pending",
        }
        path = self.paths.mind_pending / self._receipt_name(session_id, turn_id)
        _save_sealed_json(path, cipher, "mind-update", receipt)
        return receipt

    def acknowledge_mind_update(self, session_id: str, turn_id: str) -> dict[str, Any]:
        """Advance the MIND frontier only after a successful host response."""
        cipher = self._cipher()
        path = self.paths.mind_pending / self._receipt_name(session_id, turn_id)
        receipt = _load_sealed_json(path, cipher, "mind-update", {})
        if not receipt:
            raise MantleError("No pending MIND update exists for this turn")
        if receipt.get("status") == "acknowledged":
            return receipt
        current = _load_sealed_json(self.paths.mind_frontier, cipher, "mind-frontier", {})
        if current != receipt["base_frontier"]:
            raise MantleError("MIND frontier changed concurrently; pending history will be replayed")
        _save_sealed_json(self.paths.mind_frontier, cipher, "mind-frontier", receipt["proposed_frontier"])
        receipt["status"] = "acknowledged"
        receipt["acknowledged_at"] = utc_now()
        _save_sealed_json(path, cipher, "mind-update", receipt)
        return receipt

    def _complete_host_receipt(self, path: Path, *, mind_status: str) -> dict[str, Any]:
        cipher = self._cipher()
        receipt = _load_sealed_json(path, cipher, "host-heartbeat", {})
        if not receipt:
            raise MantleError("Host Heartbeat receipt is missing")
        if receipt.get("status") == "completed":
            return receipt["result"]
        vcw = self._vcw()
        proof = vcw.verify()
        result = {
            "heartbeat_id": receipt["heartbeat_id"],
            "reason": receipt["reason"],
            "started_at": receipt["started_at"],
            "completed_at": utc_now(),
            "phases": ["sense", "record", "communicate", "mind", "verify", "checkpoint"],
            "nest": receipt["nest"],
            "communication": {"route": "hermes", "turn_id": receipt["turn_id"]},
            "mind": mind_status,
            "proof": proof,
        }
        vcw.append("heart", "heartbeat.completed", result)
        receipt["status"] = "completed"
        receipt["result"] = result
        _save_sealed_json(path, cipher, "host-heartbeat", receipt)
        return result

    def recover_host_heartbeats(self, *, exclude: Path | None = None) -> list[dict[str, Any]]:
        """Finish receipts left open by a crashed or interrupted host process."""
        if not self.is_born or not self.paths.host_heartbeats.exists():
            return []
        recovered = []
        for path in sorted(self.paths.host_heartbeats.glob("*.enc")):
            if exclude is not None and path == exclude:
                continue
            receipt = _load_sealed_json(path, self._cipher(), "host-heartbeat", {})
            if receipt.get("status") == "pending":
                recovered.append(self._complete_host_receipt(path, mind_status="interrupted-or-process-lost"))
        return recovered

    def begin_host_heartbeat(self, session_id: str, turn_id: str) -> dict[str, Any]:
        """Begin a Heartbeat that spans Hermes's pre/post LLM hook boundary."""
        if not self.is_born:
            raise MantleError("Host-routed Heartbeat cannot begin before birth")
        path = self.paths.host_heartbeats / self._receipt_name(session_id, turn_id)
        self.recover_host_heartbeats(exclude=path)
        cipher = self._cipher()
        existing = _load_sealed_json(path, cipher, "host-heartbeat", {})
        if existing:
            return existing
        vcw = self._vcw()
        heartbeat_id = str(uuid.uuid4())
        started = utc_now()
        vcw.append(
            "heart",
            "heartbeat.started",
            {"heartbeat_id": heartbeat_id, "reason": "direct-user-message", "started_at": started},
        )
        nest = self._snapshot_nest(cipher)
        vcw.append("layer-0", "nest.state", nest)
        receipt = {
            "schema": "mantle.host-heartbeat.v2",
            "status": "pending",
            "session_id": session_id,
            "turn_id": turn_id,
            "heartbeat_id": heartbeat_id,
            "reason": "direct-user-message",
            "started_at": started,
            "nest": nest,
        }
        _save_sealed_json(path, cipher, "host-heartbeat", receipt)
        return receipt

    def complete_host_heartbeat(self, session_id: str, turn_id: str, *, mind_status: str) -> dict[str, Any]:
        path = self.paths.host_heartbeats / self._receipt_name(session_id, turn_id)
        return self._complete_host_receipt(path, mind_status=mind_status)

    def host_heartbeat_pending(self, session_id: str, turn_id: str) -> bool:
        if not self.is_born:
            return False
        path = self.paths.host_heartbeats / self._receipt_name(session_id, turn_id)
        receipt = _load_sealed_json(path, self._cipher(), "host-heartbeat", {})
        return receipt.get("status") == "pending"

    def verify(self) -> dict[str, Any]:
        if not self.is_born:
            proof = self._construction_proof()
            proof["live_vcw"] = False
            return proof
        primer = self._verify_primer_origin()
        proof = self._vcw().verify()
        proof["primer"] = primer
        return proof

    def watch(
        self,
        interval: float = 1.0,
        *,
        heartbeat_interval: float = 300.0,
        stop_requested: Callable[[], bool] | None = None,
    ) -> None:
        """Run the resident Heart and wake immediately on committed communication.

        ``interval`` is the inexpensive file-observation cadence. Scheduled
        Heartbeats use their own longer cadence. Stop is cooperative: finish a
        started Heartbeat, then start no further work. Idle stop checks run at
        most 100 ms apart, independently of file-observation cadence. This is
        not a deadline for synchronous storage or provider work already running.
        """
        if not self.is_born:
            raise MantleError("Communication watch cannot start before birth")
        if not math.isfinite(interval) or interval <= 0:
            raise MantleError("Communication watch interval must be finite and positive")
        if not math.isfinite(heartbeat_interval) or heartbeat_interval <= 0:
            raise MantleError("Scheduled Heartbeat interval must be finite and positive")
        should_stop = stop_requested or (lambda: False)
        if should_stop():
            return
        self.recover_host_heartbeats()
        self._ensure_communication_file()
        if should_stop():
            return
        self.heartbeat(reason="resident-startup")
        last_heartbeat = time.monotonic()
        try:
            initial = self.paths.communication.stat()
            observed = (initial.st_mtime_ns, initial.st_size)
        except OSError:
            observed = None
        last_observation = last_heartbeat
        idle_slice = min(0.1, max(0.05, min(interval, heartbeat_interval)))
        while not should_stop():
            time.sleep(idle_slice)
            if should_stop():
                break
            now = time.monotonic()
            changed = False
            if now - last_observation >= interval:
                last_observation = now
                try:
                    state = self.paths.communication.stat()
                    changed = (state.st_mtime_ns, state.st_size) != observed
                except OSError:
                    # Save/replace and temporary absence must not starve Heart.
                    pass
            scheduled = now - last_heartbeat >= heartbeat_interval
            if (scheduled or changed) and not should_stop():
                # One full scheduled beat also services any simultaneous message.
                reason = "resident-scheduled" if scheduled else "communication-file-save"
                self.heartbeat(reason=reason)
                last_heartbeat = time.monotonic()
                last_observation = last_heartbeat
                try:
                    state = self.paths.communication.stat()
                    observed = (state.st_mtime_ns, state.st_size)
                except OSError:
                    # Retain the last successful observation for a later retry.
                    pass
