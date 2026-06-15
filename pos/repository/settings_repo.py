"""Settings repository — key-value store for global preferences."""

import sqlite3


class SettingsRepo:
    """Data-access for the ``settings`` table.

    Stores global configuration as key-value pairs. All values are stored
    as strings and must be parsed by the consumer.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the value for *key*, or *default* if not found."""
        row = self._db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set(self, key: str, value: str) -> None:
        """Set the value for *key* (upsert)."""
        self._db.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   updated_at = excluded.updated_at""",
            (key, value),
        )

    def get_int(self, key: str, default: int = 0) -> int:
        """Return the value for *key* as int, or *default* if not found/invalid."""
        val = self.get(key)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Return the value for *key* as float, or *default* if not found/invalid."""
        val = self.get(key)
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
