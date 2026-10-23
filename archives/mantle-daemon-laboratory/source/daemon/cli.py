from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .body import Body
from .constitution import validate
from .development import validate_registry
from .github_actions import ActionsContext
from .git_repo import GitRepo
from .heart import Heart
from .receipt import verify_receipts
from .runtime import run_incarnations
from .stack import Stack


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="mantle-daemon")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "verify", "heartbeat"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=".")
        if name == "heartbeat":
            p.add_argument("--beat-id")
    p = sub.add_parser("incarnation")
    p.add_argument("--root", default=".")
    p.add_argument("--count", type=int, default=1)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "init":
        Stack.bootstrap(root)
        GitRepo(root).init_birth()
        print(json.dumps({"status": "born", "head": GitRepo(root).head(), "stack": Stack(root).fingerprint()}))
        return 0
    if args.command == "verify":
        problems = Stack(root).verify()
        problems += validate(root)
        problems += validate_registry(root)
        problems += verify_receipts(root)
        if problems:
            print(json.dumps({"status": "failed", "problems": problems}, indent=2))
            return 1
        print(json.dumps({"status": "verified", "stack": Stack(root).fingerprint()}))
        return 0
    if args.command == "heartbeat":
        in_actions = str(os.environ.get("GITHUB_ACTIONS", "")).lower() == "true"
        context = ActionsContext.from_environment()
        guard = (lambda: context.write_enabled) if in_actions else None
        print(json.dumps(Heart(root, checkpoint_guard=guard).beat(beat_id=args.beat_id), indent=2, sort_keys=True))
        return 0
    receipts = run_incarnations(root, args.count)
    print(json.dumps({"status": "continuous", "count": len(receipts),
                      "head": GitRepo(root).head(), "stack": Stack(root).fingerprint()}, indent=2))
    return 0
