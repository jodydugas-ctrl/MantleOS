"""Offline adapter boundary checks; no provider calls or real credentials."""

from __future__ import annotations

import http.client
import io
import json
import urllib.error
import urllib.request
from unittest.mock import Mock

import pytest

from mantleos import nutrition


def completion():
    return {
        "id": "gen-fixture-1",
        "model": "fixture/model",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "  Hello.\r\n"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7, "cost": 0},
    }


def encode(value):
    return json.dumps(value).encode("utf-8")


def invoke(monkeypatch, raw):
    response = io.BytesIO(raw)
    response.read = Mock(wraps=response.read)
    opener = Mock()
    opener.open.return_value = response
    factory = Mock(return_value=opener)
    monkeypatch.setattr(nutrition.urllib.request, "build_opener", factory)
    result = nutrition.openrouter_completion("fixture-credential", "fixture/router", "fixture input")
    return result, response, opener, factory


def test_complete_text_preserved_and_request_remains_text_only(monkeypatch):
    result, response, opener, factory = invoke(monkeypatch, encode(completion()))
    assert result == {
        "content": "  Hello.\r\n", "selected_model": "fixture/model",
        "response_id": "gen-fixture-1", "usage": completion()["usage"],
    }
    response.read.assert_called_once_with(nutrition.MAX_PROVIDER_RESPONSE_BYTES + 1)
    assert response.closed
    opener.open.assert_called_once()
    request = opener.open.call_args.args[0]
    assert request.full_url == nutrition.OPENROUTER_CHAT_URL
    payload = json.loads(request.data)
    assert payload["stream"] is False
    assert not {"tools", "plugins", "functions"} & payload.keys()
    assert isinstance(factory.call_args.args[0], nutrition._RefuseRedirect)


@pytest.mark.parametrize("finish", [None, "length", "tool_calls", "content_filter", "error", "unknown"])
def test_nonterminal_and_partial_results_are_not_completions(finish):
    value = completion()
    value["choices"][0]["finish_reason"] = finish
    with pytest.raises(nutrition.NutritionError, match="invalid or incomplete"):
        nutrition._completion_from_bytes(encode(value))


@pytest.mark.parametrize("raw", [
    b'{"choices": [], "choices": []}',
    b'{"extra": {"sensitive-name": 1, "sensitive-name": 2}}',
    b'{"extra": NaN}', b'{"extra": Infinity}', b'{"extra": -Infinity}',
    b'\xff', b'{', b'[]', b'null', b'"hello"', b'',
    b'[' * 2000 + b']' * 2000,
])
def test_malformed_ambiguous_or_deep_json_is_refused_without_echo(raw):
    with pytest.raises(nutrition.NutritionError) as failure:
        nutrition._completion_from_bytes(raw)
    assert "sensitive-name" not in str(failure.value)


@pytest.mark.parametrize("field,value", [
    ("role", "user"), ("content", " \t"), ("content", None), ("content", "\ud800"),
    ("tool_calls", [{"function": {"name": "write", "arguments": "{}"}}]),
    ("function_call", {"name": "write"}), ("refusal", "not allowed"),
])
def test_unsupported_message_is_not_admitted(field, value):
    candidate = completion()
    candidate["choices"][0]["message"][field] = value
    with pytest.raises(nutrition.NutritionError):
        nutrition._completion_from_bytes(encode(candidate))


@pytest.mark.parametrize("field,value", [
    ("choices", []), ("choices", [None]), ("choices", completion()["choices"] * 2),
    ("choices", {}), ("model", None), ("id", ""), ("id", "x" * 257),
    ("id", "contains a private sentence"), ("error", {"message": "sensitive-provider-error"}),
])
def test_invalid_envelope_does_not_fabricate_reported_identity(field, value):
    candidate = completion()
    candidate[field] = value
    with pytest.raises(nutrition.NutritionError) as failure:
        nutrition._completion_from_bytes(encode(candidate))
    assert "sensitive-provider-error" not in str(failure.value)


def test_oversize_read_is_bounded_and_not_retried(monkeypatch):
    monkeypatch.setattr(nutrition, "MAX_PROVIDER_RESPONSE_BYTES", 128)
    raw = b"x" * 1000
    with pytest.raises(nutrition.NutritionError, match="bounded"):
        invoke(monkeypatch, raw)
    opener = nutrition.urllib.request.build_opener.return_value
    opener.open.assert_called_once()
    opener.open.return_value.read.assert_called_once_with(129)
    assert opener.open.return_value.closed


def test_receipt_only_contains_declared_numeric_usage():
    candidate = completion()
    candidate["usage"] = {
        "prompt_tokens": True, "completion_tokens": -1, "total_tokens": 7,
        "cost": "sensitive-provider-data", "extra": {"arbitrary": "private"},
    }
    assert nutrition._completion_from_bytes(encode(candidate))["usage"] == {"total_tokens": 7}


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_redirects_cannot_forward_credentials_or_private_context(code):
    # Exercise urllib's real redirect dispatcher without a socket or second request.
    request = urllib.request.Request(nutrition.OPENROUTER_CHAT_URL, data=b"private context")
    request.add_header("Authorization", "Bearer fixture-credential")
    handler = nutrition._RefuseRedirect()
    handler.parent = Mock()
    dispatch = getattr(handler, f"http_error_{code}")
    with pytest.raises(nutrition.NutritionError, match="redirect refused"):
        dispatch(request, io.BytesIO(), code, "redirect", {"location": "https://other.invalid/"})
    handler.parent.open.assert_not_called()


@pytest.mark.parametrize("error", [
    TimeoutError("private payload"), urllib.error.URLError("private payload"),
    http.client.IncompleteRead(b"private payload"),
    urllib.error.HTTPError(nutrition.OPENROUTER_CHAT_URL, 401, "private payload", {}, None),
])
def test_transport_failure_is_secret_safe_and_not_retried(monkeypatch, error):
    opener = Mock()
    opener.open.side_effect = error
    monkeypatch.setattr(nutrition.urllib.request, "build_opener", Mock(return_value=opener))
    with pytest.raises(nutrition.NutritionError) as failure:
        nutrition.openrouter_completion("fixture-credential", "fixture/model", "fixture")
    assert "private payload" not in str(failure.value)
    opener.open.assert_called_once()
