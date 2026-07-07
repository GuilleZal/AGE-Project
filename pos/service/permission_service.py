"""Permission service — hardcoded role-to-permission matrix."""

from pos.model.enums import UserRole
from pos.model.user import PermissionContext, User


class PermissionService:
    """Maps roles to module access levels. No database dependency.

    Permission matrix (hardcoded):
        admin       → all modules, full access
        gerente     → Productos (full), Caja (history_only), Reportes (full)
        cajero      → Ventas (full), Devoluciones (full), Caja (restricted)
        inventario  → Productos (full CRUD)
    """

    _TAB_PERMISSIONS: dict[str, tuple[str, ...]] = {
        "admin":      ("Ventas", "Productos", "Devoluciones", "Caja", "Reportes", "Usuarios"),
        "gerente":    ("Productos", "Caja", "Reportes"),
        "cajero":     ("Ventas", "Devoluciones", "Caja"),
        "inventario": ("Productos",),
    }

    _CASH_MODE: dict[str, str] = {
        "admin":      "full",
        "gerente":    "history_only",
        "cajero":     "restricted",
        "inventario": "none",
    }

    def can_access(self, role: UserRole | str, module: str) -> bool:
        """Return True if role has access to module."""
        role_val = role.value if isinstance(role, UserRole) else role
        return module in self._TAB_PERMISSIONS.get(role_val, ())

    def get_permissions(self, user: User) -> PermissionContext:
        """Build a PermissionContext snapshot for the authenticated user.

        This is the main entry point — MainWindow calls this once at
        construction and passes the result to all child views.
        """
        role_val = user.role.value if isinstance(user.role, UserRole) else user.role
        allowed_tabs = self._TAB_PERMISSIONS.get(role_val, ())
        cash_mode = self._CASH_MODE.get(role_val, "none")
        return PermissionContext(
            user=user,
            allowed_tabs=allowed_tabs,
            cash_register_mode=cash_mode,
        )

    def get_allowed_tabs(self, role: UserRole | str) -> tuple[str, ...]:
        """Return the tuple of tab names the role can see."""
        role_val = role.value if isinstance(role, UserRole) else role
        return self._TAB_PERMISSIONS.get(role_val, ())

    def get_cash_register_mode(self, role: UserRole | str) -> str:
        """Return 'full', 'history_only', 'restricted', or 'none'."""
        role_val = role.value if isinstance(role, UserRole) else role
        return self._CASH_MODE.get(role_val, "none")