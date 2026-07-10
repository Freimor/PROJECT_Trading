"""Operator password / legacy admin key for protected console actions."""

from __future__ import annotations

import base64
import hmac
import os

_MAX_CREDENTIAL_LEN = 1024
_MAX_PASSWORD_LEN = 256


def operator_password_configured() -> bool:
    return bool(os.environ.get("OPERATOR_PASSWORD", "").strip())


def admin_key_configured() -> bool:
    return bool(os.environ.get("ADMIN_API_KEY", "").strip())


def operator_auth_required() -> bool:
    return operator_password_configured() or admin_key_configured()


def decode_operator_credential(value: str | None) -> str | None:
    """Decode operator password from header (plain or b64: prefix). Never executed as code."""
    if value is None:
        return None
    raw = value.strip()
    if not raw or len(raw) > _MAX_CREDENTIAL_LEN:
        return None
    if raw.startswith("b64:"):
        try:
            decoded = base64.b64decode(raw[4:], validate=True)
            text = decoded.decode("utf-8")
        except Exception:
            return None
    else:
        text = raw
    if not text or len(text) > _MAX_PASSWORD_LEN:
        return None
    if any(ord(ch) < 32 and ch not in ("\t",) for ch in text):
        return None
    return text


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time compare for Unicode credentials (str compare_digest is ASCII-only)."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_operator_auth(
    *,
    password: str | None = None,
    admin_key: str | None = None,
) -> bool:
    expected_pwd = os.environ.get("OPERATOR_PASSWORD", "").strip()
    expected_admin = os.environ.get("ADMIN_API_KEY", "").strip()

    if not expected_pwd and not expected_admin:
        return True

    password = decode_operator_credential(password)

    if expected_admin and admin_key and _safe_compare(admin_key.strip(), expected_admin):
        return True

    if expected_pwd and password and _safe_compare(password, expected_pwd):
        return True

    return False
