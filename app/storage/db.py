"""SQLite persistence: cache, local API keys, scoring weights.

Keys stay on this computer in data/ (gitignored). They are not encrypted at rest —
protect the machine. Never commit the database file.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.config.defaults import DEFAULT_SCORING_WEIGHTS, default_config_json
from app.storage.paths import database_path


def _params_hash(
    name: str,
    reg: Optional[str],
    country: str,
    modules: Dict[str, bool],
) -> str:
    payload = json.dumps(
        {
            "n": name.strip().lower(),
            "r": (reg or "").strip().upper(),
            "c": country.upper(),
            "m": {k: bool(v) for k, v in sorted(modules.items())},
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Db:
    """Application database."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS api_keys (
                  name TEXT PRIMARY KEY,
                  value_enc TEXT NOT NULL,
                  updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS config_json (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  json TEXT NOT NULL,
                  updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS searches (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  params_hash TEXT NOT NULL,
                  created_at REAL NOT NULL,
                  country TEXT NOT NULL,
                  query_snapshot TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  modules_bitmask INTEGER NOT NULL DEFAULT 0,
                  ttl_seconds INTEGER NOT NULL DEFAULT 86400
                );
                CREATE INDEX IF NOT EXISTS idx_searches_hash ON searches(params_hash);
                CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at);
                """
            )
            row = c.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
            if not row:
                c.execute(
                    "INSERT INTO meta (key, value) VALUES ('schema_version', '2')"
                )
            # Drop leftover admin hash/session from older private builds.
            c.execute("DELETE FROM meta WHERE key IN ('admin_password_hash', 'admin_session')")

            cfg = c.execute("SELECT json FROM config_json WHERE id = 1").fetchone()
            if not cfg:
                now = time.time()
                c.execute(
                    "INSERT INTO config_json (id, json, updated_at) VALUES (1, ?, ?)",
                    (default_config_json(), now),
                )

    def set_api_key(self, name: str, value: str) -> None:
        with self.connect() as c:
            if not (value or "").strip():
                c.execute("DELETE FROM api_keys WHERE name = ?", (name,))
                return
            c.execute(
                """
                INSERT INTO api_keys (name, value_enc, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET value_enc = excluded.value_enc,
                  updated_at = excluded.updated_at
                """,
                (name, value.strip(), time.time()),
            )

    def get_api_key(self, name: str) -> Optional[str]:
        with self.connect() as c:
            row = c.execute(
                "SELECT value_enc FROM api_keys WHERE name = ?", (name,)
            ).fetchone()
            return row[0] if row else None

    def mask_key(self, name: str) -> str:
        v = self.get_api_key(name)
        if not v:
            return ""
        if len(v) <= 6:
            return "••••"
        return v[:2] + "…" + v[-4:]

    def get_config(self) -> Dict[str, Any]:
        with self.connect() as c:
            row = c.execute("SELECT json FROM config_json WHERE id = 1").fetchone()
            if row:
                return json.loads(row[0])
        return json.loads(default_config_json())

    def set_config(self, cfg: Dict[str, Any]) -> None:
        with self.connect() as c:
            c.execute(
                "UPDATE config_json SET json = ?, updated_at = ? WHERE id = 1",
                (json.dumps(cfg, indent=2), time.time()),
            )

    def get_scoring_weights(self) -> Dict[str, float]:
        cfg = self.get_config()
        w = cfg.get("scoring_weights") or {}
        merged = DEFAULT_SCORING_WEIGHTS.copy()
        for k in merged:
            if k in w:
                try:
                    merged[k] = float(w[k])
                except (TypeError, ValueError):
                    pass
        return merged

    def cache_get(
        self,
        *,
        query_name: str,
        registration: Optional[str],
        country: str,
        modules: Dict[str, bool],
        ttl_seconds: int = 86400,
    ) -> Optional[Dict[str, Any]]:
        ph = _params_hash(query_name, registration, country, modules)
        cutoff = time.time() - ttl_seconds
        with self.connect() as c:
            row = c.execute(
                """
                SELECT payload_json, created_at FROM searches
                WHERE params_hash = ? AND created_at >= ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (ph, cutoff),
            ).fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            data["_cache"] = {"hit": True, "created_at": row[1]}
            return data

    def cache_put(
        self,
        *,
        query_name: str,
        registration: Optional[str],
        country: str,
        modules: Dict[str, bool],
        payload: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> None:
        ph = _params_hash(query_name, registration, country, modules)
        snap = json.dumps({"name": query_name, "registration": registration, "country": country})
        bitmask = 0
        with self.connect() as c:
            c.execute(
                """
                INSERT INTO searches (params_hash, created_at, country, query_snapshot,
                  payload_json, modules_bitmask, ttl_seconds)
                VALUES (?,?,?,?,?,?,?)
                """,
                (ph, time.time(), country.upper(), snap, json.dumps(payload), bitmask, ttl_seconds),
            )

    def list_recent_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.connect() as c:
            rows = c.execute(
                """
                SELECT id, created_at, country, query_snapshot, params_hash FROM searches
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        seen = set()
        for r in rows:
            try:
                snap = json.loads(r["query_snapshot"])
            except json.JSONDecodeError:
                snap = {}
            key = (snap.get("name"), snap.get("country"), snap.get("registration"))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "country": r["country"],
                    "query_snapshot": snap,
                    "params_hash": r["params_hash"],
                }
            )
        return out[:limit]

    def clear_cache(self) -> int:
        with self.connect() as c:
            cur = c.execute("DELETE FROM searches")
            return int(cur.rowcount or 0)
