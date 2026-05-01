import sqlite3
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DB_PATH = "classcast.db"

def init_db():
    """Create the events table if it doesn't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    data JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def insert_event(event_type: str, data: dict[str, Any]):
    """Insert a single event into the database."""
    try:
        with sqlite3.connect(DB_PATH, timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO events (event_type, data) VALUES (?, ?)",
                (event_type, json.dumps(data))
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to insert event {event_type}: {e}")

def get_recent_events(limit: int = 100) -> list[dict[str, Any]]:
    """Retrieve the most recent events."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT event_type, data FROM events ORDER BY id ASC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [{"event_type": row["event_type"], "data": json.loads(row["data"])} for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch recent events: {e}")
        return []

# Initialize the database on import
init_db()
