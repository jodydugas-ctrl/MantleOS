"""Append-only, Body-owned research experiment ledger."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Iterable, List, Optional

from ..vcw.bands import allocate_app_band, make_band_boot, standard_genome
from ..vcw.cube import Cube

STATUSES = (
    "PROPOSED", "MATERIALIZED", "RUNNING", "MEASURED", "ELIGIBLE",
    "DISCARDED", "CRASHED", "REFUSED", "INCONCLUSIVE", "AUTHORIZED", "ADOPTED",
)
ALLOWED_TRANSITIONS = {
    "PROPOSED": {"MATERIALIZED", "REFUSED"},
    "MATERIALIZED": {"RUNNING", "REFUSED", "CRASHED"},
    "RUNNING": {"MEASURED", "CRASHED", "REFUSED", "INCONCLUSIVE"},
    "MEASURED": {"ELIGIBLE", "DISCARDED", "INCONCLUSIVE"},
    "ELIGIBLE": {"REFUSED"},
    "DISCARDED": set(), "CRASHED": set(), "REFUSED": set(),
    "INCONCLUSIVE": set(), "AUTHORIZED": {"ADOPTED"}, "ADOPTED": set(),
}


class ResearchLedgerError(ValueError):
    """A research ledger operation violated its state or authority boundary."""


def research_band_boot(existing: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Allocate the private research band without touching standard genome bands."""
    return allocate_app_band(
        "research_runs", 8, encoding="log-json", private=True,
        purpose="Body-owned append-only bounded research receipts", existing=existing,
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash_receipt(receipt: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(receipt)).hexdigest()


class ResearchLedger:
    """The only writer for a private research receipt band.

    The ledger deliberately accepts a Cube supplied by the Body rather than constructing
    a hidden host store. Cube persistence provides the durable save/load boundary; all
    writes are tagged BODY and all transitions are reconstructed from the append-only log.
    """

    def __init__(self, body: Any, cube: Cube, band: str = "research_runs") -> None:
        if body is None:
            raise ResearchLedgerError("research ledger requires a Body owner")
        if band not in cube.bands:
            raise ResearchLedgerError("research band is not booted")
        boot = cube.bands[band]
        if not boot.get("private") or boot.get("encoding") != "log-json":
            raise ResearchLedgerError("research band must be private log-json tissue")
        self.body = body
        self.cube = cube
        self.band = band

    @classmethod
    def new(cls, body: Any, cube: Optional[Cube] = None) -> "ResearchLedger":
        if cube is None:
            cube = Cube.genesis(standard_genome() + [research_band_boot()])
        elif "research_runs" not in cube.bands:
            cube.add_band(research_band_boot(cube.bands.values()))
        return cls(body, cube)

    def _events(self) -> List[Dict[str, Any]]:
        rows = self.cube.read(self.band, reveal_private=True)
        return [row["content"] for row in rows if isinstance(row, dict)
                and isinstance(row.get("content"), dict)]

    def history(self) -> List[Dict[str, Any]]:
        return [dict(event) for event in self._events()]

    def _current(self, experiment_id: str) -> Optional[str]:
        current = None
        for event in self._events():
            if event.get("experiment_id") == experiment_id and event.get("event") == "transition":
                current = event.get("status")
        return current

    def status(self, experiment_id: str) -> Optional[str]:
        """Return the latest state without opening a second mutable write path."""
        return self._current(experiment_id)

    def _append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event = dict(event)
        event.setdefault("author", "BODY")
        event.setdefault("ts", time.time())
        prior = self._events()
        event["previous_hash"] = prior[-1].get("receipt_hash") if prior else None
        event["receipt_hash"] = _hash_receipt(event)
        self.cube.append(self.band, event)
        return event

    def propose(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        proposal = dict(receipt)
        experiment_id = str(proposal.get("experiment_id", ""))
        if not experiment_id:
            raise ResearchLedgerError("proposal requires experiment_id")
        if self._current(experiment_id) is not None:
            raise ResearchLedgerError("experiment already exists")
        proposal.update({"event": "transition", "status": "PROPOSED"})
        return self._append(proposal)

    def transition(self, experiment_id: str, status: str, **fields: Any) -> Dict[str, Any]:
        status = str(status).upper()
        current = self._current(experiment_id)
        allowed = ALLOWED_TRANSITIONS.get(current or "", set())
        if status not in STATUSES or status in {"AUTHORIZED", "ADOPTED"} or status not in allowed:
            refusal = self._append({
                "event": "transition_attempt", "experiment_id": experiment_id,
                "requested_status": status, "status": "REFUSED",
                "error": "invalid or unauthorized transition from %s" % (current or "<missing>"),
            })
            raise ResearchLedgerError(refusal["error"])
        event = {"event": "transition", "experiment_id": experiment_id,
                 "status": status, **fields}
        return self._append(event)

    def record_stop(self, reason: str, **fields: Any) -> Dict[str, Any]:
        """Record a Body-owned stop decision; it is never a candidate state transition."""
        if not isinstance(reason, str) or not reason:
            raise ResearchLedgerError("stop receipt requires a reason")
        return self._append({"event": "stop", "status": "STOPPED", "reason": reason,
                             **fields})

    @staticmethod
    def _operator_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(receipt, dict) or receipt.get("operator_authorized") is not True:
            raise ResearchLedgerError("operator authorization receipt is required")
        return dict(receipt)

    def authorize(self, experiment_id: str, receipt: Dict[str, Any]) -> Dict[str, Any]:
        receipt = self._operator_receipt(receipt)
        if self._current(experiment_id) != "ELIGIBLE":
            raise ResearchLedgerError("only ELIGIBLE experiments may be authorized")
        return self._append({"event": "transition", "experiment_id": experiment_id,
                             "status": "AUTHORIZED", "authority": "operator",
                             "operator_receipt": receipt, "automatic": False})

    def adopt(self, experiment_id: str, receipt: Dict[str, Any]) -> Dict[str, Any]:
        receipt = self._operator_receipt(receipt)
        if self._current(experiment_id) != "AUTHORIZED":
            raise ResearchLedgerError("only separately AUTHORIZED experiments may be adopted")
        return self._append({"event": "transition", "experiment_id": experiment_id,
                             "status": "ADOPTED", "authority": "operator",
                             "operator_receipt": receipt, "automatic": False})

    def snapshot(self) -> Dict[str, Any]:
        history = self.history()
        return {
            "schema": "mantle.research.ledger.v1",
            "band": self.band,
            "events": history,
            "tail_hash": history[-1].get("receipt_hash") if history else None,
        }
