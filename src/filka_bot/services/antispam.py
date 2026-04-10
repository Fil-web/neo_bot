import sqlite3
from pathlib import Path


class AntiSpamService:
    def __init__(self, db_path: Path, window_seconds: int, max_requests: int) -> None:
        self._db_path = db_path
        self._window_seconds = window_seconds
        self._max_requests = max_requests
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS request_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def is_allowed(self, user_id: int, request_type: str = "text") -> tuple[bool, int]:
        with self._connect() as connection:
            count_row = connection.execute(
                """
                SELECT COUNT(*)
                FROM request_log
                WHERE user_id = ?
                  AND created_at >= DATETIME('now', ?)
                """,
                (user_id, f"-{self._window_seconds} seconds"),
            ).fetchone()
            current_count = int(count_row[0]) if count_row else 0
            if current_count >= self._max_requests:
                return False, current_count

            connection.execute(
                """
                INSERT INTO request_log(user_id, request_type)
                VALUES (?, ?)
                """,
                (user_id, request_type),
            )
            connection.commit()
            return True, current_count + 1
