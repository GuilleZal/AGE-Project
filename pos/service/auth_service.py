"""Authentication service — login, logout, credential validation."""

import sqlite3
from pos.model.user import User, Session
from pos.model.enums import UserRole
from pos.repository.user_repo import UserRepo
from pos.repository.session_repo import SessionRepo


class AuthService:
    """Handles credential validation and session lifecycle.

    Dependencies injected via constructor (repos instantiated internally,
    following existing service pattern).
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._user_repo = UserRepo(db)
        self._session_repo = SessionRepo(db)

    def login(self, username: str, password: str) -> User | None:
        """Validate credentials and create session.

        Returns User on success, None on failure.
        Rejects inactive users (is_active=0).
        On success, creates session record via SessionRepo.
        """
        user = self._user_repo.find_by_username(username)
        if user is None:
            return None
        if user.password != password:
            return None
        if not user.is_active:
            return None
        self._session_repo.create_session(user.id)
        self._db.commit()
        return user

    def logout(self, user_id: int) -> None:
        """Close the active session for user_id."""
        self._session_repo.close_session(user_id)
        self._db.commit()

    def bootstrap_admin(self) -> None:
        """Create hardcoded admin user if not exists. Idempotent."""
        existing = self._user_repo.find_by_username("admin")
        if existing is None:
            admin = User(
                username="admin",
                password="admin123",
                role=UserRole.ADMIN,
                is_active=1,
            )
            self._user_repo.create(admin)
            self._db.commit()

    def create_synthetic_admin(self) -> User:
        """Return a synthetic admin User for test mode.

        Does NOT persist to database. Used when POS_TEST_MODE=1.
        """
        return User(
            id=0,
            username="admin",
            password="",
            role=UserRole.ADMIN,
            is_active=1,
        )