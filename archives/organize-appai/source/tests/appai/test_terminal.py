from __future__ import annotations

from pathlib import Path
import json

import pytest
from organize.mantle_appai.bridge import MantleBridge
from organize.mantle_appai.terminal import (
    DEFAULT_MODEL,
    ResidentTerminal,
    fusion_authorization,
    normalize_model,
    positive_credits,
)

try:  # pragma: no cover - exercised only in the plain (non-certification) workflow
    import mantle  # noqa: F401

    MANTLE_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    MANTLE_AVAILABLE = False

requires_mantle = pytest.mark.skipif(
    not MANTLE_AVAILABLE,
    reason="mantle-os not installed; run with the certification workflow or `.[mantle2]`",
)


def _resident_tree(tmp_path: Path) -> Path:
    from mantle.core.organism import Organism
    from mantle.primer import appai_commandments, appai_truths

    (tmp_path / "WORKSPACE.txt").write_text(str(tmp_path.resolve()), encoding="utf-8")
    product = tmp_path / "product" / "organize-appai"
    org = Organism.birth(
        identity={"name": "Organize.AppAI"},
        truths=appai_truths(), commandments=appai_commandments(),
    )
    org.save(str(product / ".mantle"))
    return product


def test_fusion_authorization_requires_both_explicit_decisions():
    assert (
        fusion_authorization(
            "Organize.AppAI", operator_approved=True, guardian_approved=False
        )
        is None
    )
    receipt = fusion_authorization(
        "Organize.AppAI", operator_approved=True, guardian_approved=True
    )
    assert receipt == {
        "target": {"resident_identity": "Organize.AppAI"},
        "operator": {"fusion_decision": "APPROVED"},
        "guardian": {"fusion_decision": "APPROVED"},
        "effective_decision": {"mind_fusion_authorized": True},
    }


def test_auto_model_alias_is_normalized():
    assert normalize_model("") == DEFAULT_MODEL
    assert DEFAULT_MODEL == "openrouter/free"
    assert normalize_model("free") == DEFAULT_MODEL
    assert normalize_model("auto") == "openrouter/auto"
    assert normalize_model(" openai/gpt-5 ") == "openai/gpt-5"
    with pytest.raises(ValueError):
        normalize_model("not a model")


def test_positive_credits_are_bounded():
    assert positive_credits("20") == 20.0
    with pytest.raises(ValueError):
        positive_credits("0")
    with pytest.raises(ValueError):
        positive_credits("100001")


@requires_mantle
def test_key_setup_keeps_secret_in_memory_and_never_passes_it_to_feed(
    tmp_path: Path, monkeypatch
):
    product = _resident_tree(tmp_path)
    outputs: list[str] = []
    prompts = iter(["", "yes", "yes"])
    feed_calls: list[tuple[tuple, dict]] = []

    def feed(*args, **kwargs):
        feed_calls.append((args, kwargs))
        return {"balance": 10.0}

    monkeypatch.setattr(
        MantleBridge, "status", lambda self: {"identity": {"name": "Organize.AppAI"}}
    )
    terminal = ResidentTerminal(
        product,
        input_fn=lambda prompt: next(prompts),
        secret_fn=lambda prompt: "sk-or-v1-test-secret",
        output_fn=outputs.append,
        feed_fn=feed,
    )
    assert terminal.setup_key() is True
    assert terminal.state.api_key == "sk-or-v1-test-secret"
    assert terminal.state.model == DEFAULT_MODEL
    assert terminal.state.ready is True
    assert "sk-or-v1-test-secret" not in "\n".join(outputs)
    assert "sk-or-v1-test-secret" not in repr(feed_calls)
    assert feed_calls == []


@requires_mantle
def test_key_payload_after_command_is_refused_without_secret_prompt(
    tmp_path: Path, monkeypatch
):
    product = _resident_tree(tmp_path)
    outputs: list[str] = []
    monkeypatch.setattr(
        MantleBridge, "status", lambda self: {"identity": {"name": "Organize.AppAI"}}
    )
    terminal = ResidentTerminal(
        product,
        secret_fn=lambda prompt: pytest.fail("secret prompt must not run"),
        output_fn=outputs.append,
        record_fn=lambda *args, **kwargs: "BODY_COMMAND_REFUSED",
    )
    assert terminal.command("/key sk-should-not-be-used") is True
    assert terminal.state.api_key is None
    assert "entered hidden" in outputs[-1]


@requires_mantle
def test_body_commands_record_redacted_change_metadata(tmp_path: Path, monkeypatch):
    product = _resident_tree(tmp_path)
    outputs: list[str] = []
    monkeypatch.setattr(
        MantleBridge, "status", lambda self: {"identity": {"name": "Organize.AppAI"}}
    )
    terminal = ResidentTerminal(
        product,
        output_fn=outputs.append,
    )

    assert terminal.command("/model free") is True
    assert terminal.command("/model openai/gpt-5") is True
    assert terminal.command("/unknown") is True

    assert terminal.state.model == "openai/gpt-5"
    events = terminal._dispatcher().organism.memory.recall("events")
    body_events = [row for row in events if row["opcode"].startswith("BODY_")]
    assert body_events[-3]["content"]["payload"]["changed_fields"] == []
    assert body_events[-2]["content"]["payload"]["changed_fields"] == ["model"]
    assert body_events[-2]["content"]["payload"]["public_state"]["model"] == "openai/gpt-5"
    assert body_events[-1]["opcode"] == "BODY_COMMAND_REFUSED"


@requires_mantle
def test_bridge_persists_body_change_without_the_key(
    tmp_path: Path, monkeypatch
):
    mantle_source = Path(__file__).resolve().parents[4] / "sources" / "mantle-os" / "src"
    monkeypatch.setenv("MANTLEOS_SRC", str(mantle_source))
    bridge = MantleBridge(_resident_tree(tmp_path))
    Organism = bridge._organism_class()
    from mantle.primer import appai_commandments, appai_truths

    product = bridge.product_root
    org = Organism.birth(
        identity={"name": "Organize.AppAI"},
        truths=appai_truths(),
        commandments=appai_commandments(),
    )
    org.save(str(product / ".mantle"))
    secret = "test-provider-secret-without-key-prefix"

    kind = bridge.remember_body_command(
        f"/key {secret}",
        status="executed",
        ok=True,
        changed_fields=("credential",),
        public_state={
            "provider": "openrouter",
            "model": DEFAULT_MODEL,
            "credential_configured": True,
        },
    )

    restored = MantleBridge(product).load()
    serialized = json.dumps(
        {
            "events": restored.prime.read("events"),
            "senses": restored.prime.read("senses"),
        },
        sort_keys=True,
    )
    assert kind == "BODY_CONFIGURATION_CHANGED"
    assert "BODY_CONFIGURATION_CHANGED" in serialized
    assert "/key [REDACTED_SECRET]" in serialized
    assert secret not in serialized
