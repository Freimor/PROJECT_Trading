"""Operator password / legacy admin key for protected console actions."""

from __future__ import annotations

import hmac
import os


def operator_password_configured() -> bool:
    return bool(os.environ.get("OPERATOR_PASSWORD", "").strip())


def admin_key_configured() -> bool:
    return bool(os.environ.get("ADMIN_API_KEY", "").strip())


def operator_auth_required() -> bool:
    return operator_password_configured() or admin_key_configured()


def verify_operator_auth(
    *,
    password: str | None = None,
    admin_key: str | None = None,
) -> bool:
    expected_pwd = os.environ.get("OPERATOR_PASSWORD", "").strip()
    expected_admin = os.environ.get("ADMIN_API_KEY", "").strip()

    if not expected_pwd and not expected_admin:
        return True

    if expected_admin and admin_key and hmac.compare_digest(admin_key, expected_admin):
        return True

    if expected_pwd and password and hmac.compare_digest(password, expected_pwd):
        return True

    return False
