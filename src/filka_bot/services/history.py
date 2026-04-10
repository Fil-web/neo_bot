import sqlite3
from pathlib import Path


class DialogHistory:
    def __init__(self, db_path: Path, max_messages: int) -> None:
        self._db_path = db_path
        self._max_messages = max_messages
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dialog_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def add(self, user_id: int, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM dialog_history
                WHERE user_id = ?
                  AND DATE(created_at) <> DATE('now', 'localtime')
                """,
                (user_id,),
            )
            connection.execute(
                "INSERT INTO dialog_history(user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )
            connection.execute(
                """
                DELETE FROM dialog_history
                WHERE user_id = ?
                  AND id NOT IN (
                      SELECT id
                      FROM dialog_history
                      WHERE user_id = ?
                      ORDER BY id DESC
                      LIMIT ?
                  )
                """,
                (user_id, user_id, self._max_messages),
            )
            connection.commit()

    def get(self, user_id: int) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM dialog_history
                WHERE user_id = ?
                  AND DATE(created_at) = DATE('now', 'localtime')
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in rows]

    def clear(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM dialog_history WHERE user_id = ?", (user_id,))
            connection.commit()

    def count(self, user_id: int) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM dialog_history
                WHERE user_id = ?
                  AND DATE(created_at) = DATE('now', 'localtime')
                """,
                (user_id,),
            ).fetchone()
        return int(row[0]) if row else 0
