#!/usr/bin/env python3
"""
mantle.graft  --  the GRAFT GERM and LIVE RESIDENCY (Mantle OS · R1 + R2)

Graft procedure is owned by the Mantle runtime docs and code. The Grimoire is the VCW
software profile, not a separate residency manual. Graft reuses the single canonical
organ-role table (ROLES from assimilator.scanner) and delegates scanning to anchor(); it
never re-classifies.

A graft is a SPORE AIMED AT A HOST: the same one-artifact story as every birth, but the
germ inside is a patch set, not a from-scratch spec. `load_graft` accepts either a germ
JSON file or a spore PNG carrying a graft germ.

The graft rests on two reframes:

  R1 -- the germ as a PATCH SET, not a from-scratch spec.
        A normal germ declares a WHOLE new AppAI. A *graft* germ instead
        carries a NON-DESTRUCTIVE diff against a NAMED host: extra app bands, hook
        directives (which classified symbols to thread through the organism), and
        instincts. Applying a graft never touches the original host -- it copies the host
        into a WORKSPACE and grows the resident there. The original is census-proven
        byte-identical. If the host has DRIFTED from the census the graft was built
        against, the apply RAISES a GraftDrift interrupt (for the MIND to re-patch) rather
        than mis-applying silently -- "managing its own survival against source drift."

  R2 -- residency that WEAVES a live nervous system, not just a static map.
        `weave()` replaces a host namespace's classified callables with the assimilator's
        fail-open, reversible wrappers (`assimilator.Assimilation`): SENSOR_EVENTs become
        senses entries, ARM_ACTIONs get Limb proofs, exceptions become immune events --
        live, on every call, zero LLM. The host's behavior is preserved EXACTLY (same
        return, same exceptions). `unweave()` restores the originals; detach is clean.

Germs carry DATA, not programs: a graft's hooks are role directives, and any instinct it
carries rides the same gauntlet as every skill. A malformed graft never applies.

    python -m mantle graft examples/spores/notes_graft.png <host-dir>
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from .assimilator.scanner import ROLES
from .vcw.bands import make_band_boot

GRAFT_FORMAT = "mantle-graft-egg-v1"
NEST = ".mantle"


class GraftError(Exception):
    """A malformed graft egg. It never applies; the reason is the message."""


class GraftDrift(Exception):
    """The host has drifted from the census the graft was built against. The graft is NOT
    applied silently -- this interrupt is the signal for the MIND to re-patch."""


def _assert_safe_host_tree(host: str) -> None:
    """Refuse symlink/junction escapes before copying an untrusted host tree."""
    root = os.path.realpath(os.path.abspath(host))
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in list(dirnames) + list(filenames):
            candidate = os.path.join(dirpath, name)
            is_link = os.path.islink(candidate)
            is_junction = bool(getattr(os.path, "isjunction", lambda _p: False)(candidate))
            if not (is_link or is_junction):
                continue
            resolved = os.path.realpath(candidate)
            try:
                inside = os.path.commonpath([root, resolved]) == root
            except ValueError:
                inside = False
            if not inside:
                raise GraftError("host link escapes approved tree: %s" % candidate)


# ---------------------------------------------------------------------------
# the graft egg: a non-destructive diff, declared as data
# ---------------------------------------------------------------------------
def _need(d: Dict[str, Any], key: str, typ, where: str):
    if key not in d:
        raise GraftError("%s: missing %r" % (where, key))
    if not isinstance(d[key], typ):
        raise GraftError("%s: %r must be %s" % (where, key, typ.__name__))
    return d[key]


def validate_graft(graft: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a graft egg dict (structure only -- it carries data, not code)."""
    if graft.get("graft_format") != GRAFT_FORMAT:
        raise GraftError("not a graft egg (graft_format != %r)" % GRAFT_FORMAT)
    ident = _need(graft, "identity", dict, "graft")
    _need(ident, "name", str, "graft.identity")
    _need(graft, "host", str, "graft")               # the NAMED host (repo/url/label)
    for i, band in enumerate(graft.get("bands", [])):
        where = "graft.bands[%d]" % i
        _need(band, "band", str, where)
        head = _need(band, "head", int, where)
        if not (550 <= head <= 749):
            raise GraftError("%s: app bands live in 550-749 (head=%d)" % (where, head))
    for i, h in enumerate(graft.get("hooks", [])):
        where = "graft.hooks[%d]" % i
        _need(h, "symbol", str, where)
        role = _need(h, "role", str, where)
        if role not in ROLES:
            raise GraftError("%s: role %r not a known organ role" % (where, role))
    if "host_census" in graft and not isinstance(graft["host_census"], dict):
        raise GraftError("graft.host_census must be a map of path -> sha256")
    return graft


