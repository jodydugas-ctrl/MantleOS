"""Deterministic contract tests for Body-governed memory consolidation."""
from __future__ import annotations

import json

from mantle import Organism
from mantle.mind import MindPort, fuse
from mantle.primer import appai_commandments, appai_truths


def _born():
    return Organism.birth({"name": "Consolidation.AppAI"}, appai_truths(), appai_commandments())


def _approval(org):
    return {
        "target": {"resident_identity": org.body.identity_name()},
        "operator": {"fusion_decision": "APPROVED"},
        "guardian": {"fusion_decision": "APPROVED"},
        "effective_decision": {"mind_fusion_authorized": True},
    }


def _proposal(window, *, weight=None, subject_band="events"):
    subject = next(item["ref"] for item in window["entries"] if item["ref"]["band"] == subject_band)
    return {
        "summary": "Later evidence changes how this experience is understood.",
        "reappraisals": [{
            "subject": subject, "status": "later_significant", "because": [],
            "interpretation": "The later record supplies a bounded new context.",
            "confidence": "plausible", **({"weight": weight} if weight is not None else {}),
        }],
        "open_questions": [],
    }


def _fused(org, model):
    org.stage1_certified = True
    return fuse(org, model, authorization=_approval(org))


def test_empty_window_does_not_call_model():
    calls = []
    org = _born()
    mind = _fused(org, lambda prompt: calls.append(prompt) or "{}")
    assert mind.consolidate({}) is None
    assert calls == []


def test_success_is_inferred_and_source_is_unchanged():
    org = _born()
    source = org.memory.remember("events", {"what": "first"})
    before = json.dumps(source, sort_keys=True)

    def model(_prompt):
        return json.dumps(_proposal(org.memory.consolidation_window()))

    result = _fused(org, model).consolidate({})
    discovery = result["discovery"]
    assert discovery["opcode"] == "CONSOLIDATED"
    assert discovery["author"] == "BODY" and discovery["source"] == "MIND"
    assert discovery["verified"] is False and discovery["confidence"] == "inferred"
    assert json.dumps(org.prime.retrieve("events", source["id"]), sort_keys=True) == before


def test_refs_must_be_from_body_window_and_facts_cannot_be_weighted():
    org = _born()
    org.memory.remember("facts", {"what": "external fact"})
    mind = _fused(org, lambda _prompt: "{}")
    window = MindPort(org).consolidation_window()
    hostile = _proposal(window, weight=.1, subject_band="facts")
    before = len(org.prime.read("facts"))
    mind.model = lambda _prompt: json.dumps(hostile)
    # The public Mind path treats the Body refusal as a non-result.
    assert mind.consolidate({}) is None
    assert len(org.prime.read("facts")) == before


def test_validation_refusal_does_not_advance_cursor_or_mutate():
    org = _born()
    org.memory.remember("events", {"what": "first"})
    window = org.memory.consolidation_window()
    proposal = _proposal(window)
    proposal["reappraisals"][0]["subject"]["id"] = 999999
    mind = _fused(org, lambda _prompt: json.dumps(proposal))
    assert mind.consolidate({}) is None
    assert org.memory.consolidation_window()["cursor_before"] == window["cursor_before"]
    assert not [e for e in org.prime.read("discoveries") if e["opcode"] == "CONSOLIDATED"]


def test_weight_updates_are_append_only_and_idempotent():
    org = _born()
    source = org.memory.remember("events", {"what": "first"})
    before = json.dumps(source, sort_keys=True)
    window = org.memory.consolidation_window()
    proposal = _proposal(window, weight=.25)
    proposal_hash = "b" * 64
    _fused(org, lambda _prompt: json.dumps(proposal))
    first = org.limbs.record_mind_consolidation(proposal, window, proposal_hash)
    count = len(org.prime.read("events", ghosts=True))
    replay = org.limbs.record_mind_consolidation(proposal, window, proposal_hash)
    assert first["applied_weight_updates"] == 1 and replay["idempotent"] is True
    assert len(org.prime.read("events", ghosts=True)) == count
    assert json.dumps(org.prime.retrieve("events", source["id"]), sort_keys=True) == before


def test_malformed_and_exception_keep_same_window():
    org = _born()
    org.memory.remember("events", {"what": "first"})
    before = org.memory.consolidation_window()
    mind = _fused(org, lambda _prompt: "not json")
    assert mind.consolidate({}) is None
    assert org.memory.consolidation_window()["cursor_before"] == before["cursor_before"]

    def broken(_prompt):
        raise RuntimeError("offline")

    org.brain.defuse()
    mind = _fused(org, broken)
    try:
        mind.consolidate({})
    except RuntimeError:
        pass
    assert org.memory.consolidation_window()["cursor_before"] == before["cursor_before"]


def test_scheduled_consolidation_is_one_model_call_and_phase1_is_inert():
    calls = []
    org = _born()
    org.memory.remember("events", {"what": "first"})
    _fused(org, lambda prompt: calls.append(prompt) or json.dumps(_proposal(org.memory.consolidation_window())))
    assert org.heart.schedule_consolidation(after=1) == 1
    org.heart.beat()
    assert len(calls) == 1
    assert org.memory.consolidation_window()["cursor_before"]["events"] >= 0

    phase1 = _born()
    phase1.memory.remember("events", {"what": "first"})
    phase1.heart.schedule_consolidation(after=1)
    phase1.heart.beat()
    assert not phase1.prime.read("discoveries")


def test_thoughts_are_never_a_consolidation_source_and_write_surface_is_unchanged():
    from mantle.mind.containment import WRITE_SURFACE

    org = _born()
    org.prime.append("thoughts", {"private": "never selected"})
    assert org.memory.consolidation_window()["entries"] == []
    assert WRITE_SURFACE == ("thoughts", "brain")
