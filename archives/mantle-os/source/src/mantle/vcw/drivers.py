#!/usr/bin/env python3
"""
mantle.vcw.drivers  --  concrete payload protocols (Mantle OS)

Five drivers, registered on import:

  log-json          append-only list of immutable, hashed entries
  keyvalue          a small mutable map (mutated hot, snapshotted on flush)
  calendar-spatial  data stored AS COLORS AT COORDINATES -- a real RGBA canvas
  exec              an executable REFLEX LAYER: organism-grown code the Body runs with no
                    MIND, behind hash + capability + provenance/trust + sandbox gates
  grimoire-v0.9 / grimoire-v0.10
                    explicit-edition semantic pixel runs over RGBA lanes

These prove the boot sector -- not hard-coded logic -- decides how a layer behaves.
The RGBA lanes are substrate hardware. A driver/profile is the software contract that
decides how a layer frames the lanes and what they encode.
"""
from __future__ import annotations

import ast
import builtins
import json
import os
import signal
import subprocess
import sys
from datetime import date
from typing import Any, Dict, List, Tuple

from .png import SIDE, CHANNELS, LAYER_BYTES
from .bands import Driver, register, code_hash
from .entry import make_entry, visible
from .grimoire import decode_statement
from .grimoire_editions import decode_statement as decode_profiled

__all__ = [
    "make_entry", "LogJsonDriver", "KeyValueDriver", "CalendarSpatialDriver", "ExecDriver",
    "GrimoireV09Driver", "GrimoireV010Driver", "GrimoireV010EntryDriver",
    "CapabilityError", "IntegrityError", "TrustError", "SandboxError", "ProvenanceError",
    "ResourceLimitError", "ProtocolError",
    "validate_skill_code", "validate_calcify_payload", "provenance_is_trusted", "trial",
    "validate_public_grant", "register_runner", "get_runner",
]


# ============================================================================
# log-json : append-only immutable entries
# ============================================================================
@register
class LogJsonDriver(Driver):
    name = "log-json"
    entry_stream = True     # entry-addressed, hashed records (the cube's base contract)

    def empty(self, params):
        return []

    def read(self, content, params, reveal_private=False):
        return visible(content)

    def retrieve(self, content, params, address):
        vis = self.read(content, params)
        i = int(address)
        return vis[i] if 0 <= i < len(vis) else None

    def append(self, content, params, value):
        e = value if isinstance(value, dict) and "hash" in value else make_entry(value)
        e = dict(e)
        if e.get("id") is None:                    # the cube assigns band-unique ids;
            e["id"] = len(content)                 # standalone driver use falls back to position
        content.append(e)
        return content


# ============================================================================
# keyvalue : a small mutable map
# ============================================================================
@register
class KeyValueDriver(Driver):
    name = "keyvalue"

    def empty(self, params):
        return {}

    def read(self, content, params, reveal_private=False):
        return dict(content)

    def retrieve(self, content, params, address):
        return content.get(str(address))

    def append(self, content, params, value):
        k, v = value
        content[str(k)] = v
        return content


