"""Login controller — orchestrates the login flow."""

import sqlite3
from pos.service.auth_service import AuthService
from pos.service.permission_service import PermissionService
from pos.model.user import User, PermissionContext


class LoginController:
    """Orchestrates credential validation → session creation → permission context.

    The view calls validate() on submit. On success, the controller returns
    the PermissionContext that MainWindow needs. The view layer (main.py)
    handles the LoginView → MainWindow transition.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._auth_service = AuthService(db)
        self._permission_service = PermissionService()

    def validate(self, username: str, password: str) -> dict:
        """Validate credentials.

        Returns:
            {"success": True, "data": {"user": User, "permissions": PermissionContext}, "error": None}
            or
            {"success": False, "data": None, "error": "Usuario o contrasena incorrectos"}
        """
        user = self._auth_service.login(username, password)
        if user is None:
            return {"success": False, "data": None, "error": "Usuario o contrasena incorrectos"}
        permissions = self._permission_service.get_permissions(user)
        return {
            "success": True,
            "data": {"user": user, "permissions": permissions},
            "error": None,
        }

    def validate_input(self, username: str, password: str) -> dict:
        """Check for empty fields before calling validate.

        Returns:
            {"success": True, "data": None, "error": None}
            or
            {"success": False, "data": None, "error": "Complete todos los campos"}
        """
        if not username.strip() or not password.strip():
            return {"success": False, "data": None, "error": "Complete todos los campos"}
        return {"success": True, "data": None, "error": None}

    def logout(self, user_id: int) -> None:
        """Close session for user_id."""
        self._auth_service.logout(user_id)

    def bootstrap_admin(self) -> None:
        """Delegate to AuthService.bootstrap_admin."""
        self._auth_service.bootstrap_admin()