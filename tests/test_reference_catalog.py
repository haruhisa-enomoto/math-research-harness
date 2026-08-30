from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.reference_catalog import audit, refresh_catalog, refresh_catalog_items
from tools.reference_utils import sha256


class ReferenceCatalogTests(unittest.TestCase):
    def test_refresh_and_audit_detect_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"
            item = root / "items/papers/sample"
            original = item / "original/paper.pdf"
            original.parent.mkdir(parents=True)
            original.write_bytes(b"sample")
            metadata = {
                "schema_version": 1,
                "id": "paper:sample",
                "kind": "paper",
                "key": "sample",
                "item_path": "items/papers/sample",
                "checked_at": "2026-01-01T00:00:00+00:00",
                "resources": {
                    "pdf": {
                        "path": "items/papers/sample/original/paper.pdf",
                        "sha256": sha256(original),
                    }
                },
            }
            (item / "item.json").write_text(json.dumps(metadata), encoding="utf-8")

            self.assertEqual(refresh_catalog(root)["catalog_items"], 1)
            self.assertEqual(audit(root), {"status": "ok", "items": 1})

            original.write_bytes(b"changed")
            with self.assertRaises(RuntimeError):
                audit(root)

    def test_incremental_update_rebuilds_a_malformed_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"
            selected = root / "items/papers/selected"
            other = root / "items/papers/other"
            for key, item in (("selected", selected), ("other", other)):
                item.mkdir(parents=True)
                (item / "item.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 2,
                            "id": f"paper:{key}",
                            "kind": "paper",
                            "key": key,
                            "item_path": f"items/papers/{key}",
                            "resources": {},
                        }
                    ),
                    encoding="utf-8",
                )
            root.mkdir(exist_ok=True)
            (root / "CATALOG.json").write_text("not json", encoding="utf-8")

            result = refresh_catalog_items(root, [selected])

            self.assertEqual(result["catalog_items"], 2)
            catalog = json.loads((root / "CATALOG.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [item["id"] for item in catalog["items"]],
                ["paper:other", "paper:selected"],
            )


if __name__ == "__main__":
    unittest.main()
