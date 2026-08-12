"""Unit tests for security helpers."""

import json
import stat
import tempfile
import unittest
from pathlib import Path

from security_utils import (
    clamp_text,
    deobfuscate_secret,
    load_smtp_password,
    obfuscate_secret,
    open_private_write,
    public_notification_settings,
    restrict_file_permissions,
    sanitize_header_value,
    save_smtp_password,
    validate_date_string,
    validate_email,
    validate_port,
    validate_priority,
    validate_recurrence,
    validate_smtp_host,
)


class SanitizeHeaderTests(unittest.TestCase):
    def test_strips_crlf(self):
        injected = "Task\r\nBcc: attacker@example.com"
        self.assertEqual(sanitize_header_value(injected), "TaskBcc: attacker@example.com")

    def test_none_becomes_empty(self):
        self.assertEqual(sanitize_header_value(None), "")


class ValidationTests(unittest.TestCase):
    def test_priority_whitelist(self):
        self.assertEqual(validate_priority("Now"), "Now")
        self.assertEqual(validate_priority("<script>alert(1)</script>"), "Next")
        self.assertEqual(validate_priority(None), "Next")

    def test_recurrence_whitelist(self):
        self.assertEqual(validate_recurrence("daily"), "daily")
        self.assertIsNone(validate_recurrence(""))
        with self.assertRaises(ValueError):
            validate_recurrence("every-second")

    def test_date_format(self):
        self.assertEqual(validate_date_string("2026-08-12"), "2026-08-12")
        self.assertIsNone(validate_date_string(""))
        with self.assertRaises(ValueError):
            validate_date_string("08/12/2026")
        with self.assertRaises(ValueError):
            validate_date_string("2026-13-40")

    def test_email(self):
        self.assertEqual(validate_email("user@example.com"), "user@example.com")
        self.assertEqual(validate_email(""), "")
        with self.assertRaises(ValueError):
            validate_email("not-an-email", required=True)
        with self.assertRaises(ValueError):
            validate_email("user@example.com\nbcc:evil@example.com")

    def test_smtp_host(self):
        self.assertEqual(validate_smtp_host("smtp.gmail.com"), "smtp.gmail.com")
        self.assertEqual(validate_smtp_host("127.0.0.1"), "127.0.0.1")
        sanitized = validate_smtp_host("smtp.gmail.com\r\n")
        self.assertEqual(sanitized, "smtp.gmail.com")
        with self.assertRaises(ValueError):
            validate_smtp_host("not a host")

    def test_port(self):
        self.assertEqual(validate_port(587), 587)
        with self.assertRaises(ValueError):
            validate_port(0)
        with self.assertRaises(ValueError):
            validate_port(70000)

    def test_clamp_text(self):
        self.assertEqual(clamp_text("hello", 3), "hel")
        self.assertEqual(clamp_text(None, 10), "")


class CredentialStorageTests(unittest.TestCase):
    def test_obfuscate_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            token = obfuscate_secret("app-password-secret", data_dir)
            self.assertNotIn("app-password-secret", token)
            self.assertEqual(deobfuscate_secret(token, data_dir), "app-password-secret")

    def test_tampered_token_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            token = obfuscate_secret("secret", data_dir)
            with self.assertRaises(ValueError):
                deobfuscate_secret(token[:-1] + "A", data_dir)

    def test_password_not_in_public_settings(self):
        public = public_notification_settings({
            "enabled": True,
            "email": "user@example.com",
            "email_password": "super-secret",
        })
        self.assertNotIn("email_password", public)
        self.assertTrue(public["password_set"])
        self.assertNotIn("super-secret", json.dumps(public))

    def test_smtp_password_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_smtp_password("super-secret", data_dir)
            creds = data_dir / ".smtp_credentials"
            self.assertTrue(creds.exists())
            mode = creds.stat().st_mode
            self.assertFalse(mode & stat.S_IROTH)
            self.assertFalse(mode & stat.S_IRGRP)
            self.assertEqual(load_smtp_password(data_dir), "super-secret")
            self.assertNotIn("super-secret", creds.read_text())

    def test_open_private_write_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.json"
            with open_private_write(path) as handle:
                handle.write("[]")
            restrict_file_permissions(path)
            mode = path.stat().st_mode
            self.assertFalse(mode & stat.S_IROTH)
            self.assertFalse(mode & stat.S_IRGRP)


if __name__ == "__main__":
    unittest.main()
