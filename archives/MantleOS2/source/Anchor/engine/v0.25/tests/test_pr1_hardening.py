from __future__ import annotations

from base64 import b64encode
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from scan.acquire_github import API_ROOT, GitHubAcquirer, git_blob_sha1
from scan.engine import ScanEngine
from scan.inventory import _stat_identity


class FakeTransport:
    def __init__(self, payloads):
        self.payloads = dict(payloads)
        self.calls: list[str] = []

    def get_json(self, url: str):
        self.calls.append(url)
        if url not in self.payloads:
            raise AssertionError(f"unexpected URL: {url}")
        return self.payloads[url]


class LocalInventoryHardeningTests(unittest.TestCase):
    def test_fresh_unchanged_scans_emit_byte_identical_projections(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "App.cpp").write_text(
                'class App { public: void save(); int state; };\n'
                'void App::save(){ state = 1; }\n',
                encoding="utf-8",
            )
            first = td / "first"
            second = td / "second"
            ScanEngine().scan(specimen, first, "deterministic@example")
            ScanEngine().scan(specimen, second, "deterministic@example")

            projections = [
                "machine_body_map.json",
                "evidence_graph.json",
                "evidence_catalog.json",
                "completeness_vector.json",
                "integrity_report.json",
                "surface_closure.json",
                "effect_closure.json",
                "nest_capability_map.json",
                "projection_manifest.json",
                "stage1_summary.md",
            ]
            for name in projections:
                self.assertEqual(
                    (first / name).read_bytes(),
                    (second / name).read_bytes(),
                    f"projection differs across fresh unchanged scans: {name}",
                )

    def test_windows_stat_identity_ignores_incomparable_ctime(self):
        common = {
            "st_dev": 12,
            "st_ino": 34,
            "st_size": 56,
            "st_mtime_ns": 78,
        }
        path_stat = SimpleNamespace(**common, st_ctime_ns=90)
        descriptor_stat = SimpleNamespace(**common, st_ctime_ns=91)

        self.assertEqual(
            _stat_identity(path_stat, platform_name="nt"),
            _stat_identity(descriptor_stat, platform_name="nt"),
        )
        self.assertNotEqual(
            _stat_identity(path_stat, platform_name="posix"),
            _stat_identity(descriptor_stat, platform_name="posix"),
        )

    def test_local_symlink_is_accounted_but_never_followed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            outside = td / "outside.cpp"
            outside.write_text('QAction *secret = new QAction("outside");\n', encoding="utf-8")
            try:
                os.symlink(outside, specimen / "leak.cpp")
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            summary = ScanEngine().scan(specimen, td / "out", "symlink@example")
            rec = next(f for f in summary["files"] if f["path"] == "leak.cpp")
            self.assertEqual(rec["acquisition_state"], "SYMLINK_REFERENCE")
            self.assertEqual(rec["content_available"], 0)
            self.assertFalse(any(n["path"] == "leak.cpp" for n in summary["nodes"]))
            self.assertEqual(summary["inventory"]["content_unavailable_file_count"], 1)

    def test_symlink_scan_root_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            real = td / "real"
            real.mkdir()
            (real / "x.cpp").write_text("void f(){}\n", encoding="utf-8")
            alias = td / "alias"
            try:
                os.symlink(real, alias, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "root must not be a symlink"):
                ScanEngine().scan(alias, td / "out", "root-symlink@example")

    def test_oversized_local_file_is_explicit_resource_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            specimen = td / "specimen"
            specimen.mkdir()
            (specimen / "large.cpp").write_bytes(b"A" * 65)
            summary = ScanEngine(max_file_bytes=64).scan(specimen, td / "out", "limit@example")
            rec = summary["files"][0]
            self.assertEqual(rec["acquisition_state"], "RESOURCE_LIMIT")
            self.assertEqual(rec["coverage"], "BLOCKED")
            self.assertEqual(rec["content_available"], 0)
            self.assertEqual(summary["extraction"]["node_count"], 0)

    def test_manifest_parent_traversal_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            manifest = td / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {"specimen_id": "owner/repo@pin", "provider": "github"},
                "files": [{"path": "../escape.cpp", "size": 1, "type": "blob"}],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe manifest path"):
                ScanEngine().scan_manifest(manifest, td / "out", td)

    def test_manifest_local_symlink_is_blocked_even_when_target_matches_digest(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            target = td / "real.cpp"
            data = b"void f(){}\n"
            target.write_bytes(data)
            content = td / "content"
            content.mkdir()
            try:
                os.symlink(target, content / "x.cpp")
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            manifest = td / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {"specimen_id": "owner/repo@pin", "provider": "github", "tree_sha": "a" * 40},
                "files": [{
                    "path": "x.cpp", "size": len(data), "sha": git_blob_sha1(data),
                    "provider_digest_algorithm": "git-object-sha1", "type": "blob", "mode": "100644",
                }],
            }), encoding="utf-8")
            summary = ScanEngine().scan_manifest(manifest, td / "out", content)
            rec = summary["files"][0]
            self.assertEqual(rec["acquisition_state"], "SYMLINK_REFERENCE")
            self.assertEqual(rec["coverage"], "BLOCKED")
            self.assertEqual(rec["content_available"], 0)
            self.assertEqual(summary["extraction"]["node_count"], 0)


class ProviderResourceLimitTests(unittest.TestCase):
    def test_declared_oversized_github_blob_is_not_fetched(self):
        repo = "owner/repo"
        ref = "pin"
        commit_sha = "1" * 40
        tree_sha = "2" * 40
        blob_sha = "3" * 40
        base = f"{API_ROOT}/repos/owner/repo"
        transport = FakeTransport({
            f"{base}/commits/{ref}": {"sha": commit_sha, "commit": {"tree": {"sha": tree_sha}}},
            f"{base}/git/trees/{tree_sha}?recursive=1": {
                "sha": tree_sha, "truncated": False,
                "tree": [{"path": "huge.bin", "mode": "100644", "type": "blob", "sha": blob_sha, "size": 1025}],
            },
        })
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = GitHubAcquirer(transport=transport, max_workers=1, max_blob_bytes=1024).acquire(repo, ref, out)
            self.assertEqual(report["materialized_file_count"], 0)
            self.assertEqual(report["blocked_file_count"], 1)
            self.assertFalse(report["complete_for_provider_blobs"])
            self.assertFalse(any("/git/blobs/" in call for call in transport.calls))
            item = json.loads((out / "source_manifest.json").read_text())["files"][0]
            self.assertEqual(item["acquisition_state"], "RESOURCE_LIMIT")
            self.assertEqual(item["attributes"]["max_blob_bytes"], 1024)


if __name__ == "__main__":
    unittest.main()
