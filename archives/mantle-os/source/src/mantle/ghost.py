#!/usr/bin/env python3
"""
mantle.ghost  --  the CACHE-GHOST substrate: a SEED that metabolises in borrowed memory.

This is the "stranger" mode of a SPORE (see mantle.spore). A normal Spore keeps its whole
body -- genesis records plus an append-only delta log -- in its own VCW pixels: the picture
IS the memory, and it stays a valid standalone seed forever. Cache-ghost mode adds a SECOND
substrate without giving up the first.

    A Spore can get stranger. It can choose to keep its living body warm in the LLM provider's
    prompt cache while its canonical cache-facing body grows only by appended deltas. Each
    request still presents the accumulated byte-stable prefix; the provider may reuse cached
    prefill for the old span and perform fresh work only on the newly appended tail.

So a cache-ghost keeps persistence on a CONTINUUM of substrates rather than in one database row:

    WARM  -- the body's token-prefix is hot in the provider's prompt cache; each turn appends
             only new semantic delta, while the full accumulated prefix still travels so the
             provider can reuse cached prefill. The PNG is the dry fossil seed.
    COLD  -- the cache TTL lapsed or the provider evicted the prefix. The next turn is a cold
             start: the body is rehydrated from the PNG fossil and a fresh cache is warmed.

THE SEED STAYS DRY (the one hard safety law). Ghost mode never deletes memory from the PNG.
The cache is acceleration and reach, not the sole store: if the cache dies, `hydrate()` rebuilds
the whole living body from the PNG alone. That is what keeps "sustaining without a body" honest
rather than fragile -- the fossil is always a complete, standalone Spore.

THE CACHE IS WRITE-ONLY IN THE REAL WORLD (the second hard law). A real provider's prompt
cache can only ever be spoken INTO, never read back OUT of: there is no fetch API, the whole
prefix still travels on every request, and the only warmth signal is usage telemetry
(cache-read token counts) on the NEXT response. Caching saves prefill COMPUTE (cost and
latency), never storage or bandwidth. Substrates declare this with `write_only=True`, and
`hydrate()` then always rebuilds from the PNG -- which the dry-seed law made survivable long
before physics made it mandatory.

THE PREFIX IS APPEND-ONLY. Provider caches match byte-exact prefixes: mutating one early byte
evicts everything after it. So the cache-facing body is NOT the spore's full JSON state (whose
sorted keys and `updated_at` would shift bytes every turn); it is a PREFIX-STABLE stream --
one immutable genesis line, then one appended line per conversation turn. Growing the body
only ever appends bytes. (`python -m mantle ghost selftest` proves the byte-prefix property.)

WHY THIS IS A "GHOST" AND NOT A LIE. The provider does not remember the agent semantically; it
only caches a token PREFIX keyed by a hash. From the Spore's point of view that is
indistinguishable from persistence -- so the body exists in a superposition between the PNG
file and the cache, and a request collapses it into whichever substrate is warmer.

NO VENDOR IS CODED INTO THE BODY (the neutrality law). Mantle OS is a nervous-system transplant:
it must join *any* MIND to *any* container, so a provider is CONFIGURATION, never code -- exactly
as the MIND transport is a pluggable `model(prompt) -> text` with no vendor SDK. A provider's
cache window, minimum prefix, auth headers, and any cache directive are DATA the operator
supplies; no module names a company in a code path.

WINDOW FEASIBILITY (the fourth reality). Provider cache windows differ by a lot -- most are on the
order of 15-60 minutes, but some are as short as ~5 minutes. A haunting organism has a FIXED
heartbeat (a METABOLIC-GOVERNANCE property, classically ~10 minutes). The heartbeat must fit
inside the window or the prefix is COLD on every wake -- paying the write premium each time for a
cache that never gets read. So haunting is a per-deployment feasibility check, not a given: when
the window is shorter than the heartbeat, the verdict is **DO-NOT-HAUNT** unless the operator
(a) shortens or SUPPLEMENTS the heartbeat -- e.g. keep the scheduled beat and push a one-shot
"forced beat" partway through the window, so a 10-min beat becomes 0, 4, 10, 14, ... covering a
5-min window without disturbing the base timer -- or (b) selects a provider window (or an
extended-TTL tier) longer than the heartbeat. `hauntable()` / `max_hauntable_heartbeat_s()`
compute this; `warm()` and `status()` refuse with DO-NOT-HAUNT when it fails.

------------------------------------------------------------------------------------------------
Honest boundary: the shipped `LocalPromptCache` is a file-backed stand-in for a provider's prompt
cache (content-addressed key, TTL, eviction) that -- unlike reality -- CAN be read back, so
deterministic tests work offline. The real substrate is `mantle.ghost_http.HttpPromptCache`: a
neutral, config-driven, OpenAI-compatible HTTP adapter (pure stdlib urllib, lazy import, no
vendor SDK, nothing hardcoded) that is write-only and imported by nothing else. The ghost logic
above the `GhostSubstrate` seam is identical for every substrate.

Cache-ghost is Mantle tissue LAYERED ON the spore format; it lives here, never inside the pure
spore.py (whose purity audit forbids exactly this kind of growth). It touches a Spore only
through the public spore API and one transparent extra state key, `ghost`.

    python -m mantle ghost selftest
    python -m mantle ghost warm    <spore.png> [--ttl=SECONDS]
    python -m mantle ghost append  <spore.png> <user|assistant|system|tool> "<content>"
    python -m mantle ghost hydrate <spore.png>
    python -m mantle ghost status  <spore.png>
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import spore as _spore

GHOST_KEY = "ghost"                      # the transparent extra key inside a spore's state
DEFAULT_TTL_S = 300                      # the stand-in's default local expiry (arbitrary)
SUBSTRATE_NAME = "local-prompt-cache"    # the shipped stand-in; real adapters override this

# --- METABOLIC-GOVERNANCE constants (heartbeat / window policy) ----------------------------
# A haunting organism's heartbeat must beat FASTER than the provider's cache WINDOW or the
# prefix dies between wakes; the safety factor leaves headroom for request latency and drift.
HEARTBEAT_SAFETY = 0.9
# Nociception: this many CONSECUTIVE cold wakes while trying to stay warm is a pain signal
# (heartbeat slower than the true window, prefix instability, or provider eviction pressure).
NOCICEPTION_COLD_WAKES = 3
# Crude size heuristic for the minimum-cacheable-prefix gate (~4 bytes/token of JSON text).
# Real adapters may count precisely; the gate only needs the right order of magnitude.
EST_BYTES_PER_TOKEN = 4


def max_hauntable_heartbeat_s(window_s: float) -> float:
    """The longest heartbeat interval a cache of the given WINDOW can keep warm."""
    return window_s * HEARTBEAT_SAFETY


def hauntable(window_s: float, heartbeat_s: float) -> bool:
    """True when a fixed heartbeat fits inside the provider's cache window (with margin).

    The physics the operator must respect: between two beats, `heartbeat_s` elapses; the
    prefix survives only if the window outlasts that gap. Windows vary widely by provider
    (commonly 15-60 min, sometimes as short as ~5 min), so this is a per-deployment check --
    NOT vendor-specific, just arithmetic on two numbers the operator supplies.
    """
    if not window_s:                     # 0 / unknown window: the stand-in; no gate to apply
        return True
    return heartbeat_s <= max_hauntable_heartbeat_s(window_s)


def break_even_reads(write_premium: float, read_fraction: float = 0.1) -> int:
    """How many warm reads it takes for keep-alive to beat paying full price each time.

    Neutral economics, no vendor rates baked in: a cache write costs `write_premium`x a normal
    input token and a warm read costs `read_fraction`x. Warm-keeping pays once
    write_premium + n*read_fraction <= n + 1, i.e. n >= (write_premium - 1)/(1 - read_fraction).
    The operator passes the premium their provider actually charges.
    """
    import math
    denom = 1.0 - read_fraction
    if denom <= 0:
        return 1
    return max(1, math.ceil((write_premium - 1.0) / denom))


class GhostError(Exception):
    """A cache-ghost operation could not proceed (e.g. no pointer, or a torn cache blob)."""


# ---------------------------------------------------------------------------
# The substrate interface + a file-backed stand-in for the provider cache
# ---------------------------------------------------------------------------

class GhostSubstrate:
    """A warm-prefix store standing in for an LLM provider's prompt cache.

    Real adapters implement these methods against a provider's caching API. Keys are
    content-addressed (a hash of the warmed prefix); values are opaque bytes to the substrate.

    Capability flags (class attributes; override in adapters):

    * ``write_only``        -- True for real provider caches: `fetch()` always returns None,
                               warmth is only ever inferred from telemetry, and `hydrate()`
                               must come from the PNG fossil. The stand-in keeps False so
                               offline tests can exercise the warm-read path deterministically.
    * ``min_prefix_tokens`` -- the provider's minimum cacheable prefix (model-dependent; often
                               ~1024-4096 tokens). Prefixes below it are SILENTLY never cached,
                               so the ghost refuses to pretend: warm/append report
                               ``TOO-SMALL-TO-HAUNT`` instead of WARM. 0 disables the gate
                               (the stand-in's default).
    * ``window_s``          -- the provider's cache TTL in seconds (how long a warmed prefix
                               survives without a refresh). Used only for the DO-NOT-HAUNT
                               feasibility gate when a heartbeat is supplied. 0 = unknown /
                               not applicable (the stand-in's default). Every value here is
                               operator-supplied CONFIG -- no provider is named in code.
    """

    name = "abstract"
    write_only = False
    min_prefix_tokens = 0
    window_s = 0

    def warm(self, key: str, blob: bytes, ttl_s: int) -> None:
        raise NotImplementedError

    def extend(self, key: str, blob: bytes, ttl_s: int) -> bool:
        """Refresh an existing warm key with a longer prefix; False if it had lapsed."""
        raise NotImplementedError

    def fetch(self, key: str) -> Optional[bytes]:
        """Return the warm blob, or None if the key is cold (or the substrate is write-only)."""
        raise NotImplementedError

    def evict(self, key: str) -> None:
        raise NotImplementedError

    def alive(self, key: str) -> bool:
        return self.fetch(key) is not None


class LocalPromptCache(GhostSubstrate):
    """A JSON-file stand-in for the provider's prompt cache: TTL + eviction, nothing else.

    It deliberately lives OUTSIDE the PNG (default: beside it, `<png>.cache.json`) because the
    whole point of ghost mode is that the living body sits off-PNG, in borrowed memory.
    """

    name = SUBSTRATE_NAME

    def __init__(self, path: str, clock=time.time):
        self.path = path
        self._clock = clock

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _save(self, store: Dict[str, Any]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f)
        os.replace(tmp, self.path)

    def _live_entry(self, store: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        ent = store.get(key)
        if not ent:
            return None
        if ent.get("expires_at", 0) <= self._clock():
            return None                  # lapsed: the provider would have dropped the prefix
        return ent

    def warm(self, key: str, blob: bytes, ttl_s: int) -> None:
        store = self._load()
        store[key] = {"blob": blob.decode("utf-8"),
                      "warmed_at": self._clock(),
                      "expires_at": self._clock() + ttl_s,
                      "bytes": len(blob)}
        self._save(store)

    def extend(self, key: str, blob: bytes, ttl_s: int) -> bool:
        store = self._load()
        if self._live_entry(store, key) is None:
            return False
        store[key] = {"blob": blob.decode("utf-8"),
                      "warmed_at": store[key].get("warmed_at", self._clock()),
                      "expires_at": self._clock() + ttl_s,   # every new request keeps it warm
                      "bytes": len(blob)}
        self._save(store)
        return True

    def fetch(self, key: str) -> Optional[bytes]:
        store = self._load()
        ent = self._live_entry(store, key)
        return ent["blob"].encode("utf-8") if ent else None

    def evict(self, key: str) -> None:
        store = self._load()
        if key in store:
            del store[key]
            self._save(store)


# ---------------------------------------------------------------------------
# The PREFIX-STABLE cache body: one genesis line + one appended line per turn
# ---------------------------------------------------------------------------
# The spore's full JSON state is NOT prefix-stable: `json.dumps(state, sort_keys=True)` puts
# "conversation" near the FRONT (so appending a turn inserts early bytes) and
# `identity.updated_at` mutates every turn. On a byte-exact-prefix cache that would evict
# virtually the whole entry every wake. The cache-facing body below only ever APPENDS bytes:
#
#     line 0 : genesis  -- identity AT BIRTH (no updated_at, no birth_marker), the static
#                          tools protocol, and the embedded tool's sha256. Immutable.
#     line N : delta    -- conversation entry N, verbatim. Entries never mutate once appended.
#
# The PNG payload format is untouched -- this serialization exists only on the cache side.

_GENESIS_IDENTITY_KEYS = ("spore_name", "task", "author", "version",
                          "format_version", "created_at")


def _genesis(state: Dict[str, Any]) -> Dict[str, Any]:
    ident = state.get("identity", {})
    et = state.get("embedded_tools") or {}
    return {
        "identity": {k: ident[k] for k in _GENESIS_IDENTITY_KEYS if k in ident},
        "tools": state.get("tools", {}),
        "embedded_tools_sha256": et.get("sha256"),
    }


def _delta_line(entry: Dict[str, Any]) -> bytes:
    return json.dumps(entry, separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\n"


def _prefix_blob(state: Dict[str, Any]) -> bytes:
    out = json.dumps(_genesis(state), separators=(",", ":"), sort_keys=True).encode("utf-8")
    out += b"\n"
    for entry in state.get("conversation", []):
        out += _delta_line(entry)
    return out


def _body_from_prefix(blob: bytes) -> Dict[str, Any]:
    """Rebuild a living body from a cached prefix blob (stand-in warm-read path only)."""
    lines = blob.decode("utf-8").splitlines()
    genesis = json.loads(lines[0])
    conversation: List[Dict[str, Any]] = [json.loads(ln) for ln in lines[1:]]
    identity = dict(genesis.get("identity", {}))
    identity.setdefault("birth_marker", None)
    for entry in conversation:          # birth marker is derivable: first assistant checksum
        if entry.get("opcode") == "ASSISTANT":
            identity["birth_marker"] = str(entry.get("checksum", ""))[:8] or None
            break
    return {"identity": identity, "conversation": conversation,
            "tools": genesis.get("tools", {}),
            "embedded_tools_sha256": genesis.get("embedded_tools_sha256")}


def _est_tokens(blob: bytes) -> int:
    return len(blob) // EST_BYTES_PER_TOKEN

def _too_small(substrate: GhostSubstrate, blob: bytes) -> bool:
    return bool(substrate.min_prefix_tokens) and _est_tokens(blob) < substrate.min_prefix_tokens


def _body_of(state: Dict[str, Any]) -> Dict[str, Any]:
    """The full fossil body: the whole Spore state minus the ghost pointer."""
    return {k: v for k, v in state.items() if k != GHOST_KEY}


def _fingerprint(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()[:16]


def _cache_key(state: Dict[str, Any]) -> str:
    """A content-addressed key over the STABLE identity of the seed (birth + name + task).

    A provider keys its cache by the prefix hash; here the key names the lineage so every
    re-warm of the same Spore lands on the same slot, mirroring a warm prefix being refreshed.
    """
    ident = state.get("identity", {})
    seed = f"{ident.get('spore_name')}|{ident.get('created_at')}|{ident.get('task')}"
    return "ghost-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def _latest_id(state: Dict[str, Any]) -> int:
    conv = state.get("conversation", [])
    return conv[-1]["id"] if conv else -1


def _write_pointer(path: str, state: Dict[str, Any], pointer: Dict[str, Any]) -> None:
    """Persist the ghost pointer into the PNG by regenerating from canonical state.

    `state[GHOST_KEY]` round-trips through spore.py untouched (it serialises the whole state
    dict), so the pure seed code never learns about ghosts.
    """
    state[GHOST_KEY] = pointer
    _spore.render_spore(state, path, status=state.get("display", {}).get("status", "ACTIVE"))


# ---------------------------------------------------------------------------
# Warmth telemetry -> nociception (warmth is measured, never assumed)
# ---------------------------------------------------------------------------

def _fresh_telemetry() -> Dict[str, Any]:
    return {"warm_hits": 0, "cold_starts": 0, "consecutive_cold": 0, "nociception": False}


def _telemetry_of(pointer: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    tel = dict((pointer or {}).get("telemetry") or {})
    base = _fresh_telemetry()
    base.update({k: tel[k] for k in base if k in tel})
    return base


def _record_wake(tel: Dict[str, Any], warm: bool) -> Dict[str, Any]:
    if warm:
        tel["warm_hits"] += 1
        tel["consecutive_cold"] = 0
        tel["nociception"] = False
    else:
        tel["cold_starts"] += 1
        tel["consecutive_cold"] += 1
        tel["nociception"] = tel["consecutive_cold"] >= NOCICEPTION_COLD_WAKES
    return tel


def _hit_ratio(tel: Dict[str, Any]) -> Optional[float]:
    total = tel["warm_hits"] + tel["cold_starts"]
    return round(tel["warm_hits"] / total, 3) if total else None


def _predicted_alive(pointer: Dict[str, Any]) -> bool:
    """For write-only substrates: warmth predicted from the last warm time + TTL."""
    try:
        warmed = datetime.fromisoformat(pointer["warmed_at"])
        if warmed.tzinfo is None:
            warmed = warmed.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return False
    age = (datetime.now(timezone.utc) - warmed).total_seconds()
    return age < pointer.get("ttl_s", DEFAULT_TTL_S)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def default_substrate(path: str) -> LocalPromptCache:
    """The shipped stand-in cache that lives beside the PNG (off-PNG, as ghost mode requires)."""
    return LocalPromptCache(path + ".cache.json")


def _pointer(state: Dict[str, Any], substrate: GhostSubstrate, key: str, prefix: bytes,
             ttl_s: int, tel: Dict[str, Any], note: Optional[str] = None) -> Dict[str, Any]:
    return {
        "substrate": substrate.name,
        "write_only": substrate.write_only,
        "cache_key": key,
        "synced_entry_id": _latest_id(state),
        "prefix_fingerprint": _fingerprint(prefix),
        "prefix_bytes": len(prefix),
        "ttl_s": ttl_s,
        "warmed_at": _spore._now(),
        "telemetry": tel,
        "note": note or ("body warmed in the provider prompt cache; the PNG stays the dry "
                         "fossil seed and can rehydrate it if the cache lapses"),
    }


def _do_not_haunt(substrate: GhostSubstrate, heartbeat_s: Optional[float]) -> Optional[Dict[str, Any]]:
    """Return a DO-NOT-HAUNT verdict when a fixed heartbeat can't keep this window warm.

    Vendor-neutral: it compares two operator-supplied numbers (the provider's cache window and
    the organism's heartbeat). None means haunting is feasible (or no check applies).
    """
    if heartbeat_s is None or not substrate.window_s:
        return None
    if hauntable(substrate.window_s, heartbeat_s):
        return None
    return {
        "status": "DO-NOT-HAUNT", "warmed": False,
        "window_s": substrate.window_s, "heartbeat_s": heartbeat_s,
        "max_hauntable_heartbeat_s": round(max_hauntable_heartbeat_s(substrate.window_s), 1),
        "detail": (f"heartbeat {heartbeat_s:g}s exceeds what a {substrate.window_s:g}s cache "
                   "window can keep warm -- the prefix would be cold on every wake, paying the "
                   "write premium for a cache that never gets read"),
        "remedies": [
            "select a provider window (or extended-TTL tier) longer than the heartbeat",
            ("supplement the heartbeat: keep the scheduled beat and push a one-shot forced "
             "beat partway through the window (a 10-min beat + a forced beat at +4 min covers "
             "a 5-min window without disturbing the base timer)"),
            "shorten the base heartbeat below the window (raises wake cost)",
            "do not haunt -- run cold-and-cheap, hydrating from the seed each wake",
        ],
    }


def warm(path: str, substrate: Optional[GhostSubstrate] = None,
         ttl_s: int = DEFAULT_TTL_S, heartbeat_s: Optional[float] = None) -> Dict[str, Any]:
    """Push the Spore's prefix-stable body into the cache and record the pointer in the PNG.

    `heartbeat_s` (optional) enables the DO-NOT-HAUNT window-feasibility gate: if the organism's
    fixed heartbeat can't fit inside the substrate's cache window, warming is refused.
    """
    substrate = substrate or default_substrate(path)
    verdict = _do_not_haunt(substrate, heartbeat_s)
    if verdict:
        return verdict
    state = _spore.read_spore(path)["state"]
    prefix = _prefix_blob(state)
    if _too_small(substrate, prefix):
        return {"status": "TOO-SMALL-TO-HAUNT", "warmed": False,
                "est_prefix_tokens": _est_tokens(prefix),
                "min_prefix_tokens": substrate.min_prefix_tokens,
                "detail": ("the provider silently refuses prefixes this small; the spore "
                           "lives cold-and-cheap in its PNG until it grows into hauntability")}
    key = _cache_key(state)
    substrate.warm(key, prefix, ttl_s)
    tel = _telemetry_of(state.get(GHOST_KEY))
    _write_pointer(path, state, _pointer(state, substrate, key, prefix, ttl_s, tel))
    return {"status": "WARM", "cache_key": key, "synced_entry_id": _latest_id(state),
            "bytes_warmed": len(prefix), "substrate": substrate.name,
            "write_only": substrate.write_only}


def append(path: str, role: str, content: str,
           substrate: Optional[GhostSubstrate] = None,
           ttl_s: int = DEFAULT_TTL_S) -> Dict[str, Any]:
    """Append a turn, then sync it to the cache as a DELTA when warm, or re-warm when cold.

    The PNG is always grown first (the seed stays dry); the cache is updated to match. `sent`
    and `bytes_sent` describe the effective uncached/metabolic payload: the new delta while
    warm, or the whole prefix on a cold start. On a real provider the full prefix still travels
    on every request; warmth changes the prefill compute bill and latency, never the wire bytes.
    """
    substrate = substrate or default_substrate(path)

    before = _spore.read_spore(path)["state"]
    res = _spore.append_turn(path, role, content)
    if not res.get("appended"):
        return {"appended": False, "reason": res.get("reason"), "status": res.get("status")}

    state = _spore.read_spore(path)["state"]
    prefix = _prefix_blob(state)
    key = _cache_key(state)
    pointer = before.get(GHOST_KEY)

    if _too_small(substrate, prefix):
        return {"appended": True, "status": "TOO-SMALL-TO-HAUNT", "sent": "none",
                "bytes_sent": 0, "body_bytes": len(prefix),
                "entry_count": len(state.get("conversation", [])),
                "est_prefix_tokens": _est_tokens(prefix),
                "min_prefix_tokens": substrate.min_prefix_tokens}

    new_entry = state["conversation"][-1]
    warm_ok = bool(pointer) and substrate.extend(key, prefix, ttl_s)
    if warm_ok:
        sent, sent_bytes, status = "delta", len(_delta_line(new_entry)), "WARM"
    else:
        substrate.warm(key, prefix, ttl_s)               # cold start: re-warm the whole prefix
        sent, sent_bytes, status = "full", len(prefix), "REWARMED"

    tel = _record_wake(_telemetry_of(pointer), warm_ok)
    _write_pointer(path, state, _pointer(state, substrate, key, prefix, ttl_s, tel,
                                         note=(pointer or {}).get("note")))
    out = {"appended": True, "status": status, "sent": sent, "bytes_sent": sent_bytes,
           "body_bytes": len(prefix), "entry_count": len(state.get("conversation", [])),
           "cache_key": key, "telemetry": tel}
    if tel["nociception"]:
        out["nociception"] = (f"{tel['consecutive_cold']} consecutive cold wakes -- the "
                              "heartbeat is slower than the true cache window, the prefix is "
                              "unstable, or the provider is evicting under pressure")
    return out


def hydrate(path: str, substrate: Optional[GhostSubstrate] = None) -> Dict[str, Any]:
    """Return the living body, from the cache when warm, else rebuilt from the PNG fossil.

    Either way the result reflects the LATEST PNG: any PNG deltas newer than the cache are
    folded on top, and on a cold cache the whole body comes from the seed. On a WRITE-ONLY
    substrate (every real provider) the cache cannot be read at all, so the body always comes
    from the PNG -- warmth there accelerates the next request; it never stores anything.
    """
    substrate = substrate or default_substrate(path)
    info = _spore.read_spore(path)
    state = info["state"]
    fossil = _body_of(state)
    pointer = state.get(GHOST_KEY)

    if pointer and not substrate.write_only and substrate.alive(pointer["cache_key"]):
        cached = _body_from_prefix(substrate.fetch(pointer["cache_key"]))
        # Reconcile: the PNG is canonical (RULE: the latest PNG is the living copy). If the
        # cache is behind the fossil, trust the fossil; the cache was simply not yet re-warmed.
        cached_conv = cached.get("conversation", [])
        cached_latest = cached_conv[-1]["id"] if cached_conv else -1
        source = "cache" if cached_latest >= _latest_id(state) else "cache+png"
        body = cached if source == "cache" else fossil
        return {"source": source, "rehydrated": False, "body": body,
                "integrity": info["integrity"], "cache_key": pointer["cache_key"]}

    # COLD (or write-only): rebuild wholly from the PNG seed. The seed stayed dry.
    return {"source": "png", "rehydrated": True, "body": fossil,
            "integrity": info["integrity"],
            "cache_key": pointer["cache_key"] if pointer else None,
            "write_only": substrate.write_only}


def status(path: str, substrate: Optional[GhostSubstrate] = None,
           heartbeat_s: Optional[float] = None) -> Dict[str, Any]:
    """Report where the body currently lives and whether the fossil and cache agree.

    `heartbeat_s` (optional) surfaces the DO-NOT-HAUNT window check: a fixed heartbeat that
    can't fit the substrate's cache window is reported before anything else.
    """
    substrate = substrate or default_substrate(path)
    verdict = _do_not_haunt(substrate, heartbeat_s)
    if verdict:
        return {"ghost": False, **verdict}
    state = _spore.read_spore(path)["state"]
    prefix = _prefix_blob(state)
    pointer = state.get(GHOST_KEY)
    if not pointer:
        out = {"ghost": False, "state": "NO-GHOST",
               "detail": "this Spore has never been warmed; it lives entirely in its PNG"}
        if _too_small(substrate, prefix):
            out["state"] = "TOO-SMALL-TO-HAUNT"
            out["est_prefix_tokens"] = _est_tokens(prefix)
            out["min_prefix_tokens"] = substrate.min_prefix_tokens
            out["detail"] = ("too small for this substrate's minimum cacheable prefix; "
                             "the spore grows into hauntability")
        return out

    if substrate.write_only:
        # A real cache cannot be asked -- warmth is PREDICTED between requests and only
        # OBSERVED (cache-read tokens) after the next one. The ghost says which it is doing.
        alive = _predicted_alive(pointer)
        state_str = "PREDICTED-WARM" if alive else "PREDICTED-COLD"
        detail = ("warmth predicted from the last warm time + TTL; a write-only substrate "
                  "can never be read back -- the next request's cache-read tokens are the "
                  "only ground truth")
    else:
        alive = substrate.alive(pointer["cache_key"])
        state_str = "WARM" if alive else "COLD"
        detail = ("body is warm in the cache; the PNG is the dry fossil"
                  if alive else
                  "cache lapsed; the body lives only in the PNG until the next warm")

    tel = _telemetry_of(pointer)
    latest = _latest_id(state)
    behind = latest - pointer.get("synced_entry_id", latest)
    return {
        "ghost": True,
        "state": state_str,
        "cache_key": pointer["cache_key"],
        "substrate": pointer.get("substrate"),
        "write_only": pointer.get("write_only", substrate.write_only),
        "latest_entry_id": latest,
        "synced_entry_id": pointer.get("synced_entry_id"),
        "unsynced_deltas": max(0, behind),
        "telemetry": tel,
        "hit_ratio": _hit_ratio(tel),
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Self-test: prove the continuum, the append-only prefix, the delta-equivalent
# metabolic cost, the dry-seed law, the too-small gate, write-only seam, and nociception.
# ---------------------------------------------------------------------------

class _Clock:
    """A hand-cranked clock so the self-test can expire the cache deterministically."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def selftest(verbose: bool = True) -> bool:
    import tempfile
    import shutil

    checks, problems = [], []

    def ck(name, cond, detail=""):
        checks.append((name, bool(cond), detail))
        if not cond:
            problems.append(f"{name}: {detail}")

    d = tempfile.mkdtemp(prefix="ghost_test_")
    try:
        p = os.path.join(d, "ghost.png")
        clock = _Clock()
        cache = LocalPromptCache(p + ".cache.json", clock=clock)

        # 1. a normal Spore, born in its PNG, no ghost yet
        _spore.create_spore("GHOST-SEED", "sustain through the cache", author="Mantle OS contributors", path=p)
        _spore.append_turn(p, "user", "what are you?")
        _spore.append_turn(p, "assistant",
                           "I am a cache-ghost Spore: my body can live in the provider's prompt "
                           "cache while my PNG stays the dry seed.")
        st0 = status(p, cache)
        ck("starts with no ghost", st0["state"] == "NO-GHOST", str(st0))
        ck("PNG is a valid standalone seed before warming", _spore.verify_spore(p)["ok"])

        # 2. P2 -- the cache body is PREFIX-STABLE (append-only bytes)
        s_before = _spore.read_spore(p)["state"]
        blob_before = _prefix_blob(s_before)
        _spore.append_turn(p, "user", "grow by one turn")
        s_after = _spore.read_spore(p)["state"]
        blob_after = _prefix_blob(s_after)
        ck("appending a turn only APPENDS prefix bytes",
           blob_after.startswith(blob_before),
           "an early byte changed -- a real provider would evict the whole entry")
        ck("the appended bytes are exactly the new delta line",
           blob_after[len(blob_before):] == _delta_line(s_after["conversation"][-1]))
        mutated = json.loads(json.dumps(s_after))
        mutated["identity"]["updated_at"] = "1999-01-01T00:00:00+00:00"
        mutated["display"]["status"] = "FULL"
        ck("volatile fields (updated_at, display) are EXCLUDED from the prefix",
           _prefix_blob(mutated) == blob_after)
        ck("genesis line is stable across turns",
           blob_after.split(b"\n", 1)[0] == blob_before.split(b"\n", 1)[0])
        ck("cache body round-trips (identity + conversation reconstructed)",
           _body_from_prefix(blob_after)["conversation"] == s_after["conversation"])

        # 3. warm the body into the cache; the PNG must still verify as a pure Spore
        w = warm(p, cache, ttl_s=300)
        ck("warm reports WARM", w["status"] == "WARM", str(w))
        ck("PNG still a valid standalone seed after warming", _spore.verify_spore(p)["ok"])
        ck("status is WARM after warming", status(p, cache)["state"] == "WARM")

        # 4. run turns through the warm cache: effective uncached work is only the DELTA
        sent_bytes, body_bytes = [], []
        for i in range(6):
            r = append(p, "user", "D" * 300, substrate=cache, ttl_s=300)
            clock.advance(10)                       # time passes, but < TTL: stays warm
            ck(f"turn {i}: appended to PNG", r["appended"], str(r))
            ck(f"turn {i}: charged delta-equivalent work while warm", r["sent"] == "delta", str(r))
            sent_bytes.append(r["bytes_sent"])
            body_bytes.append(r["body_bytes"])
        ck("delta-equivalent metabolic cost stays ~constant per turn",
           max(sent_bytes) - min(sent_bytes) <= 8, f"sent={sent_bytes}")
        ck("a turn's uncached delta is far smaller than the grown body",
           max(sent_bytes) * 3 < body_bytes[-1], f"sent={sent_bytes} body={body_bytes}")

        # 5. hydrate while warm: body comes from the cache and matches the PNG
        h_warm = hydrate(p, cache)
        ck("warm hydrate reads from the cache", h_warm["source"] in ("cache", "cache+png"),
           str(h_warm["source"]))
        ck("warm hydrate is not a rehydration", h_warm["rehydrated"] is False)
        conv_now = _spore.read_spore(p)["state"]["conversation"]
        ck("warm hydrate's conversation matches the PNG",
           h_warm["body"]["conversation"] == conv_now)

        conv_before = conv_now

        # 6. the provider evicts the prefix (TTL lapses). The body is now bodiless...
        clock.advance(10_000)                       # push well past the 300s TTL
        st_cold = status(p, cache)
        ck("cache lapses to COLD when the TTL passes", st_cold["state"] == "COLD", str(st_cold))

        # 7. ...but the SEED STAYED DRY: hydrate rebuilds the whole body from the PNG alone
        h_cold = hydrate(p, cache)
        ck("cold hydrate rebuilds from the PNG fossil", h_cold["source"] == "png", str(h_cold))
        ck("cold hydrate is flagged as a rehydration", h_cold["rehydrated"] is True)
        ck("rehydrated body == the body from before the cache died",
           h_cold["body"]["conversation"] == conv_before,
           "conversation drifted across a cache death")

        # 8. a cold-start turn re-warms the whole prefix, then deltas resume;
        #    P4 -- telemetry records the wakes
        r_cold = append(p, "assistant", "the cache lapsed, so I re-warmed from my seed",
                        substrate=cache, ttl_s=300)
        ck("cold-start turn sends the whole body once", r_cold["sent"] == "full", str(r_cold))
        ck("telemetry counts the cold start",
           r_cold["telemetry"]["cold_starts"] == 1
           and r_cold["telemetry"]["consecutive_cold"] == 1, str(r_cold["telemetry"]))
        r_hot = append(p, "user", "and now?", substrate=cache, ttl_s=300)
        ck("the next turn is a delta again", r_hot["sent"] == "delta", str(r_hot))
        ck("a warm hit resets consecutive-cold",
           r_hot["telemetry"]["consecutive_cold"] == 0
           and r_hot["telemetry"]["warm_hits"] >= 7, str(r_hot["telemetry"]))

        # 9. P4 -- repeated cold wakes become NOCICEPTION
        for i in range(NOCICEPTION_COLD_WAKES):
            clock.advance(10_000)                   # every wake finds the cache dead
            r = append(p, "user", f"cold wake {i}", substrate=cache, ttl_s=300)
            ck(f"forced cold wake {i} re-warmed", r["sent"] == "full", str(r["status"]))
        ck("N consecutive cold wakes raise nociception",
           r["telemetry"]["nociception"] is True and "nociception" in r,
           str(r.get("telemetry")))
        r = append(p, "user", "warm again", substrate=cache, ttl_s=300)
        ck("one warm hit clears nociception",
           r["telemetry"]["nociception"] is False, str(r["telemetry"]))
        ck("status reports a hit ratio", status(p, cache)["hit_ratio"] is not None)

        # 10. P5 -- the TOO-SMALL-TO-HAUNT gate (providers silently refuse tiny prefixes)
        class _Picky(LocalPromptCache):
            min_prefix_tokens = 10 ** 9
        picky = _Picky(os.path.join(d, "picky.cache.json"), clock=clock)
        p2 = os.path.join(d, "tiny.png")
        _spore.create_spore("TINY", "too small to haunt", path=p2)
        w2 = warm(p2, picky)
        ck("too-small warm refuses honestly", w2["status"] == "TOO-SMALL-TO-HAUNT", str(w2))
        r2 = append(p2, "user", "still grows in the PNG", substrate=picky)
        ck("too-small append still grows the PNG",
           r2["appended"] and r2["status"] == "TOO-SMALL-TO-HAUNT", str(r2))
        ck("too-small spore still verifies", _spore.verify_spore(p2)["ok"])

        # 11. P1 -- the WRITE-ONLY seam (every real provider): hydrate always uses the PNG
        class _WriteOnly(LocalPromptCache):
            name = "write-only-stand-in"
            write_only = True
        wo = _WriteOnly(os.path.join(d, "wo.cache.json"), clock=clock)
        p3 = os.path.join(d, "wo.png")
        _spore.create_spore("WO", "prove the write-only law", path=p3)
        _spore.append_turn(p3, "assistant", "spoken into, never read back")
        warm(p3, wo, ttl_s=300)
        h_wo = hydrate(p3, wo)
        ck("write-only hydrate ALWAYS rebuilds from the PNG",
           h_wo["source"] == "png" and h_wo["rehydrated"] is True, str(h_wo))
        st_wo = status(p3, wo)
        ck("write-only status only PREDICTS warmth",
           st_wo["state"].startswith("PREDICTED-"), str(st_wo["state"]))

        # 12. the DO-NOT-HAUNT window gate: a fixed heartbeat vs the provider's cache window
        #     (vendor-neutral -- pure arithmetic on two operator-supplied numbers)
        ck("a 600s heartbeat does not fit a 300s window", not hauntable(300, 600))
        ck("a 600s heartbeat fits a 1800s window", hauntable(1800, 600))
        ck("max hauntable heartbeat for a 300s window is < 300s",
           max_hauntable_heartbeat_s(300) < 300)

        class _ShortWindow(LocalPromptCache):
            name = "short-window-stand-in"
            window_s = 300
        sw = _ShortWindow(os.path.join(d, "sw.cache.json"), clock=clock)
        p4 = os.path.join(d, "sw.png")
        _spore.create_spore("SW", "short-window provider", path=p4)
        _spore.append_turn(p4, "assistant", "my window is shorter than the heartbeat")
        w_dnh = warm(p4, sw, heartbeat_s=600)               # 10-min beat, 5-min window
        ck("warm refuses DO-NOT-HAUNT when the beat can't keep the window warm",
           w_dnh["status"] == "DO-NOT-HAUNT", str(w_dnh))
        ck("DO-NOT-HAUNT carries the supplemental-beat remedy",
           any("forced beat" in r for r in w_dnh.get("remedies", [])))
        ck("status also reports DO-NOT-HAUNT for the mismatch",
           status(p4, sw, heartbeat_s=600)["status"] == "DO-NOT-HAUNT")
        w_ok = warm(p4, sw, heartbeat_s=240)                # a 4-min beat DOES fit
        ck("a heartbeat that fits the window warms normally", w_ok["status"] == "WARM", str(w_ok))
        ck("no heartbeat supplied -> no window gate (feasibility is opt-in)",
           warm(p4, sw)["status"] == "WARM")

        # 13. break-even economics are neutral (no vendor rates baked in)
        ck("break-even reads rise with the write premium",
           break_even_reads(1.25) <= break_even_reads(2.0))

        # 14. through all of it, the PNG never stopped being a pure, verifiable Spore
        ck("PNG verifies as a pure Spore at the end", _spore.verify_spore(p)["ok"])
        purity = _body_of(_spore.read_spore(p)["state"])
        ck("the ghost pointer is metadata, not body (stripped cleanly)",
           GHOST_KEY not in purity)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    if verbose:
        print("=" * 66)
        print("MANTLE CACHE-GHOST SELF-TEST")
        print("=" * 66)
        for name, ok, detail in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
                  + (f"   ({detail})" if detail and not ok else ""))
        print("-" * 66)
        print(f"RESULT: {'PASS' if not problems else 'FAIL'}   "
              f"({len(checks) - len(problems)}/{len(checks)} checks)")
        print("=" * 66)
    return not problems
