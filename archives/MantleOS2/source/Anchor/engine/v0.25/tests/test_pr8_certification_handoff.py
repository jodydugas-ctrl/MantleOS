from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scan.inventory import git_blob_sha1
from scan.release import (
    CERTIFICATION_MANIFEST,
    CERTIFICATION_RECEIPT,
    certify_manifest,
    certify_specimen,
    verify_certification,
    write_package_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "qualification_sample"


class CertificationHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Certification intentionally verifies the exact working release tree.
        write_package_manifest(ROOT)

    def test_certify_seals_llm_disabled_agent_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out = base / "cert"
            bundle = base / "handoff.zip"
            result = certify_specimen(ROOT, FIXTURE, out, specimen_id="cert-fixture", bundle_path=bundle)
            self.assertEqual(result["state"], "PASS")
            receipt = json.loads((out / CERTIFICATION_RECEIPT).read_text(encoding="utf-8"))
            self.assertEqual(receipt["state"], "PASS")
            self.assertEqual(receipt["llm_environment"], "DISABLED")
            self.assertEqual(receipt["mechanical_health"]["queries_passed"], 12)
            self.assertEqual(receipt["mechanical_health"]["queries_required"], 12)
            self.assertEqual(receipt["specimen"]["fingerprint"]["kind"], "scan-ledger-sha256")
            self.assertTrue((out / CERTIFICATION_MANIFEST).is_file())
            self.assertEqual(verify_certification(out)["state"], "PASS")
            self.assertTrue(bundle.is_file())
            with zipfile.ZipFile(bundle) as zf:
                names = set(zf.namelist())
            self.assertIn(CERTIFICATION_RECEIPT, names)
            self.assertIn(CERTIFICATION_MANIFEST, names)
            self.assertIn("scan/scan_index.sqlite", names)

    def test_certification_verifier_detects_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cert"
            result = certify_specimen(ROOT, FIXTURE, out, specimen_id="tamper-fixture")
            self.assertEqual(result["state"], "PASS")
            target = out / "scan" / "stage1_summary.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nTAMPER\n", encoding="utf-8")
            check = verify_certification(out)
            self.assertEqual(check["state"], "FAIL")
            self.assertTrue(any(x["kind"] == "hash_mismatch" for x in check["issues"]))

    def test_budget_stop_is_explicit_in_receipt_not_hidden(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cert"
            result = certify_specimen(ROOT, FIXTURE, out, specimen_id="bounded-fixture", max_nodes=1)
            self.assertEqual(result["state"], "PASS")
            receipt = json.loads((out / CERTIFICATION_RECEIPT).read_text(encoding="utf-8"))
            self.assertEqual(receipt["coverage"]["execution_state"], "PARTIAL")
            self.assertTrue(receipt["coverage"]["budget_triggered"])
            self.assertTrue(str(receipt["coverage"]["budget_reason"]).startswith("RESOURCE_LIMIT"))
            self.assertIn("not a claim of complete understanding", receipt["meaning"])
            self.assertEqual(verify_certification(out)["state"], "PASS")

    def test_manifest_certification_preserves_provider_identity(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            content = base / "content"
            content.mkdir()
            text = 'int main(){ return 0; }\n'
            (content / "main.cpp").write_text(text, encoding="utf-8")
            manifest = base / "source_manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {
                    "specimen_id": "owner/repo@deadbeef",
                    "provider": "github",
                    "repository": "owner/repo",
                    "commit_sha": "deadbeef",
                    "tree_sha": "tree123",
                },
                "files": [{
                    "path": "main.cpp",
                    "size": len(text.encode("utf-8")),
                    "sha": git_blob_sha1(text.encode("utf-8")),
                    "type": "blob",
                }],
            }), encoding="utf-8")
            out = base / "cert"
            result = certify_manifest(ROOT, manifest, out, content_root=content, specimen_id="owner/repo@deadbeef")
            self.assertEqual(result["state"], "PASS")
            receipt = json.loads((out / CERTIFICATION_RECEIPT).read_text(encoding="utf-8"))
            self.assertEqual(receipt["specimen"]["acquisition_mode"], "manifest")
            self.assertEqual(receipt["specimen"]["provider"], "github")
            self.assertEqual(receipt["specimen"]["repository"], "owner/repo")
            self.assertEqual(receipt["specimen"]["commit_sha"], "deadbeef")
            self.assertEqual(receipt["specimen"]["tree_sha"], "tree123")
            self.assertEqual(receipt["specimen"]["fingerprint"]["value"], "tree123")
            self.assertEqual(verify_certification(out)["state"], "PASS")

    def test_manifest_revision_populates_commit_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            content = base / "content"
            content.mkdir()
            data = b"int main(){ return 0; }\n"
            (content / "main.cpp").write_bytes(data)
            commit = "f" * 40
            manifest = base / "source_manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {
                    "specimen_id": f"owner/repo@{commit}",
                    "provider": "github",
                    "repository": "owner/repo",
                    "revision": commit,
                    "tree_sha": "e" * 40,
                },
                "files": [{
                    "path": "main.cpp",
                    "size": len(data),
                    "sha": git_blob_sha1(data),
                    "provider_digest_algorithm": "git-object-sha1",
                    "type": "blob",
                }],
            }), encoding="utf-8")

            out = base / "cert"
            result = certify_manifest(ROOT, manifest, out, content_root=content)
            self.assertEqual(result["state"], "PASS")
            receipt = json.loads((out / CERTIFICATION_RECEIPT).read_text(encoding="utf-8"))
            self.assertEqual(receipt["specimen"]["specimen_id"], f"owner/repo@{commit}")
            self.assertEqual(receipt["specimen"]["commit_sha"], commit)
            machine = json.loads((out / "scan" / "machine_body_map.json").read_text(encoding="utf-8"))
            self.assertEqual(machine["specimen"]["commit_sha"], commit)


if __name__ == "__main__":
    unittest.main()