# ============================================================================
# calendar-spatial : data stored as colors at coordinates (a real RGBA canvas)
# ============================================================================
@register
class CalendarSpatialDriver(Driver):
    """params = {"epoch": "2026-01-01", "palette": {"ff0000": "urgent", ...}}
    A date maps to a cell (x = weekday 0..6, y = week index since epoch); the cell's RGBA
    stores the appointment color; alpha 0 means 'free'."""
    name = "calendar-spatial"

    def empty(self, params):
        return bytearray(LAYER_BYTES)

    def coord_for_date(self, params, iso: str) -> Tuple[int, int]:
        epoch = date.fromisoformat(params["epoch"])
        d = date.fromisoformat(iso)
        days = d.toordinal() - epoch.toordinal() + epoch.weekday()
        return d.weekday(), days // 7

    def _palette_inverse(self, params) -> Dict[str, str]:
        return {v: k for k, v in params.get("palette", {}).items()}

    def _offset(self, x: int, y: int) -> int:
        return (y * SIDE + x) * CHANNELS

    def read(self, content, params, reveal_private=False):
        out = []
        palette = params.get("palette", {})
        for i in range(0, LAYER_BYTES, CHANNELS):
            r, g, b, a = content[i:i + CHANNELS]
            if a:
                hexc = "%02x%02x%02x" % (r, g, b)
                pix = i // CHANNELS
                out.append({"x": pix % SIDE, "y": pix // SIDE,
                            "color": hexc, "meaning": palette.get(hexc, "unknown")})
        return out

    def retrieve(self, content, params, address):
        x, y = address
        off = self._offset(int(x), int(y))
        r, g, b, a = content[off:off + CHANNELS]
        if not a:
            return "free"
        return params.get("palette", {}).get("%02x%02x%02x" % (r, g, b), "unknown")

    def append(self, content, params, value):
        iso, meaning = value
        x, y = self.coord_for_date(params, iso)
        hexc = self._palette_inverse(params).get(meaning)
        if hexc is None:
            raise ValueError("meaning %r not in palette" % meaning)
        off = self._offset(x, y)
        content[off:off + CHANNELS] = bytes.fromhex(hexc) + b"\xff"
        return content

    def get_date(self, content, params, iso: str):
        return self.retrieve(content, params, self.coord_for_date(params, iso))


# ============================================================================
# grimoire-v0.9 : semantic RGBA pixel runs (atom/role/evidence/force)
# ============================================================================
@register
class GrimoireV09Driver(Driver):
    """content = [decoded statement dicts]

    The payload passed to append may be raw bytes, hex text, or a dict with raw/hex,
    frame_id, and optional raw-run fingerprint. Adoption is never read from the payload:
    only the boot sector's params may mark the decoded profile as data, quote,
    quarantine, or adopted.
    """
    name = "grimoire-v0.9"

    def empty(self, params):
        return []

    def read(self, content, params, reveal_private=False):
        return list(content)

    def retrieve(self, content, params, address):
        try:
            i = int(address)
        except (TypeError, ValueError):
            return None
        return content[i] if 0 <= i < len(content) else None

    def append(self, content, params, value):
        params = params or {}
        if isinstance(value, dict):
            frame_id = value.get("frame_id", "frame-%d" % len(content))
            fingerprint = value.get("fingerprint")
            raw = value
        else:
            frame_id = "frame-%d" % len(content)
            fingerprint = None
            raw = value
        decoded = decode_statement(
            raw,
            frame_id=frame_id,
            fingerprint=fingerprint,
            claim_tamper_evidence=bool(params.get("claim_tamper_evidence", False)),
            allow_parity_absent=bool(params.get("allow_parity_absent", False)),
            adoption_policy=str(params.get("adoption_policy", "data")),
        )
        content.append(decoded)
        return content


