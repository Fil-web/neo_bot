import sqlite3
from pathlib import Path
from typing import Optional
from typing import Tuple


class ModerationService:
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
                CREATE TABLE IF NOT EXISTS moderation_actions (
                    user_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    until_at TIMESTAMP,
                    reason TEXT DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def ban(self, user_id: int, reason: str = "") -> None:
        self._set_status(user_id=user_id, status="banned", until_at=None, reason=reason)

    def mute(self, user_id: int, minutes: int, reason: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO moderation_actions(user_id, status, until_at, reason, updated_at)
                VALUES (?, 'muted', DATETIME('now', ?), ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    status = 'muted',
                    until_at = DATETIME('now', ?),
                    reason = excluded.reason,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, f"+{minutes} minutes", reason, f"+{minutes} minutes"),
            )
            connection.commit()

    def unban(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM moderation_actions WHERE user_id = ?", (user_id,))
            connection.commit()

    def check_status(self, user_id: int) -> Tuple[str, str]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT status, COALESCE(reason, '')
                FROM moderation_actions
                WHERE user_id = ?
                  AND (status = 'banned' OR until_at IS NULL OR until_at > CURRENT_TIMESTAMP)
                """,
                (user_id,),
            ).fetchone()
            connection.execute(
                """
                DELETE FROM moderation_actions
                WHERE user_id = ?
                  AND status = 'muted'
                  AND until_at IS NOT NULL
                  AND until_at <= CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            connection.commit()

        if not row:
            return "active", ""
        return row[0], row[1]

    def _set_status(self, user_id: int, status: str, until_at: Optional[str], reason: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO moderation_actions(user_id, status, until_at, reason, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    status = excluded.status,
                    until_at = excluded.until_at,
                    reason = excluded.reason,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, status, until_at, reason),
            )
            connection.commit()
