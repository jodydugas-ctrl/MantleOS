"""Optional session-local organ: no external storage or MIND dependency."""


class Continuity:
    def __init__(self):
        self.events = []

    def record(self, command, value, response):
        self.events.append({"command": command, "value": value, "response": response.copy()})

    def recall(self):
        return list(self.events)

    def on_success(self, result, agent, command, value=None):
        """Supported KPP after-success observer contract for staged adapters."""
        self.record(command, value, result)