@register
class GrimoireV010Driver(GrimoireV09Driver):
    """Explicit v0.10 carrier driver; no implicit fallback from its profile."""
    name = "grimoire-v0.10"

    def _carrier_payload(self, value, content):
        """Extract (frame_id, fingerprint, raw) from a raw/hex/dict carrier."""
        if isinstance(value, dict):
            frame_id = value.get("frame_id", "frame-%d" % len(content))
            fingerprint = value.get("fingerprint")
            raw = value.get("raw", value.get("hex", value))
        else:
            frame_id = "frame-%d" % len(content)
            fingerprint = None
            raw = value
        return frame_id, fingerprint, raw

    def decode_carrier(self, content, params, value):
        """Decode one raw v0.10 carrier run (no profile-name check; always the base
        edition profile). Shared by the carrier path of both v0.10 drivers."""
        frame_id, fingerprint, raw = self._carrier_payload(value, content)
        return decode_profiled(
            raw,
            profile="grimoire-v0.10",
            frame_id=frame_id,
            fingerprint=fingerprint,
            claim_tamper_evidence=bool(params.get("claim_tamper_evidence", False)),
            allow_parity_absent=bool(params.get("allow_parity_absent", False)),
            adoption_policy=str(params.get("adoption_policy", "data")),
            container_evidence=params.get("container_evidence"),
            container_force=params.get("container_force"),
            container_frame_id=params.get("container_frame_id"),
        )

    def append(self, content, params, value):
        params = params or {}
        if params.get("profile") != self.name:
            raise ValueError("v0.10 carrier params require profile %r" % self.name)
        if isinstance(value, dict):
            profile = value.get("profile")
            if profile != self.name:
                raise ValueError("v0.10 payload requires profile %r" % self.name)
        decoded = self.decode_carrier(content, params, value)
        content.append(decoded)
        return content


@register
class GrimoireV010EntryDriver(GrimoireV010Driver):
    """The one-step semantic memory driver: append ENCODES (entry -> v0.10 statement).

    `entry_stream = True` declares that this band's content is a list of entry-shaped
    records, so the cube gives it the same guarantees as `log-json`: band-unique ids,
    multi-layer reads, weight overlay, indexes, immune marks, and metabolism.

    append() has two paths:
      * entry-shaped value (a dict with `hash`) -> encoded through the semantic
        encoder into one record holding the structural statement (raw) and the
        content QUOTE frame (content_raw), both hex, both hash-covered;
      * raw/hex/dict-with-raw (a v0.10 carrier) -> the frozen carrier decode path
        (compatibility with `grimoire-v0.10` semantics).
    """
    name = "grimoire-v0.10-entry"
    entry_stream = True

    def empty(self, params):
        return []

    def append(self, content, params, value):
        params = params or {}
        if params.get("profile") != self.name:
            raise ValueError("grimoire-v0.10-entry params require profile %r" % self.name)
        if isinstance(value, dict) and "hash" in value:
            from .grimoire_editions.semantic import encode_entry
            record = encode_entry(value, frame_id="semantic-%d" % len(content))
            content.append(record)
            return content
        # carrier compatibility: raw v0.10 runs decode exactly like the v0.10 driver
        decoded = self.decode_carrier(content, params, value)
        content.append(decoded)
        return content

    def read(self, content, params, reveal_private=False):
        return visible(content)

    def retrieve(self, content, params, address):
        vis = self.read(content, params)
        i = int(address)
        return vis[i] if 0 <= i < len(vis) else None


# ============================================================================
# exec : the executable reflex layer (learning -> instinct)
# ============================================================================
SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n)
                 for n in ("abs", "min", "max", "sum", "round", "len", "range", "float",
                           "int", "str", "bool", "list", "dict", "tuple", "enumerate",
                           "sorted", "map", "filter", "zip", "all", "any")}


class CapabilityError(Exception):
    """A call requested a band/limb/net the layer never declared (HF-B48)."""


class IntegrityError(Exception):
    """The exec layer's code does not match its promoted hash (HF-B47)."""


class ProvenanceError(Exception):
    """A calcify payload is missing its hash, capability set, signature, or provenance --
    a skill without a verifiable origin and bounds may never become an instinct."""


class SandboxError(Exception):
    """The candidate contains a STATIC escape vector (import / dunder traversal / forbidden
    builtin) and must never be calcified (HF-B51). The Python runner's restricted namespace
    is not a hard sandbox; the cheapest reliable defense is refusal at cultivation time."""


class TrustError(Exception):
    """An untrusted/foreign-provenance exec layer was asked to run on a non-isolating runner
    (HF-B50). Such code must run on the 'wasm' runner (hard sandbox) instead."""


class ResourceLimitError(Exception):
    """A cultivated skill exceeded an enforced time, memory, or result-size budget."""


