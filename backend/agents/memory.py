"""
WorkflowMemory — SQLite-backed shared memory for all agents in a workflow.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class WorkflowMemory:
    """
    SQLite-backed shared memory for all agents in a workflow.
    
    This enables agents to share context across iterations and allows
    the supervisor to make informed routing decisions.
    """

    def __init__(self, workflow_id: str, db_path: str = None):
        self.workflow_id = workflow_id
        self.data_dir = Path(__file__).parent.parent / "data" / "workflow_memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(self.data_dir / f"{workflow_id}.db")
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Lazy connection — create on first use."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        """Create the messages table if it doesn't exist."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_workflow
            ON messages (agent_id, timestamp)
        """)
        conn.commit()

    def write(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        Append an agent's message to shared memory.
        Returns the row ID.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """
            INSERT INTO messages (agent_id, role, content, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                role,
                content,
                json.dumps(metadata) if metadata else None,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def read(self, agent_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Read conversation history for context.
        If agent_id is provided, only reads messages from that agent.
        """
        conn = self._get_conn()
        if agent_id:
            cursor = conn.execute(
                """
                SELECT agent_id, role, content, metadata, timestamp
                FROM messages
                WHERE agent_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (agent_id, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT agent_id, role, content, metadata, timestamp
                FROM messages
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        return [
            {
                "agent_id": row["agent_id"],
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def get_summary(self, max_chars: int = 2000) -> str:
        """
        Summarize conversation so far for supervisor context.
        Truncates to max_chars.
        """
        messages = self.read(limit=50)
        if not messages:
            return "(No conversation history yet)"

        parts = []
        for msg in messages[-10:]:  # Last 10 messages
            role = msg["role"].upper()
            content = msg["content"][:500]  # Truncate each message
            parts.append(f"[{role}] {content}")

        summary = "\n".join(parts)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        return summary

    def get_all(self) -> List[Dict[str, Any]]:
        """Read all messages in the workflow."""
        return self.read(limit=10000)

    def clear(self):
        """Clear memory after workflow completes."""
        conn = self._get_conn()
        conn.execute("DELETE FROM messages")
        conn.commit()

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_agent_messages(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all messages from a specific agent."""
        return self.read(agent_id=agent_id, limit=10000)
