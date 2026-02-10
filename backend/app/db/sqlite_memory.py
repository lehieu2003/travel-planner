# backend/app/db/sqlite_memory.py

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List


DB_PATH = Path(__file__).resolve().parents[2] / "data.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 0.1  # 100ms


class SQLiteMemory:
    def __init__(self):
        self.conn = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            timeout=30.0  # 30 seconds timeout
        )
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")  # Better performance with WAL
        self.conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds busy timeout
        self._init_tables()
    
    def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute database operation with retry logic for handling locked database"""
        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    continue
                raise

    # ----------------------------------------------------------------------
    # CREATE TABLES
    # ----------------------------------------------------------------------
    def _init_tables(self):
        cur = self.conn.cursor()

        # USERS TABLE
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            full_name TEXT,
            hashed_password TEXT,

            age INTEGER,
            gender TEXT,
            energy_level TEXT,

            budget_min INTEGER,
            budget_max INTEGER,

            preferences_json TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # LONG-TERM MEMORY
        cur.execute("""
        CREATE TABLE IF NOT EXISTS long_memory (
            user_id INTEGER PRIMARY KEY,
            data_json TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # SHORT-TERM MEMORY (SESSION MEMORY)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS short_memory (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # CONVERSATIONS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # MESSAGES
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            itinerary_data_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        """)

        # ITINERARIES
        cur.execute("""
        CREATE TABLE IF NOT EXISTS itineraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            payload_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # PREFERENCE SIGNALS (reinforcement personalization)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS preference_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            preference TEXT,
            score INTEGER DEFAULT 1,
            signal_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # INDEXES
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);")

        self.conn.commit()

    # ----------------------------------------------------------------------
    # USER CRUD
    # ----------------------------------------------------------------------
    def create_user(
        self, email: str, full_name: str, hashed_password: str,
        age: Optional[int] = None, gender: Optional[str] = None,
        energy_level: Optional[str] = None,
        budget_min: Optional[int] = None, budget_max: Optional[int] = None,
        preferences: Optional[List[str]] = None
    ) -> int:
        def _create_user():
            cur = self.conn.cursor()
            cur.execute("""
            INSERT INTO users (email, full_name, hashed_password, age, gender, energy_level, 
                               budget_min, budget_max, preferences_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email, full_name, hashed_password,
                age, gender, energy_level,
                budget_min, budget_max,
                json.dumps(preferences or [])
            ))
            self.conn.commit()
            return cur.lastrowid
        
        return self._execute_with_retry(_create_user)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_user_profile(
        self, user_id: int,
        full_name: Optional[str], age: Optional[int],
        gender: Optional[str], energy_level: Optional[str],
        budget_min: Optional[int], budget_max: Optional[int],
        preferences: Optional[List[str]]
    ):
        def _update_user():
            cur = self.conn.cursor()
            cur.execute("""
            UPDATE users SET full_name=?, age=?, gender=?, energy_level=?,
                             budget_min=?, budget_max=?, preferences_json=?
            WHERE id = ?
            """, (
                full_name, age, gender, energy_level,
                budget_min, budget_max,
                json.dumps(preferences or []),
                user_id
            ))
            self.conn.commit()
        
        self._execute_with_retry(_update_user)

    # ----------------------------------------------------------------------
    # LONG-TERM MEMORY
    # ----------------------------------------------------------------------
    def set_long_memory(self, user_id: int, data: dict):
        def _set_long_memory():
            cur = self.conn.cursor()
            cur.execute("""
            REPLACE INTO long_memory (user_id, data_json, updated_at)
            VALUES (?, ?, ?)
            """, (user_id, json.dumps(data), datetime.utcnow()))
            self.conn.commit()
        
        self._execute_with_retry(_set_long_memory)

    def get_long_memory(self, user_id: int) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT data_json FROM long_memory WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    # ----------------------------------------------------------------------
    # SHORT-TERM MEMORY
    # ----------------------------------------------------------------------
    def set_short_memory(self, session_id: str, user_id: int, data: dict):
        def _set_short_memory():
            cur = self.conn.cursor()
            cur.execute("""
            REPLACE INTO short_memory (session_id, user_id, data_json, created_at)
            VALUES (?, ?, ?, ?)
            """, (session_id, user_id, json.dumps(data), datetime.utcnow()))
            self.conn.commit()
        
        self._execute_with_retry(_set_short_memory)

    def get_short_memory(self, session_id: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT data_json FROM short_memory WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        return json.loads(row["data_json"]) if row else None

    # ----------------------------------------------------------------------
    # CONVERSATIONS
    # ----------------------------------------------------------------------
    def create_conversation(self, conversation_id: str, user_id: int, title: str = "Cuộc trò chuyện mới"):
        def _create_conversation():
            cur = self.conn.cursor()
            cur.execute("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, user_id, title, datetime.utcnow(), datetime.utcnow()))
            self.conn.commit()
        
        self._execute_with_retry(_create_conversation)

    def get_conversation(self, conversation_id: str):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_conversations(self, user_id: int, limit: int = 100):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """, (user_id, limit))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def update_conversation_title(self, conversation_id: str, title: str):
        def _update_title():
            cur = self.conn.cursor()
            cur.execute("""
            UPDATE conversations SET title=?, updated_at=?
            WHERE id = ?
            """, (title, datetime.utcnow(), conversation_id))
            self.conn.commit()
        
        self._execute_with_retry(_update_title)

    def update_conversation_updated_at(self, conversation_id: str, commit: bool = True):
        """Update conversation updated_at timestamp.
        
        Args:
            conversation_id: The conversation ID to update
            commit: Whether to commit the transaction (default True)
                   Set to False if called within a larger transaction
        """
        cur = self.conn.cursor()
        cur.execute("""
        UPDATE conversations SET updated_at=?
        WHERE id = ?
        """, (datetime.utcnow(), conversation_id))
        if commit:
            self.conn.commit()

    def delete_conversation(self, conversation_id: str):
        def _delete_conversation():
            cur = self.conn.cursor()
            cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            self.conn.commit()
        
        self._execute_with_retry(_delete_conversation)

    # ----------------------------------------------------------------------
    # MESSAGES
    # ----------------------------------------------------------------------
    def add_message(self, message_id: str, conversation_id: str, role: str, content: str, itinerary_data=None):
        """Add a message to the conversation with retry logic."""
        def _add_message():
            cur = self.conn.cursor()
            cur.execute("""
            INSERT INTO messages (id, conversation_id, role, content, itinerary_data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(itinerary_data) if itinerary_data else None,
                datetime.utcnow(),
            ))
            # Update conversation timestamp without committing (we'll commit together)
            self.update_conversation_updated_at(conversation_id, commit=False)
            self.conn.commit()
        
        self._execute_with_retry(_add_message)

    def get_messages(self, conversation_id: str, limit: int = 1000):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        LIMIT ?
        """, (conversation_id, limit))
        rows = cur.fetchall()

        messages = []
        for r in rows:
            item = dict(r)
            if item.get("itinerary_data_json"):
                item["itinerary_data"] = json.loads(item["itinerary_data_json"])
            messages.append(item)

        return messages

    def get_last_itinerary(self, conversation_id: str):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT itinerary_data_json
        FROM messages
        WHERE conversation_id = ? AND itinerary_data_json IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
        """, (conversation_id,))
        row = cur.fetchone()
        return json.loads(row["itinerary_data_json"]) if row and row["itinerary_data_json"] else None

    # ----------------------------------------------------------------------
    # ITINERARIES (SAVED PLANS)
    # ----------------------------------------------------------------------
    def save_itinerary(self, user_id: int, title: str, payload: dict) -> int:
        def _save_itinerary():
            cur = self.conn.cursor()
            cur.execute("""
            INSERT INTO itineraries (user_id, title, payload_json)
            VALUES (?, ?, ?)
            """, (user_id, title, json.dumps(payload)))
            self.conn.commit()
            return cur.lastrowid
        
        return self._execute_with_retry(_save_itinerary)

    def list_itineraries(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM itineraries
        WHERE user_id = ?
        ORDER BY created_at DESC
        """, (user_id,))
        rows = cur.fetchall()

        return [
            {
                "id": r["id"],
                "title": r["title"],
                "payload": json.loads(r["payload_json"]),
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    # ----------------------------------------------------------------------
    # PREFERENCE SIGNALS
    # ----------------------------------------------------------------------
    def add_preference_signal(self, user_id: int, preference: str, signal_type: str):
        def _add_signal():
            cur = self.conn.cursor()
            cur.execute("""
            INSERT INTO preference_signals (user_id, preference, score, signal_type)
            VALUES (?, ?, ?, ?)
            """, (user_id, preference, 1, signal_type))
            self.conn.commit()
        
        self._execute_with_retry(_add_signal)

    def get_preference_signals(self, user_id: int):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT preference, SUM(score) AS total
        FROM preference_signals
        WHERE user_id = ?
        GROUP BY preference
        ORDER BY total DESC
        """, (user_id,))
        rows = cur.fetchall()

        return {r["preference"]: r["total"] for r in rows}
