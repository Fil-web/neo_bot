import sqlite3
from pathlib import Path


DEFAULT_MODE = "default"


class UserProfileService:
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
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    mode TEXT NOT NULL DEFAULT 'default',
                    admin_mode INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def ensure_user(self, user_id: int, username: str = "", first_name: str = "") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_profiles(user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (user_id, username, first_name),
            )
            connection.commit()

    def set_mode(self, user_id: int, mode: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_profiles(user_id, mode)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    mode = excluded.mode,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (user_id, mode),
            )
            connection.commit()

    def get_mode(self, user_id: int) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT mode FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row[0] if row and row[0] else DEFAULT_MODE

    def set_admin_mode(self, user_id: int, enabled: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_profiles(user_id, admin_mode)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    admin_mode = excluded.admin_mode,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (user_id, 1 if enabled else 0),
            )
            connection.commit()

    def is_admin_mode(self, user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT admin_mode FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return bool(row[0]) if row else False
