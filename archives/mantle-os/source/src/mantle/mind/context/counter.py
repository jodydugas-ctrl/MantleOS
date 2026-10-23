"""Provider-neutral context token accounting."""
from __future__ import annotations

import math
from typing import Callable, Protocol

from .types import ModelRequest


class TokenCounter(Protocol):
    name: str
    version: str

    def count_text(self, text: str) -> int:
        ...

    def count_request(self, request: ModelRequest) -> int:
        ...


class ConservativeByteCounter:
    name = "conservative-byte-estimator"
    version = "1"

    def __init__(self, bytes_per_token: float = 3.0) -> None:
        if bytes_per_token <= 0:
            raise ValueError("bytes_per_token must be positive")
        self.bytes_per_token = float(bytes_per_token)

    def count_text(self, text: str) -> int:
        return int(math.ceil(len(text.encode("utf-8")) / self.bytes_per_token))

    def count_request(self, request: ModelRequest) -> int:
        return self.count_text(request.prompt)


class CallableTokenCounter:
    def __init__(self, counter: Callable[[str], int], *, name: str,
                 version: str = "1") -> None:
        self._counter = counter
        self.name = name
        self.version = version

    def count_text(self, text: str) -> int:
        count = int(self._counter(text))
        if count < 0:
            raise ValueError("token counter returned a negative count")
        return count

    def count_request(self, request: ModelRequest) -> int:
        return self.count_text(request.prompt)
