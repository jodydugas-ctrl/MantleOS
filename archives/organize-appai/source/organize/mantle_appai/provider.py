"""Small vendor-neutral provider boundary for optional natural-language interpretation."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderUnavailable(RuntimeError):
    pass


class ProposalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_yaml: str = Field(min_length=1, max_length=32_000)
    explanation: str = Field(min_length=1, max_length=4_000)
    assumptions: list[str] = Field(default_factory=list, max_length=30)


class EvidenceCitation(BaseModel):
    """A model citation into the bounded evidence packet supplied by AppAI."""

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(min_length=1, max_length=240)
    claim: str = Field(min_length=1, max_length=500)


class AnswerPayload(BaseModel):
    """Typed answer returned by an optional MIND provider."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=8_000)
    citations: list[EvidenceCitation] = Field(min_length=1, max_length=30)
    uncertainty: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def citations_are_unique(self) -> AnswerPayload:
        refs = [citation.ref for citation in self.citations]
        if len(refs) != len(set(refs)):
            raise ValueError("citation refs must be unique")
        return self


class MindProvider(Protocol):
    name: str

    def complete(self, prompt: str) -> str: ...


class DisabledProvider:
    name = "disabled"

    def complete(self, prompt: str) -> str:
        raise ProviderUnavailable("no MIND provider is configured")


class FakeProvider:
    """Deterministic provider for tests and the offline demo."""

    name = "fake"

    def __init__(self, response: str | dict[str, object]) -> None:
        self.response = response if isinstance(response, str) else json.dumps(response)

    def complete(self, prompt: str) -> str:
        return self.response


class MantleCallableProvider:
    """Adapter for an operator-supplied callable already bounded by MantleOS."""

    name = "mantle-callable"

    def __init__(self, model: Callable[[str], str]) -> None:
        self.model = model

    def complete(self, prompt: str) -> str:
        return self.model(prompt)


def parse_proposal_response(raw: str) -> ProposalPayload:
    """Treat model output as untrusted JSON and reject anything outside the schema."""

    return ProposalPayload.model_validate_json(raw)


def parse_answer_response(raw: str) -> AnswerPayload:
    """Treat a natural-language answer as untrusted typed JSON."""

    return AnswerPayload.model_validate_json(raw)
