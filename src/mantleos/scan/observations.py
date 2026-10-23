"""Explicitly permitted, bounded observations in disposable copies; no sandbox."""
import copy
from pathlib import Path
import platform
import sys
import tempfile
import uuid
from .common import ScanError, digest, outside, sha
from .evidence import base, context, core_provider, external_evidence, fields, provider, seal, source_bytes, timestamp, utc_now, verify_evidence
from .providers import HEX
from .investigator import _report


def run(*args, **kwargs):
    # The native static workflow does not initialize a process transport.
    from .provider_process import run as transport
    return transport(*args, **kwargs)

SCOPE = "Only this authorized command's exit code and captured output; no generalized behavior or equivalence"


def snapshot_check(report, source_root):
    value = external_evidence(report, {"check": "source snapshot"}, core_provider(_report(report)))
    return verify_evidence(value, report, source_root)


def observe(report, source_root, command, *, permit_execution=False, timeout=20, output_limit=1_000_000):
    if permit_execution is not True:
        raise ScanError("Controlled observation requires explicit execution permission")
    if not isinstance(command, list) or not 1 <= len(command) <= 64 or any(not isinstance(item, str) or not 1 <= len(item) <= 4096 or "\x00" in item for item in command):
        raise ScanError("Observation command must be a bounded argument array; shell strings are forbidden")
    if type(timeout) is not int or not 1 <= timeout <= 30 or type(output_limit) is not int or not 1 <= output_limit <= 1_000_000:
        raise ScanError("Observation deadline/output budget is invalid")
    graph = _report(report)
    if graph["scope"].get("inventory_exhausted_within_exclusions") is not True or any(entry.get("sha256") is None for entry in graph["files"]):
        raise ScanError("Controlled observation needs a complete hashed inventory within the declared exclusions")
    snapshot_check(report, source_root)
    argv = [sys.executable if item == "{python}" else item for item in command]
    executable = Path(argv[0])
    if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
        raise ScanError("Observation executable must be a trusted absolute host path or {python}")
    outside(executable, source_root)
    if executable.stat().st_size > 150_000_000: raise ScanError("Observation executable budget exceeded")
    executable_hash = sha(executable.read_bytes())
    started = utc_now()
    with tempfile.TemporaryDirectory(prefix="mantle-observation-") as temporary:
        folder = Path(temporary)
        outside(folder, source_root)
        for entry in graph["files"]:
            data = source_bytes(source_root, entry["path"], entry["sha256"])
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        captured = run(argv, b"", cwd=folder, timeout=timeout, output_limit=output_limit, check=False)
    # A failed snapshot recheck yields no accepted observation record. Effects
    # of the trusted host command outside the copy cannot be undone or denied.
    snapshot_check(report, source_root)
    if sha(executable.read_bytes()) != executable_hash:
        raise ScanError("Observation host executable changed during the run")
    ctx = context(report)
    body = {"schema": "scan.observation/1", "run_id": "run:" + str(uuid.uuid4()), "context": ctx,
            "provider": {"name": "mantleos-controlled-process", "version": "1",
                         "revision": digest([sha(Path(__file__).read_bytes()), sha((Path(__file__).parent / "provider_process.py").read_bytes())])},
            "permission": {"execution": "EXPLICIT_OPERATOR_INVOCATION", "shell": False},
            "host": {"system": platform.system(), "machine": platform.machine(), "python": sys.version.split()[0],
                     "executable_sha256": executable_hash},
            "command": copy.deepcopy(argv), "started_at": started, "finished_at": utc_now(),
            "limits": {"timeout_seconds": timeout, "stdout_bytes": output_limit, "stderr_bytes": 64_000},
            "environment": {"policy": "SYSTEM_AND_TEMP_ONLY", "application_variables_forwarded": False},
            "isolation": "Disposable source copy; no OS sandbox, network denial or descendant containment",
            "result": {"status": "COMPLETED", "exit_code": captured["exit_code"], "seconds": captured["seconds"],
                       "stdout": captured["stdout"].decode("utf-8", errors="replace"),
                       "stderr": captured["stderr"].decode("utf-8", errors="replace"),
                       "stdout_raw_hex": captured["stdout"].hex(), "stderr_raw_hex": captured["stderr"].hex(),
                       "stdout_sha256": sha(captured["stdout"]), "stderr_sha256": sha(captured["stderr"]), "truncated": False},
            "limitations": [SCOPE, "Observation authenticity requires a separately trusted authorization digest; a self-hash is insufficient."]}
    return dict(body, id="observation:" + digest(body))


