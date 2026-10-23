from __future__ import annotations

from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from scan.acquire_github import API_ROOT, GitHubAcquirer, git_blob_sha1
from scan.engine import ScanEngine
from scan.cli import main as cli_main


class FakeTransport:
    def __init__(self, payloads):
        self.payloads = dict(payloads)
        self.calls = []

    def get_json(self, url):
        self.calls.append(url)
        if url not in self.payloads:
            raise AssertionError(f"unexpected URL: {url}")
        value = self.payloads[url]
        if isinstance(value, Exception):
            raise value
        return value


def blob_payload(data: bytes):
    return {"encoding": "base64", "content": b64encode(data).decode("ascii"), "size": len(data)}


class GitHubAcquisitionTests(unittest.TestCase):
    def test_exact_blobs_are_verified_materialized_and_scannable(self):
        repo = "owner/repo"
        ref = "abc123"
        commit_sha = "1" * 40
        tree_sha = "2" * 40
        cpp = b'#include <QAction>\nvoid f(){ QProcess p; }\n'
        ui = b'<?xml version="1.0"?><ui version="4.0"><widget class="QMainWindow" name="Main"><action name="actionSave"><property name="text"><string>Save</string></property></action></widget></ui>'
        cpp_sha = git_blob_sha1(cpp)
        ui_sha = git_blob_sha1(ui)
        submodule_sha = "3" * 40

        base = f"{API_ROOT}/repos/owner/repo"
        transport = FakeTransport({
            f"{base}/commits/{ref}": {"sha": commit_sha, "commit": {"tree": {"sha": tree_sha}}},
            f"{base}/git/trees/{tree_sha}?recursive=1": {
                "sha": tree_sha,
                "truncated": False,
                "tree": [
                    {"path": "src/main.cpp", "mode": "100644", "type": "blob", "sha": cpp_sha, "size": len(cpp)},
                    {"path": "ui/Main.ui", "mode": "100644", "type": "blob", "sha": ui_sha, "size": len(ui)},
                    {"path": "thirdparty/ext", "mode": "160000", "type": "commit", "sha": submodule_sha},
                ],
            },
            f"{base}/git/blobs/{cpp_sha}": blob_payload(cpp),
            f"{base}/git/blobs/{ui_sha}": blob_payload(ui),
        })

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            acquired = td / "acquired"
            report = GitHubAcquirer(transport=transport, max_workers=2).acquire(repo, ref, acquired)
            self.assertEqual(report["revision"], commit_sha)
            self.assertEqual(report["tree_sha"], tree_sha)
            self.assertEqual(report["materialized_file_count"], 2)
            self.assertEqual(report["blocked_file_count"], 0)
            self.assertEqual(report["external_reference_count"], 1)
            self.assertTrue(report["complete_for_provider_blobs"])
            self.assertFalse(report["all_visible_entries_materialized"])
            self.assertEqual((acquired / "content/src/main.cpp").read_bytes(), cpp)
            self.assertEqual((acquired / "content/ui/Main.ui").read_bytes(), ui)

            manifest = json.loads((acquired / "source_manifest.json").read_text())
            by_path = {x["path"]: x for x in manifest["files"]}
            self.assertTrue(by_path["src/main.cpp"]["verified_provider_digest"])
            self.assertEqual(by_path["src/main.cpp"]["sha256"], sha256(cpp).hexdigest())
            self.assertEqual(by_path["thirdparty/ext"]["acquisition_state"], "EXTERNAL_REFERENCE")

            summary = ScanEngine().scan_manifest(
                acquired / "source_manifest.json", td / "scan", acquired / "content"
            )
            self.assertEqual(summary["schema_version"], "scan-machine-body-map/0.9")
            self.assertEqual(summary["inventory"]["file_count"], 3)
            self.assertEqual(summary["inventory"]["materialized_file_count"], 2)
            self.assertEqual(summary["inventory"]["content_unavailable_file_count"], 1)
            self.assertEqual(summary["inventory"]["metadata_only_file_count"], 0)
            self.assertTrue(any(n["kind"] == "human_surface" and n["name"] == "actionSave" for n in summary["nodes"]))
            self.assertTrue(any(n["kind"] == "nest_boundary" and n["name"] == "subprocess" for n in summary["nodes"]))

    def test_hash_mismatch_is_blocked_and_not_parsed(self):
        correct = b'<?xml version="1.0"?><ui version="4.0"><action name="actionExpected"/></ui>'
        wrong = b'<?xml version="1.0"?><ui version="4.0"><action name="actionWrong"/></ui>'
        expected_git = git_blob_sha1(correct)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            content = td / "content"
            content.mkdir()
            (content / "Main.ui").write_bytes(wrong)
            manifest = td / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {"specimen_id": "owner/repo@pinned", "provider": "github", "tree_sha": "t" * 40},
                "files": [{
                    "path": "Main.ui", "size": len(correct), "sha": expected_git,
                    "provider_digest_algorithm": "git-object-sha1", "type": "blob", "mode": "100644",
                }],
            }))
            summary = ScanEngine().scan_manifest(manifest, td / "scan", content)
            rec = summary["files"][0]
            self.assertEqual(rec["coverage"], "BLOCKED")
            self.assertEqual(rec["acquisition_state"], "HASH_MISMATCH")
            self.assertEqual(rec["content_available"], 0)
            self.assertEqual(summary["extraction"]["node_count"], 0)
            self.assertEqual(summary["inventory"]["content_unavailable_file_count"], 1)

    def test_truncated_recursive_tree_falls_back_to_explicit_walk(self):
        repo = "owner/repo"
        ref = "pin"
        commit_sha = "4" * 40
        root_sha = "5" * 40
        dir_sha = "6" * 40
        data = b"hello\n"
        blob_sha = git_blob_sha1(data)
        base = f"{API_ROOT}/repos/owner/repo"
        transport = FakeTransport({
            f"{base}/commits/{ref}": {"sha": commit_sha, "commit": {"tree": {"sha": root_sha}}},
            f"{base}/git/trees/{root_sha}?recursive=1": {"sha": root_sha, "truncated": True, "tree": []},
            f"{base}/git/trees/{root_sha}": {"sha": root_sha, "tree": [
                {"path": "src", "mode": "040000", "type": "tree", "sha": dir_sha},
            ]},
            f"{base}/git/trees/{dir_sha}": {"sha": dir_sha, "tree": [
                {"path": "note.txt", "mode": "100644", "type": "blob", "sha": blob_sha, "size": len(data)},
            ]},
            f"{base}/git/blobs/{blob_sha}": blob_payload(data),
        })
        with tempfile.TemporaryDirectory() as td:
            report = GitHubAcquirer(transport=transport, max_workers=1).acquire(repo, ref, Path(td))
            self.assertEqual(report["tree_strategy"], "explicit-tree-walk")
            self.assertEqual(report["materialized_file_count"], 1)
            self.assertEqual((Path(td) / "content/src/note.txt").read_bytes(), data)

    def test_provider_blob_mismatch_is_preserved_as_blocked(self):
        repo = "owner/repo"
        ref = "pin"
        commit_sha = "7" * 40
        tree_sha = "8" * 40
        expected_data = b"expected"
        returned_data = b"tampered"
        expected_sha = git_blob_sha1(expected_data)
        base = f"{API_ROOT}/repos/owner/repo"
        transport = FakeTransport({
            f"{base}/commits/{ref}": {"sha": commit_sha, "commit": {"tree": {"sha": tree_sha}}},
            f"{base}/git/trees/{tree_sha}?recursive=1": {"sha": tree_sha, "truncated": False, "tree": [
                {"path": "x.txt", "mode": "100644", "type": "blob", "sha": expected_sha, "size": len(expected_data)},
            ]},
            f"{base}/git/blobs/{expected_sha}": blob_payload(returned_data),
        })
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            report = GitHubAcquirer(transport=transport, max_workers=1).acquire(repo, ref, td)
            self.assertEqual(report["blocked_file_count"], 1)
            self.assertEqual(report["materialized_file_count"], 0)
            self.assertFalse((td / "content/x.txt").exists())
            manifest = json.loads((td / "source_manifest.json").read_text())
            item = manifest["files"][0]
            self.assertEqual(item["acquisition_state"], "BLOCKED")
            self.assertIn("hash mismatch", item["error"].lower())

    def test_cli_transport_failure_is_structured_without_traceback(self):
        class FailingAcquirer:
            def __init__(self, *args, **kwargs):
                pass
            def acquire(self, *args, **kwargs):
                raise RuntimeError("GitHub transport failure: DNS unavailable")

        stderr = StringIO()
        with tempfile.TemporaryDirectory() as td, \
             patch("scan.cli.GitHubAcquirer", FailingAcquirer), \
             redirect_stderr(stderr):
            rc = cli_main([
                "acquire-github", "owner/repo", "--ref", "a" * 40,
                "--out", td,
            ])
        self.assertEqual(rc, 2)
        payload = json.loads(stderr.getvalue())
        self.assertFalse(payload["success"])
        self.assertEqual(payload["stage"], "ACQUIRE")
        self.assertEqual(payload["acquisition_state"], "BLOCKED")
        self.assertEqual(payload["repository"], "owner/repo")
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
