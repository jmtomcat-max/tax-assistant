# -*- coding: utf-8 -*-
"""Unit tests for authentication and data path abstraction."""

import os
import unittest
from unittest.mock import patch
import config
from components.auth import is_authenticated, get_current_user


class TestAuthAndConfig(unittest.TestCase):
    def test_default_auth_users(self):
        users = config.get_auth_users()
        self.assertIn("admin", users)
        self.assertIn("user", users)
        self.assertEqual(users["admin"]["role"], "admin")
        self.assertEqual(users["user"]["role"], "viewer")

    def test_verify_user_credentials_success(self):
        valid, info = config.verify_user_credentials("admin", "cj_tax_admin_2026!")
        self.assertTrue(valid)
        self.assertIsNotNone(info)
        self.assertEqual(info["id"], "admin")
        self.assertEqual(info["role"], "admin")

        valid_user, info_user = config.verify_user_credentials("user", "cj_freshway_2026!")
        self.assertTrue(valid_user)
        self.assertEqual(info_user["id"], "user")

    def test_verify_user_credentials_failure(self):
        valid, info = config.verify_user_credentials("admin", "wrong_password")
        self.assertFalse(valid)
        self.assertIsNone(info)

        valid_none, _ = config.verify_user_credentials("nonexistent_user", "password")
        self.assertFalse(valid_none)

        valid_empty, _ = config.verify_user_credentials("", "")
        self.assertFalse(valid_empty)

    def test_data_path_resolution(self):
        # Default data dir should point to workspace
        data_dir = config.get_data_dir()
        self.assertTrue(os.path.isdir(data_dir))

        # Existing files should resolve to existing paths
        tax_rates_path = config.get_data_file_path("tax_rates.json")
        self.assertTrue(os.path.exists(tax_rates_path))

    @patch("config.is_auth_enabled", return_value=False)
    def test_auth_disabled_mode(self, mock_auth):
        self.assertTrue(is_authenticated())


if __name__ == "__main__":
    unittest.main()
