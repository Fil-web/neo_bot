import hashlib
import sqlite3
from pathlib import Path
from typing import Optional


class ResponseCacheService:
    def __init__(self, db_path: Path, ttl_seconds: int) -> None:
        self._db_path = db_path
        self._ttl_seconds = ttl_seconds
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def build_key(self, *, mode: str, user_text: str, knowledge_context: str = "") -> str:
        payload = f"{mode}\n{user_text.strip().lower()}\n{knowledge_context.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[str]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT response_text
                FROM response_cache
                WHERE cache_key = ?
                  AND created_at >= DATETIME('now', ?)
                """,
                (cache_key, f"-{self._ttl_seconds} seconds"),
            ).fetchone()
        return row[0] if row else None

    def set(self, cache_key: str, response_text: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO response_cache(cache_key, response_text, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_text = excluded.response_text,
                    created_at = CURRENT_TIMESTAMP
                """,
                (cache_key, response_text),
            )
            connection.commit()
