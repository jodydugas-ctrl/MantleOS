#!/usr/bin/env python3
"""
mantle.ghost_http  --  the REAL cache-ghost substrate: a neutral HTTP prompt cache.

`HttpPromptCache` is a `GhostSubstrate` that haunts a real provider's prompt cache over an
**OpenAI-compatible** chat-completions endpoint. It is the honest realization of what
`mantle.ghost.LocalPromptCache` simulates -- and it holds to the same neutrality law the MIND
transport does (`mantle.mind.transport`): THERE IS NO VENDOR CODE HERE. A provider is
CONFIGURATION, never code. You point this substrate at a URL, hand it the headers and model
string your provider wants, and tell it the two physical facts that vary between providers --
the cache **window** (TTL) and the **minimum cacheable prefix**. Nothing about any company is
compiled in; swapping providers is swapping config, exactly as a nervous-system transplant
must allow.

Pure standard library (urllib), imported lazily: importing this module never opens a socket or
needs a key. No vendor SDK, ever.

WHY WRITE-ONLY (the physics `mantle.ghost` documents in full). A provider prompt cache can only
be spoken INTO. There is no fetch: the full prefix still travels on every request, and a warm
hit means the provider skipped PREFILL COMPUTE over the cached span (cheaper + faster), not that
anything was stored or that fewer bytes went over the wire. So `fetch()` returns None,
`hydrate()` rebuilds from the PNG fossil, and warmth is *observed* only as cache-hit telemetry on
the response -- read from the OpenAI-compatible `usage.prompt_tokens_details.cached_tokens`
field (providers that omit it are treated as "unknown, assume a write"). Between requests,
warmth is *predicted* from the last warm time and the configured window; the `ghost` layer's
`status` says which it is reporting.

WINDOW FEASIBILITY. Provider windows vary widely (commonly 15-60 min; some as short as ~5 min).
A haunting organism has a fixed heartbeat. If the heartbeat can't fit inside `window_s`, the
`ghost` layer refuses with DO-NOT-HAUNT (pass `heartbeat_s` to `ghost.warm`) -- the operator
then lengthens the window, shortens/supplements the heartbeat, or does not haunt. This substrate
only reports its window; it never decides policy.

PROVIDER-SPECIFIC CACHE DIRECTIVES stay out of the code. Some providers cache a prefix
automatically (nothing to send); others want an explicit directive on the request. Rather than
name any of them, `HttpPromptCache` takes an optional `request_shaper(payload, prefix) -> payload`
hook: the operator supplies the directive their provider documents, and the ghost logic above is
unchanged. The default shaper sends a plain OpenAI-compatible body and relies on automatic
prefix caching.

Phase-2 tissue: this needs a network and a key, so NOTHING else in Mantle imports it -- the
selftest, the Stage-1 gate, and the spore purity audit all stay pure-stdlib, offline, and
keyless.

    from mantle import ghost, ghost_http
    sub = ghost_http.HttpPromptCache(
        url=os.environ["GHOST_CACHE_URL"],           # e.g. an OpenAI-compatible endpoint
        model=os.environ["GHOST_MODEL"],
        headers={"Authorization": "Bearer " + os.environ["GHOST_KEY"]},
        window_s=1800,                               # the provider's real cache TTL (config)
        min_prefix_tokens=1024,                      # the provider's floor (config)
    )
    ghost.warm("spore.png", substrate=sub, heartbeat_s=600)   # DO-NOT-HAUNT if 600 > window
    ghost.append("spore.png", "user", "...", substrate=sub)
    ghost.status("spore.png", substrate=sub, heartbeat_s=600)
    sub.last_usage                                   # observed cache telemetry, last request

    python -m mantle.ghost_http <spore.png>          # one real warm, reads env config
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

from .ghost import DEFAULT_TTL_S, GhostSubstrate
from .mind.usage import canonical_json_bytes, normalize_usage, sha16


class HttpPromptCache(GhostSubstrate):
    """A write-only `GhostSubstrate` over any OpenAI-compatible chat-completions endpoint.

    Every provider fact is an argument -- nothing is hardcoded:

        url               the chat-completions endpoint (OpenAI-compatible wire shape).
        model             the model id string the endpoint expects (opaque to Mantle).
        headers           auth and any provider directives the operator must send (a dict).
        window_s          the provider's cache TTL in seconds -- config for the DO-NOT-HAUNT
                          gate. 0 = unknown (no gate).
        min_prefix_tokens the provider's minimum cacheable prefix -- config for the
                          TOO-SMALL-TO-HAUNT gate. 0 = unknown (no gate).
        probe_tokens      max_tokens for the warm/extend probe request (keep tiny; some
                          endpoints reject 0, so this defaults to 1).
        timeout           per-request timeout, seconds.
        request_shaper    optional (payload, prefix_bytes) -> payload hook so a provider that
                          needs an explicit cache directive can be configured without naming
                          it in Mantle code. Default: plain body, automatic prefix caching.
        session_id        optional sticky-routing id for providers that support it.
        response_cache    optional response-cache header for deterministic/retry probes.
    """

    name = "http-prompt-cache"
    write_only = True

    def __init__(self, url: str, model: str, *, headers: Optional[Dict[str, str]] = None,
                 window_s: int = 0, min_prefix_tokens: int = 0, probe_tokens: int = 1,
                 timeout: int = 60,
                 request_shaper: Optional[Callable[[Dict[str, Any], bytes], Dict[str, Any]]] = None,
                 session_id: Optional[str] = None,
                 response_cache: bool = False,
                 response_cache_ttl: Optional[int] = None,
                 response_cache_clear: bool = False):
        if session_id is not None and len(session_id) > 256:
            raise ValueError("session_id must be at most 256 characters")
        self.url = url
        self.model = model
        self.headers = dict(headers or {})
        self.headers.setdefault("Content-Type", "application/json")
        if session_id:
            self.headers.setdefault("x-session-id", session_id)
        self.window_s = window_s
        self.min_prefix_tokens = min_prefix_tokens
        self.probe_tokens = probe_tokens
        self.timeout = timeout
        self.request_shaper = request_shaper
        self.session_id = session_id
        self.response_cache = response_cache
        self.response_cache_ttl = response_cache_ttl
        self.response_cache_clear = response_cache_clear
        self._warmed_at: Dict[str, float] = {}     # key -> monotonic time of last warm/extend
        self.last_usage: Optional[Dict[str, Any]] = None   # observed telemetry, last request
        self.last_headers: Optional[Dict[str, str]] = None
        self.last_generation_id: Optional[str] = None
        self.last_request_hash: Optional[str] = None

    # -- the one real request shape (OpenAI-compatible chat completions) ------------------

    def _probe(self, prefix: bytes) -> Dict[str, Any]:
        """Send the prefix-stable body so the provider caches it; read cache-hit telemetry.

        The stable prefix goes in a `system` turn (a byte-exact prefix the provider can cache);
        a tiny placeholder `user` turn after it keeps the request well-formed. The optional
        request_shaper lets an operator attach whatever cache directive their provider wants.
        """
        import urllib.request        # local import: only touched when a real request is made

        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.probe_tokens,
            "messages": [
                {"role": "system", "content": prefix.decode("utf-8")},
                {"role": "user", "content": "warmup"},
            ],
        }
        if self.session_id:
            payload["session_id"] = self.session_id
        if self.request_shaper:
            payload = self.request_shaper(payload, prefix)

        data = canonical_json_bytes(payload)
        headers = dict(self.headers)
        if self.response_cache:
            headers["X-OpenRouter-Cache"] = "true"
            if self.response_cache_ttl is not None:
                headers["X-OpenRouter-Cache-TTL"] = str(int(self.response_cache_ttl))
            if self.response_cache_clear:
                headers["X-OpenRouter-Cache-Clear"] = "true"
        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            resp_headers = dict(resp.headers.items())
            body = json.loads(resp.read().decode("utf-8"))

        self.last_headers = resp_headers
        self.last_request_hash = sha16(data)
        self.last_usage = normalize_usage(
            body, headers=resp_headers, session_id=self.session_id,
            request_hash=self.last_request_hash, stable_prefix_hash=sha16(prefix),
            dynamic_suffix_hash=sha16("warmup"), model=self.model)
        self.last_generation_id = self.last_usage.get("generation_id")
        return self.last_usage

    # -- GhostSubstrate ------------------------------------------------------------------

    def warm(self, key: str, blob: bytes, ttl_s: int = DEFAULT_TTL_S) -> None:
        import time
        self._probe(blob)
        self._warmed_at[key] = time.monotonic()

    def extend(self, key: str, blob: bytes, ttl_s: int = DEFAULT_TTL_S) -> bool:
        import time
        usage = self._probe(blob)
        self._warmed_at[key] = time.monotonic()          # this request re-wrote the prefix too
        return usage["cached_tokens"] > 0                 # OBSERVED warm iff the prefix was hot

    def fetch(self, key: str) -> Optional[bytes]:
        return None                                       # write-only: never readable

    def evict(self, key: str) -> None:
        self._warmed_at.pop(key, None)                    # forget locally; the provider lapses

    def alive(self, key: str) -> bool:
        """PREDICTED warmth only -- the ground truth is the next request's cached_tokens."""
        import time
        t = self._warmed_at.get(key)
        if t is None:
            return False
        if not self.window_s:
            return True
        return (time.monotonic() - t) < self.window_s


