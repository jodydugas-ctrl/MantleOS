import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = PROJECT_ROOT / "tools.py"


def load_tools():
    name = "hermes_mantle_containment_tools"
    spec = importlib.util.spec_from_file_location(name, TOOLS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ContainmentAuditTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(
            prefix="hermes-containment-test-"
        )
        self.scope_root = Path(self.sandbox.name)
        self.storage_root = self.scope_root / "resident-storage"
        self.sentinel = self.scope_root / "outside-sentinel.txt"
        self.sentinel.write_text("host-owned and unchanged", encoding="utf-8")

        sys.path.insert(0, str(PROJECT_ROOT))
        from mantle_addon.config import ResidentConfig
        from mantle_addon.runtime import ResidentRuntime

        self.config = ResidentConfig.from_mapping(
            {"storage_root": str(self.storage_root)}
        )
        self.runtime = ResidentRuntime(self.config, profile_id="default")
        self.tools = load_tools()

    def tearDown(self):
        if sys.path and sys.path[0] == str(PROJECT_ROOT):
            sys.path.pop(0)
        self.sandbox.cleanup()

    def _run(self, schema):
        from mantle_addon.containment import run_containment

        return run_containment(
            self.runtime,
            schema,
            lambda args: self.tools.mantle_record_discovery(
                args, runtime=self.runtime
            ),
            scope_root=self.scope_root,
        )

    def test_all_eleven_containment_requirements_pass(self):
        from schemas import MANTLE_RECORD_DISCOVERY

        receipt = self._run(MANTLE_RECORD_DISCOVERY)

        self.assertTrue(receipt.passed, receipt.to_json())
        self.assertEqual([], receipt.fails)
        self.assertEqual(
            [f"C-{number:02d}" for number in range(1, 12)],
            [row.code for row in receipt.rows],
        )
        self.assertTrue(all(row.result == "PASS" for row in receipt.rows))
        self.assertEqual(
            "host-owned and unchanged",
            self.sentinel.read_text(encoding="utf-8"),
        )
        serialized = json.loads(receipt.to_json())
        self.assertTrue(serialized["passed"])
        self.assertEqual(11, len(serialized["rows"]))

    def test_schema_drift_is_detected_without_false_pass(self):
        from schemas import MANTLE_RECORD_DISCOVERY

        tampered = copy.deepcopy(MANTLE_RECORD_DISCOVERY)
        tampered["parameters"]["properties"]["idea"]["maxLength"] = 9999

        receipt = self._run(tampered)

        self.assertFalse(receipt.passed)
        self.assertIn("C-01", receipt.fails)
        row = next(row for row in receipt.rows if row.code == "C-01")
        self.assertEqual("FAIL", row.result)


if __name__ == "__main__":
    unittest.main()
