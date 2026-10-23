"""Fixed-oracle checks complement baseline-vs-integrated comparisons."""
from task_agent import TaskAgent, run_command
from integration import run_with_continuity
from continuity import Continuity


def main():
    # Fixed independent oracle for both paths: matching each other alone is inadequate.
    baseline = TaskAgent()
    integrated = TaskAgent()
    organ = Continuity()
    cases = [("add", "tea", {"ok": True, "message": "Added: tea"}),
             ("unknown", None, {"ok": False, "message": "Unknown or invalid command"}),
             ("list", None, {"ok": True, "message": ["tea"]})]
    for cmd, value, expected in cases:
        assert run_command(baseline, cmd, value) == expected
        assert run_with_continuity(integrated, cmd, value, organ) == expected
    assert [event["command"] for event in organ.recall()] == ["add", "list"]
    no_organ = TaskAgent()
    assert run_with_continuity(no_organ, "add", "tea") == {"ok": True, "message": "Added: tea"}
    assert run_with_continuity(no_organ, "list") == {"ok": True, "message": ["tea"]}
    print("PASS: original behavior, after-success continuity and optional-organ absence")


if __name__ == "__main__":
    main()
