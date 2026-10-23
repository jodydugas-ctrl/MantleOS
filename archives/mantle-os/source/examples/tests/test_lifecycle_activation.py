#!/usr/bin/env python3
"""External activation authorization and transaction invariants."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mantle.graft import GraftError, apply_artifact
from mantle.hatchery import HatchError, hatch
from mantle.lifecycle import (LifecycleAction, LifecycleAuthorization,
                              LifecycleAuthorizationError, begin_transaction)


ROOT = Path(__file__).resolve().parents[2]
GERM = ROOT / "examples" / "eggs" / "greeter.json"


class LifecycleActivationTest(unittest.TestCase):
    def test_hatch_requires_exact_authorization_before_target_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nest"
            with self.assertRaises(HatchError):
                hatch(str(GERM), out_dir=str(target), warmup_beats=0)
            self.assertFalse(target.exists())

            wrong = LifecycleAuthorization.issue(LifecycleAction.GRAFT, str(GERM), str(target))
            with self.assertRaises(HatchError):
                hatch(str(GERM), out_dir=str(target), warmup_beats=0, authorization=wrong)
            self.assertFalse(target.exists())

            expired = replace(
                LifecycleAuthorization.issue(LifecycleAction.HATCH, str(GERM), str(target)),
                expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            )
            with self.assertRaises(HatchError):
                hatch(str(GERM), out_dir=str(target), warmup_beats=0, authorization=expired)
            self.assertFalse(target.exists())

    def test_hatch_promotes_atomically_and_replay_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nest"
            auth = LifecycleAuthorization.issue(LifecycleAction.HATCH, str(GERM), str(target))
            result = hatch(str(GERM), out_dir=str(target), warmup_beats=0,
                           authorization=auth)
            self.assertTrue(result["report"]["certified"])
            self.assertTrue((target / "lifecycle_journal.json").is_file())
            self.assertEqual(result["report"]["lifecycle"]["result"], "pass")

            replay_target = Path(tmp) / "replay"
            replay = LifecycleAuthorization.issue(
                LifecycleAction.HATCH, str(GERM), str(replay_target)
            )
            transaction = begin_transaction(
                replay, LifecycleAction.HATCH, str(GERM), str(replay_target)
            )
            transaction.interrupt("test")
            with self.assertRaises(LifecycleAuthorizationError):
                begin_transaction(replay, LifecycleAction.HATCH, str(GERM), str(replay_target))
            self.assertFalse(replay_target.exists())

    def test_graft_external_artifact_uses_authorized_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host = root / "host"
            host.mkdir()
            (host / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            artifact = root / "graft.json"
            artifact.write_text(json.dumps({
                "graft_format": "mantle-graft-egg-v1",
                "identity": {"name": "Grafted.AppAI"},
                "host": "synthetic-host",
                "bands": [], "hooks": [],
            }), encoding="utf-8")
            workspace = root / "workspace"
            workspace.mkdir()
            target = workspace / host.name
            auth = LifecycleAuthorization.issue(
                LifecycleAction.GRAFT, str(artifact), str(target)
            )
            result = apply_artifact(
                str(artifact), str(host), workspace=str(workspace),
                authorization=auth, starter_credits=1,
            )
            self.assertTrue(result["report"]["original_unchanged"])
            self.assertTrue((target / ".mantle" / "organism.json").is_file())
            self.assertTrue((target / "graft_report.json").is_file())
            self.assertEqual((host / "app.py").read_text(encoding="utf-8"),
                             "def run():\n    return 1\n")

    def test_graft_refuses_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); host = root / "host"; host.mkdir()
            outside = root / "outside.txt"; outside.write_text("secret", encoding="utf-8")
            try:
                os.symlink(outside, host / "escape.txt")
            except OSError:
                self.skipTest("symlink creation is unavailable on this Windows profile")
            artifact = root / "graft.json"
            artifact.write_text(json.dumps({
                "graft_format": "mantle-graft-egg-v1",
                "identity": {"name": "Grafted.AppAI"}, "host": "synthetic",
            }), encoding="utf-8")
            workspace = root / "workspace"; workspace.mkdir()
            target = workspace / "host"
            auth = LifecycleAuthorization.issue(
                LifecycleAction.GRAFT, str(artifact), str(target)
            )
            with self.assertRaises(GraftError):
                apply_artifact(str(artifact), str(host), workspace=str(workspace),
                               authorization=auth)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
