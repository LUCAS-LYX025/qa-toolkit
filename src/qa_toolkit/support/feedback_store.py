import datetime
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from qa_toolkit.paths import FEEDBACK_DB_PATH


class FeedbackStore:
    """Persist user feedback records in a local SQLite database."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        configured_path = db_path or os.environ.get("QA_TOOLKIT_FEEDBACK_DB_PATH") or FEEDBACK_DB_PATH
        self.db_path = Path(configured_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    nickname TEXT NOT NULL,
                    tool_name TEXT,
                    source TEXT NOT NULL,
                    reaction TEXT
                )
                """
            )
            connection.commit()

    def add_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "timestamp": feedback.get("timestamp") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": feedback["type"],
            "urgency": feedback["urgency"],
            "rating": int(feedback["rating"]),
            "content": feedback["content"],
            "nickname": feedback.get("nickname") or "匿名用户",
            "tool_name": feedback.get("tool_name"),
            "source": feedback.get("source") or "unknown",
            "reaction": feedback.get("reaction"),
        }

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO feedback_records (
                    timestamp,
                    type,
                    urgency,
                    rating,
                    content,
                    nickname,
                    tool_name,
                    source,
                    reaction
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["timestamp"],
                    payload["type"],
                    payload["urgency"],
                    payload["rating"],
                    payload["content"],
                    payload["nickname"],
                    payload["tool_name"],
                    payload["source"],
                    payload["reaction"],
                ),
            )
            row = connection.execute(
                "SELECT * FROM feedback_records WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            connection.commit()

        return self._row_to_feedback(row)

    def list_feedbacks(
        self,
        *,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None,
        newest_first: bool = False,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM feedback_records"
        params: List[Any] = []

        if tool_name:
            query += " WHERE tool_name = ?"
            params.append(tool_name)

        order = "DESC" if newest_first else "ASC"
        query += f" ORDER BY id {order}"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return [self._row_to_feedback(row) for row in rows]

    @staticmethod
    def _row_to_feedback(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "type": row["type"],
            "urgency": row["urgency"],
            "rating": row["rating"],
            "content": row["content"],
            "nickname": row["nickname"],
            "tool_name": row["tool_name"],
            "source": row["source"],
            "reaction": row["reaction"],
        }
