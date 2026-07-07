"""Tests for AuthService — login, logout, bootstrap."""

import pytest
import sqlite3
from pos.service.auth_service import AuthService
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


@pytest.fixture
def auth_service(db: sqlite3.Connection) -> AuthService:
    """Return an AuthService instance."""
    return AuthService(db)


def test_bootstrap_admin(auth_service: AuthService) -> None:
    """Test bootstrap creates admin user."""
    auth_service.bootstrap_admin()
    
    user_repo = UserRepo(auth_service._db)
    admin = user_repo.find_by_username("admin")
    assert admin is not None
    assert admin.username == "admin"
    assert admin.password == "admin123"
    assert admin.role == "admin"
    assert admin.is_active == 1


def test_bootstrap_admin_idempotent(auth_service: AuthService) -> None:
    """Test bootstrap is idempotent — doesn't duplicate admin."""
    auth_service.bootstrap_admin()
    auth_service.bootstrap_admin()
    auth_service.bootstrap_admin()
    
    user_repo = UserRepo(auth_service._db)
    admins = [u for u in user_repo.get_all() if u.username == "admin"]
    assert len(admins) == 1


def test_login_valid_credentials(auth_service: AuthService, db: sqlite3.Connection) -> None:
    """Test login with valid credentials returns User."""
    user_repo = UserRepo(db)
    user_repo.create(User(username="valid", password="pass123", role=UserRole.CAJERO))
    db.commit()
    
    result = auth_service.login("valid", "pass123")
    assert result is not None
    assert result.username == "valid"


def test_login_wrong_password(auth_service: AuthService, db: sqlite3.Connection) -> None:
    """Test login with wrong password returns None."""
    user_repo = UserRepo(db)
    user_repo.create(User(username="wrong", password="correct", role=UserRole.CAJERO))
    db.commit()
    
    result = auth_service.login("wrong", "incorrect")
    assert result is None


def test_login_inactive_user(auth_service: AuthService, db: sqlite3.Connection) -> None:
    """Test login rejects inactive user."""
    user_repo = UserRepo(db)
    user = user_repo.create(User(username="inactive", password="pass", role=UserRole.CAJERO, is_active=0))
    db.commit()
    
    result = auth_service.login("inactive", "pass")
    assert result is None


def test_login_nonexistent_user(auth_service: AuthService) -> None:
    """Test login with non-existent username returns None."""
    result = auth_service.login("ghost", "pass")
    assert result is None


def test_logout(auth_service: AuthService, db: sqlite3.Connection) -> None:
    """Test logout closes the session."""
    user_repo = UserRepo(db)
    user = user_repo.create(User(username="logout_test", password="pass", role=UserRole.CAJERO))
    db.commit()
    
    # Login creates session
    auth_service.login("logout_test", "pass")
    
    # Logout should close it
    auth_service.logout(user.id)
    
    # Verify session is closed
    from pos.repository.session_repo import SessionRepo
    session_repo = SessionRepo(db)
    active = session_repo.get_active_session(user.id)
    assert active is None


def test_create_synthetic_admin(auth_service: AuthService) -> None:
    """Test synthetic admin creation for test mode."""
    user = auth_service.create_synthetic_admin()
    assert user.username == "admin"
    assert user.role == UserRole.ADMIN
    assert user.id == 0