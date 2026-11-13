import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS results (
                chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                title TEXT NOT NULL, date TEXT NOT NULL, text TEXT NOT NULL,
                link TEXT NOT NULL, PRIMARY KEY (chat_id, message_id));
        """)

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def add(self, result):
        with self.db:
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO results VALUES (:chat_id,:message_id,:title,:date,:text,:link)", result)
        return cursor.rowcount == 1

    def results(self, limit=2000):
        return [dict(r) for r in self.db.execute("SELECT * FROM results ORDER BY date DESC LIMIT ?", (limit,))]

    def clear(self):
        with self.db:
            self.db.execute("DELETE FROM results")
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.db.execute("VACUUM")

    def close(self):
        self.db.close()
