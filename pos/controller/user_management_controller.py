"""User management controller — admin CRUD for users."""

import sqlite3
from pos.repository.user_repo import UserRepo
from pos.model.user import User
from pos.model.enums import UserRole


class UserManagementController:
    """Admin-only user CRUD. All methods return the standard response dict."""

    ADMIN_USERNAME = "admin"

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._user_repo = UserRepo(db)

    def create_user(self, username: str, password: str, role: str) -> dict:
        """Create a new user.

        Returns:
            {"success": True, "data": user_dict, "error": None}
            or {"success": False, "data": None, "error": message}

        Validates: non-empty fields, unique username, role not 'admin'.
        On IntegrityError → "El nombre de usuario ya existe".
        """
        if not username.strip() or not password.strip():
            return {"success": False, "data": None, "error": "Complete todos los campos"}
        if role == "admin":
            return {"success": False, "data": None, "error": "No se puede crear un usuario admin"}
        user = User(username=username.strip(), password=password, role=role, is_active=1)
        try:
            created = self._user_repo.create(user)
            self._db.commit()
            return {
                "success": True,
                "data": {
                    "id": created.id,
                    "username": created.username,
                    "role": created.role,
                    "is_active": created.is_active,
                },
                "error": None,
            }
        except sqlite3.IntegrityError:
            return {"success": False, "data": None, "error": "El nombre de usuario ya existe"}

    def list_users(self) -> dict:
        """Return all users as list of dicts."""
        users = self._user_repo.get_all()
        data = []
        for u in users:
            role_val = u.role.value if isinstance(u.role, UserRole) else u.role
            data.append({
                "id": u.id,
                "username": u.username,
                "role": role_val,
                "is_active": u.is_active,
            })
        return {"success": True, "data": data, "error": None}

    def update_user(self, user_id: int, password: str | None = None, role: str | None = None) -> dict:
        """Update user password and/or role."""
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return {"success": False, "data": None, "error": "Usuario no encontrado"}
        if self.is_admin_protected(user_id):
            return {"success": False, "data": None, "error": "No se puede modificar el usuario admin"}
        if password is not None:
            user.password = password
        if role is not None:
            user.role = role
        self._user_repo.update(user)
        self._db.commit()
        return {"success": True, "data": None, "error": None}

    def deactivate_user(self, user_id: int) -> dict:
        """Set is_active=0 for user_id. Cannot deactivate 'admin'."""
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return {"success": False, "data": None, "error": "Usuario no encontrado"}
        if self.is_admin_protected(user_id):
            return {"success": False, "data": None, "error": "No se puede desactivar el usuario admin"}
        user.is_active = 0
        self._user_repo.update(user)
        self._db.commit()
        return {"success": True, "data": None, "error": None}

    def activate_user(self, user_id: int) -> dict:
        """Set is_active=1 for user_id."""
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return {"success": False, "data": None, "error": "Usuario no encontrado"}
        user.is_active = 1
        self._user_repo.update(user)
        self._db.commit()
        return {"success": True, "data": None, "error": None}

    def is_admin_protected(self, user_id: int) -> bool:
        """Return True if user_id belongs to the bootstrap admin."""
        user = self._user_repo.find_by_id(user_id)
        if user is None:
            return False
        return user.username == self.ADMIN_USERNAME