"""Direct Hermes innervation.

This module is a construction-time language mapper.  It inserts direct calls
at verified Hermes lifecycle seams and records enough evidence to reproduce or
reverse every insertion.  It is not loaded by Hermes at runtime.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from mantleos.contracts import Direction, NerveSpec, SourceAnchor, TissueState, contract_dict


class HermesInnervationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Insertion:
    path: str
    symbol: str
    semantic_event: str
    direction: Direction
    anchor: str
    source: str
    book_id: str = "book:layer-0:v2"
    capability_id: str | None = None
    nerve_id: str | None = None


INSERTIONS = (
    Insertion(
        path="agent/conversation_loop.py",
        symbol="initialize_conversation",
        semantic_event="body.session.started",
        direction=Direction.AFFERENT,
        anchor="    # Plugin hook: on_session_start",
        source="""    # MantleOS direct afferent nerve: session boundary.\n    try:\n        from mantle.nerves import session_started as _mantle_session_started\n        _mantle_session_started(\n            session_id=agent.session_id or \"\",\n            model=agent.model or \"\",\n            surface=getattr(agent, \"platform\", None) or \"\",\n        )\n    except Exception:\n        logger.debug(\"Mantle session nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
    ),
    Insertion(
        path="agent/turn_context.py",
        symbol="prepare_turn_context",
        semantic_event="communication.user.message",
        direction=Direction.BIDIRECTIONAL,
        anchor="    # Gateway must-deliver notes (auto-reset note, first-contact intro,",
        source="""    # MantleOS direct nerve: committed user turn and Primer-first AppAI context.\n    try:\n        from mantle.nerves import before_mind as _mantle_before_mind\n        _mantle_turn = _mantle_before_mind(\n            user_message=original_user_message,\n            session_id=agent.session_id or \"\",\n            turn_id=turn_id,\n            surface=getattr(agent, \"platform\", None) or \"\",\n        )\n        _mantle_context = _mantle_turn.get(\"context\", \"\")\n        if _mantle_context:\n            plugin_user_context = (\n                _mantle_context + \"\\n\\n\" + plugin_user_context\n                if plugin_user_context\n                else _mantle_context\n            )\n    except Exception:\n        logger.debug(\"Mantle committed-turn nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
    ),
    Insertion(
        path="agent/turn_finalizer.py",
        symbol="finalize_turn",
        semantic_event="appai.mind.turn",
        direction=Direction.AFFERENT,
        anchor="    # Plugin hook: post_llm_call",
        source="""    # MantleOS direct afferent nerve: finalized semantic MIND turn.\n    if final_response and not interrupted:\n        try:\n            from mantle.nerves import after_mind as _mantle_after_mind\n            _mantle_after_mind(\n                user_message=original_user_message,\n                assistant_response=final_response,\n                session_id=agent.session_id or \"\",\n                turn_id=turn_id,\n                surface=getattr(agent, \"platform\", None) or \"\",\n            )\n        except Exception:\n            logger.debug(\"Mantle MIND-result nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
    ),
    Insertion(
        path="agent/tool_executor.py",
        symbol="_authorized_dispatch",
        semantic_event="appai.limb.proposed",
        direction=Direction.EFFERENT,
        anchor='        if block_message is None:\n            block_error_type = "plugin_block"',
        source="""        # MantleOS direct efferent nerve: AppAI Limb proposal.\n        if block_message is None:\n            try:\n                from mantle.nerves import authorize_tool as _mantle_authorize_tool\n                _mantle_block = _mantle_authorize_tool(\n                    tool_name=function_name,\n                    arguments=final_args,\n                    session_id=getattr(agent, \"session_id\", \"\") or \"\",\n                    turn_id=getattr(agent, \"_current_turn_id\", \"\") or \"\",\n                )\n                if _mantle_block:\n                    block_message = _mantle_block\n                    block_error_type = \"mantle_authority_block\"\n            except Exception:\n                logger.debug(\"Mantle Limb-authority nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
        book_id="book:actions:v2",
        capability_id="hermes.tool-dispatch",
    ),
    Insertion(
        path="agent/tool_executor.py",
        symbol="_emit_terminal_post_tool_call",
        semantic_event="body.tool.completed",
        direction=Direction.AFFERENT,
        anchor='def _cancelled_tool_result(reason: str = "user interrupt") -> str:',
        source="""\n    # MantleOS direct afferent nerve: one terminal semantic tool event.\n    try:\n        from mantle.nerves import tool_completed as _mantle_tool_completed\n        _mantle_tool_completed(\n            tool_name=function_name,\n            arguments=function_args,\n            status=status or (\"failed\" if error_type else \"completed\"),\n            duration_ms=duration_ms,\n            session_id=getattr(agent, \"session_id\", \"\") or \"\",\n            turn_id=getattr(agent, \"_current_turn_id\", \"\") or \"\",\n        )\n    except Exception:\n        logger.debug(\"Mantle tool nerve unavailable\", exc_info=True)\n""",  # noqa: E501
    ),
    Insertion(
        path="agent/turn_finalizer.py",
        symbol="finalize_turn",
        semantic_event="body.turn.ended",
        direction=Direction.AFFERENT,
        anchor="    # Plugin hook: on_session_end",
        source="""    # MantleOS direct afferent nerve: completed turn boundary.\n    try:\n        from mantle.nerves import turn_ended as _mantle_turn_ended\n        _mantle_turn_ended(\n            session_id=agent.session_id or \"\",\n            turn_id=turn_id,\n            completed=completed,\n            failed=failed,\n            interrupted=interrupted,\n        )\n    except Exception:\n        logger.debug(\"Mantle turn-end nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
    ),
    Insertion(
        path="cli.py",
        symbol="_notify_session_finalize",
        semantic_event="body.session.ended",
        direction=Direction.AFFERENT,
        anchor="    try:\n        from hermes_cli.lifecycle import finalize_session",
        source="""    # MantleOS direct afferent nerve: actual CLI session boundary.\n    try:\n        from mantle.nerves import session_ended as _mantle_session_ended\n        _mantle_session_ended(\n            session_id=session_id or \"\",\n            surface=platform or \"cli\",\n            reason=reason or \"shutdown\",\n        )\n    except Exception:\n        logger.debug(\"Mantle CLI session-end nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
        nerve_id="hermes:cli:body.session.ended",
    ),
    Insertion(
        path="tui_gateway/server.py",
        symbol="_finalize_session",
        semantic_event="body.session.ended",
        direction=Direction.AFFERENT,
        anchor='    agent = session.get("agent")\n    lock = session.get("history_lock")',
        source="""    # MantleOS direct afferent nerve: actual gateway session boundary.\n    _mantle_agent = session.get(\"agent\")\n    if _mantle_agent is not None:\n        try:\n            from mantle.nerves import session_ended as _mantle_session_ended\n            _mantle_session_ended(\n                session_id=getattr(_mantle_agent, \"session_id\", None)\n                or session.get(\"session_key\", \"\"),\n                surface=_session_source(session) or \"tui\",\n                reason=end_reason or \"tui_close\",\n            )\n        except Exception:\n            logger.debug(\"Mantle gateway session-end nerve unavailable\", exc_info=True)\n\n""",  # noqa: E501
        nerve_id="hermes:gateway:body.session.ended",
    ),
)


