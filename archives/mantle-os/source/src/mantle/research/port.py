"""Least-authority MIND-facing research proposal port."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Callable, Mapping, Optional


class ResearchPortError(ValueError):
    """A MIND request contains an authority-bearing or malformed field."""


_FORBIDDEN_KEYS = frozenset({
    "adopt", "adopted", "calcify", "execute", "authorized", "authorization",
    "ledger", "network", "filesystem", "shell", "process", "organism",
    "evaluator", "protocol_mutation", "genome_adoption", "skill_calcification",
})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


class ResearchPort:
    """Inspection and proposal surface only; it has no runtime authority methods."""

    __slots__ = ("_protocols", "_results", "_submit", "_outbox")

    def __init__(self, *, protocols: Optional[Mapping[str, Any]] = None,
                 results: Optional[list[Mapping[str, Any]]] = None,
                 submit: Optional[Callable[[dict[str, Any]], Any]] = None):
        self._protocols = dict(protocols or {})
        self._results = list(results or [])
        self._submit = submit
        self._outbox: list[dict[str, Any]] = []

    @classmethod
    def from_mind_port(cls, mind_port: Any, *, protocols: Optional[Mapping[str, Any]] = None,
                       results: Optional[list[Mapping[str, Any]]] = None) -> "ResearchPort":
        """Route proposals into the existing guarded brain surface, never the ledger."""
        if mind_port is None or not callable(getattr(mind_port, "write", None)):
            raise TypeError("ResearchPort.from_mind_port requires a guarded MindPort")

        def submit(record: dict[str, Any]) -> Any:
            return mind_port.write("brain", {"research_proposal": _copy(record),
                                               "author": "MIND", "verified": False})

        return cls(protocols=protocols, results=results, submit=submit)

    @staticmethod
    def _require_id(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ResearchPortError("%s requires a non-empty identifier" % label)
        return value.strip()

    @staticmethod
    def _reject_authority(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if str(key).lower() in _FORBIDDEN_KEYS:
                    raise ResearchPortError("MIND proposal cannot carry authority field %r" % key)
                ResearchPort._reject_authority(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                ResearchPort._reject_authority(nested)

    def inspect_protocol(self, protocol_id: str) -> dict[str, Any]:
        protocol_id = self._require_id(protocol_id, "protocol_id")
        if protocol_id not in self._protocols:
            raise ResearchPortError("unknown research protocol %r" % protocol_id)
        value = self._protocols[protocol_id]
        if hasattr(value, "to_dict"):
            value = value.to_dict()
        if not isinstance(value, Mapping):
            raise ResearchPortError("research protocol is not inspectable data")
        return _copy(dict(value))

    def inspect_results(self, filters: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
        if filters is not None and not isinstance(filters, Mapping):
            raise ResearchPortError("result filters must be an object")
        filters = dict(filters or {})
        self._reject_authority(filters)
        rows = []
        for result in self._results:
            if all(result.get(key) == value for key, value in filters.items()):
                rows.append(_copy(dict(result)))
        return rows

    def _emit(self, record: dict[str, Any]) -> dict[str, Any]:
        self._outbox.append(_copy(record))
        if self._submit is not None:
            self._submit(_copy(record))
        return _copy(record)

    def propose_candidate(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(proposal, Mapping) or not proposal:
            raise ResearchPortError("candidate proposal must be a non-empty object")
        self._reject_authority(proposal)
        data = _copy(dict(proposal))
        proposal_id = "proposal-" + hashlib.sha256(_canonical(data)).hexdigest()[:16]
        return self._emit({"event": "MIND_HYPOTHESIS", "proposal_id": proposal_id,
                           "status": "PROPOSED", "author": "MIND", "proposal": data})

    def request_trial(self, proposal_id: str) -> dict[str, Any]:
        proposal_id = self._require_id(proposal_id, "proposal_id")
        return self._emit({"event": "TRIAL_REQUEST", "proposal_id": proposal_id,
                           "status": "AWAITING_BODY_AUTHORIZATION", "authorized": False,
                           "author": "MIND"})

    def request_future_pulse(self, proposal_id: str, beat: int) -> dict[str, Any]:
        proposal_id = self._require_id(proposal_id, "proposal_id")
        if isinstance(beat, bool) or not isinstance(beat, int) or beat < 1:
            raise ResearchPortError("future pulse beat must be a positive integer")
        return self._emit({"event": "FUTURE_PULSE_REQUEST", "proposal_id": proposal_id,
                           "beat": beat, "status": "AWAITING_BODY_POLICY",
                           "authorized": False, "author": "MIND"})