def verify_observation(receipt, report, source_root, *, expected_sha256):
    try:
        fields(receipt, ("schema", "id", "run_id", "context", "provider", "permission", "host", "command", "started_at", "finished_at",
                         "limits", "environment", "isolation", "result", "limitations"))
        if not isinstance(expected_sha256, str) or digest(receipt) != expected_sha256:
            raise ScanError("Observation does not match its independently trusted authorization digest")
        body = {key: value for key, value in receipt.items() if key != "id"}
        if receipt["schema"] != "scan.observation/1" or receipt["id"] != "observation:" + digest(body):
            raise ScanError("Observation receipt identity mismatch")
        if receipt["context"] != context(report) or str(Path(source_root).resolve()) != receipt["context"]["source_root"]:
            raise ScanError("Observation source context mismatch")
        if receipt["permission"] != {"execution": "EXPLICIT_OPERATOR_INVOCATION", "shell": False}:
            raise ScanError("Observation execution permission missing")
        if receipt["environment"] != {"policy": "SYSTEM_AND_TEMP_ONLY", "application_variables_forwarded": False}:
            raise ScanError("Unknown observation environment policy")
        provider(receipt["provider"])
        if receipt["provider"]["name"] != "mantleos-controlled-process" or receipt["provider"]["version"] != "1":
            raise ScanError("Unknown controlled observation provider")
        fields(receipt["host"], ("system", "machine", "python", "executable_sha256"))
        if any(not isinstance(receipt["host"][key], str) or not 1 <= len(receipt["host"][key]) <= 200 for key in ("system", "machine", "python")) or not HEX.fullmatch(receipt["host"]["executable_sha256"]):
            raise ScanError("Observation host provenance missing")
        command = receipt["command"]
        if not isinstance(command, list) or not 1 <= len(command) <= 64 or any(not isinstance(item, str) or not 1 <= len(item) <= 4096 or "\x00" in item for item in command) or not Path(command[0]).is_absolute():
            raise ScanError("Observation command provenance missing")
        if receipt["isolation"] != "Disposable source copy; no OS sandbox, network denial or descendant containment":
            raise ScanError("Observation isolation scope mismatch")
        if not isinstance(receipt["run_id"], str) or not receipt["run_id"].startswith("run:"):
            raise ScanError("Observation run identity missing")
        uuid.UUID(receipt["run_id"][4:])
        if timestamp(receipt["started_at"]) > timestamp(receipt["finished_at"]):
            raise ScanError("Observation timestamps are reversed")
        result = receipt["result"]
        fields(result, ("status", "exit_code", "seconds", "stdout", "stderr", "stdout_raw_hex", "stderr_raw_hex", "stdout_sha256", "stderr_sha256", "truncated"))
        if result["status"] != "COMPLETED" or type(result["exit_code"]) is not int or type(result["seconds"]) not in (int, float) or not 0 <= result["seconds"] <= 35 or result["truncated"] is not False:
            raise ScanError("Incomplete or invalid observation result")
        fields(receipt["limits"], ("timeout_seconds", "stdout_bytes", "stderr_bytes"))
        limits = receipt["limits"]
        if type(limits["timeout_seconds"]) is not int or not 1 <= limits["timeout_seconds"] <= 30 or type(limits["stdout_bytes"]) is not int or not 1 <= limits["stdout_bytes"] <= 1_000_000 or limits["stderr_bytes"] != 64_000:
            raise ScanError("Invalid observation limits")
        for key, limit in (("stdout", limits["stdout_bytes"]), ("stderr", 64_000)):
            text, raw_hex = result[key], result[key + "_raw_hex"]
            if not isinstance(text, str) or not isinstance(raw_hex, str) or len(raw_hex) > 2 * limit:
                raise ScanError("Observation stream budget exceeded")
            raw = bytes.fromhex(raw_hex)
            if sha(raw) != result[key + "_sha256"] or raw.decode("utf-8", errors="replace") != text:
                raise ScanError("Observation stream identity mismatch")
        if SCOPE not in receipt["limitations"]:
            raise ScanError("Observation scope limitation missing")
        snapshot_check(report, source_root)
        return {"schema": "scan.observation-verification/1", "result": "PASS", "run_id": receipt["run_id"], "scope": SCOPE}
    except ScanError: raise
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError) as error:
        raise ScanError("Malformed observation receipt") from error


def runtime_evidence(report, observation, *, authorized_sha256, source_root, **kwargs):
    verify_observation(observation, report, source_root, expected_sha256=authorized_sha256)
    body = base(report, "RUNTIME_OBSERVED", "controlled-observation", observation["provider"], **kwargs)
    if timestamp(body["created_at"]) < timestamp(observation["finished_at"]):
        raise ScanError("Runtime evidence predates its completed observation")
    body["runtime_receipt_id"] = observation["run_id"]
    body["assertions"] = [{"record_type": "runtime", "evidence_class": "RUNTIME_OBSERVED", "observation": copy.deepcopy(observation["result"])}]
    body["limitations"].extend(observation["limitations"])
    return seal(body)
