"""Focused cache-first tests for the Brand Connect catalog snapshot script."""

from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from modules.brandconnect.brandconnect_product_catalog import (
    CATALOG_REUSE_POLICY,
    load_cached_brandconnect_catalog,
)
from scripts import save_brandconnect_catalog_snapshot as saver


def _snapshot(product_id: str, name: str) -> dict:
    return {
        "source": "owner_authorized_ui_snapshot",
        "captured_at": "2026-07-17T17:00:00+09:00",
        "products": [{"product_id": product_id, "name": name}],
    }


class BrandConnectCatalogCacheTest(unittest.TestCase):
    def test_loader_is_cache_only_and_reports_missing_without_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            result = load_cached_brandconnect_catalog(Path(directory) / "missing.json")
        self.assertFalse(result["complete"])
        self.assertFalse(result["cache_hit"])
        self.assertFalse(result["refresh_requested"])
        self.assertFalse(result["network_used"])
        self.assertEqual(result["catalog_reuse_policy"], CATALOG_REUSE_POLICY)

    def test_existing_snapshot_is_reused_until_refresh_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "catalog.json"
            with patch.object(saver, "OUTPUT", output), patch.object(
                saver.sys, "stdin", io.StringIO(json.dumps(_snapshot("P-1", "첫 상품")))
            ):
                self.assertEqual(saver.main([]), 0)
            first_bytes = output.read_bytes()

            with patch.object(saver, "OUTPUT", output), patch.object(
                saver.sys, "stdin", io.StringIO(json.dumps(_snapshot("P-2", "교체 시도")))
            ):
                self.assertEqual(saver.main([]), 0)
            self.assertEqual(output.read_bytes(), first_bytes)
            self.assertEqual(load_cached_brandconnect_catalog(output)["products"][0]["product_id"], "P-1")

            with patch.object(saver, "OUTPUT", output), patch.object(
                saver.sys, "stdin", io.StringIO(json.dumps(_snapshot("P-2", "명시적 교체")))
            ):
                self.assertEqual(saver.main(["--refresh"]), 0)
            refreshed = load_cached_brandconnect_catalog(output)
            self.assertTrue(refreshed["cache_hit"])
            self.assertEqual(refreshed["products"][0]["product_id"], "P-2")


if __name__ == "__main__":
    unittest.main()
