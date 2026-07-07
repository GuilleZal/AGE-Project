"""Tests for LoginController — login flow orchestration."""

import pytest
import sqlite3
from pos.controller.login_controller import LoginController
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


@pytest.fixture
def login_ctrl(db: sqlite3.Connection) -> LoginController:
    """Return a LoginController instance."""
    return LoginController(db)


def test_validate_success(login_ctrl: LoginController, db: sqlite3.Connection) -> None:
    """Test validate returns success dict with valid credentials."""
    user_repo = UserRepo(db)
    user_repo.create(User(username="valid", password="pass123", role=UserRole.CAJERO))
    db.commit()
    
    result = login_ctrl.validate("valid", "pass123")
    assert result["success"] is True
    assert result["error"] is None
    assert "user" in result["data"]
    assert "permissions" in result["data"]
    assert result["data"]["user"].username == "valid"


def test_validate_failure(login_ctrl: LoginController, db: sqlite3.Connection) -> None:
    """Test validate returns failure dict with invalid credentials."""
    result = login_ctrl.validate("nonexistent", "pass")
    assert result["success"] is False
    assert result["data"] is None
    assert result["error"] == "Usuario o contrasena incorrectos"


def test_validate_input_empty_fields(login_ctrl: LoginController) -> None:
    """Test validate_input rejects empty fields."""
    result = login_ctrl.validate_input("", "pass")
    assert result["success"] is False
    assert result["error"] == "Complete todos los campos"
    
    result = login_ctrl.validate_input("user", "")
    assert result["success"] is False
    assert result["error"] == "Complete todos los campos"


def test_validate_input_valid(login_ctrl: LoginController) -> None:
    """Test validate_input accepts non-empty fields."""
    result = login_ctrl.validate_input("user", "pass")
    assert result["success"] is True
    assert result["error"] is None


def test_bootstrap_admin(login_ctrl: LoginController) -> None:
    """Test bootstrap_admin creates admin user."""
    login_ctrl.bootstrap_admin()
    
    result = login_ctrl.validate("admin", "admin123")
    assert result["success"] is True
    assert result["data"]["user"].username == "admin"


def test_logout(login_ctrl: LoginController, db: sqlite3.Connection) -> None:
    """Test logout closes session."""
    user_repo = UserRepo(db)
    user = user_repo.create(User(username="logout", password="pass", role=UserRole.CAJERO))
    db.commit()
    
    # Login first
    login_ctrl.validate("logout", "pass")
    
    # Logout should not raise
    login_ctrl.logout(user.id)