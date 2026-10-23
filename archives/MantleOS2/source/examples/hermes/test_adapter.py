from __future__ import annotations

import py_compile
from pathlib import Path

from examples.hermes.adapter import INSERTIONS, innervate, is_hermes


def _hermes_fixture(root: Path) -> Path:
    agent = root / "agent"
    agent.mkdir()
    gateway = root / "tui_gateway"
    gateway.mkdir()
    (root / "run_agent.py").write_text("class Agent: pass\n", encoding="utf-8")
    (root / "cli.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def _notify_session_finalize(*, session_id, platform='cli', reason='shutdown'):\n"
        "    try:\n"
        "        from hermes_cli.lifecycle import finalize_session\n"
        "        return finalize_session(session_id=session_id)\n"
        "    except Exception:\n"
        "        return None\n",
        encoding="utf-8",
    )
    (gateway / "server.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def _session_source(session):\n"
        "    return 'tui'\n"
        "def _finalize_session(session, end_reason='tui_close'):\n"
        "    agent = session.get(\"agent\")\n"
        "    lock = session.get(\"history_lock\")\n"
        "    return agent, lock\n",
        encoding="utf-8",
    )
    (agent / "conversation_loop.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def initialize_conversation(agent):\n"
        "    # Plugin hook: on_session_start — fired once when a brand-new\n"
        "    pass\n",
        encoding="utf-8",
    )
    (agent / "turn_context.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def prepare_turn_context(agent, original_user_message, turn_id):\n"
        "    plugin_user_context = ''\n"
        "    # Gateway must-deliver notes (auto-reset note, first-contact intro,\n"
        "    return plugin_user_context\n",
        encoding="utf-8",
    )
    (agent / "turn_finalizer.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def finalize_turn(agent, final_response, interrupted, original_user_message, turn_id, "
        "completed, failed):\n"
        "    # Plugin hook: post_llm_call\n"
        "    pass\n"
        "    # Plugin hook: on_session_end\n"
        "    return final_response\n",
        encoding="utf-8",
    )
    (agent / "tool_executor.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def execute(agent, function_name):\n"
        "    def _authorized_dispatch(final_args):\n"
        "        block_message = None\n"
        "        if block_message is None:\n"
        "            block_error_type = \"plugin_block\"\n"
        "        return block_message\n"
        "    return _authorized_dispatch({})\n"
        "\n\n"
        "def _emit_terminal_post_tool_call(agent, function_name, function_args, duration_ms=0, "
        "status=None, error_type=None):\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
        "\n\n"
        "def _cancelled_tool_result(reason: str = \"user interrupt\") -> str:\n"
        "    return reason\n",
        encoding="utf-8",
    )
    return root


def test_direct_innervation_is_reproducible_and_not_a_plugin(tmp_path: Path):
    root = _hermes_fixture(tmp_path)
    assert is_hermes(root)
    records = innervate(root)
    assert len(records) == len(INSERTIONS) == 8
    assert len({record["nerve_id"] for record in records}) == 8
    assert sum(record["semantic_event"] == "body.session.ended" for record in records) == 2
    assert {record["failure_mode"] for record in records} == {"native-no-op"}
    action_nerve = next(
        record for record in records if record["semantic_event"] == "appai.limb.proposed"
    )
    assert action_nerve["direction"] == "efferent"
    assert action_nerve["book_id"] == "book:actions:v2"
    assert action_nerve["capability_id"] == "hermes.tool-dispatch"
    all_source = "\n".join(
        (root / insertion.path).read_text(encoding="utf-8") for insertion in INSERTIONS
    )
    assert "from mantle.nerves import" in all_source
    assert "register_hook" not in all_source
    for path in {root / insertion.path for insertion in INSERTIONS}:
        py_compile.compile(str(path), doraise=True)
