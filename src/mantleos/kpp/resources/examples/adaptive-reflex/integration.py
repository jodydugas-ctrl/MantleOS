"""Small explicit adapter; original task_agent.py is not changed."""
from task_agent import run_command


def run_with_continuity(agent, command, value=None, continuity=None):
    result = run_command(agent, command, value)
    if result["ok"] and continuity is not None:
        continuity.record(command, value, result)
    return result
