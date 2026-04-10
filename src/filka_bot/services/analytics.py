import sqlite3
from pathlib import Path
from typing import Optional


class AnalyticsService:
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
                CREATE TABLE IF NOT EXISTS bot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 1,
                    details TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def log_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        success: bool = True,
        details: str = "",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO bot_events(user_id, event_type, success, details)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, event_type, 1 if success else 0, details),
            )
            connection.commit()

    def get_admin_stats(self) -> dict[str, int]:
        with self._connect() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_events,
                    COUNT(DISTINCT user_id) AS total_users,
                    COUNT(DISTINCT CASE WHEN DATE(created_at) = DATE('now', 'localtime') THEN user_id END) AS active_today,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS errors_today
                FROM bot_events
                WHERE DATE(created_at) = DATE('now', 'localtime')
                """
            ).fetchone()
            by_type = connection.execute(
                """
                SELECT event_type, COUNT(*)
                FROM bot_events
                WHERE DATE(created_at) = DATE('now', 'localtime')
                GROUP BY event_type
                """
            ).fetchall()

        stats = {
            "total_events_today": int(totals[0]) if totals and totals[0] else 0,
            "total_users": int(totals[1]) if totals and totals[1] else 0,
            "active_today": int(totals[2]) if totals and totals[2] else 0,
            "errors_today": int(totals[3]) if totals and totals[3] else 0,
        }
        for event_type, count in by_type:
            stats[f"type_{event_type}"] = int(count)
        return stats