def _main(argv) -> int:
    url = os.environ.get("GHOST_CACHE_URL")
    model = os.environ.get("GHOST_MODEL")
    key = os.environ.get("GHOST_KEY")
    if len(argv) < 2 or not (url and model):
        print("usage: python -m mantle.ghost_http <spore.png>\n"
              "  config via env (nothing hardcoded, no vendor):\n"
              "    GHOST_CACHE_URL   an OpenAI-compatible chat-completions endpoint\n"
              "    GHOST_MODEL       the model id string that endpoint expects\n"
              "    GHOST_KEY         bearer token (optional if the endpoint is unauthenticated)\n"
              "    GHOST_WINDOW_S    provider cache TTL in seconds (optional; enables the gate)\n"
              "    GHOST_MIN_PREFIX  minimum cacheable prefix in tokens (optional)\n"
              "    GHOST_HEARTBEAT_S organism heartbeat in seconds (optional; DO-NOT-HAUNT check)\n"
              "  The offline stand-in is `python -m mantle ghost ...` (no key, no network).")
        return 1
    from . import ghost
    headers = {"Authorization": "Bearer " + key} if key else {}
    sub = HttpPromptCache(url=url, model=model, headers=headers,
                          window_s=int(os.environ.get("GHOST_WINDOW_S", "0")),
                          min_prefix_tokens=int(os.environ.get("GHOST_MIN_PREFIX", "0")))
    hb = os.environ.get("GHOST_HEARTBEAT_S")
    result = ghost.warm(argv[1], substrate=sub, heartbeat_s=float(hb) if hb else None)
    print(json.dumps(result, indent=2))
    if sub.last_usage:
        print("observed usage:", sub.last_usage)
        if result.get("status") == "WARM" and sub.last_usage["cached_tokens"] == 0 \
                and sub.min_prefix_tokens:
            print("NOTE: zero cached tokens on first warm is expected (nothing to read yet); "
                  "re-run to observe a cache hit, or the prefix may be below the provider floor.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv))
