"""Bounded, one-shot Body inbox for externally offered resources."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from typing import Any, Dict, Optional


class ResourceOfferError(PermissionError):
    pass


class ResourceOfferAdapter:
    name = "disabled"

    def accept(self, offer: Dict[str, Any]) -> Dict[str, Any]:
        raise ResourceOfferError("resource-offer adapter is disabled")


class DisabledResourceOfferAdapter(ResourceOfferAdapter):
    pass


class FakeResourceOfferAdapter(ResourceOfferAdapter):
    """Deterministic test adapter; never persists secret material."""

    name = "fake"

    def accept(self, offer: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "accepted": True,
            "adapter": self.name,
            "resource_type": offer.get("type"),
            "resource_name": offer.get("name"),
        }


@dataclass(frozen=True)
class ResourceOfferInbox:
    root: str
    adapter: ResourceOfferAdapter
    max_bytes: int = 16384

    def __post_init__(self) -> None:
        root = os.path.realpath(os.path.abspath(self.root))
        if not os.path.isdir(root):
            raise ResourceOfferError("resource-offer inbox does not exist")
        if self.max_bytes <= 0:
            raise ValueError("resource-offer size limit must be positive")
        object.__setattr__(self, "root", root)

    def inspect(self, path: str) -> Dict[str, Any]:
        candidate = os.path.abspath(path)
        real = os.path.realpath(candidate)
        try:
            contained = os.path.commonpath((self.root, real)) == self.root
        except ValueError:
            contained = False
        if not contained or os.path.islink(candidate):
            raise ResourceOfferError("resource offer escapes the bounded inbox")
        if not os.path.isfile(real):
            raise ResourceOfferError("resource offer is not a regular file")
        size = os.path.getsize(real)
        if size > self.max_bytes:
            raise ResourceOfferError("resource offer exceeds the size limit")
        with open(real, "rb") as handle:
            raw = handle.read(self.max_bytes + 1)
        digest = hashlib.sha256(raw).hexdigest()
        try:
            offer = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResourceOfferError("resource offer must be bounded JSON") from exc
        if not isinstance(offer, dict):
            raise ResourceOfferError("resource offer must be a JSON object")
        forbidden = {"key", "api_key", "token", "password", "secret", "credential"}
        def keys(value: Any):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield str(key).lower()
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)
        if forbidden.intersection(keys(offer)):
            raise ResourceOfferError("plaintext credential fields are refused")
        if offer.get("classification", "OTHER") != "OTHER":
            raise ResourceOfferError("external resource offers must be classified OTHER")
        return {
            "schema": "mantle-resource-offer-v1",
            "classification": "OTHER",
            "sha256": digest,
            "bytes": size,
            "type": offer.get("type"),
            "name": offer.get("name"),
            "path_hint": os.path.basename(real),
        }

    def process(self, path: str) -> Dict[str, Any]:
        offer = self.inspect(path)
        marker = os.path.join(self.root, ".processed-" + offer["sha256"])
        try:
            with open(marker, "x", encoding="ascii") as handle:
                handle.write("processed\n")
        except FileExistsError as exc:
            raise ResourceOfferError("resource offer has already been processed") from exc
        try:
            result = self.adapter.accept(offer)
        except Exception:
            # The marker intentionally remains: an external offer is one-shot even
            # when the registered adapter refuses it.
            raise
        return {"offer": offer, "result": result, "raw_secret_stored": False}


__all__ = [
    "DisabledResourceOfferAdapter", "FakeResourceOfferAdapter",
    "ResourceOfferAdapter", "ResourceOfferError", "ResourceOfferInbox",
]
