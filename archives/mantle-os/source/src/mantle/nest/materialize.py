"""Private temporary hydration/dehydration lifecycle.

The remote NEST is materialized into an owner-private temporary local directory;
the Body runs only on local bytes there; then a sealed remote form is produced.
Plaintext is confined to private temporary directories and deleted best-effort
with failures recorded (never silently ignored).
"""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Dict, Optional

from .envelope import BodyEnvelopeProvider, EnvelopeContext
from .manifest import file_inventory, read_json, write_json
from .transport import MaterializationReceipt, NestTransport


class NestMaterializeError(Exception):
    pass


@dataclass
class HydrationReceipt:
    manifest: Dict[str, object]
    manifests_match: bool
    opened_envelope: bool
    cleanup_failed: bool
    destination: str


def _manifest_hash_cmp(expected: str, actual: str) -> bool:
    return bool(expected) and expected == actual


def hydrate(
    transport: NestTransport,
    target: object,
    destination: str,
    *,
    provider: Optional[BodyEnvelopeProvider] = None,
    private: bool = True,
) -> HydrationReceipt:
    """Materialize a remote NEST into ``destination`` and hydrate the Body.

    Plaintext appears only under ``destination`` (an owner-private temp dir).
    If a provider is supplied and a ``mantle-nest/body.sealed`` is present, it is
    opened only after the manifest hash is verified; the envelope context binds
    the repository ID, schema, key fingerprint, and manifest hash.
    """
    os.makedirs(destination, exist_ok=True)
    if private:
        _make_private(destination)
    rec = transport.materialize(target, destination)  # type: ignore[attr-defined]

    manifest_path = os.path.join(destination, "mantle-nest", "nest.json")
    if not os.path.isfile(manifest_path):
        raise NestMaterializeError("remote NEST has no mantle-nest/nest.json")

    manifest = read_json(manifest_path)
    from .manifest import manifest_hash

    actual_hash = manifest_hash(manifest)
    manifest_ok = _manifest_hash_cmp(rec.manifest_hash, actual_hash)

    opened_envelope = False
    sealed_path = os.path.join(destination, "mantle-nest", "body.sealed")
    if os.path.isfile(sealed_path):
        # GHNEST-16: a visibility flip to public is refused before any secret opening.
        repo_info = manifest.get("repository", {})
        vis = str(repo_info.get("visibility", ""))
        if vis != "private":
            raise NestMaterializeError(
                "visibility flip refused before secret opening (repository is %r, "
                "not private)" % vis
            )
        if provider is None:
            raise NestMaterializeError("body.sealed present but no envelope provider configured")
        if not manifest_ok:
            raise NestMaterializeError(
                "refusing to open envelope for unverified manifest (hash mismatch)"
            )
        body_out = os.path.join(destination, "body.json")
        context = EnvelopeContext(
            schema=str(manifest.get("schema", "mantle-github-nest-v1")),
            repo_id=int(manifest["repository"]["id"]),
            key_fingerprint=str(manifest["organism"]["key_fingerprint"]),
            manifest_hash=actual_hash,
        )
        with open(sealed_path, "rb") as f:
            envelope = f.read()
        plaintext = provider.open(envelope, context)
        with open(body_out, "wb") as f:
            f.write(plaintext)
        opened_envelope = True
    return HydrationReceipt(
        manifest=manifest,
        manifests_match=manifest_ok,
        opened_envelope=opened_envelope,
        cleanup_failed=False,
        destination=destination,
    )


def seal_for_publish(
    plaintext_body: bytes,
    provider: BodyEnvelopeProvider,
    manifest: Dict[str, object],
    *,
    extra_files: Optional[Dict[str, bytes]] = None,
) -> Dict[str, bytes]:
    """Produce the publishable remote file map under ``mantle-nest/``.

    ``plaintext_body`` is sealed into ``mantle-nest/body.sealed``. ``body.json``
    never appears. ``extra_files`` (e.g. transport_seal.json) are added.
    """
    context = EnvelopeContext(
        schema=str(manifest.get("schema", "mantle-github-nest-v1")),
        repo_id=int(manifest["repository"]["id"]),
        key_fingerprint=str(manifest["organism"]["key_fingerprint"]),
        manifest_hash=_manifest_hash_of(manifest),
    )
    sealed = provider.seal(plaintext_body, context)
    out: Dict[str, bytes] = {
        "mantle-nest/body.sealed": sealed,
        "mantle-nest/nest.json": _manifest_bytes(manifest),
    }
    for rel, data in (extra_files or {}).items():
        out[rel] = data
    return out


def _manifest_hash_of(manifest: Dict[str, object]) -> str:
    from .manifest import manifest_hash

    return manifest_hash(manifest)


def _manifest_bytes(manifest: Dict[str, object]) -> bytes:
    from .manifest import canonical_json

    return canonical_json(manifest)


def _make_private(path: str) -> None:
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def safe_cleanup(path: str) -> bool:
    """Best-effort removal; returns False (and keeps going) if cleanup failed."""
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=False)
        elif os.path.exists(path):
            os.remove(path)
        return not os.path.exists(path)
    except OSError:
        return False
