#!/usr/bin/env python3
"""
mantle.organs.memory  --  the Memory organ: recall & metabolism (Mantle OS)

Owns the durable knowledge bands -- identity, facts, events, discoveries -- AND their
metabolism: the hot working-set -> durable flush cycle, on-demand layer allocation,
compaction, deduplication, and layer reclaim/reuse. "Every layer has a purpose; be
efficient."

CAPACITY DOCTRINE (executable here): the substrate fires the pressure hook when a band
crosses OVERFLOW (0.75) or EMERGENCY (0.90) of its reserved span; Memory's response is
METABOLISM (already run by the substrate) plus an immune event so the pressure is on the
record -- never a rebirth, never a silent reset. Promotion of inferred content into
`facts` requires external, cited evidence (verified=True + a source) -- self-inquiry can
never launder an inference into a fact.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .contract import Organ, OrganContract
from ..vcw.entry import make_entry

MEMORY_BANDS = ("identity", "facts", "events", "discoveries")
CONSOLIDATION_SOURCE_BANDS = ("facts", "events", "discoveries", "senses")
CONSOLIDATION_WEIGHT_BANDS = ("events", "discoveries", "senses")
CONSOLIDATION_RECEIPT_OPCODE = "CONSOLIDATION.RECEIPT"
CONSOLIDATION_DISCOVERY_OPCODE = "CONSOLIDATED"

CONTRACT = OrganContract(
    "memory", "recall & metabolism -- durable knowledge + keeping the working set lean",
    reads=list(MEMORY_BANDS),
    writes=list(MEMORY_BANDS),
    reflexes=[
        {"name": "remember", "trigger": "an organ records knowledge",
         "effect": "append one immutable, hashed entry to the owned band"},
        {"name": "recall", "trigger": "a read", "effect": "visible entries through the veil, "
         "ordered by weight (graded memory)"},
        {"name": "deweight", "trigger": "a value is contradicted/superseded",
         "effect": "lower its weight via an append-only event; it survives as a ghost, never "
                   "overwritten or deleted (M3)"},
        {"name": "allocate", "trigger": "a band tail fills",
         "effect": "grow onto the next layer in range, preferring the reuse pool"},
        {"name": "compact", "trigger": "metabolism / pressure",
         "effect": "drop tombstoned entries; emptied layers return to the free pool"},
        {"name": "dedupe", "trigger": "aggressive metabolism",
         "effect": "tombstone duplicate (opcode, content) entries; history preserved"},
        {"name": "overflow", "trigger": "pressure >= 0.75 (emergency >= 0.90)",
         "effect": "metabolize + immune event; may MOTIVATE a chosen rebirth, never force one"},
        {"name": "promote", "trigger": "external, cited evidence arrives",
         "effect": "an inferred discovery may become a fact ONLY with verified evidence"},
    ],
    phase1="active",
    phase2_extension="the MIND may REQUEST a write; the write is performed by this organ "
                     "into the correct band; metabolism stays pure Body",
    audit=[
        "entries are immutable + hashed; reads honor the veil; history never rewritten",
        "capacity != rebirth: thresholds trigger metabolism (0.75 overflow, 0.90 emergency)",
        "compaction preserves visible history",
        "inferred content is never auto-promoted to facts",
        "deweighting is graded + append-only: a ghost is hidden by default yet recoverable, "
        "and the original entry is never mutated",
    ],
)


class Memory(Organ):
    contract = CONTRACT

    # ---- remember / recall ---------------------------------------------------
    def remember(self, band: str, content: Any, opcode: str = "WRITE",
                 source: str = "", **extra) -> Dict[str, Any]:
        e = make_entry(content, opcode=opcode, author="BODY", source=source, **extra)
        return self.append(band, e)

    def recall(self, band: str) -> List[Dict[str, Any]]:
        """Visible entries through the veil, ordered by weight (ghosts hidden)."""
        return self.org.prime.read(band)

    # ---- graded memory (M3): deweight instead of delete -----------------------
    def deweight(self, band: str, entry_id: int, weight: float = 0.0, **extra: Any) -> bool:
        """Lower an entry's weight (default: fully suppress) via an append-only event. The
        entry becomes a behavioral ghost -- hidden from `recall`, still recoverable and never
        overwritten. Restoring is the same call with a higher weight."""
        return self.org.prime.deweight(band, entry_id, weight, **extra)

    def recall_ghosts(self, band: str) -> List[Dict[str, Any]]:
        """Surface the suppressed ghosts of a band -- the latent values the heavy path hid."""
        return self.org.prime.read(band, ghosts=True)

    # ---- Body-governed retrospective consolidation --------------------------
    def _successful_receipts(self) -> List[Dict[str, Any]]:
        return [
            entry for entry in self.org.prime.read("events")
            if entry.get("opcode") == CONSOLIDATION_RECEIPT_OPCODE
            and isinstance(entry.get("content"), dict)
            and entry["content"].get("success") is True
        ]

    def _cursor(self) -> Dict[str, int]:
        cursor = {band: -1 for band in CONSOLIDATION_SOURCE_BANDS}
        receipts = self._successful_receipts()
        if not receipts:
            return cursor
        latest = max(receipts, key=lambda item: int(item.get("id", -1)))
        committed = latest.get("content", {}).get("cursor", {})
        if isinstance(committed, dict):
            for band in cursor:
                value = committed.get(band, -1)
                if isinstance(value, int) and not isinstance(value, bool):
                    cursor[band] = value
        # A receipt is an implementation record, not experience for the next pass.
        cursor["events"] = max(cursor["events"], int(latest.get("id", -1)))
        return cursor

    def consolidation_window(self, limit: int = 48) -> Dict[str, Any]:
        """Return a deterministic, visible, bounded delta without moving its cursor."""
        try:
            limit = max(1, min(int(limit), 48))
        except (TypeError, ValueError):
            limit = 48
        before = self._cursor()
        candidates: List[Dict[str, Any]] = []
        for band in CONSOLIDATION_SOURCE_BANDS:
            for entry in self.org.prime.read(band):
                entry_id = entry.get("id")
                if not isinstance(entry_id, int) or isinstance(entry_id, bool):
                    continue
                if entry_id > before[band]:
                    candidates.append({
                        "ref": {"generation": self.org.prime.generation,
                                "band": band, "id": entry_id},
                        "entry": entry,
                    })
        candidates.sort(key=lambda item: (
            item["ref"]["generation"], item["ref"]["band"], item["ref"]["id"]
        ))
        entries = candidates[:limit]
        after = dict(before)
        for item in entries:
            ref = item["ref"]
            after[ref["band"]] = max(after[ref["band"]], ref["id"])
        return {"generation": self.org.prime.generation, "cursor_before": before,
                "cursor_after": after, "entries": entries}

    def _existing_consolidation(self, proposal_hash: str) -> Dict[str, Any]:
        for entry in self.org.prime.read("discoveries"):
            if (entry.get("opcode") == CONSOLIDATION_DISCOVERY_OPCODE
                    and entry.get("proposal_hash") == proposal_hash):
                return entry
        return {}

    def record_consolidation(self, proposal: Dict[str, Any], *,
                             cursor_after: Dict[str, int], proposal_hash: str) -> Dict[str, Any]:
        """Append Body-approved retrospective meaning, then commit its cursor last."""
        for receipt in self._successful_receipts():
            if receipt.get("content", {}).get("proposal_hash") == proposal_hash:
                return {"discovery": self._existing_consolidation(proposal_hash),
                        "receipt": receipt, "idempotent": True,
                        "applied_weight_updates": 0}

        discovery = self._existing_consolidation(proposal_hash)
        if not discovery:
            discovery = self.remember(
                "discoveries", proposal, opcode=CONSOLIDATION_DISCOVERY_OPCODE,
                source="MIND", guided_by="MIND", verified=False,
                confidence="inferred", proposal_hash=proposal_hash,
            )

        applied = 0
        reappraisals = proposal.get("reappraisals", [])
        for appraisal in reappraisals:
            if "weight" not in appraisal:
                continue
            subject = appraisal["subject"]
            band, entry_id = subject["band"], subject["id"]
            if band not in CONSOLIDATION_WEIGHT_BANDS:
                continue
            already_applied = any(
                item.get("opcode") == "DEWEIGHT"
                and item.get("proposal_hash") == proposal_hash
                and (item.get("content") or {}).get("target") == entry_id
                for layer in self.org.prime.band_layers[band]
                for item in self.org.prime.layer_content(layer)
            )
            if not already_applied and self.deweight(
                    band, entry_id, appraisal["weight"],
                    source="consolidation", proposal_hash=proposal_hash):
                applied += 1

        refs = [item["subject"] for item in reappraisals]
        receipt = self.remember(
            "events", {
                "proposal_hash": proposal_hash, "cursor": dict(cursor_after),
                "references": refs, "reappraisals": len(reappraisals),
                "applied_weight_updates": applied, "success": True,
            }, opcode=CONSOLIDATION_RECEIPT_OPCODE, source="BODY",
        )
        return {"discovery": discovery, "receipt": receipt, "idempotent": False,
                "applied_weight_updates": applied}

    # ---- metabolism -------------------------------------------------------------
    def compact(self, band: str) -> Dict[str, Any]:
        return self.org.prime.compact(band)

    def dedupe(self, band: str) -> Dict[str, Any]:
        return self.org.prime.dedupe(band)

    def metabolize(self, band: str, aggressive: bool = False) -> Dict[str, Any]:
        return self.org.prime.reclaim(band, aggressive=aggressive)

    def pressure(self, band: str) -> float:
        return self.org.prime.pressure(band)

    def pressures(self) -> Dict[str, float]:
        return {b: self.org.prime.pressure(b) for b in self.org.prime.bands}

    def on_pressure(self, band: str, level: str, report: Dict[str, Any]) -> None:
        """The substrate's pressure hook: metabolism already ran; put it on the record.
        NOTE WHAT THIS DOES NOT DO: it never calls rebirth."""
        self.org.immune_event("capacity_" + level, {
            "band": band, "pressure_before": report.get("pressure_before"),
            "pressure_after": report.get("pressure_after"),
            "response": "metabolism (compact%s)" % ("+dedupe" if level == "emergency" else ""),
        })
        self.bus.emit("pressure", {"band": band, "level": level})

    # ---- honest promotion (inference -> fact requires evidence) ----------------
    def promote_to_fact(self, discovery_entry: Dict[str, Any],
                        evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Promote an inferred discovery into `facts` -- ONLY with external, cited
        evidence. Anything less is refused and recorded as an immune event."""
        if not evidence or not evidence.get("source") or not evidence.get("verified"):
            self.org.immune_event("promotion_refused", {
                "reason": "facts require external, cited, verified evidence",
                "discovery_id": discovery_entry.get("id")})
            raise PermissionError("inferred content cannot become a fact without "
                                  "external, cited, verified evidence")
        return self.remember("facts", discovery_entry.get("content"),
                             opcode="PROMOTED",
                             source=str(evidence.get("source")),
                             verified=True, evidence=evidence)
