from mantleos.contracts import ActionFrame, CapabilitySpec
from mantleos.organs import LimbAuthority, redact_semantic_data


def capability() -> CapabilitySpec:
    return CapabilitySpec(
        capability_id="body.echo",
        host_symbol="body.echo",
        description="Echo one admitted semantic action",
        effect="local",
        input_schema="mantle.test.v2",
        verifier="digest",
    )


def test_limb_authority_defaults_to_denied_and_requires_body_grant():
    authority = LimbAuthority()
    authority.register(capability(), lambda arguments: arguments)
    frame = ActionFrame("a-1", "body.echo", {"message": "hello"}, "thought:1")
    assert authority.execute(frame).disposition == "refused"
    authority.grant("body.echo")
    receipt = authority.execute(frame)
    assert receipt.disposition == "completed"
    assert receipt.result_digest


def test_semantic_redaction_removes_nested_credentials():
    safe = redact_semantic_data(
        {"message": "ok", "authorization": "Bearer secret", "nested": {"api_key": "key"}}
    )
    assert safe == {
        "message": "ok",
        "authorization": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]"},
    }


def test_semantic_redaction_removes_credentials_embedded_in_text():
    key = "sk-or-v1-" + "a" * 40
    assert redact_semantic_data(f"delivery {key} complete") == "delivery [REDACTED] complete"
