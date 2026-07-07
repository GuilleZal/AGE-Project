"""Tests for SessionRepo — session lifecycle tracking."""

import pytest
import sqlite3
from pos.repository.session_repo import SessionRepo
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


@pytest.fixture
def session_repo(db: sqlite3.Connection) -> SessionRepo:
    """Return a SessionRepo instance."""
    return SessionRepo(db)


@pytest.fixture
def user_with_id(db: sqlite3.Connection) -> int:
    """Create a user and return their ID."""
    user_repo = UserRepo(db)
    user = User(username="sessionuser", password="pass", role=UserRole.CAJERO)
    created = user_repo.create(user)
    db.commit()
    return created.id


def test_create_session(session_repo: SessionRepo, user_with_id: int) -> None:
    """Test creating a new session."""
    session = session_repo.create_session(user_with_id)
    assert session.id is not None
    assert session.user_id == user_with_id
    assert session.login_time is not None
    assert session.logout_time is None


def test_get_active_session(session_repo: SessionRepo, user_with_id: int, db: sqlite3.Connection) -> None:
    """Test getting active session."""
    session_repo.create_session(user_with_id)
    db.commit()
    
    active = session_repo.get_active_session(user_with_id)
    assert active is not None
    assert active.user_id == user_with_id
    assert active.logout_time is None


def test_get_active_session_none_when_closed(
    session_repo: SessionRepo, user_with_id: int, db: sqlite3.Connection
) -> None:
    """Test getting active session returns None when closed."""
    session_repo.create_session(user_with_id)
    db.commit()
    
    session_repo.close_session(user_with_id)
    db.commit()
    
    active = session_repo.get_active_session(user_with_id)
    assert active is None


def test_close_session(session_repo: SessionRepo, user_with_id: int, db: sqlite3.Connection) -> None:
    """Test closing a session sets logout_time."""
    session_repo.create_session(user_with_id)
    db.commit()
    
    session_repo.close_session(user_with_id)
    db.commit()
    
    # Verify by checking the database directly
    row = db.execute(
        "SELECT logout_time FROM sessions WHERE user_id = ? AND logout_time IS NOT NULL",
        (user_with_id,)
    ).fetchone()
    assert row is not None
    assert row["logout_time"] is not None