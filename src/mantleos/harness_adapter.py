"""Optional, stdlib-only Harness model-response adapter for the HostedBridge.

The caller supplies a *restricted, externally configured* subprocess SDK runner.
This adapter grants no filesystem, shell, network, approval, or publication rights.
Never treat a Harness session or tool response as an Engram record or effect receipt.
"""
from __future__ import annotations

import json
import hashlib
from collections.abc import Callable

MAX_FRAME_BYTES = 2_500_000
MAX_RESPONSE_BYTES = 524_288


class HarnessResponseAdapter:
    """Make a Harness text runner satisfy HostedBridge's `generate(frame)` seam.

    `runner(prompt, session_id)` returns raw *JSON object* text, not markdown.
    The externally provided runner owns process lifecycle, isolation, timeouts,
    model selection, and plugin capabilities; none is inferred or granted here.
    """

    def __init__(self, runner: Callable[[str, str], str]):
        if not callable(runner):
            raise TypeError("Harness runner must be callable")
        self._runner = runner

    def __call__(self, frame: dict) -> dict:
        if not isinstance(frame, dict) or frame.get("schema") != "mantle.hosted-frame/1":
            raise ValueError("Invalid hosted frame")
        request = frame.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("request_id"), str):
            raise ValueError("Hosted frame is missing request identity")
        if frame.get("stage") not in ("ORIENT", "RESPOND"):
            raise ValueError("Unsupported hosted stage")
        prompt = json.dumps(frame, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(prompt.encode("utf-8")) > MAX_FRAME_BYTES:
            raise ValueError("Hosted frame exceeds Harness prompt budget")
        # Explicitly distinct stage sessions prevent accidental cross-stage model-memory
        # authority; all stage-relevant data is already in the bounded hosted frame.
        request_digest = hashlib.sha256(request["request_id"].encode("utf-8")).hexdigest()
        session_id = f"mantle-{request_digest}-{frame['stage'].lower()}"
        raw = self._runner(prompt, session_id)
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ValueError("Invalid or oversized Harness response")
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate Harness response key")
                result[key] = value
            return result
        try:
            parsed = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite number")))
        except (ValueError, TypeError) as exc:
            raise ValueError("Harness response must be a strict JSON object") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Harness response must be a JSON object")
        # HostedBridge independently validates stage schema, request bindings,
        # action permission, native program source, and Engram append authority.
        return parsed
