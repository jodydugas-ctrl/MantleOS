from __future__ import annotations

import unittest
from pathlib import Path

from daemon.development import validate_registry


PROJECT = Path(__file__).resolve().parents[1]


class DevelopmentRegistryTest(unittest.TestCase):
    def test_current_organ_registry_is_hashed_and_tested(self):
        self.assertEqual(validate_registry(PROJECT), [])

