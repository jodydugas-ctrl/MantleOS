"""Append-only, Body-authored rolling-context ledger in a private VCW band."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from ...vcw.bands import allocate_app_band
from ...vcw.entry import make_entry
from .canonical import canonical_json_bytes, chain_hash, sha256_hex
from .types import (
    CONTEXT_SCHEMA,
    ContextIntegrityError,
    ContextKey,
    ContextMigrationRequired,
    SourceCursor,
)


VISIBLE_KINDS = frozenset({"OPEN", "CHECKPOINT", "DELTA", "INTENT", "RESPONSE"})


def _credit_source_range(available: Dict[str, int],
                         record: Mapping[str, Any]) -> None:
    """Credit the ids a receipt-only delta consumed.

    Non-exact persistence modes store `DELTA_RECEIPT` instead of the projected
    entries, so the ids must come from the recorded range or every later commit
    would look like it had advanced past uncommitted source material.
    """
    for name, bounds in (record.get("source_range") or {}).items():
        if name in available and bounds:
            available[name] = max(available[name], int(bounds[-1]) + 1)


def context_band_boot(existing: Iterable[Dict[str, Any]], *,
                      band: str = "context", span: int = 8) -> Dict[str, Any]:
    return allocate_app_band(
        band,
        span,
        encoding="log-json",
        private=True,
        purpose="exact model-visible rolling context ledger",
        existing=existing,
    )


def install_context_band(organism: Any, *, authorized: bool,
                         band: str = "context", span: int = 8) -> Dict[str, Any]:
    """Perform the explicit Body-authorized experimental context-band graft."""
    if not authorized:
        organism.immune_event("context_migration_refused", {
            "band": band, "reason": "explicit Body authorization required",
        })
        raise PermissionError("context-band migration requires explicit Body authorization")
    if band in organism.prime.bands:
        boot = organism.prime.bands[band]
        if not boot.get("private") or boot.get("encoding") != "log-json":
            raise ValueError("existing context band has an unsafe boot contract")
        return dict(boot)
    boot = context_band_boot(organism.prime.bands.values(), band=band, span=span)
    organism.prime.add_band(boot)
    organism.immune_event("context_migration", {
        "band": band,
        "head": boot["head"],
        "span": boot["span"],
        "authorized": True,
    })
    return boot


class ContextLedger:
    """Read, append, and verify one context key's records."""

    def __init__(self, organism: Any, key: ContextKey, *,
                 band: str = "context") -> None:
        self.organism = organism
        self.key = key
        self.band = band
        if band not in organism.prime.bands:
            raise ContextMigrationRequired(
                "rolling context requires an explicit private %r band migration" % band
            )
        boot = organism.prime.bands[band]
        if boot.get("encoding") != "log-json" or not boot.get("private"):
            raise ContextMigrationRequired(
                "context band must be private and use log-json"
            )

    def records(self) -> List[Dict[str, Any]]:
        result = []
        for entry in self._physical_entries():
            if not isinstance(entry, dict):
                continue
            payload = entry.get("content")
            if not isinstance(payload, dict):
                continue
            if payload.get("context_schema") != CONTEXT_SCHEMA:
                continue
            if payload.get("context_key") == self.key.as_dict():
                result.append(payload)
        return result

    def _physical_entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        cube = self.organism.prime
        for layer in cube.band_layers[self.band]:
            content = cube.layer_content(layer)
            if isinstance(content, list):
                entries.extend(
                    entry for entry in content if isinstance(entry, dict)
                )
        return entries

    def _wrapper_problems(self, generation: Optional[int] = None) -> List[str]:
        from ...vcw.entry import entry_hash
        problems = []
        for entry in self._physical_entries():
            payload = entry.get("content")
            if not isinstance(payload, dict):
                continue
            if payload.get("context_schema") != CONTEXT_SCHEMA:
                continue
            if payload.get("context_key") != self.key.as_dict():
                continue
            if generation is not None and payload.get("generation") != generation:
                continue
            if entry.get("tombstone") or entry.get("quarantined"):
                problems.append(
                    "context record %r is tombstoned or quarantined"
                    % payload.get("sequence")
                )
            if entry.get("hash") != entry_hash(entry):
                problems.append(
                    "context record %r VCW entry hash mismatch"
                    % payload.get("sequence")
                )
        return problems

    def next_sequence(self, generation: int) -> int:
        same = [int(record["sequence"]) for record in self.records()
                if record.get("generation") == generation]
        return max(same, default=-1) + 1

    def active_generation(self) -> int:
        opened = [
            int(record["generation"])
            for record in self.records()
            if record.get("kind") == "OPEN"
        ]
        return max(opened, default=0)

    def latest_open(self) -> Optional[Dict[str, Any]]:
        generation = self.active_generation()
        opened = [
            record for record in self.records()
            if record.get("kind") == "OPEN"
            and record.get("generation") == generation
        ]
        return opened[-1] if opened else None

    def latest_cursor(self, generation: Optional[int] = None) -> SourceCursor:
        generation = self.active_generation() if generation is None else generation
        commits = [
            record for record in self.records()
            if record.get("kind") == "COMMIT"
            and record.get("generation") == generation
        ]
        if commits:
            return SourceCursor.from_mapping(commits[-1].get("source_cursors"))
        opened = [
            record for record in self.records()
            if record.get("kind") in {"OPEN", "CHECKPOINT"}
            and record.get("generation") == generation
        ]
        return SourceCursor.from_mapping(
            opened[-1].get("source_cursors") if opened else None
        )

    def committed_request_hashes(self, generation: int) -> Set[str]:
        return {
            str(record.get("request_hash"))
            for record in self.records()
            if record.get("kind") == "COMMIT"
            and record.get("generation") == generation
            and record.get("request_hash")
        }

    def visible_records(self, generation: Optional[int] = None) -> List[Dict[str, Any]]:
        generation = self.active_generation() if generation is None else generation
        committed = self.committed_request_hashes(generation)
        visible = []
        for record in self.records():
            if record.get("generation") != generation:
                continue
            if record.get("kind") not in VISIBLE_KINDS:
                continue
            request_hash = record.get("request_hash")
            if request_hash and request_hash not in committed:
                continue
            visible.append(self.model_visible(record))
        return visible

    @staticmethod
    def model_visible(record: Mapping[str, Any]) -> Dict[str, Any]:
        excluded = {
            "previous_context_hash", "record_hash", "chain_hash",
            # `request_prompt` is no longer written; the entry stays so a ledger
            # from a build that did write it can never render it into a prefix.
            "request_hash", "request_prompt", "error", "sequence",
        }
        return {key: value for key, value in record.items() if key not in excluded}

    def append(self, kind: str, generation: int, data: Mapping[str, Any],
               *, sequence: Optional[int] = None,
               reset_chain: bool = False) -> Dict[str, Any]:
        records = self.records()
        previous = (
            "" if reset_chain
            else (records[-1].get("chain_hash", "") if records else "")
        )
        core: Dict[str, Any] = {
            "context_schema": CONTEXT_SCHEMA,
            "context_key": self.key.as_dict(),
            "generation": int(generation),
            "sequence": (
                self.next_sequence(generation) if sequence is None else int(sequence)
            ),
            "kind": str(kind),
        }
        core.update(dict(data))
        record_hash = sha256_hex(core)
        chained = dict(core)
        chained["previous_context_hash"] = previous
        chained["record_hash"] = record_hash
        chained["chain_hash"] = chain_hash(previous, chained)
        self.organism.prime.append(
            self.band,
            make_entry(
                chained,
                opcode="CONTEXT." + kind,
                author="BODY",
                authorship="BODY",
                source="rolling-context",
            ),
        )
        return chained

    def verify_generation(self, generation: int) -> List[str]:
        records = [
            record for record in self.records()
            if record.get("generation") == generation
        ]
        if not records:
            return ["generation %d has no records" % generation]
        problems: List[str] = self._wrapper_problems(generation)
        previous = str(records[0].get("previous_context_hash") or "")
        seen: Set[Tuple[str, int]] = set()
        prior_cursor = SourceCursor()
        available_cursor = SourceCursor().as_dict()
        for expected, record in enumerate(records):
            if record.get("sequence") != expected:
                problems.append(
                    "generation %d sequence %r follows %d"
                    % (generation, record.get("sequence"), expected - 1)
                )
            if record.get("previous_context_hash") != previous:
                problems.append("generation %d sequence %d previous hash mismatch"
                                % (generation, expected))
            core = {
                key: value for key, value in record.items()
                if key not in {"previous_context_hash", "record_hash", "chain_hash"}
            }
            if sha256_hex(core) != record.get("record_hash"):
                problems.append("generation %d sequence %d content hash mismatch"
                                % (generation, expected))
            chained = dict(core)
            chained["previous_context_hash"] = previous
            chained["record_hash"] = record.get("record_hash")
            if chain_hash(previous, chained) != record.get("chain_hash"):
                problems.append("generation %d sequence %d chain hash mismatch"
                                % (generation, expected))
            previous = str(record.get("chain_hash") or "")
            if record.get("kind") in {"OPEN", "CHECKPOINT"}:
                declared = SourceCursor.from_mapping(
                    record.get("source_cursors")
                ).as_dict()
                for name, value in declared.items():
                    available_cursor[name] = max(available_cursor[name], value)
            if record.get("kind") == "DELTA":
                for item in record.get("entries", []) or []:
                    identity = (str(item.get("source_band")),
                                int(item.get("source_id", -1)))
                    if identity in seen:
                        problems.append("duplicate source inclusion %r" % (identity,))
                    seen.add(identity)
                    if identity[0] in available_cursor:
                        available_cursor[identity[0]] = max(
                            available_cursor[identity[0]], identity[1] + 1
                        )
            if record.get("kind") == "DELTA_RECEIPT":
                _credit_source_range(available_cursor, record)
            if record.get("kind") == "COMMIT":
                cursor = SourceCursor.from_mapping(record.get("source_cursors"))
                for name, value in cursor.as_dict().items():
                    if value < prior_cursor.as_dict()[name]:
                        problems.append("cursor %s moved backwards" % name)
                    if value > available_cursor[name]:
                        problems.append("cursor %s advanced beyond committed entries" % name)
                prior_cursor = cursor
        return problems

    def require_active_valid(self) -> None:
        generation = self.active_generation()
        problems = self.verify_generation(generation)
        if problems:
            self.organism.immune_event("context_corruption", {
                "band": self.band,
                "generation": generation,
                "problems": problems[:5],
            })
            raise ContextIntegrityError("; ".join(problems))

    def verify(self) -> List[str]:
        problems: List[str] = self._wrapper_problems()
        records = self.records()
        previous = ""
        expected_by_generation: Dict[int, int] = {}
        last_cursor: Dict[int, SourceCursor] = {}
        included: Dict[int, Set[Tuple[str, int]]] = {}
        available: Dict[int, Dict[str, int]] = {}
        for index, record in enumerate(records):
            generation = record.get("generation")
            sequence = record.get("sequence")
            if not isinstance(generation, int) or not isinstance(sequence, int):
                problems.append("record %d has invalid generation/sequence" % index)
                continue
            expected = expected_by_generation.get(generation, 0)
            if sequence != expected:
                problems.append(
                    "generation %d sequence %d follows %d"
                    % (generation, sequence, expected - 1)
                )
            expected_by_generation[generation] = sequence + 1
            if record.get("previous_context_hash") != previous:
                problems.append("record %d previous hash mismatch" % index)
            core = {
                key: value for key, value in record.items()
                if key not in {"previous_context_hash", "record_hash", "chain_hash"}
            }
            if sha256_hex(core) != record.get("record_hash"):
                problems.append("record %d content hash mismatch" % index)
            chained = dict(core)
            chained["previous_context_hash"] = previous
            chained["record_hash"] = record.get("record_hash")
            expected_chain = chain_hash(previous, chained)
            if expected_chain != record.get("chain_hash"):
                problems.append("record %d chain hash mismatch" % index)
            previous = str(record.get("chain_hash") or "")
            if canonical_json_bytes(record) != canonical_json_bytes(dict(record)):
                problems.append("record %d cannot be canonically reserialized" % index)
            generation_available = available.setdefault(
                generation, SourceCursor().as_dict()
            )
            if record.get("kind") in {"OPEN", "CHECKPOINT"}:
                declared = SourceCursor.from_mapping(
                    record.get("source_cursors")
                ).as_dict()
                for name, value in declared.items():
                    generation_available[name] = max(
                        generation_available[name], value
                    )
            if record.get("kind") == "DELTA":
                seen = included.setdefault(generation, set())
                for item in record.get("entries", []) or []:
                    identity = (str(item.get("source_band")), int(item.get("source_id", -1)))
                    if identity in seen:
                        problems.append("duplicate source inclusion %r" % (identity,))
                    seen.add(identity)
                    if identity[0] in generation_available:
                        generation_available[identity[0]] = max(
                            generation_available[identity[0]], identity[1] + 1
                        )
            if record.get("kind") == "DELTA_RECEIPT":
                _credit_source_range(generation_available, record)
            if record.get("kind") == "COMMIT":
                cursor = SourceCursor.from_mapping(record.get("source_cursors"))
                prior = last_cursor.get(generation, SourceCursor())
                for name, value in cursor.as_dict().items():
                    if value < prior.as_dict()[name]:
                        problems.append("cursor %s moved backwards" % name)
                    if value > generation_available[name]:
                        problems.append("cursor %s advanced beyond committed entries" % name)
                last_cursor[generation] = cursor
        return problems

    def require_valid(self) -> None:
        problems = self.verify()
        if problems:
            self.organism.immune_event("context_corruption", {
                "band": self.band,
                "problems": problems[:5],
            })
            raise ContextIntegrityError("; ".join(problems))
