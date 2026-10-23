#!/usr/bin/env python3
"""
mantle.core.audit  --  shared scaffolding for the audit/test harnesses (Mantle OS)

Standardizes how checks are recorded and shown; every correctness assertion lives in its
harness (mantle.audits). Fail-open: a buggy check is a FAIL with evidence, never a crash.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

PASS, FAIL, NA = "PASS", "FAIL", "N/A"


def make_row(code: str, requirement: str, result: Any, hf: str = None,
             note: str = "") -> Dict[str, Any]:
    """One audit-table row. `result` may be a bool (True->PASS) or PASS/FAIL/N-A."""
    if isinstance(result, bool):
        result = PASS if result else FAIL
    return {"code": code, "requirement": requirement, "hf": hf, "result": result,
            "note": note}


def safe(rows: List[Dict[str, Any]], code: str, requirement: str, hf: str,
         fn: Callable[[], Tuple[bool, str]]) -> None:
    """Run a check returning (ok, note) and append its row. Fail-open."""
    try:
        ok, note = fn()
    except Exception as e:  # noqa: BLE001 -- a check bug is a FAIL with evidence
        ok, note = False, "check crashed: %s: %s" % (type(e).__name__, e)
    rows.append(make_row(code, requirement, ok, hf, note))


def print_row(r: Dict[str, Any], width: int, result_width: int = 9) -> None:
    hf = (" [%s]" % r["hf"]) if r["hf"] else ""
    print("  %-5s %-*s %-*s %s%s" % (r["code"], result_width, r["result"], width,
                                     r["requirement"], r["note"], hf))


def expect_raise(fn: Callable[[], Any], exc) -> Tuple[bool, str]:
    """(True, ...) iff calling fn() raises `exc` -- the standard shape for guard tests."""
    try:
        fn()
        return False, "expected %s, nothing raised" % getattr(exc, "__name__", exc)
    except exc:
        return True, "raised %s as required" % getattr(exc, "__name__", exc)
    except Exception as e:  # noqa: BLE001
        return False, "expected %s, got %s: %s" % (getattr(exc, "__name__", exc),
                                                   type(e).__name__, e)
