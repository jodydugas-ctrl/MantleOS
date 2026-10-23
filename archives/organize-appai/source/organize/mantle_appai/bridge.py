"""Optional MantleOS resident bridge; host behavior remains useful without it."""

from __future__ import annotations

import json
import hashlib
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .events import EvaluationEvent
from .privacy import sanitize


class MantleUnavailable(RuntimeError):
    pass


def _mantle_source_candidates(product_root: Path) -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("MANTLEOS_SRC")
    if configured:
        candidates.append(Path(configured))
    try:
        workspace = product_root.parents[1]
        candidates.append(workspace / "sources" / "mantle-os" / "src")
    except IndexError:
        pass
    return candidates


class MantleBridge:
    def __init__(
        self, product_root: str | Path, nest: str | Path | None = None
    ) -> None:
        self.product_root = Path(product_root).resolve()
        self.nest = Path(nest or self.product_root / ".mantle").resolve()

    def _organism_class(self):
        try:
            from mantle.core.organism import Organism

            return Organism
        except ImportError:
            for candidate in _mantle_source_candidates(self.product_root):
                if (candidate / "mantle").is_dir() and str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                    break
            try:
                from mantle.core.organism import Organism

                return Organism
            except ImportError as error:
                raise MantleUnavailable(
                    "MantleOS is not installed and no pinned source tree was found"
                ) from error

    def available(self) -> bool:
        try:
            return (
                self._organism_class() is not None
                and (self.nest / "organism.json").is_file()
            )
        except MantleUnavailable:
            return False

    def load(self):
        if not (self.nest / "organism.json").is_file():
            raise MantleUnavailable(f"no Mantle resident found at {self.nest}")
        return self._organism_class().load(str(self.nest), verify_seals=True)

    def status(self) -> dict[str, Any]:
        if not self.available():
            return {
                "available": False,
                "nest": str(self.nest),
                "mind": "offline",
                "body": "unavailable",
            }
        org = self.load()
        persisted = json.loads(
            (self.nest / "organism.json").read_text(encoding="utf-8")
        )
        primer = org.body.self_record()["primer"]
        identity = next(
            (item["identity"] for item in primer if "identity" in item),
            {"name": "unknown"},
        )
        protocol_path = self.nest / "resident_protocol.json"
        try:
            protocol = json.loads(
                protocol_path.read_text(encoding="utf-8")
            ).get("protocol")
        except (OSError, ValueError, AttributeError):
            protocol = None
        certificate_path = self.nest / "certification.json"
        certificate_hash = None
        certified_target = None
        if certificate_path.is_file():
            certificate_hash = hashlib.sha256(certificate_path.read_bytes()).hexdigest()
            try:
                certified_target = json.loads(
                    certificate_path.read_text(encoding="utf-8")
                ).get("target", {}).get("fingerprint")
            except (ValueError, AttributeError):
                certified_target = None
        host_fingerprint = hashlib.sha256(
            json.dumps(persisted, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {
            "available": True,
            "nest": str(self.nest),
            "identity": identity,
            "prime_generation": org.prime.generation,
            "persisted_stage1_certified": bool(persisted.get("stage1_certified")),
            "runtime_stage1_certified": org.stage1_certified,
            "mind": "fused" if org.brain.fused else "offline",
            "immune_events": len(org.immune.log),
            "mantle_version": __import__("mantle").__version__,
            "resident_protocol": protocol,
            "command_contract_drift": protocol != "mantle-resident-v2",
            "historical_certification_receipt": certificate_hash,
            "current_runtime_authority": bool(org.stage1_certified),
            "host_fingerprint": host_fingerprint,
            "certified_target_fingerprint": certified_target,
            "certification_stale": not bool(certificate_hash and certified_target),
            "provider_state": "session-owned",
            "energy_state": "read-from-symbiosis-ledger",
        }

    def sense_question(self, question: str) -> str:
        org = self.load()
        classification = org.senses.inhale(
            {
                "action_id": "organize.assist",
                "event_type": "user_question",
                "question": str(sanitize(question)),
            }
        )
        org.save(str(self.nest))
        return classification

    def remember_events(
        self,
        events: Iterable[EvaluationEvent],
        *,
        verified_simulation: bool = False,
    ) -> int:
        org = self.load()
        count = 0
        for event in events:
            if event.outcome == "refused":
                classification = "refused"
            elif event.outcome == "executed":
                classification = "executed"
            elif event.simulation and verified_simulation:
                classification = "verified"
            else:
                classification = "observed"
            org.memory.remember(
                "events",
                {
                    "classification": classification,
                    "event": sanitize(event.to_dict(), root=self.product_root),
                },
                opcode="ORGANIZE." + event.outcome.upper(),
                source=f"trace:{event.run_id}:{event.sequence}",
                verified=classification in {"verified", "executed"},
            )
            if event.outcome == "failed":
                org.immune_event(
                    "organize_execution_failure",
                    {
                        "trace": event.run_id,
                        "sequence": event.sequence,
                        "reason_code": event.reason_code,
                    },
                )
            count += 1
        org.save(str(self.nest))
        return count

    def remember_proposal(self, proposal: dict[str, Any]) -> None:
        org = self.load()
        org.memory.remember(
            "discoveries",
            {
                "classification": "proposed",
                "proposal": sanitize(proposal, root=self.product_root),
            },
            opcode="PROPOSED",
            source="organize.assist",
            verified=False,
            confidence="proposed",
        )
        org.save(str(self.nest))

    def remember_configuration(self, report: dict[str, Any]) -> None:
        org = self.load()
        org.memory.remember(
            "events",
            {
                "classification": "observed",
                "configuration_map": sanitize(report, root=self.product_root),
            },
            opcode="ORGANIZE.CONFIG_MAP",
            source="organize.explain",
            verified=False,
        )
        org.save(str(self.nest))

    def remember_inference(self, interpretation: str, evidence_refs: list[str]) -> None:
        org = self.load()
        org.memory.remember(
            "discoveries",
            {
                "classification": "inferred",
                "interpretation": str(sanitize(interpretation)),
                "evidence_refs": list(sanitize(evidence_refs)),
            },
            opcode="INFERRED",
            source="organize.assist",
            verified=False,
            confidence="inferred",
        )
        org.save(str(self.nest))

    def remember_body_command(
        self,
        command_text: str,
        *,
        status: str,
        ok: bool,
        changed_fields: Iterable[str] = (),
        public_state: dict[str, Any] | None = None,
    ) -> str:
        """Record a Body-owned slash command without exposing its credential payload."""

        from mantle.resident.protocol import resident_vcw_event, sanitize_user_submit

        org = self.load()
        sanitized_text = sanitize_user_submit(command_text)
        command = sanitized_text.strip().split(None, 1)[0].lower()
        fields = sorted({str(field) for field in changed_fields if str(field)})
        changed = bool(ok and fields)
        event_kind = (
            "BODY_CONFIGURATION_CHANGED"
            if changed
            else "BODY_COMMAND"
            if ok
            else "BODY_COMMAND_REFUSED"
        )
        org.senses.mark_routine("resident.body_command", "submit")
        org.senses.inhale(
            {
                "action_id": "resident.body_command",
                "event_type": "submit",
                "command": command,
                "text": sanitized_text,
                "handled_by": "BODY",
            }
        )
        event = resident_vcw_event(
            event_kind,
            {
                "command": command,
                "status": str(status),
                "changed_fields": fields,
                "handled_by": "BODY",
                "mind_invoked": False,
                "public_state": sanitize(public_state or {}, root=self.product_root),
            },
            text=sanitized_text,
            source="organize-appai-resident-body",
            ok=ok,
        )
        org.memory.remember(
            "events",
            event,
            opcode=event_kind,
            source="organize-appai-resident-body",
        )
        if changed:
            org.bus.emit(
                "body_configuration_changed",
                {
                    "command": command,
                    "changed_fields": fields,
                    "public_state": sanitize(
                        public_state or {}, root=self.product_root
                    ),
                    "event_kind": event_kind,
                },
            )
        org.save(str(self.nest))
        return event_kind
