from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .png import SIDE, pack_layer, unpack_layer

FORMAT = "vcw-cube-png-v2"
BANDS = {
    "identity": {"layer": 100, "path": "vcw/100_identity.png", "purpose": "experiential identity state"},
    "events": {"layer": 200, "path": "vcw/200_events.png", "purpose": "heartbeat and sensed events"},
    "immune": {"layer": 300, "path": "vcw/300_immune.png", "purpose": "integrity and policy evidence"},
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k not in {"id", "hash"}}
    return digest(canonical_json(body))[:16]


def make_entry(opcode: str, author: str, content: Any, source: str = "") -> dict:
    import time
    entry = {"id": None, "ts": time.time(), "opcode": opcode, "author": author,
             "source": source, "content": content, "tombstone": False}
    entry["hash"] = entry_hash(entry)
    return entry


class Stack:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.manifest_path = self.root / "STACK.json"

    @classmethod
    def bootstrap(cls, root: Path) -> "Stack":
        root = Path(root)
        (root / "vcw").mkdir(parents=True, exist_ok=True)
        (root / "receipts").mkdir(parents=True, exist_ok=True)
        special = json.loads((root / "genome/special.json").read_text(encoding="utf-8"))
        declared_bands = special.get("bands")
        if not isinstance(declared_bands, dict) or set(declared_bands) != set(BANDS):
            raise ValueError("SPECIAL band declaration does not match laboratory profile")
        manifest = {"format": FORMAT, "generation": 0, "identity_in_body": True,
                    "dimensions": [SIDE, SIDE], "bands": {}}
        stack = cls(root)
        for band, spec in declared_bands.items():
            boot = {"format": FORMAT, "band": band, "layer": spec["layer"], "driver": "log-json",
                    "purpose": spec["purpose"], "private": False}
            data = pack_layer(boot, {"entries": []})
            path = root / spec["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            manifest["bands"][band] = {**spec, "driver": "log-json", "size": [SIDE, SIDE], "sha256": digest(data)}
        stack.manifest_path.write_bytes(canonical_json(manifest) + b"\n")
        return stack

    def manifest(self) -> dict:
        if not self.manifest_path.exists():
            raise FileNotFoundError("STACK.json is missing")
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest: dict) -> None:
        self.manifest_path.write_bytes(canonical_json(manifest) + b"\n")

    def layer_bytes(self, band: str) -> bytes:
        spec = self.manifest()["bands"].get(band)
        if not spec:
            raise KeyError(band)
        return (self.root / spec["path"]).read_bytes()

    def layer_hashes(self) -> dict[str, str]:
        return {band: digest(self.layer_bytes(band)) for band in self.manifest()["bands"]}

    def fingerprint(self) -> str:
        m = self.manifest()
        canonical = {"format": m["format"], "generation": m["generation"],
                     "bands": [{"band": band, "layer": m["bands"][band]["layer"],
                                "path": m["bands"][band]["path"], "sha256": digest(self.layer_bytes(band))}
                               for band in sorted(m["bands"])]}
        return digest(canonical_json(canonical))

    def read(self, band: str) -> list[dict]:
        _boot, payload = unpack_layer(self.layer_bytes(band))
        return list(payload.get("entries", []))

    def append(self, band: str, entry: dict) -> dict:
        manifest = self.manifest()
        spec = manifest["bands"].get(band)
        if not spec:
            raise KeyError(band)
        boot, payload = unpack_layer(self.layer_bytes(band))
        entries = list(payload.get("entries", []))
        entry = dict(entry)
        entry["id"] = (max((e.get("id", -1) for e in entries), default=-1) + 1)
        entry["hash"] = entry_hash(entry)
        entries.append(entry)
        data = pack_layer(boot, {"entries": entries})
        (self.root / spec["path"]).write_bytes(data)
        manifest["bands"][band]["sha256"] = digest(data)
        self._write_manifest(manifest)
        return entry

    def verify(self) -> list[str]:
        problems: list[str] = []
        try:
            m = self.manifest()
        except Exception as exc:
            return [f"manifest: {exc}"]
        if m.get("format") != FORMAT:
            problems.append("manifest: unsupported format")
        if m.get("dimensions") != [SIDE, SIDE]:
            problems.append("manifest: wrong dimensions")
        bands = m.get("bands")
        if not isinstance(bands, dict) or set(bands) != set(BANDS):
            problems.append("manifest: band mapping mismatch")
            return problems
        seen_layers = set()
        for band, spec in bands.items():
            path = self.root / spec.get("path", "")
            layer = spec.get("layer")
            if layer in seen_layers:
                problems.append(f"manifest: duplicate layer {layer}")
            seen_layers.add(layer)
            if spec.get("driver") != "log-json" or spec.get("size") != [SIDE, SIDE]:
                problems.append(f"{band}: profile mismatch")
            if not path.is_file():
                problems.append(f"{band}: missing layer")
                continue
            actual = digest(path.read_bytes())
            if actual != spec.get("sha256"):
                problems.append(f"{band}: hash mismatch")
            try:
                boot, payload = unpack_layer(path.read_bytes())
                if boot.get("band") != band or boot.get("layer") != layer:
                    problems.append(f"{band}: boot mapping mismatch")
                if not isinstance(payload.get("entries"), list):
                    problems.append(f"{band}: entries are not a list")
                for entry in payload.get("entries", []):
                    if entry.get("hash") != entry_hash(entry):
                        problems.append(f"{band}: entry hash mismatch")
            except Exception as exc:
                problems.append(f"{band}: {exc}")
        return problems
