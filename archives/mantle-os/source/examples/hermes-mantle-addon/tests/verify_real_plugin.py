"""Reproducible real-Hermes PluginManager verification.

Run with the Python interpreter from a Hermes Agent environment, for example:
    ~/.hermes/hermes-agent/venv/bin/python tests/verify_real_plugin.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace


OBSERVER_HOOKS = {
    "on_session_start",
    "on_session_end",
    "on_session_finalize",
    "pre_llm_call",
    "post_llm_call",
    "pre_tool_call",
    "post_tool_call",
    "pre_approval_request",
    "post_approval_response",
    "subagent_start",
    "subagent_stop",
    "pre_gateway_dispatch",
}


def _worker(mode: str) -> dict[str, object]:
    import hermes_cli.plugins as plugins_module  # pyright: ignore[reportMissingImports]
    from hermes_cli.plugins import (  # pyright: ignore[reportMissingImports]
        PluginManager,
        VALID_HOOKS,
    )
    from model_tools import handle_function_call  # pyright: ignore[reportMissingImports]
    from tools.registry import registry  # pyright: ignore[reportMissingImports]

    assert OBSERVER_HOOKS <= VALID_HOOKS
    manager = PluginManager()
    manager.discover_and_load()
    row = next(
        item for item in manager.list_plugins() if item.get("name") == "mantle-os"
    )
    if mode == "disabled":
        assert row["enabled"] is False
        assert "not enabled" in str(row["error"])
        assert registry.get_entry("mantle_status") is None
        assert registry.get_entry("mantle_record_discovery") is None
        assert "mind" not in manager._plugin_commands
        assert not (OBSERVER_HOOKS & set(manager._hooks))
        return {"mode": mode, "enabled": False, "hooks": 0, "commands": 0}

    assert row["enabled"] is True and row["error"] is None, row
    plugins_module._plugin_manager = manager
    assert OBSERVER_HOOKS <= set(manager._hooks)
    status_entry = registry.get_entry("mantle_status")
    assert status_entry is not None
    status = json.loads(
        handle_function_call(
            "mantle_status",
            {},
            tool_call_id="status-integration",
            session_id="session-integration",
        )
    )
    assert status["mantle_version"], "runtime version must be reported"
    discovery_entry = registry.get_entry("mantle_record_discovery")
    assert discovery_entry is not None
    discovery_text = "bounded integration discovery"
    discovery_result = json.loads(
        handle_function_call(
            "mantle_record_discovery",
            {"idea": discovery_text},
            tool_call_id="discovery-integration",
            session_id="session-integration",
        )
    )
    assert discovery_result["success"] is True
    assert discovery_result["verified"] is False
    assert discovery_result["classification"] == "inferred"

    sensitive = [
        "sk-integration-user",
        "sk-integration-history",
        "sk-integration-assistant",
        "sk-integration-command",
        "sk-integration-result",
        "call-integration-ok",
        "call-integration-blocked",
        "approval-secret-command",
        "subagent-secret-goal",
        "gateway-secret-message",
    ]
    dispatched: list[str] = []

    def invoke(hook_name: str, **kwargs: object) -> None:
        results = manager.invoke_hook(hook_name, **kwargs)
        assert results == [], (hook_name, results)
        dispatched.append(hook_name)

    invoke("on_session_start", session_id="session-integration")
    invoke(
        "pre_llm_call",
        session_id="session-integration",
        user_message=sensitive[0],
        conversation_history=[{"role": "user", "content": sensitive[1]}],
        is_first_turn=False,
        model="provider/model",
    )
    invoke(
        "post_llm_call",
        session_id="session-integration",
        user_message=sensitive[0],
        assistant_response=sensitive[2],
        conversation_history=[],
        model="provider/model",
    )
    invoke(
        "pre_tool_call",
        tool_name="terminal",
        args={"command": sensitive[3], sensitive[3]: "value"},
        tool_call_id=sensitive[5],
        session_id="session-integration",
    )
    invoke(
        "post_tool_call",
        tool_name="terminal",
        args={"command": sensitive[3]},
        result=sensitive[4],
        tool_call_id=sensitive[5],
        session_id="session-integration",
        status="error",
        error_type="PermissionError",
        error_message="private",
        duration_ms=3,
    )
    invoke(
        "post_tool_call",
        tool_name="write_file",
        args={"path": "/tmp/x"},
        result="blocked",
        tool_call_id=sensitive[6],
        session_id="session-integration",
        status="blocked",
        error_type="plugin_block",
    )
    invoke(
        "pre_approval_request",
        command=sensitive[7],
        description="dangerous command",
        surface="cli",
    )
    invoke(
        "post_approval_response",
        command=sensitive[7],
        description="dangerous command",
        surface="cli",
        choice="deny",
    )
    invoke(
        "subagent_start",
        child_goal=sensitive[8],
        child_role="leaf",
        parent_session_id="parent-secret-id",
        child_session_id="child-secret-id",
    )
    invoke(
        "subagent_stop",
        child_summary=sensitive[8],
        child_status="completed",
        duration_ms=7,
        parent_session_id="parent-secret-id",
        child_session_id="child-secret-id",
    )
    invoke(
        "pre_gateway_dispatch",
        event=SimpleNamespace(
            text=sensitive[9],
            message_type=SimpleNamespace(value="text"),
            media_urls=[],
            source=SimpleNamespace(platform=SimpleNamespace(value="telegram")),
        ),
        gateway=object(),
        session_store=object(),
    )
    invoke("on_session_finalize", session_id="session-integration")
    invoke("on_session_end", session_id="session-integration")

    callback = manager._hooks["pre_llm_call"][0]
    registry_runtime = callback.func.__self__
    runtime = registry_runtime.current()

    mind_prompt = "Who are you? echo-safe-integration-7319"

    class FakeMindModel:
        last_receipt = {
            "schema_version": "mantle-cognition-v1",
            "outcome": "SUCCESS",
            "attempts": 1,
            "provider": "integration-host",
            "model": "active",
            "total_tokens": 7,
            "cost_usd": 0.0,
        }

        def __call__(self, prompt: str) -> str:
            assert mind_prompt in prompt
            return mind_prompt

    runtime._model_factory = FakeMindModel
    mind_handler = manager._plugin_commands["mind"]["handler"]
    mind_result = mind_handler(mind_prompt)
    assert mind_result == f"AppAI MIND › {mind_prompt}"
    assert runtime.organism.brain.fused is False

    organism = runtime.organism
    senses = organism.prime.read("senses")
    brain = organism.prime.read("brain")
    discoveries = organism.memory.recall("discoveries")
    assert discoveries[-1]["content"]["idea"] == discovery_text
    assert discoveries[-1]["verified"] is False
    assert discoveries[-1]["confidence"] == "inferred"
    serialized = json.dumps(
        {
            "bands": {
                band: organism.prime.read(band, reveal_private=True)
                for band in organism.prime.bands
            },
            "immune": organism.immune.log,
        },
        sort_keys=True,
    )
    assert mind_prompt not in serialized
    for value in sensitive:
        assert value not in serialized, value
    assert "parent-secret-id" not in serialized
    assert "child-secret-id" not in serialized
    assert len(dispatched) == 13
    assert set(dispatched) == OBSERVER_HOOKS

    signals = [
        item["content"]["signal"]
        for item in senses
        if isinstance(item.get("content", {}).get("signal"), dict)
    ]
    pre = next(item for item in signals if item.get("event_type") == "pre_llm_call")
    post = next(item for item in signals if item.get("event_type") == "post_llm_call")
    assert pre["metadata"]["user_message"]["chars"] == len(sensitive[0])
    assert pre["metadata"]["conversation_history"]["items"] == 1
    assert post["metadata"]["assistant_response"]["chars"] == len(sensitive[2])

    proofs = [
        item["content"]["action_proof"]
        for item in brain
        if isinstance(item.get("content", {}).get("action_proof"), dict)
    ]
    assert any(
        proof["control"] == "hermes.mantle.record_discovery"
        and proof["attempted"] is True
        and proof["ok"] is True
        and proof["method"] == "ControlBridge"
        for proof in proofs
    )
    assert any(
        proof["attempted"] is True
        and proof["ok"] is False
        and proof["method"] == "Hermes dispatch"
        for proof in proofs
    )
    assert any(
        proof["attempted"] is False
        and proof["ok"] is False
        and proof["method"] is None
        and proof["evidence"][0]["status"] == "blocked"
        for proof in proofs
    )

    resident = Path(runtime._handle.path)
    assert json.loads((resident / "organism.json").read_text(encoding="utf-8"))[
        "stage1_certified"
    ] is False
    for node in [resident, *resident.rglob("*")]:
        assert node.lstat().st_mode & 0o077 == 0, (node, oct(node.lstat().st_mode))
    return {
        "mode": mode,
        "enabled": True,
        "hooks": len(OBSERVER_HOOKS),
        "commands": 1,
        "proofs": len(proofs),
        "stage1_certified": False,
        "raw_exclusion": True,
        "owner_only": True,
        "dispatched": len(dispatched),
        "distinct_hooks_dispatched": len(set(dispatched)),
        "tools_dispatched": 2,
    }


def _coordinator() -> None:
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="hermes-mantle-integration-") as temp:
        sandbox = Path(temp)
        workspace = sandbox / "workspace"
        plugin = workspace / ".hermes" / "plugins" / "mantle-os"
        shutil.copytree(
            project,
            plugin,
            ignore=shutil.ignore_patterns(".git", ".runtime", "__pycache__", "*.pyc"),
        )
        results: dict[str, object] = {}
        for mode in ("enabled", "disabled"):
            hermes_home = sandbox / f"home-{mode}"
            hermes_home.mkdir()
            enabled = ["mantle-os"] if mode == "enabled" else []
            (hermes_home / "config.yaml").write_text(
                "plugins:\n  enabled: " + json.dumps(enabled) + "\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "HERMES_HOME": str(hermes_home),
                    "HERMES_ENABLE_PROJECT_PLUGINS": "1",
                    "MANTLE_ADDON_RUNTIME_ROOT": str(
                        (project.parents[1] / "src" / "mantle").resolve()
                    ),
                }
            )
            completed = subprocess.run(
                [sys.executable, __file__, "--worker", mode],
                cwd=workspace,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
                timeout=180,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{mode} PluginManager verification failed:\n"
                    + completed.stdout
                    + completed.stderr
                )
            results[mode] = json.loads(completed.stdout)
        print(json.dumps(results, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        print(json.dumps(_worker(sys.argv[2]), sort_keys=True))
    else:
        _coordinator()
