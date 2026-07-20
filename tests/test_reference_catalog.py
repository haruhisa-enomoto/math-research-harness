from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.reference_catalog import audit, refresh_catalog
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


if __name__ == "__main__":
    unittest.main()