def load_graft(path: str) -> Dict[str, Any]:
    """Load a graft from a germ JSON file or from a spore PNG carrying a graft germ
    (a spore aimed at a host)."""
    with open(path, "rb") as f:
        if f.read(8) == b"\x89PNG\r\n\x1a\n":
            from . import spore as _spore
            germ = _spore.read_spore(path)["state"].get("germ")
            if germ is None:
                raise GraftError("spore %r carries no germ to graft" % path)
            return validate_graft(germ)
    with open(path, "r", encoding="utf-8") as f:
        return validate_graft(json.load(f))


def graft_bands(graft: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The graft's extra app bands as boot sectors, ready for the resident's genome."""
    return [make_band_boot(b["band"], b["head"], b.get("encoding", "log-json"),
                           params=b.get("params"), private=bool(b.get("private")),
                           span=b.get("span", 1), purpose=b.get("purpose", b["band"]))
            for b in graft.get("bands", [])]


# ---------------------------------------------------------------------------
# R1: apply the graft -- non-destructively, in a workspace
# ---------------------------------------------------------------------------
def _drift(graft: Dict[str, Any], host: str) -> List[str]:
    """Which census-recorded host files have drifted from the graft's expectation.
    Empty list == the host still matches what the graft was built against."""
    from .anchor import census
    recorded = graft.get("host_census") or {}
    if not recorded:
        return []                                # no census recorded -> nothing to check
    now = census(host)
    return sorted(p for p, h in recorded.items() if now.get(p) != h)


def apply(graft: Dict[str, Any], host: str, workspace: Optional[str] = None,
          starter_credits: float = 5.0, allow_drift: bool = False) -> Dict[str, Any]:
    """Apply a graft egg to `host` WITHOUT touching it: copy the host into a workspace,
    grow the resident there (with the graft's extra bands), and return
    {organism, workspace, report, hooks}. The original host is census-verified unchanged.
    A drifted host raises GraftDrift unless `allow_drift=True`."""
    from .anchor import anchor, census
    graft = validate_graft(graft)
    host = os.path.abspath(host)
    if not os.path.isdir(host):
        raise GraftError("host %r is not a directory" % host)
    _assert_safe_host_tree(host)

    drifted = _drift(graft, host)
    if drifted and not allow_drift:
        raise GraftDrift("host drifted from the graft's census (%d file(s): %s); the MIND "
                         "must re-patch" % (len(drifted), ", ".join(drifted[:5])))

    before = census(host)                        # the ORIGINAL, must stay byte-identical
    ws_root = workspace or tempfile.mkdtemp(prefix="mantle-graft-")
    ws_host = os.path.join(ws_root, os.path.basename(host.rstrip("/\\")) or "host")
    shutil.copytree(host, ws_host, dirs_exist_ok=True)

    # the resident grows in the WORKSPACE copy; the graft's bands ride into its genome
    result = anchor(ws_host, name=graft["identity"]["name"],
                    starter_credits=starter_credits, extra_bands=graft_bands(graft))
    org = result["organism"]

    # remember the hook directives as observed facts (R2 reads these to weave a host)
    hooks = list(graft.get("hooks", []))
    org.memory.remember("facts", {"graft_hooks": hooks, "graft_host": graft["host"]},
                        opcode="OBSERVED", source="graft", verified=True)
    org.save(os.path.join(ws_host, NEST))

    after = census(host)                         # prove the ORIGINAL host untouched
    if before != after:
        raise GraftError("GRAFT MODIFIED THE ORIGINAL HOST -- this must never happen")

    report = {"graft": graft["identity"]["name"], "host": graft["host"],
              "workspace": ws_host, "original_unchanged": before == after,
              "drifted": drifted, "extra_bands": [b["band"] for b in graft.get("bands", [])],
              "hooks": len(hooks), "certified": org.stage1_certified}
    return {"organism": org, "workspace": ws_host, "report": report, "hooks": hooks}


def apply_artifact(path: str, host: str, *, workspace: str,
                   authorization: Any, starter_credits: float = 5.0,
                   allow_drift: bool = False) -> Dict[str, Any]:
    """Authorized transactional external graft activation.

    ``apply`` remains the Body-internal data operation used by reconstruction/tests;
    all external artifacts enter here and are authorized before a target exists.
    """
    from .anchor import anchor, census
    from .lifecycle import (LifecycleAction, LifecycleAuthorizationError,
                            begin_transaction)
    graft = load_graft(path)
    host = os.path.abspath(host)
    if not os.path.isdir(host):
        raise GraftError("host %r is not a directory" % host)
    _assert_safe_host_tree(host)
    target = os.path.join(os.path.abspath(workspace),
                          os.path.basename(host.rstrip("/\\")) or "host")
    try:
        transaction = begin_transaction(
            authorization, LifecycleAction.GRAFT, path, target
        )
    except (LifecycleAuthorizationError, FileExistsError) as exc:
        raise GraftError("activation refused: %s" % exc) from exc
    try:
        transaction.phase("drift_check")
        drifted = _drift(graft, host)
        if drifted and not allow_drift:
            raise GraftDrift(
                "host drifted from the graft census (%d file(s): %s)"
                % (len(drifted), ", ".join(drifted[:5]))
            )
        before = census(host)
        transaction.phase("copy_host")
        shutil.copytree(host, transaction.staging, dirs_exist_ok=True)
        transaction.phase("anchor_resident")
        result = anchor(
            transaction.staging, name=graft["identity"]["name"],
            starter_credits=starter_credits, extra_bands=graft_bands(graft),
        )
        org = result["organism"]
        hooks = list(graft.get("hooks", []))
        org.memory.remember(
            "facts", {"graft_hooks": hooks, "graft_host": graft["host"]},
            opcode="OBSERVED", source="graft", verified=True,
        )
        org.save(os.path.join(transaction.staging, NEST))
        if not org.stage1_certified:
            raise GraftError("Stage-1 gate did not certify the graft resident")
        after = census(host)
        if before != after:
            raise GraftError("GRAFT MODIFIED THE ORIGINAL HOST -- this must never happen")
        report = {
            "graft": graft["identity"]["name"], "host": graft["host"],
            "workspace": target, "original_unchanged": True, "drifted": drifted,
            "extra_bands": [b["band"] for b in graft.get("bands", [])],
            "hooks": len(hooks), "certified": org.stage1_certified,
            "lifecycle": {"result": "pass", "action": "graft",
                          "authorization": authorization.redacted(),
                          "journal": os.path.join(target, "lifecycle_journal.json")},
        }
        with open(os.path.join(transaction.staging, "graft_report.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
        transaction.phase("artifact_verified")
        transaction.promote()
        return {"organism": org, "workspace": target, "report": report, "hooks": hooks}
    except Exception as exc:
        transaction.interrupt(type(exc).__name__)
        raise


# ---------------------------------------------------------------------------
# R2: weave a live nervous system into a running host namespace
# ---------------------------------------------------------------------------
def weave(namespace: Dict[str, Any], hooks: List[Dict[str, Any]],
          assimilation: Any) -> List[str]:
    """Replace each hooked callable in `namespace` with its fail-open organ wrapper. The
    host's behavior is preserved EXACTLY; every call now also perceives/proves/mirrors
    through the organism. Returns the symbols woven. Reversible via `unweave`."""
    woven: List[str] = []
    for h in hooks:
        sym, role = h["symbol"], h["role"]
        fn = namespace.get(sym)
        if callable(fn) and not getattr(fn, "mantle_role", None):   # not already woven
            namespace[sym] = assimilation.wrap(role, fn, sym)
            woven.append(sym)
    return woven


def unweave(namespace: Dict[str, Any], symbols: List[str], assimilation: Any) -> List[str]:
    """Detach: restore each woven symbol to its original callable (byte-for-byte behavior).
    Returns the symbols restored."""
    restored: List[str] = []
    for sym in symbols:
        fn = namespace.get(sym)
        if getattr(fn, "mantle_role", None):
            namespace[sym] = assimilation.unwrap(fn)
            restored.append(sym)
    return restored
