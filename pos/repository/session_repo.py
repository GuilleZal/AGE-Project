"""Session repository — login/logout tracking."""

import sqlite3
from pos.model.user import Session


class SessionRepo:
    """Data-access for the ``sessions`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def create_session(self, user_id: int) -> Session:
        """Insert session row with logout_time=NULL. Returns Session with id."""
        cur = self._db.execute(
            """INSERT INTO sessions (user_id)
               VALUES (?)
               RETURNING id, login_time""",
            (user_id,),
        )
        row = cur.fetchone()
        return Session(
            id=row["id"],
            user_id=user_id,
            login_time=row["login_time"],
            logout_time=None,
        )

    def close_session(self, user_id: int) -> None:
        """Set logout_time=now for the open session of user_id."""
        self._db.execute(
            """UPDATE sessions
               SET logout_time = datetime('now')
               WHERE user_id = ? AND logout_time IS NULL""",
            (user_id,),
        )

    def get_active_session(self, user_id: int) -> Session | None:
        """Return open session (logout_time IS NULL) for user_id, or None."""
        row = self._db.execute(
            """SELECT * FROM sessions
               WHERE user_id = ? AND logout_time IS NULL""",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Session:
        """Map sqlite3.Row to Session dataclass."""
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            login_time=row["login_time"],
            logout_time=row["logout_time"],
        )