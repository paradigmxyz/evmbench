import json
import sqlite3
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


@dataclass(frozen=True)
class CachedResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


class ResponseCache:
    def __init__(self, *, db_path: Path, ttl_seconds: int, max_entry_bytes: int, max_entries: int) -> None:
        self.db_path = db_path
        self.ttl_seconds = max(0, ttl_seconds)
        self.max_entry_bytes = max(0, max_entry_bytes)
        self.max_entries = max(0, max_entries)
        self._lock = Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_cache (
                    key TEXT PRIMARY KEY,
                    status_code INTEGER NOT NULL,
                    headers_json TEXT NOT NULL,
                    body BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_response_cache_accessed_at
                ON response_cache (accessed_at)
                """
            )

    def get(self, key: str) -> CachedResponse | None:
        now = time.time()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT status_code, headers_json, body, created_at
                FROM response_cache
                WHERE key = ?
                """,
                (key,),
            ).fetchone()
            if row is None:
                return None

            status_code, headers_json, body, created_at = row
            if self.ttl_seconds and now - float(created_at) > self.ttl_seconds:
                conn.execute('DELETE FROM response_cache WHERE key = ?', (key,))
                return None

            conn.execute('UPDATE response_cache SET accessed_at = ? WHERE key = ?', (now, key))

        try:
            headers = json.loads(str(headers_json))
        except json.JSONDecodeError:
            return None
        if not isinstance(headers, dict):
            return None

        return CachedResponse(
            status_code=int(status_code),
            headers={str(k): str(v) for k, v in headers.items()},
            body=bytes(body),
        )

    def set(self, key: str, *, status_code: int, headers: Mapping[str, str], body: bytes) -> bool:
        if status_code < 200 or status_code >= 300:
            return False
        if self.max_entry_bytes and len(body) > self.max_entry_bytes:
            return False

        now = time.time()
        headers_json = json.dumps(dict(headers), separators=(',', ':'), sort_keys=True)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO response_cache (key, status_code, headers_json, body, created_at, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    status_code = excluded.status_code,
                    headers_json = excluded.headers_json,
                    body = excluded.body,
                    created_at = excluded.created_at,
                    accessed_at = excluded.accessed_at
                """,
                (key, status_code, headers_json, body, now, now),
            )
            if self.max_entries:
                conn.execute(
                    """
                    DELETE FROM response_cache
                    WHERE key NOT IN (
                        SELECT key
                        FROM response_cache
                        ORDER BY accessed_at DESC
                        LIMIT ?
                    )
                    """,
                    (self.max_entries,),
                )
        return True
