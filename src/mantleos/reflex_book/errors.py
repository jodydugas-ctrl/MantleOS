"""Stable, machine-readable prototype refusal codes."""


class ReflexError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def refuse(code: str, detail: str):
    raise ReflexError(code, detail)
