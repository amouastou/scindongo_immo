"""Utility helpers for role-based access checks."""

from __future__ import annotations

from typing import Any


def is_admin_user(user: Any) -> bool:
    """Return True when the user has administrative privileges."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return bool(getattr(user, "is_admin_scindongo", False))
