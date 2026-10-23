"""Copy into a disposable integrated Hermes tests/ directory and use its runner.

Calls real pinned host functions with upstream fake agents and local tool stubs.
No model or specimen code executes. Birth is synthetic and NEST-local.
"""
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from mantle import nerves
from mantle.runtime.mantleos import appai, engram


@pytest.fixture(scope='module')
def nest():
    root = nerves.NEST
    if appai.status(root)['phase'] == 'UNBORN':
        appai.birth(root)
    appai.phase(root, True)
    yield root
    appai.phase(root, False)


def helper(path):
    return runpy.run_path(str(nerves.NEST / path))


def test_session_and_committed_turn_connections(nest, monkeypatch):
    from agent.conversation_loop import _restore_or_build_system_prompt
    monkeypatch.setattr('agent.credits_tracker.seed_credits_at_session_start', lambda a: None)
    agent = SimpleNamespace(_session_db=None, session_id='connection-start', model='fixture',
                            platform='cli', _build_system_prompt=lambda s: 'SYSTEM')
    _restore_or_build_system_prompt(agent, None, [])
    assert agent._cached_system_prompt == 'SYSTEM'
    h = helper('tests/agent/test_turn_context.py')
    agent = h['_FakeAgent']()
    agent.session_id = 'connection-turn'
    ctx = h['_build'](agent, user_message='@appai inspect safely')
    assert 'SELF is the complete host installation' in ctx.plugin_user_context
    assert agent._mantle_addressed is True
    events = [r['body'].get('event') for r in engram.read(appai.body(nest) / 'ENGRAM.jsonl')]
    assert 'body.session.started' in events
    assert 'communication.user.message' in events


def test_finalized_mind_and_turn_connections(nest, monkeypatch):
    helper('tests/agent/test_turn_finalizer_final_response_persistence.py')[
        'test_final_response_closes_tool_tail_before_persistence'](monkeypatch)
    events = [r['body'].get('event') for r in engram.read(appai.body(nest) / 'ENGRAM.jsonl')]
    assert 'appai.mind.turn' in events
    assert 'body.turn.ended' in events


def test_both_session_end_connections(nest):
    from cli import _notify_session_finalize
    from tui_gateway.server import _finalize_session
    _notify_session_finalize(session_id='connection-cli', platform='cli', reason='fixture')
    h = helper('tests/tui_gateway/test_finalize_session_persist.py')
    agent = h['_make_agent'](session_id='connection-tui')
    _finalize_session(h['_make_session'](agent=agent), end_reason='fixture')
    ended = [r['body']['values']['session_id'] for r in engram.read(appai.body(nest) / 'ENGRAM.jsonl')
             if r['body'].get('event') == 'body.session.ended']
    assert 'connection-cli' in ended and 'connection-tui' in ended


def test_motor_authority_completion_and_unavailable_tissue(nest, monkeypatch):
    from agent.tool_executor import _run_agent_tool_execution_middleware as dispatch
    agent = SimpleNamespace(session_id='connection-tool', _current_turn_id='tool-turn',
                            _tool_guardrails=SimpleNamespace(before_call=lambda *a: SimpleNamespace(allows_execution=True)))
    execute = Mock(return_value='local result')
    def invoke():
        return dispatch(agent, function_name='read_fixture', function_args={},
                        effective_task_id='fixture', tool_call_id='fixture-call', execute=execute,
                        begin_execution=lambda callback=None: None)
    nerves.before_mind(user_message='@appai inspect', session_id=agent.session_id, turn_id=agent._current_turn_id)
    agent._mantle_addressed = True
    result = invoke()
    assert result.blocked and 'operator grant' in result.result
    execute.assert_not_called()
    events = [r['body'].get('event') for r in engram.read(appai.body(nest) / 'ENGRAM.jsonl')]
    assert 'appai.limb.proposed' in events and 'body.tool.completed' in events
    appai.phase(nest, True, allowed_tools=['read_fixture'])
    assert invoke().result == 'local result'
    execute.assert_called_once()
    # Native guardrails still override the Mantle grant.
    agent._tool_guardrails.before_call = lambda *a: SimpleNamespace(allows_execution=False, message='native veto')
    agent._guardrail_block_result = lambda decision: decision.message
    assert invoke().blocked
    agent._tool_guardrails.before_call = lambda *a: SimpleNamespace(allows_execution=True)
    def unavailable(**kwargs):
        raise RuntimeError('injected unavailable tissue')
    monkeypatch.setattr(nerves, 'authorize_tool', unavailable)
    assert invoke().blocked
    agent._mantle_addressed = False
    assert invoke().result == 'local result'
