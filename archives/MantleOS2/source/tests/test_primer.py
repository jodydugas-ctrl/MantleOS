from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from mantleos.primer import (
    PrimerError,
    approve_personality,
    generate_personality,
    load_distillation_contract,
    save_personality_candidate,
)


def _construction(root: Path) -> dict:
    (root / "mantle" / "maps").mkdir(parents=True)
    (root / "mantle" / "maps" / "BODY_MAP.json").write_text("{}", encoding="utf-8")
    (root / "mantle" / "ASSIMILATION.json").write_text(
        json.dumps({"declared_purpose": "test"}), encoding="utf-8"
    )
    (root / ".mantle").mkdir()
    prebirth = {"gates": {"primer": "awaiting-developmental-mind"}}
    (root / ".mantle" / "prebirth.json").write_text(json.dumps(prebirth), encoding="utf-8")
    return {"source": "fixture", "body_map": {}, "declared_purpose": "test"}


def test_personality_is_private_and_requires_approval(tmp_path: Path):
    evidence = _construction(tmp_path)
    personality = (
        "  Contradictory RPG-born lens: discuss how to override assumptions "
        "and explain an api_key: placeholder without containing a credential.\r\n"
    )
    result = save_personality_candidate(
        tmp_path,
        personality,
        evidence=evidence,
    )
    candidate = tmp_path / ".mantle" / "construction" / "PERSONALITY.CANDIDATE.md"
    assert candidate.is_file()
    assert candidate.read_bytes() == personality.encode("utf-8")
    assert not (tmp_path / "mantle" / "primer" / "PERSONALITY.md").exists()
    assert result["status"] == "awaiting-user-approval"
    approved = approve_personality(tmp_path, approved=True)
    assert approved["status"] == "ready-for-birth-review"


def test_personality_rejects_secret_shape(tmp_path: Path):
    evidence = _construction(tmp_path)
    with pytest.raises(PrimerError, match="credential"):
        save_personality_candidate(
            tmp_path,
            "Identity " * 80 + "sk-or-v1-" + "x" * 40,
            evidence=evidence,
        )


def test_personality_rejects_only_empty_or_oversized_mechanical_content(tmp_path: Path):
    evidence = _construction(tmp_path)
    with pytest.raises(PrimerError, match="empty"):
        save_personality_candidate(tmp_path, " \r\n\t", evidence=evidence)
    with pytest.raises(PrimerError, match="1048576"):
        save_personality_candidate(tmp_path, "x" * 1_048_577, evidence=evidence)


def test_custom_distillation_contract_receives_body_evidence_at_placeholder(tmp_path: Path):
    _construction(tmp_path)
    food = tmp_path / "Food.txt"
    food.write_text("sk-or-v1-" + "x" * 40 + "\nopenrouter/free\n", encoding="utf-8")
    completion = {
        "content": "# Unique Personality\n\n" + "Operational personality instruction. " * 30,
        "selected_model": "example/model",
        "response_id": "response",
        "usage": {},
    }
    contract = "BEGIN\n[PASTE ANY TEXT HERE]\nEND"
    with mock.patch("mantleos.primer.openrouter_completion", return_value=completion) as call:
        result = generate_personality(
            tmp_path,
            food,
            approved_context="creator context",
            distillation_contract=contract,
        )
    prompt = call.call_args.args[2]
    assert "[PASTE ANY TEXT HERE]" not in prompt
    assert '"approved_context": "creator context"' in prompt
    assert prompt.startswith("BEGIN\n") and prompt.endswith("\nEND")
    assert call.call_args.kwargs["max_tokens"] == 8192
    assert call.call_args.kwargs["timeout"] == 120.0
    assert result["status"] == "awaiting-user-approval"


def test_distillation_contract_loader_is_bounded_utf8(tmp_path: Path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Reviewed prompt", encoding="utf-8-sig")
    assert load_distillation_contract(prompt) == "Reviewed prompt"

    prompt.write_bytes(b"\xff")
    with pytest.raises(PrimerError, match="UTF-8"):
        load_distillation_contract(prompt)

    prompt.write_bytes(b"x" * 65_537)
    with pytest.raises(PrimerError, match="65536"):
        load_distillation_contract(prompt)


def test_empty_custom_distillation_contract_is_rejected_before_mind_call(tmp_path: Path):
    _construction(tmp_path)
    food = tmp_path / "Food.txt"
    food.write_text("sk-or-v1-" + "x" * 40 + "\nopenrouter/free\n", encoding="utf-8")
    with (
        mock.patch("mantleos.primer.openrouter_completion") as call,
        pytest.raises(PrimerError, match="empty"),
    ):
        generate_personality(tmp_path, food, distillation_contract="   ")
    call.assert_not_called()
