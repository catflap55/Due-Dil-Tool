"""Resolve application data directory (dev vs PyInstaller bundle)."""

from __future__ import annotations

import sys
from pathlib import Path

from appdirs import user_data_dir


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def resource_base() -> Path:
    """Directory containing bundled web assets (read-only when frozen)."""

    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(".").resolve()))
    return Path(__file__).resolve().parent.parent.parent


def user_app_data_dir(app_name: str = "DueDiligenceTool") -> Path:
    """Writable user data dir for SQLite and exports."""

    if is_frozen():
        root = Path(user_data_dir(app_name, roaming=False))
    else:
        root = resource_base() / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def database_path(app_name: str = "DueDiligenceTool") -> Path:
    return user_app_data_dir(app_name) / "duedil.sqlite3"


def exports_dir(app_name: str = "DueDiligenceTool") -> Path:
    d = user_app_data_dir(app_name) / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d
