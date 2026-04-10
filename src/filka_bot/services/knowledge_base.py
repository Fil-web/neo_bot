import json
import math
import re
import sqlite3
from collections import Counter
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
                    embedding_json TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(document_id) REFERENCES kb_documents(id) ON DELETE CASCADE
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(kb_chunks)").fetchall()
            }
            if "embedding_json" not in columns:
                connection.execute("ALTER TABLE kb_chunks ADD COLUMN embedding_json TEXT DEFAULT ''")
            connection.commit()

    def add_document(
        self,
        *,
        title: str,
        content: str,
        source_type: str,
        source_ref: str = "",
        added_by: Optional[int] = None,
    ) -> tuple[int, list[str]]:
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
        return document_id, chunks

    def set_embeddings(self, document_id: int, embeddings: list[list[float]]) -> None:
        with self._connect() as connection:
            for index, embedding in enumerate(embeddings):
                connection.execute(
                    """
                    UPDATE kb_chunks
                    SET embedding_json = ?
                    WHERE document_id = ? AND chunk_index = ?
                    """,
                    (json.dumps(embedding), document_id, index),
                )
            connection.commit()

    def search(
        self,
        query: str,
        limit: int = 4,
        query_embedding: Optional[list[float]] = None,
    ) -> list[dict[str, str]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        token_weights = Counter(tokens)

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT kb_documents.id, kb_documents.title, kb_chunks.content, kb_chunks.embedding_json
                FROM kb_chunks
                JOIN kb_documents ON kb_documents.id = kb_chunks.document_id
                """
            ).fetchall()

        scored: list[tuple[int, int, str, str]] = []
        for document_id, title, content, embedding_json in rows:
            lowered = content.lower()
            score = 0
            for token, weight in token_weights.items():
                occurrences = lowered.count(token)
                if occurrences:
                    score += occurrences * weight
                    if token in title.lower():
                        score += 3
            if any(phrase in lowered for phrase in self._build_phrases(tokens)):
                score += 5
            if query_embedding and embedding_json:
                chunk_embedding = json.loads(embedding_json)
                score += int(self._cosine_similarity(query_embedding, chunk_embedding) * 100)
            if score > 0:
                scored.append((score, document_id, title, content))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        seen = set()
        results = []
        for _, _, title, content in scored:
            dedupe_key = (title, content[:120])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            results.append({"title": title, "content": content})
            if len(results) >= limit:
                break
        return results

    def stats(self) -> dict[str, int]:
        with self._connect() as connection:
            docs = connection.execute("SELECT COUNT(*) FROM kb_documents").fetchone()
            chunks = connection.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()
            embedded = connection.execute(
                "SELECT COUNT(*) FROM kb_chunks WHERE embedding_json IS NOT NULL AND embedding_json != ''"
            ).fetchone()
        return {
            "documents": int(docs[0]) if docs else 0,
            "chunks": int(chunks[0]) if chunks else 0,
            "embedded_chunks": int(embedded[0]) if embedded else 0,
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

    def _build_phrases(self, tokens: list[str]) -> list[str]:
        if len(tokens) < 2:
            return []
        return [f"{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1)]

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)
