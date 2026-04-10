import re
import sqlite3
from pathlib import Path
from typing import Optional


class KnowledgeBaseService:
    def __init__(self, db_path: Path, chunk_size: int = 1200, chunk_overlap: int = 200) -> None:
        self._db_path = db_path
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kb_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_ref TEXT,
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kb_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES kb_documents(id) ON DELETE CASCADE
                )
                """
            )
            connection.commit()

    def add_document(
        self,
        *,
        title: str,
        content: str,
        source_type: str,
        source_ref: str = "",
        added_by: Optional[int] = None,
    ) -> int:
        chunks = self._split_into_chunks(content)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO kb_documents(title, source_type, source_ref, added_by)
                VALUES (?, ?, ?, ?)
                """,
                (title, source_type, source_ref, added_by),
            )
            document_id = int(cursor.lastrowid)
            for index, chunk in enumerate(chunks):
                connection.execute(
                    """
                    INSERT INTO kb_chunks(document_id, chunk_index, content)
                    VALUES (?, ?, ?)
                    """,
                    (document_id, index, chunk),
                )
            connection.commit()
        return document_id

    def search(self, query: str, limit: int = 4) -> list[dict[str, str]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT kb_documents.title, kb_chunks.content
                FROM kb_chunks
                JOIN kb_documents ON kb_documents.id = kb_chunks.document_id
                """
            ).fetchall()

        scored: list[tuple[int, str, str]] = []
        for title, content in rows:
            lowered = content.lower()
            score = sum(lowered.count(token) for token in tokens)
            if score > 0:
                scored.append((score, title, content))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"title": title, "content": content}
            for _, title, content in scored[:limit]
        ]

    def stats(self) -> dict[str, int]:
        with self._connect() as connection:
            docs = connection.execute("SELECT COUNT(*) FROM kb_documents").fetchone()
            chunks = connection.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()
        return {
            "documents": int(docs[0]) if docs else 0,
            "chunks": int(chunks[0]) if chunks else 0,
        }

    def _split_into_chunks(self, content: str) -> list[str]:
        cleaned = content.strip()
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + self._chunk_size, len(cleaned))
            chunks.append(cleaned[start:end])
            if end >= len(cleaned):
                break
            start = max(0, end - self._chunk_overlap)
        return chunks

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in re.findall(r"[a-zA-Zа-яА-Я0-9_]+", text.lower()) if len(token) > 2]
