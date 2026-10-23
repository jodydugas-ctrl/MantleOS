"""``mantle nest ...`` command family (additive, out-of-core).

Implements the additive CLI surface from the GitHub NEST brief:

    python -m mantle nest inspect github:OWNER/REPO
    python -m mantle nest connect LOCAL_NEST github:OWNER/REPO --auth=AUTH.json
    python -m mantle nest pull github:OWNER/REPO --out=LOCAL_DIR
    python -m mantle nest push LOCAL_NEST github:OWNER/REPO --auth=AUTH.json
    python -m mantle nest sync github:OWNER/REPO
    python -m mantle nest doctor github:OWNER/REPO
    python -m mantle nest disconnect github:OWNER/REPO --preserve-remote

Creation, first publication, rebinding, force replacement, visibility changes,
release publication, and deletion require explicit target-bound lifecycle
authorization. There is no implicit ``--force`` path.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from .envelope import AESGCMEnvelopeProvider, EnvelopeKey
from .target import NestTarget, parse_location
from .transport import NestConflict

BINDING_FILE = ".mantle-nest-binding.json"

# repo root = <root>/src/mantle/nest/cli.py -> up 4
_REPO_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_ASSETS_WORKFLOWS = os.path.join(_REPO_ROOT, "nest_assets", "workflows")


class NestCliError(Exception):
    pass


def _load_transport(flags: Dict[str, object]):
    """Build a transport from --auth (JSON with optional provider) or use the fake.

    Tests pass an explicit transport; the operator path reads ``--auth=AUTH.json``
    which must contain ``{"token": "...", "token_type": "token"}`` (a short-lived
    credential). For hermetic tests / dry runs, ``--transport=fake`` builds a
    deterministic in-memory transport.
    """
    if flags.get("--transport") == "fake":
        from .fake import FakeGithubTransport

        return FakeGithubTransport()
    auth_path = flags.get("--auth")
    if not isinstance(auth_path, str) or not os.path.isfile(auth_path):
        raise NestCliError(
            "cluster auth required: pass --auth=AUTH.json with a short-lived token, "
            "or --transport=fake for hermetic use"
        )
    with open(auth_path, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
    if "token" not in auth_data:
        raise NestCliError("AUTH.json must contain a 'token' field (short-lived)")
    from .github import GithubAuth, GithubNestTransport

    return GithubNestTransport(GithubAuth(str(auth_data["token"]),
                                          token_type=str(auth_data.get("token_type", "token"))))


def _load_envelope(flags: Dict[str, object]) -> AESGCMEnvelopeProvider:
    """Load or mint the Body secret envelope.

    An operator may pass ``--envelope-key=FILE`` (a 32-byte key) for a persistent
    provider, or omit it to mint an ephemeral key (a clearly labeled personal
    prototype). Production should use GitHub OIDC to an external KMS.
    """
    from .envelope import EnvelopeKey

    key_path = flags.get("--envelope-key")
    if isinstance(key_path, str) and os.path.isfile(key_path):
        with open(key_path, "rb") as f:
            secret = f.read()
        if len(secret) != 32:
            raise NestCliError("envelope key file must contain exactly 32 bytes")
        import hashlib

        key = EnvelopeKey(secret=secret,
                          fingerprint="sha256:" + hashlib.sha256(secret).hexdigest())
        return AESGCMEnvelopeProvider(key)
    return AESGCMEnvelopeProvider(EnvelopeKey.generate())


def _read_binding(local_nest: str) -> NestTarget:
    path = os.path.join(local_nest, BINDING_FILE)
    if not os.path.isfile(path):
        raise NestCliError("no nest binding in %s (run 'nest connect' first)" % local_nest)
    with open(path, "r", encoding="utf-8") as f:
        return NestTarget.from_dict(json.load(f))


def _write_binding(local_nest: str, target: NestTarget) -> str:
    os.makedirs(local_nest, exist_ok=True)
    path = os.path.join(local_nest, BINDING_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(target.to_dict(), f, indent=2, sort_keys=True)
    return path


# ---- subcommands -----------------------------------------------------------

def nest_inspect(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 1:
        print("usage: python -m mantle nest inspect github:OWNER/REPO [--transport=fake]")
        return 2
    target = parse_location(args[0])
    if target.kind != "github":
        print("nest inspect requires a github:OWNER/REPO target")
        return 1
    tr = transport or _load_transport(flags)
    status = tr.inspect(target)
    print("repository        : %s" % status.full_name)
    print("numeric id        : %s" % status.repo_id)
    print("visibility        : %s" % status.visibility)
    print("state branch      : %s" % status.state_branch)
    print("head commit       : %s" % (status.head_commit or "(none)"))
    print("manifest present  : %s" % status.manifest_present)
    return 0


def nest_connect(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 2:
        print("usage: python -m mantle nest connect LOCAL_NEST github:OWNER/REPO "
              "--auth=AUTH.json")
        return 2
    local_nest, locator = args
    target = parse_location(locator)
    if target.kind != "github":
        print("nest connect requires a github:OWNER/REPO target")
        return 1
    tr = transport or _load_transport(flags)
    resolved = tr.resolve_target(target) if hasattr(tr, "resolve_target") else target
    path = _write_binding(local_nest, resolved)
    print("bound %s -> github:%s/%s (id %s)" % (local_nest, resolved.owner,
                                                 resolved.repository, resolved.repo_id))
    print("binding file: %s" % path)
    return 0


def nest_pull(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 1:
        print("usage: python -m mantle nest pull github:OWNER/REPO --out=LOCAL_DIR")
        return 2
    target = parse_location(args[0])
    dest = str(flags.get("--out") or ".")
    tr = transport or _load_transport(flags)
    prov = _load_envelope(flags)
    os.makedirs(dest, exist_ok=True)
    from .github_runtime import full_pull

    outcome = full_pull(tr, target, dest, prov)
    print("pulled %s -> %s (envelope opened: %s, manifest match: %s)"
          % (args[0], dest, outcome.hydration.opened_envelope,
             outcome.hydration.manifests_match))
    return 0


def nest_push(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 2:
        print("usage: python -m mantle nest push LOCAL_NEST github:OWNER/REPO "
              "--auth=AUTH.json")
        return 2
    local_nest, locator = args
    tr = transport or _load_transport(flags)
    target = tr.resolve_target(parse_location(locator)) if hasattr(tr, "resolve_target") \
        else parse_location(locator)
    prov = _load_envelope(flags)
    status = tr.inspect(target)
    expected_parent = status.head_commit
    from .github_runtime import full_publish

    try:
        outcome = full_publish(tr, target, local_nest, prov,
                               expected_parent=expected_parent,
                               author="mantle-operator", reason="push")
    except NestConflict as e:
        print("CONFLICT (%s): state-branch moved; fetch and reconcile, do not force"
              % e)
        return 1
    print("published checkpoint (tx %s, commit %s)" % (outcome.receipt.transaction_id,
                                                       outcome.receipt.commit[:12]))
    return 0


def nest_sync(argv, *, transport=None):
    args, flags = _split_flags(argv)
    # sync requires an existing binding in a local nest OR a github target
    local_nest = str(flags.get("--nest") or ".")
    tr = transport or _load_transport(flags)
    if args:
        target = parse_location(args[0])
    else:
        target = _read_binding(local_nest)
    status = tr.inspect(target)
    print("sync: %s" % target.full_name)
    print("  state branch : %s" % status.state_branch)
    print("  head commit  : %s" % (status.head_commit or "(none)"))
    print("  manifest     : %s" % ("present" if status.manifest_present else "absent"))
    print("  manifest hash: %s" % (status.manifest_hash or "-"))
    if status.head_commit:
        rec = tr.reconcile(target, _head_transaction(tr, target))
        print("  reconcile    : completed=%s request_verified=%s tree_matches=%s"
              % (rec.completed, rec.request_verified, rec.tree_matches))
    return 0


def _head_transaction(tr, target):
    # best-effort: derive the head transaction id from a materialization receipt
    import tempfile as _tf

    with _tf.TemporaryDirectory() as td:
        try:
            return tr.materialize(target, td).transaction_id
        except Exception:  # noqa: BLE001
            return ""


def nest_install_template(argv, *, transport=None):
    """Copy an inert workflow template into .github/workflows/ (EXPLICIT only).

    Templates are never written automatically; this operator command is the only
    path, keeping GitHub Actions inert until the operator explicitly adopts them.
    """
    args, flags = _split_flags(argv)
    if len(args) != 1:
        print("usage: python -m mantle nest install-template audit|heartbeat [--out=DIR]")
        return 2
    name = args[0]
    src = os.path.join(_ASSETS_WORKFLOWS, "mantle-%s.yml" % name)
    if not os.path.isfile(src):
        print("unknown template %r (available: audit, heartbeat)" % name)
        return 1
    out_dir = str(flags.get("--out") or os.path.join(_REPO_ROOT, ".github", "workflows"))
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, "mantle-%s.yml" % name)
    import shutil

    with open(src, "rb") as f:
        data = f.read()
    with open(dest, "wb") as f:
        f.write(data)
    print("installed template %s -> %s" % (name, dest))
    print("note: review permissions and SHA pins before relying on the workflow.")
    return 0


def nest_doctor(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 1:
        print("usage: python -m mantle nest doctor github:OWNER/REPO")
        return 2
    target = parse_location(args[0])
    tr = transport or _load_transport(flags)
    status = tr.inspect(target)
    print("NEST DOCTOR (github:%s/%s)" % (target.owner, target.repository))
    checks = [
        ("repository is private", status.visibility == "private",
         "enforced" if status.visibility == "private" else "detected"),
        ("numeric repo id resolved", bool(status.repo_id), "enforced"),
        ("state branch exists", bool(status.head_commit), "detected"),
        ("manifest present", status.manifest_present, "detected"),
        ("force pushes blocked (ruleset)", False, "unavailable"),
        ("Pages disabled for NEST repo", False, "unavailable"),
        ("Actions default token read-only", None, "detected"),
    ]
    ok = True
    for name, passed, ctrl in checks:
        verdict = "PASS" if passed else ("UNKNOWN" if passed is None else "FAIL")
        print("  [%s] %-38s (%s)" % (verdict, name, ctrl))
        if passed is False:
            ok = False
    print("plan-dependent controls reported as enforced/detected/unavailable.")
    return 0 if ok else 1


def nest_disconnect(argv, *, transport=None):
    args, flags = _split_flags(argv)
    if len(args) != 1:
        print("usage: python -m mantle nest disconnect github:OWNER/REPO "
              "[--preserve-remote]")
        return 2
    local_nest = str(flags.get("--nest") or ".")
    path = os.path.join(local_nest, BINDING_FILE)
    if os.path.isfile(path):
        os.remove(path)
        print("removed binding %s" % path)
    else:
        print("no binding to remove in %s" % local_nest)
    if not flags.get("--preserve-remote"):
        print("note: remote NEST preserved; use --preserve-remote explicitly to keep it.")
    return 0


# ---- dispatcher ------------------------------------------------------------

def _split_flags(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a.split("=")[0]: (a.split("=", 1)[1] if "=" in a else True)
             for a in argv if a.startswith("--")}
    return args, flags


_SUBCOMMANDS = {
    "inspect": nest_inspect,
    "connect": nest_connect,
    "pull": nest_pull,
    "push": nest_push,
    "sync": nest_sync,
    "doctor": nest_doctor,
    "disconnect": nest_disconnect,
    "install-template": nest_install_template,
}


def main(argv, *, transport=None) -> int:
    if not argv:
        print("usage: python -m mantle nest <inspect|connect|pull|push|sync|doctor|"
              "disconnect|install-template> ...")
        return 2
    sub = argv[0]
    handler = _SUBCOMMANDS.get(sub)
    if handler is None:
        print("unknown nest subcommand %r" % sub)
        return 2
    return handler(argv[1:], transport=transport)
