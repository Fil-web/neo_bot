import sqlite3
from pathlib import Path


class AccessRegistry:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS allowed_users (
                    user_id INTEGER PRIMARY KEY,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def allow_user(self, user_id: int, source: str = "manual") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO allowed_users(user_id, source)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET source = excluded.source
                """,
                (user_id, source),
            )
            connection.commit()

    def is_allowed(self, user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM allowed_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def count_allowed(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM allowed_users").fetchone()
        return int(row[0]) if row else 0