def is_hermes(root: Path) -> bool:
    return all(
        (root / path).is_file()
        for path in ("run_agent.py", "agent/conversation_loop.py", "agent/turn_context.py")
    )


def innervate(root: Path) -> list[dict]:
    if not is_hermes(root):
        raise HermesInnervationError("The Body does not match the Hermes substrate map")
    records: list[dict] = []
    for insertion in INSERTIONS:
        path = root / insertion.path
        before = path.read_bytes()
        text = before.decode("utf-8")
        eol = "\r\n" if "\r\n" in text else "\n"
        inserted_source = insertion.source.replace("\n", eol)
        anchor = insertion.anchor.replace("\n", eol)
        if inserted_source in text:
            raise HermesInnervationError(f"Nerve is already present: {insertion.semantic_event}")
        if text.count(anchor) != 1:
            raise HermesInnervationError(
                f"Hermes seam drifted for {insertion.semantic_event}: {insertion.path}"
            )
        anchor_sha = hashlib.sha256(insertion.anchor.encode("utf-8")).hexdigest()
        changed = text.replace(anchor, inserted_source + anchor, 1)
        path.write_bytes(changed.encode("utf-8"))
        nerve = NerveSpec(
            nerve_id=insertion.nerve_id or f"hermes:{insertion.semantic_event}",
            direction=insertion.direction,
            semantic_event=insertion.semantic_event,
            anchor=SourceAnchor(
                insertion.path,
                insertion.symbol,
                anchor_sha,
                "before-anchor",
            ),
            book_id=insertion.book_id,
            capability_id=insertion.capability_id,
            tissue_state=TissueState.STAGED,
        )
        record = contract_dict(nerve)
        record["before_sha256"] = hashlib.sha256(before).hexdigest()
        record["after_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(record)
    return records
