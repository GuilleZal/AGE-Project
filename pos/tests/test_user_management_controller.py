"""Tests for UserManagementController — admin CRUD for users."""

import pytest
import sqlite3
from pos.controller.user_management_controller import UserManagementController
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


@pytest.fixture
def user_mgmt_ctrl(db: sqlite3.Connection) -> UserManagementController:
    """Return a UserManagementController instance."""
    return UserManagementController(db)


@pytest.fixture
def admin_user(db: sqlite3.Connection) -> int:
    """Create admin user and return ID."""
    user_repo = UserRepo(db)
    admin = user_repo.create(User(username="admin", password="admin123", role=UserRole.ADMIN))
    db.commit()
    return admin.id


def test_create_user_success(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test creating a new user."""
    result = user_mgmt_ctrl.create_user("cajero1", "pass123", "cajero")
    assert result["success"] is True
    assert result["error"] is None
    assert result["data"]["username"] == "cajero1"
    assert result["data"]["role"] == "cajero"


def test_create_user_empty_fields(user_mgmt_ctrl: UserManagementController) -> None:
    """Test creating user with empty fields fails."""
    result = user_mgmt_ctrl.create_user("", "pass", "cajero")
    assert result["success"] is False
    assert result["error"] == "Complete todos los campos"
    
    result = user_mgmt_ctrl.create_user("user", "", "cajero")
    assert result["success"] is False
    assert result["error"] == "Complete todos los campos"


def test_create_user_duplicate(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test creating duplicate username fails."""
    user_mgmt_ctrl.create_user("duplicate", "pass1", "cajero")
    db.commit()
    
    result = user_mgmt_ctrl.create_user("duplicate", "pass2", "gerente")
    assert result["success"] is False
    assert result["error"] == "El nombre de usuario ya existe"


def test_create_user_admin_role_rejected(user_mgmt_ctrl: UserManagementController) -> None:
    """Test creating admin role is rejected."""
    result = user_mgmt_ctrl.create_user("newadmin", "pass", "admin")
    assert result["success"] is False
    assert "no se puede crear" in result["error"].lower() or "admin" in result["error"].lower()


def test_list_users(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test listing all users."""
    user_mgmt_ctrl.create_user("user1", "pass", "cajero")
    user_mgmt_ctrl.create_user("user2", "pass", "gerente")
    db.commit()
    
    result = user_mgmt_ctrl.list_users()
    assert result["success"] is True
    assert len(result["data"]) == 2


def test_update_user(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test updating user password and role."""
    create_result = user_mgmt_ctrl.create_user("update_me", "old_pass", "cajero")
    db.commit()
    user_id = create_result["data"]["id"]
    
    result = user_mgmt_ctrl.update_user(user_id, password="new_pass", role="gerente")
    assert result["success"] is True
    
    user_repo = UserRepo(db)
    updated = user_repo.find_by_id(user_id)
    assert updated.password == "new_pass"
    assert updated.role == "gerente"


def test_delete_user(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test deleting a user."""
    create_result = user_mgmt_ctrl.create_user("delete_me", "pass", "cajero")
    db.commit()
    user_id = create_result["data"]["id"]
    
    result = user_mgmt_ctrl.delete_user(user_id)
    assert result["success"] is True
    
    user_repo = UserRepo(db)
    user = user_repo.find_by_id(user_id)
    assert user is None


def test_is_admin_protected(user_mgmt_ctrl: UserManagementController, admin_user: int) -> None:
    """Test admin user is protected."""
    assert user_mgmt_ctrl.is_admin_protected(admin_user) is True


def test_cannot_delete_admin(user_mgmt_ctrl: UserManagementController, admin_user: int) -> None:
    """Test admin cannot be deleted."""
    result = user_mgmt_ctrl.delete_user(admin_user)
    assert result["success"] is False
    assert "admin" in result["error"].lower()


def test_update_admin_password_allowed(user_mgmt_ctrl: UserManagementController, admin_user: int, db: sqlite3.Connection) -> None:
    """Test updating admin password is allowed but role change is rejected."""
    result = user_mgmt_ctrl.update_user(admin_user, password="new_admin_pass")
    assert result["success"] is True
    
    user_repo = UserRepo(db)
    admin = user_repo.find_by_id(admin_user)
    assert admin.password == "new_admin_pass"

    result2 = user_mgmt_ctrl.update_user(admin_user, role="gerente")
    assert result2["success"] is False
    assert "rol" in result2["error"].lower()


def test_get_user_password(user_mgmt_ctrl: UserManagementController, db: sqlite3.Connection) -> None:
    """Test retrieving user password."""
    create_result = user_mgmt_ctrl.create_user("pass_user", "supersecret", "cajero")
    db.commit()
    user_id = create_result["data"]["id"]
    
    result = user_mgmt_ctrl.get_user_password(user_id)
    assert result["success"] is True
    assert result["data"] == "supersecret"