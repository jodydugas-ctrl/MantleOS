from __future__ import annotations

from mantleos.contracts import (
    ActionFrame,
    BodyMap,
    CapabilitySpec,
    Direction,
    HabitatSpec,
    NerveSpec,
    SourceAnchor,
    SourceKind,
    contract_dict,
)


def test_contracts_are_substrate_neutral_and_json_ready():
    mapped = BodyMap(
        source_uri="fixture://body",
        source_fingerprint="sha256:" + "0" * 64,
        languages={"javascript": 2},
        entrypoints=("index.html",),
    )
    result = contract_dict(mapped)
    assert result["default_body"] == "NEST"
    assert result["logical_layer"] == 0
    assert result["languages"] == {"javascript": 2}


def test_nerve_and_action_are_distinct_contracts():
    nerve = NerveSpec(
        nerve_id="fixture:save",
        direction=Direction.BIDIRECTIONAL,
        semantic_event="document.saved",
        anchor=SourceAnchor("app.js", "save", "0" * 64, "after-statement"),
        capability_id="document.save",
    )
    action = ActionFrame("a1", "document.save", {"path": "note.txt"}, "thought:1")
    assert contract_dict(nerve)["direction"] == "bidirectional"
    assert contract_dict(action)["requested_by"] == "MIND"


def test_habitat_and_capability_axes_do_not_confuse_evidence_with_authority():
    habitat = HabitatSpec(
        source_kind=SourceKind.INSTALLED_APPLICATION,
        ecosystem="android",
        host_application="MacroDroid",
        storage_boundary="android-saf-tree",
    )
    capability = CapabilitySpec(
        "host.file-write",
        "WriteToFileAction",
        "Write through a host-owned SAF grant",
        "external-effect",
        "mantle.file-write.v2",
        "native-artifact-readback",
        implementation_status="mapped",
        availability_status="configured-but-unverified",
        evidence_status="observed",
        default_authority="denied",
        transition_owner="USER",
    )
    mapped = contract_dict(
        BodyMap(
            source_uri="installed://macrodroid",
            source_fingerprint="sha256:" + "1" * 64,
            habitat=habitat,
            capabilities=(capability,),
        )
    )
    assert mapped["default_body"] == "NEST"
    assert mapped["habitat"]["host_application"] == "MacroDroid"
    assert mapped["capabilities"][0]["evidence_status"] == "observed"
    assert mapped["capabilities"][0]["default_authority"] == "denied"