class ProtocolError(Exception):
    """The isolated child returned data outside the bounded JSON response protocol."""


_FORBIDDEN_NAMES = frozenset({
    "eval", "exec", "compile", "__import__", "open", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "memoryview", "exit", "quit",
    "help", "__builtins__",
})


def validate_skill_code(code: str) -> None:
    """Static gate for a Python skill: reject `import`, dunder attribute access, and forbidden
    builtins. Raises SandboxError on the first violation."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxError("skill does not parse: %s" % e)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxError("skill may not import modules")
        if isinstance(node, ast.Attribute) and isinstance(node.attr, str) \
                and node.attr.startswith("__") and node.attr.endswith("__"):
            raise SandboxError("skill may not access dunder attribute %r (escape vector)"
                               % node.attr)
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            raise SandboxError("skill may not reference %r" % node.id)
        # These checks are intentionally conservative heuristics, not the resource
        # boundary.  The child-process limits below remain authoritative.
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) \
                and node.test.value is True \
                and not any(isinstance(child, ast.Break) for child in ast.walk(node)):
            raise SandboxError("skill contains an obvious unbounded while loop")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "range" and node.args \
                and all(isinstance(arg, ast.Constant) and isinstance(arg.value, int)
                        for arg in node.args):
            values = [arg.value for arg in node.args]
            stop = values[0] if len(values) == 1 else values[1]
            start = 0 if len(values) == 1 else values[0]
            if abs(stop - start) > 1_000_000:
                raise SandboxError("skill contains an oversized literal range")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            constants = [
                side.value for side in (node.left, node.right)
                if isinstance(side, ast.Constant) and isinstance(side.value, int)
            ]
            if constants and max(constants) > 1_000_000:
                raise SandboxError("skill contains an oversized literal repetition")


def validate_calcify_payload(content: Dict[str, Any]) -> None:
    """The calcification gate beyond the code itself: a skill may not become an instinct
    without (1) a content hash, (2) a declared capability set, (3) a signature, and
    (4) provenance naming its author. Raises ProvenanceError on the first gap."""
    if not content.get("code_hash"):
        raise ProvenanceError("calcify refused: no code_hash (integrity gate)")
    if content.get("capabilities") is None:
        raise ProvenanceError("calcify refused: no declared capability set")
    if content.get("signature") is None:
        raise ProvenanceError("calcify refused: no signature")
    prov = content.get("provenance")
    if not prov or not prov.get("author"):
        raise ProvenanceError("calcify refused: provenance must name an author")


TRUSTED_AUTHORS = frozenset({"MIND", "BODY"})
_PUBLIC_GRANT_KEYS = frozenset({"reads", "writes", "limbs", "net"})
_TRIAL_AUTHORITY = object()


def validate_public_grant(granted: Dict[str, Any] = None) -> Dict[str, Any]:
    """Validate the public invocation grant schema.

    A grant describes resource capabilities; it never grants provenance trust. Unknown
    keys are refused so a caller cannot mint authority by discovering a magic string.
    """
    if granted is None:
        return {}
    if not isinstance(granted, dict):
        raise CapabilityError("exec grant must be a dictionary")
    unknown = set(granted) - _PUBLIC_GRANT_KEYS
    if unknown:
        raise CapabilityError("unknown/reserved exec grant key(s): %s"
                              % ", ".join(sorted(map(str, unknown))))
    return dict(granted)


def provenance_is_trusted(provenance: Dict[str, Any]) -> bool:
    """Trusted only if authored by this organism's own MIND/BODY and not flagged foreign.
    Trust governs which RUNNER may run it, not whether it runs at all."""
    p = provenance or {}
    return (p.get("author") in TRUSTED_AUTHORS) and not p.get("foreign", False)


# ---- pluggable exec runners ------------------------------------------------
_RUNNERS: Dict[str, "ExecRunner"] = {}


def register_runner(cls):
    inst = cls() if isinstance(cls, type) else cls
    _RUNNERS[inst.name] = inst
    return cls


def get_runner(name: str) -> "ExecRunner":
    if name not in _RUNNERS:
        raise NotImplementedError(
            "no exec runner %r registered (have: %s). To enable WASM, register an "
            "ExecRunner(name='wasm')." % (name, ", ".join(sorted(_RUNNERS))))
    return _RUNNERS[name]


class ExecRunner:
    """Executes a calcified exec layer's payload. Gates are applied by ExecDriver BEFORE a
    runner runs; a runner only builds the environment, calls the entry, enforces the limit."""
    name = "base"

    def run(self, content: Dict[str, Any], args: Dict[str, Any],
            granted: Dict[str, Any]) -> Any:
        raise NotImplementedError


@register_runner
class PythonExecRunner(ExecRunner):
    """Restricted child + enforced time/memory/result bounds. NOT a hard sandbox.

    Trusted Python skills run in a separate process.  POSIX uses ``setrlimit`` and a
    process group; Windows assigns the child to a kill-on-close Job Object with a
    per-process memory cap.  The wire protocol is bounded JSON, never pickle.
    """
    name = "python"

    def run(self, content, args, granted):
        limits = content.get("limits", {}) or {}
        declared = max(1, int(limits.get("ms", 200))) / 1000.0
        memory_bytes = max(16 * 1024 * 1024,
                           int(limits.get("memory_bytes", 128 * 1024 * 1024)))
        result_bytes = max(1024, int(limits.get("result_bytes", 256 * 1024)))
        output_bytes = max(result_bytes + 1024,
                           int(limits.get("output_bytes", 512 * 1024)))
        # The hard kill is applied to the child process as a whole. On Windows, process
        # startup itself can exceed the old in-thread 200 ms default, so keep a small
        # floor while preserving caller-requested larger budgets.
        limit = max(declared, 1.0)
        payload = {
            "code": content["code"],
            "entry": content["entry"],
            "args": args,
            "safe_builtins": sorted(SAFE_BUILTINS),
            "memory_bytes": memory_bytes,
            "result_bytes": result_bytes,
            "output_bytes": output_bytes,
        }
        try:
            request = json.dumps(payload, ensure_ascii=True,
                                 separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ProtocolError("exec arguments are not JSON-safe: %s" % exc)
        if len(request) > output_bytes:
            raise ResourceLimitError("exec request exceeded its protocol-size budget")
        runner = r"""
