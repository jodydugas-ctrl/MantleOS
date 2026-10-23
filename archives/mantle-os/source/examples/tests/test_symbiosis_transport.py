"""Focused tests for transport metadata across the symbiosis metering seam."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from mantle.mind.context import ProviderCapabilities
from mantle.mind.context.strategy import model_info_from_transport
from mantle.symbiosis import metered


class CacheAwareModel:
    provider = "test-provider"
    model_name = "test/model"
    context_window_tokens = 128_000
    reserved_output_tokens = 4_096
    capabilities = ProviderCapabilities(
        prefix_cache=True,
        reports_cached_tokens=True,
    )

    def __init__(self):
        self.last_usage = None
        self.last_cache = None

    def __call__(self, prompt):
        self.last_usage = {
            "prompt_tokens": 100,
            "cached_tokens": 80,
            "cache_write_tokens": 20,
        }
        self.last_cache = {"cached_tokens": 80, "cache_write_tokens": 20}
        return "ok:%s" % prompt


class SymbiosisTransportTests(unittest.TestCase):
    def test_meter_preserves_cache_capability_and_receipts(self):
        model = CacheAwareModel()
        wrapped = metered(model, object())

        info = model_info_from_transport(wrapped)
        self.assertEqual(info.provider, "test-provider")
        self.assertEqual(info.model, "test/model")
        self.assertEqual(info.context_window_tokens, 128_000)
        self.assertEqual(info.reserved_output_tokens, 4_096)
        self.assertTrue(info.capabilities.prefix_cache)
        self.assertTrue(info.capabilities.reports_cached_tokens)

        with patch("mantle.symbiosis.spend", return_value=True):
            self.assertEqual(wrapped("hello"), "ok:hello")

        self.assertEqual(wrapped.last_usage["cached_tokens"], 80)
        self.assertEqual(wrapped.last_usage["cache_write_tokens"], 20)
        self.assertEqual(wrapped.last_cache["cached_tokens"], 80)


if __name__ == "__main__":
    unittest.main()
