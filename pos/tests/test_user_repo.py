"""Tests for UserRepo — CRUD operations on users table."""

import pytest
import sqlite3
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


@pytest.fixture
def user_repo(db: sqlite3.Connection) -> UserRepo:
    """Return a UserRepo instance."""
    return UserRepo(db)


def test_create_user(user_repo: UserRepo) -> None:
    """Test creating a new user."""
    user = User(username="testuser", password="pass123", role=UserRole.CAJERO, is_active=1)
    created = user_repo.create(user)
    assert created.id is not None
    assert created.username == "testuser"
    assert created.created_at is not None


def test_find_by_username(user_repo: UserRepo) -> None:
    """Test finding user by username."""
    user = User(username="findme", password="pass", role=UserRole.GERENTE)
    user_repo.create(user)
    
    found = user_repo.find_by_username("findme")
    assert found is not None
    assert found.username == "findme"
    assert found.role == "gerente"


def test_find_by_username_not_found(user_repo: UserRepo) -> None:
    """Test finding non-existent user returns None."""
    found = user_repo.find_by_username("ghost")
    assert found is None


def test_find_by_id(user_repo: UserRepo) -> None:
    """Test finding user by ID."""
    user = User(username="byid", password="pass", role=UserRole.INVENTARIO)
    created = user_repo.create(user)
    
    found = user_repo.find_by_id(created.id)
    assert found is not None
    assert found.username == "byid"


def test_find_by_id_not_found(user_repo: UserRepo) -> None:
    """Test finding non-existent user ID returns None."""
    found = user_repo.find_by_id(9999)
    assert found is None


def test_update_user(user_repo: UserRepo, db: sqlite3.Connection) -> None:
    """Test updating user password and role."""
    user = User(username="update_me", password="old", role=UserRole.CAJERO)
    created = user_repo.create(user)
    db.commit()
    
    created.password = "new"
    created.role = UserRole.GERENTE
    user_repo.update(created)
    db.commit()
    
    updated = user_repo.find_by_id(created.id)
    assert updated.password == "new"
    assert updated.role == "gerente"


def test_get_all(user_repo: UserRepo, db: sqlite3.Connection) -> None:
    """Test getting all users."""
    user_repo.create(User(username="alpha", password="p", role=UserRole.CAJERO))
    user_repo.create(User(username="beta", password="p", role=UserRole.GERENTE))
    user_repo.create(User(username="gamma", password="p", role=UserRole.INVENTARIO))
    db.commit()
    
    users = user_repo.get_all()
    assert len(users) == 3
    # Should be ordered by username
    assert users[0].username == "alpha"
    assert users[1].username == "beta"
    assert users[2].username == "gamma"


def test_duplicate_username_raises(user_repo: UserRepo) -> None:
    """Test that duplicate username raises IntegrityError."""
    user_repo.create(User(username="duplicate", password="p", role=UserRole.CAJERO))
    
    with pytest.raises(sqlite3.IntegrityError):
        user_repo.create(User(username="duplicate", password="p2", role=UserRole.GERENTE))