import builtins
import ctypes
import json
import os
import sys

def emit(value, cap):
    data = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    if len(data) > cap:
        data = json.dumps({"ok": False, "limit": "output",
                           "error_type": "ResourceLimitError",
                           "error": "exec response exceeded output budget"},
                          separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(data)

def apply_limits(memory_bytes):
    if os.name == "posix":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        return None
    if os.name != "nt":
        raise RuntimeError("memory enforcement unavailable on this platform")

    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class BASIC_LIMITS(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class EXTENDED_LIMITS(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BASIC_LIMITS),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE, wintypes.HANDLE
    ]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
    info = EXTENDED_LIMITS()
    info.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        | JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    info.BasicLimitInformation.ActiveProcessLimit = 1
    info.ProcessMemoryLimit = memory_bytes
    if not kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info)):
        raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")
    return job

raw = sys.stdin.buffer.read()
try:
    payload = json.loads(raw.decode("utf-8"))
except BaseException as e:
    emit({"ok": False, "error_type": "ProtocolError",
          "error": "malformed request: " + str(e)}, 4096)
    raise SystemExit(0)

try:
    job_handle = apply_limits(int(payload["memory_bytes"]))
except BaseException as e:
    emit({"ok": False, "error_type": "ResourceLimitError",
          "error": "memory limit setup failed: " + str(e)}, payload["output_bytes"])
    raise SystemExit(0)

