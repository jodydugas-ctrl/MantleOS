"""Bounded serial research orchestration under Body authority."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .chamber import CandidateArtifact, CandidateChamber, CandidateChamberError
from .evaluator import Evaluation, ImmutableEvaluator
from .ledger import ResearchLedger, ResearchLedgerError
from .protocol import ResearchProtocol
from .runner import BoundedProcessError, BoundedProcessRunner, ProcessBudget


class ResearchGanglionError(RuntimeError):
    """A serial research pulse was refused before it could safely run."""


class ResearchGanglion:
    """One bounded experiment per pulse, with no adoption method by design."""

    def __init__(self, *, body: Any, ledger: ResearchLedger, protocol: ResearchProtocol,
                 evaluator: ImmutableEvaluator, chamber: CandidateChamber,
                 runner: Optional[BoundedProcessRunner] = None,
                 budget: Optional[ProcessBudget] = None,
                 energy: Optional[Callable[[], float]] = None,
                 energy_floor: float = 0.0, heart: Any = None,
                 strict_check: Optional[Callable[[], bool]] = None,
                 cancelled: Optional[Callable[[], bool]] = None):
        if body is None or ledger.body is not body:
            raise ResearchGanglionError("research ganglion and ledger must share the Body")
        if evaluator.protocol.digest != protocol.digest:
            raise ResearchGanglionError("evaluator protocol differs from ganglion protocol")
        self.body = body
        self.ledger = ledger
        self.protocol = protocol
        self.evaluator = evaluator
        self.chamber = chamber
        self.runner = runner
        self.budget = budget
        self.energy = energy or (lambda: float("inf"))
        self.energy_floor = float(energy_floor)
        self.heart = heart
        self.strict_check = strict_check
        self.cancelled = cancelled or (lambda: False)
        self._baseline = None
        self._baseline_identity = None
        self._stopped = False

    @property
    def max_experiments(self) -> int:
        value = self.protocol.stop_policy.get(
            "max_experiments", self.protocol.resource_budget.get("max_experiments", 1))
        return max(1, int(value))

    def _completed_count(self) -> int:
        terminal = {"ELIGIBLE", "DISCARDED", "CRASHED", "REFUSED", "INCONCLUSIVE"}
        return len({event.get("experiment_id") for event in self.ledger.history()
                    if event.get("event") == "transition" and event.get("status") in terminal})

    def _stop(self, reason: str, **fields: Any) -> dict[str, Any]:
        self._stopped = True
        receipt = self.ledger.record_stop(reason, protocol_hash=self.protocol.digest, **fields)
        return {"status": "STOPPED", "reason": reason, "receipt_hash": receipt["receipt_hash"],
                "adopted": False}

    def _identity_ok(self) -> bool:
        if self._baseline_identity is None:
            return True
        return self.evaluator.identity() == self._baseline_identity

    def _establish_baseline(self) -> None:
        if self._baseline is None:
            self._baseline = self.evaluator.baseline({"protocol_hash": self.protocol.digest,
                                                       "tree_hash": "baseline"})
            self._baseline_identity = dict(self._baseline.evaluator_identity)
        if not self._identity_ok():
            raise ResearchGanglionError("evaluator, protocol, corpus, or environment hash drift")

    def _transition_refused(self, experiment_id: str, reason: str) -> dict[str, Any]:
        event = self.ledger.transition(experiment_id, "REFUSED", reason=reason)
        return {"status": "REFUSED", "experiment_id": experiment_id, "reason": reason,
                "receipt_hash": event["receipt_hash"], "adopted": False}

    def pulse(self, proposal: Mapping[str, Any]) -> dict[str, Any]:
        """Run at most one authorized proposal and return a JSON-compatible report."""
        if self._stopped:
            return {"status": "STOPPED", "reason": "ganglion already stopped", "adopted": False}
        if not isinstance(proposal, Mapping):
            raise ResearchGanglionError("research proposal must be an object")
        experiment_id = str(proposal.get("experiment_id", "")).strip()
        if not experiment_id:
            raise ResearchGanglionError("research proposal requires experiment_id")
        prior = self.ledger.status(experiment_id)
        if prior in {"ELIGIBLE", "DISCARDED", "CRASHED", "REFUSED", "INCONCLUSIVE"}:
            return {"status": "ALREADY-COMPLETE", "experiment_id": experiment_id,
                    "prior_status": prior, "adopted": False}
        if self._completed_count() >= self.max_experiments:
            return self._stop("maximum experiment count reached")
        if self.cancelled():
            return self._stop("operator cancellation")
        if self.strict_check is not None and not self.strict_check():
            return self._stop("strict certification failed")
        try:
            self._establish_baseline()
        except Exception as exc:  # noqa: BLE001
            return self._stop("baseline or immutable-surface failure", error=str(exc))

        if prior is None:
            receipt = {
                "schema": "mantle.research.receipt.v1", "experiment_id": experiment_id,
                "protocol_hash": self.protocol.digest,
                "evaluator_identity": dict(self._baseline.evaluator_identity),
                "proposal": dict(proposal), "adopted": False,
            }
            try:
                self.ledger.propose(receipt)
            except ResearchLedgerError as exc:
                return self._stop("ledger proposal failure", error=str(exc))
        if proposal.get("operator_authorized") is not True:
            return self._transition_refused(experiment_id, "operator authorization is required")
        if any(proposal.get(key) is True for key in ("adopt", "calcify", "execute")):
            return self._transition_refused(experiment_id, "proposal carries forbidden authority")
        try:
            candidate_spec = proposal.get("candidate", proposal)
            candidate = self.chamber.materialize(candidate_spec)
            self.ledger.transition(experiment_id, "MATERIALIZED",
                                   candidate_hash=candidate.tree_hash,
                                   mutable_surface=candidate.mutable_surface)
        except (CandidateChamberError, OSError, ValueError) as exc:
            return self._transition_refused(experiment_id, "candidate materialization refused: %s" % exc)

        if float(self.energy()) <= self.energy_floor:
            try:
                self.chamber.discard(candidate)
            except Exception:
                pass
            return self._transition_refused(experiment_id, "energy floor reached")
        self.ledger.transition(experiment_id, "RUNNING", budget=self._budget_dict())

        process_report: dict[str, Any] = {"status": "not-requested", "bounded": True}
        argv = proposal.get("argv")
        if argv is not None:
            if self.runner is None or self.budget is None:
                return self._crash(candidate, experiment_id, "process runner or budget unavailable")
            try:
                result = self.runner.run(
                    list(argv), cwd=candidate.workspace, env=dict(proposal.get("env") or {}),
                    budget=self.budget, network=bool(proposal.get("network", False)),
                    require_network_isolation=bool(proposal.get("require_network_isolation", False)),
                )
                process_report = {"status": "ok" if result.ok else "failed", "bounded": True,
                                  "returncode": result.returncode, "timed_out": result.timed_out,
                                  "output_limited": result.output_limited,
                                  "changed_paths": list(result.changed_paths),
                                  "network_isolated": result.network_isolated}
                if not result.ok:
                    return self._crash(candidate, experiment_id, "bounded process failed",
                                       process=process_report)
            except (BoundedProcessError, OSError, ValueError) as exc:
                return self._crash(candidate, experiment_id, "bounded process refused: %s" % exc,
                                   process=process_report)

        if not self._identity_ok():
            return self._stop("evaluator, protocol, or corpus hash drift", experiment_id=experiment_id)
        evaluation = self.evaluator.evaluate(candidate, self._baseline)
        if evaluation.status == "ABORTED":
            self.ledger.transition(experiment_id, "INCONCLUSIVE", evaluation=evaluation.to_dict(),
                                   process=process_report)
            return self._stop("immutable evaluator aborted", experiment_id=experiment_id)
        self.ledger.transition(experiment_id, "MEASURED", evaluation=evaluation.to_dict(),
                               process=process_report)
        if evaluation.status == "PASS":
            final = self.ledger.transition(experiment_id, "ELIGIBLE", score=evaluation.score,
                                           adopted=False)
            status = "ELIGIBLE"
        else:
            final = self.ledger.transition(experiment_id, "DISCARDED", reason=evaluation.reason,
                                           adopted=False)
            status = "DISCARDED"

        artifact = candidate if proposal.get("artifact_policy") == "preserve" else None
        if artifact is None:
            try:
                self.chamber.discard(candidate)
            except Exception:
                pass
        future = None
        if self.heart is not None and status in {"ELIGIBLE", "DISCARDED"} and not self._stopped:
            future = self.heart.schedule_pulse(after=1, reason="research", band="research_runs",
                                               ref=experiment_id)
        return {"status": status, "experiment_id": experiment_id,
                "score": evaluation.score, "adopted": False,
                "receipt_hash": final["receipt_hash"], "future_pulse": future,
                "artifact": artifact}

    def _crash(self, candidate: CandidateArtifact, experiment_id: str, reason: str,
               **fields: Any) -> dict[str, Any]:
        event = self.ledger.transition(experiment_id, "CRASHED", error=reason, **fields)
        try:
            self.chamber.discard(candidate)
        except Exception:
            pass
        return {"status": "CRASHED", "experiment_id": experiment_id, "reason": reason,
                "receipt_hash": event["receipt_hash"], "adopted": False}

    def _budget_dict(self) -> dict[str, Any]:
        if self.budget is None:
            return dict(self.protocol.resource_budget)
        return {"wall_seconds": self.budget.wall_seconds, "cpu_seconds": self.budget.cpu_seconds,
                "memory_bytes": self.budget.memory_bytes, "output_bytes": self.budget.output_bytes,
                "file_count": self.budget.file_count}
