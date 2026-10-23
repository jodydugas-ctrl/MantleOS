"""Bounded optional host process. This is not an OS security sandbox."""
import os
import subprocess
import threading
import time
from .common import ScanError


def run(argv, payload, *, cwd, timeout=30, output_limit=8_000_000, check=True):
    if not 0 < timeout <= 30 or type(output_limit) is not int or not 1 <= output_limit <= 8_000_000:
        raise ScanError("Invalid provider process limits")
    if not isinstance(payload, bytes) or len(payload) > 3_000_000:
        raise ScanError("Provider input budget exceeded")
    # Exclude inherited Node injection flags, package paths, proxy settings,
    # credentials and application environment. The configured host remains trusted.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP") if key in os.environ}
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    output, errors, overflow = bytearray(), bytearray(), threading.Event()
    failures = []
    def receive(stream, target, limit):
        try:
            while chunk := stream.read(8192):
                if len(target) + len(chunk) > limit:
                    overflow.set()
                    process.kill()
                    break
                target.extend(chunk)
        except OSError as error:
            failures.append(error)
        finally:
            stream.close()
    def send():
        try:
            process.stdin.write(payload)
            process.stdin.close()
        except (OSError, ValueError) as error:
            failures.append(error)
    threads = [threading.Thread(target=receive, args=(process.stdout, output, output_limit), daemon=True),
               threading.Thread(target=receive, args=(process.stderr, errors, 64_000), daemon=True),
               threading.Thread(target=send, daemon=True)]
    start = time.monotonic()
    for thread in threads: thread.start()
    try:
        process.wait(timeout=timeout)
        for thread in threads: thread.join(timeout=max(0, timeout - (time.monotonic() - start)))
        if any(thread.is_alive() for thread in threads):
            raise ScanError("Provider streams did not close within the deadline")
        if overflow.is_set(): raise ScanError("Provider output budget exceeded")
        if failures: raise ScanError("Provider transport failed")
        if check and process.returncode != 0:
            # Provider text is inert diagnostic data, never a command or permission.
            raise ScanError("Provider failed: " + errors.decode("utf-8", errors="replace")[:400])
        if check: return bytes(output)
        return {"stdout": bytes(output), "stderr": bytes(errors), "exit_code": process.returncode,
                "seconds": time.monotonic() - start}
    except subprocess.TimeoutExpired as error:
        raise ScanError("Provider deadline exceeded") from error
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        # Only the directly launched process is owned here. Descendant isolation
        # and network denial are not claimed; optional executables must be trusted.