safe = {name: getattr(builtins, name) for name in payload["safe_builtins"]}
g = {"__builtins__": safe}
try:
    exec(payload["code"], g, g)
    fn = g.get(payload["entry"])
    if fn is None:
        raise NameError("entry %r not defined by exec layer" % payload["entry"])
    result = fn(**payload["args"])
    encoded_result = json.dumps(result, ensure_ascii=True,
                                separators=(",", ":")).encode("utf-8")
    if len(encoded_result) > payload["result_bytes"]:
        out = {"ok": False, "limit": "result",
               "error_type": "ResourceLimitError",
               "error": "exec result exceeded result-size budget"}
    else:
        out = {"ok": True, "result": result}
except BaseException as e:
    out = {"ok": False, "error_type": type(e).__name__, "error": str(e)}
emit(out, payload["output_bytes"])
"""
        kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        if os.name == "posix":
            kwargs["start_new_session"] = True
        elif os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [sys.executable, "-I", "-c", runner],
            **kwargs,
        )
        try:
            stdout, stderr = proc.communicate(input=request, timeout=limit)
        except subprocess.TimeoutExpired:
            self._kill_tree(proc)
            proc.communicate()
            raise ResourceLimitError("exec layer exceeded its time budget")
        if len(stdout) > output_bytes or len(stderr) > output_bytes:
            raise ResourceLimitError("exec runner exceeded its output budget")
        if proc.returncode != 0:
            raise ResourceLimitError(
                "exec child terminated under a memory/process budget: %s"
                % stderr[:1024].decode("utf-8", "replace")
            )
        out = self._decode_response(stdout)
        if out.get("ok"):
            return out.get("result")
        if out.get("limit") or out.get("error_type") == "ResourceLimitError":
            raise ResourceLimitError(out.get("error", "exec resource budget exceeded"))
        if out.get("error_type") == "MemoryError":
            raise ResourceLimitError("exec layer exceeded its memory budget")
        if out.get("error_type") == "ProtocolError":
            raise ProtocolError(out.get("error", "exec protocol failed"))
        exc = getattr(builtins, out.get("error_type", ""), RuntimeError)
        if not isinstance(exc, type) or not issubclass(exc, BaseException):
            exc = RuntimeError
        raise exc(out.get("error", "exec layer failed"))

    @staticmethod
    def _decode_response(raw: bytes) -> Dict[str, Any]:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError("malformed exec child response: %s" % exc)
        if not isinstance(value, dict) or not isinstance(value.get("ok"), bool):
            raise ProtocolError("exec child response violates schema")
        allowed = {"ok", "result", "error_type", "error", "limit"}
        if set(value) - allowed:
            raise ProtocolError("exec child response contains unknown fields")
        if value["ok"] and "result" not in value:
            raise ProtocolError("successful exec response has no result")
        if not value["ok"] and not isinstance(value.get("error"), str):
            raise ProtocolError("failed exec response has no error string")
        return value

    @staticmethod
    def _kill_tree(proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            # The child owns a KILL_ON_JOB_CLOSE Job Object. Terminating it closes
            # that handle and tears down any descendants admitted by the job.
            proc.kill()


@register_runner
class WasmExecRunner(ExecRunner):
    """DOCUMENTED EXTENSION POINT -- a prepared seam, intentionally NOT built (keeps the core
    pure-stdlib). A WASM runner gives a hard sandbox + portability across any Body with a wasm
    runtime. Contract: content["runner"]=="wasm", content["code"]=base64 .wasm module
    (code_hash covers it unchanged), instantiate with ONLY the imports implied by `granted`,
    apply limits["ms"]."""
    name = "wasm"

    def run(self, content, args, granted):
        raise NotImplementedError(
            "exec-wasm is a prepared seam, not yet built. Register a real ExecRunner("
            "name='wasm') with a wasm runtime to enable portable, hard-sandboxed skills.")


@register
class ExecDriver(Driver):
    """content = {code, code_hash, entry, language, runner, signature, capabilities,
                  limits, provenance}
    The Body invokes via execute(); it never runs unless the hash matches, the call stays
    within declared capabilities, and the provenance/trust gate admits the runner."""
    name = "exec"

    def empty(self, params):
        return {}

    def read(self, content, params, reveal_private=False):
        # the code is readable; the reflex is described, not auto-run
        return {k: content.get(k) for k in
                ("entry", "language", "signature", "capabilities", "limits", "provenance")}

    def retrieve(self, content, params, address):
        return content.get(str(address))

    def append(self, content, params, value):
        raise PermissionError("exec layers are installed via CALCIFY, not append")

    def execute(self, content: Dict[str, Any], args: Dict[str, Any],
                granted: Dict[str, Any] = None) -> Any:
        """Public execution path. Trust can never be minted through ``granted``."""
        return self._execute(content, args, validate_public_grant(granted))

    def _execute(self, content: Dict[str, Any], args: Dict[str, Any],
                 granted: Dict[str, Any], *, trial_authority: Any = None) -> Any:
        # 1. integrity gate: code must match the hash it was promoted with
        if code_hash(content["code"]) != content["code_hash"]:
            raise IntegrityError("exec layer hash mismatch -- refusing to run")
        # 2. capability gate: the call may not exceed the declared capability set
        caps = content.get("capabilities", {})
        for kind in ("reads", "writes", "limbs"):
            asked = set(granted.get(kind, []))
            allowed = set(caps.get(kind, []))
            if not asked <= allowed:
                raise CapabilityError("exec layer exceeded %s capability: %s not in %s"
                                      % (kind, asked - allowed, allowed))
        if granted.get("net") and not caps.get("net"):
            raise CapabilityError("exec layer requested net without capability")
        # 3. trust gate (HF-B50): non-isolating runners run only trusted, in-lineage code.
        runner_name = content.get("runner", "python")
        if (runner_name != "wasm"
                and not provenance_is_trusted(content.get("provenance", {}))
                and trial_authority is not _TRIAL_AUTHORITY):
            prov = content.get("provenance", {})
            raise TrustError(
                "untrusted-provenance exec layer (author=%r, foreign=%r) refused on "
                "non-isolating runner %r -- run it on the 'wasm' runner, or earn trust via "
                "the private trial+calcify ceremony."
                % (prov.get("author"), prov.get("foreign", False), runner_name))
        # 4. dispatch to the selected runner
        return get_runner(runner_name).run(content, args, granted)


def trial(code: str, entry: str, cases: List[Tuple[Dict[str, Any], Any]]) -> Dict[str, Any]:
    """Run a candidate skill against (args, expected) cases. The static sandbox gate runs
    FIRST: code that could escape the namespace never reaches the proving step. Used by the
    calcification pipeline BEFORE a skill is allowed into an exec layer."""
    validate_skill_code(code)
    drv = ExecDriver()
    candidate = {"code": code, "code_hash": code_hash(code), "entry": entry,
                 "capabilities": {},
                 "limits": {"ms": 200, "memory_bytes": 128 * 1024 * 1024,
                            "result_bytes": 256 * 1024, "output_bytes": 512 * 1024}}
    passed = 0
    detail = []
    for args, expected in cases:
        try:
            # Trial authority is a private object capability, not a public dictionary key.
            got = drv._execute(candidate, args, {}, trial_authority=_TRIAL_AUTHORITY)
            ok = (got == expected)
        except Exception as e:                   # noqa: BLE001
            got, ok = "ERROR:%s" % e, False
        passed += ok
        detail.append({"args": args, "expected": expected, "got": got, "ok": ok})
    return {"cases": len(cases), "passed": passed, "ok": passed == len(cases), "detail": detail}
