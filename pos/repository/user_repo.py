"""User repository — CRUD for the users table."""

import sqlite3
from pos.model.user import User
from pos.model.enums import UserRole


class UserRepo:
    """Data-access for the ``users`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def find_by_username(self, username: str) -> User | None:
        """Return user with exact *username* match, or None."""
        row = self._db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def find_by_id(self, user_id: int) -> User | None:
        """Return user with *user_id*, or None."""
        row = self._db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def create(self, user: User) -> User:
        """Insert user. Returns user with id populated.

        Raises sqlite3.IntegrityError on duplicate username.
        """
        role_val = user.role.value if isinstance(user.role, UserRole) else user.role
        cur = self._db.execute(
            """INSERT INTO users (username, password, role, is_active)
               VALUES (?, ?, ?, ?)
               RETURNING id, created_at""",
            (user.username, user.password, role_val, user.is_active),
        )
        row = cur.fetchone()
        user.id = row["id"]
        user.created_at = row["created_at"]
        return user

    def update(self, user: User) -> None:
        """Update password, role, and is_active for existing user."""
        role_val = user.role.value if isinstance(user.role, UserRole) else user.role
        self._db.execute(
            """UPDATE users
               SET password = ?, role = ?, is_active = ?
               WHERE id = ?""",
            (user.password, role_val, user.is_active, user.id),
        )

    def get_all(self) -> list[User]:
        """Return all users ordered by username."""
        rows = self._db.execute(
            "SELECT * FROM users ORDER BY username"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> User:
        """Map sqlite3.Row to User dataclass."""
        return User(
            id=row["id"],
            username=row["username"],
            password=row["password"],
            role=row["role"],
            is_active=row["is_active"],
            created_at=row["created_at"],
        )