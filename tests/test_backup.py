# -*- coding: utf-8 -*-
"""Unit tests for backup and restore service."""

import os
import unittest
import zipfile
import io
from services.backup_service import create_backup_zip_bytes, restore_from_backup_zip, get_data_storage_status


class TestBackupService(unittest.TestCase):
    def test_create_backup_zip(self):
        zip_bytes = create_backup_zip_bytes()
        self.assertIsInstance(zip_bytes, bytes)
        self.assertGreater(len(zip_bytes), 0)

        # Verify it's a valid zip file
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            self.assertTrue(len(namelist) > 0)
            self.assertIn("tax_rates.json", namelist)

    def test_get_data_storage_status(self):
        status = get_data_storage_status()
        self.assertIn("tax_rates.json", status)
        self.assertTrue(status["tax_rates.json"]["exists"])

    def test_restore_empty_bytes(self):
        ok, msg = restore_from_backup_zip(b"")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
