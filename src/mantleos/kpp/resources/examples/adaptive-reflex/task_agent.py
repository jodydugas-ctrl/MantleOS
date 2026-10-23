"""Original conventional task agent. Keep unchanged during the demo splice."""


class TaskAgent:
    def __init__(self):
        self.tasks = []

    def execute(self, command, value=None):
        if command == "add" and isinstance(value, str) and value.strip():
            self.tasks.append(value)
            return {"ok": True, "message": "Added: " + value}
        if command == "list":
            return {"ok": True, "message": list(self.tasks)}
        return {"ok": False, "message": "Unknown or invalid command"}


def run_command(agent, command, value=None):
    return agent.execute(command, value)
