# Technical Design: Login System with Role-Based Access Control

## Overview

This document specifies the technical implementation of the login system with RBAC for the POS application. It covers database schema, all architecture layers (model, repository, service, controller, view), application flow, permission enforcement, test compatibility, and file organization.

The design strictly follows existing patterns: dataclasses for models, `sqlite3.Connection` injection for repos/services/controllers, `{"success", "data", "error"}` response dicts from controllers, and `set_controller()` wiring in views.

---

## 1. Database Schema Design

### 1.1 New Tables

```sql
-- ================================================================ USERS
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin', 'gerente', 'cajero', 'inventario')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================================== SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    login_time      TEXT NOT NULL DEFAULT (datetime('now')),
    logout_time     TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(logout_time);
```

### 1.2 Migration Strategy

Add as **Migration 7** inside `_run_migrations()` in `pos/model/database.py`:

```python
# Migration 7: Add users and sessions tables for login system
row = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
).fetchone()
if row is None:
    conn.executescript("""
        CREATE TABLE users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('admin', 'gerente', 'cajero', 'inventario')),
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX idx_users_username ON users(username);
        CREATE INDEX idx_users_role ON users(role);

        CREATE TABLE sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            login_time      TEXT NOT NULL DEFAULT (datetime('now')),
            logout_time     TEXT
        );
        CREATE INDEX idx_sessions_user ON sessions(user_id);
        CREATE INDEX idx_sessions_active ON sessions(logout_time);
    """)
```

Also add both `CREATE TABLE IF NOT EXISTS` statements to the `DDL` string so new databases get the tables at creation time.

### 1.3 Admin Bootstrap

After `init_db(conn)` + `conn.commit()` in `main.py`, call `AuthService.bootstrap_admin(conn)`. This method checks if a user with `username='admin'` exists; if not, inserts the hardcoded admin. This is idempotent.

```python
def bootstrap_admin(db: sqlite3.Connection) -> None:
    existing = db.execute(
        "SELECT id FROM users WHERE username = ?", ("admin",)
    ).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO users (username, password, role, is_active) VALUES (?, ?, ?, 1)",
            ("admin", "admin123", "admin"),
        )
        db.commit()
```

---

## 2. Model Layer Design

### 2.1 UserRole Enum

File: `pos/model/enums.py` (add to existing file)

```python
class UserRole(str, Enum):
    """User role for RBAC — maps to CHECK constraint in users table."""
    ADMIN = "admin"
    GERENTE = "gerente"
    CAJERO = "cajero"
    INVENTARIO = "inventario"
```

### 2.2 User Dataclass

File: `pos/model/user.py` (new)

```python
"""User domain dataclass."""

from dataclasses import dataclass
from pos.model.enums import UserRole


@dataclass
class User:
    """An authenticated user account.

    Plain-text password — intentional for school project.
    """
    username: str
    password: str
    role: UserRole | str
    id: int | None = None
    is_active: int = 1
    created_at: str | None = None
```

### 2.3 Session Dataclass

File: `pos/model/user.py` (same file, keeps auth models together)

```python
@dataclass
class Session:
    """An active login session."""
    user_id: int
    id: int | None = None
    login_time: str | None = None
    logout_time: str | None = None
```

### 2.4 Permission Context Dataclass

File: `pos/model/user.py` (same file)

```python
@dataclass
class PermissionContext:
    """Immutable snapshot of what the current user can access.

    Passed from MainWindow to child views at construction time.
    """
    user: User
    allowed_tabs: tuple[str, ...]
    cash_register_mode: str  # "full" | "history_only" | "restricted"
```

---

## 3. Repository Layer Design

### 3.1 UserRepo

File: `pos/repository/user_repo.py` (new)

```python
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

    def find_by_id(self, user_id: int) -> User | None:
        """Return user with *user_id*, or None."""

    def create(self, user: User) -> User:
        """Insert user. Returns user with id populated.
        Raises sqlite3.IntegrityError on duplicate username."""

    def update(self, user: User) -> None:
        """Update password, role, and is_active for existing user."""

    def get_all(self) -> list[User]:
        """Return all users ordered by username."""

    @staticmethod
    def _from_row(row: sqlite3.Row) -> User:
        """Map sqlite3.Row to User dataclass."""
```

All queries parameterized. `_from_row` follows the existing pattern from `SaleRepo._from_row`.

### 3.2 SessionRepo

File: `pos/repository/session_repo.py` (new)

```python
"""Session repository — login/logout tracking."""

import sqlite3
from pos.model.user import Session


class SessionRepo:
    """Data-access for the ``sessions`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def create_session(self, user_id: int) -> Session:
        """Insert session row with logout_time=NULL. Returns Session with id."""

    def close_session(self, user_id: int) -> None:
        """Set logout_time=now for the open session of user_id.
        UPDATE sessions SET logout_time=datetime('now')
        WHERE user_id=? AND logout_time IS NULL"""

    def get_active_session(self, user_id: int) -> Session | None:
        """Return open session (logout_time IS NULL) for user_id, or None."""

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Session:
        """Map sqlite3.Row to Session dataclass."""
```

---

## 4. Service Layer Design

### 4.1 AuthService

File: `pos/service/auth_service.py` (new)

```python
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

    def logout(self, user_id: int) -> None:
        """Close the active session for user_id."""

    def bootstrap_admin(self) -> None:
        """Create hardcoded admin user if not exists. Idempotent."""

    def create_synthetic_admin(self) -> User:
        """Return a synthetic admin User for test mode.
        Does NOT persist to database. Used when POS_TEST_MODE=1."""
```

### 4.2 PermissionService

File: `pos/service/permission_service.py` (new)

```python
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

    def get_permissions(self, user: User) -> PermissionContext:
        """Build a PermissionContext snapshot for the authenticated user.

        This is the main entry point — MainWindow calls this once at
        construction and passes the result to all child views.
        """

    def get_allowed_tabs(self, role: UserRole | str) -> tuple[str, ...]:
        """Return the tuple of tab names the role can see."""

    def get_cash_register_mode(self, role: UserRole | str) -> str:
        """Return 'full', 'history_only', 'restricted', or 'none'."""
```

The `PermissionContext` is built once per login and passed down. This avoids repeated service calls from views and makes the permission snapshot immutable for the session duration.

---

## 5. Controller Layer Design

### 5.1 LoginController

File: `pos/controller/login_controller.py` (new)

```python
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

    def validate_input(self, username: str, password: str) -> dict:
        """Check for empty fields before calling validate.

        Returns:
            {"success": True, "data": None, "error": None}
            or
            {"success": False, "data": None, "error": "Complete todos los campos"}
        """

    def logout(self, user_id: int) -> None:
        """Close session for user_id."""

    def bootstrap_admin(self) -> None:
        """Delegate to AuthService.bootstrap_admin."""
```

### 5.2 UserManagementController

File: `pos/controller/user_management_controller.py` (new)

```python
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

    def list_users(self) -> dict:
        """Return all users as list of dicts."""

    def update_user(self, user_id: int, password: str | None, role: str | None) -> dict:
        """Update user password and/or role."""

    def deactivate_user(self, user_id: int) -> dict:
        """Set is_active=0 for user_id. Cannot deactivate 'admin'."""

    def activate_user(self, user_id: int) -> dict:
        """Set is_active=1 for user_id."""

    def is_admin_protected(self, user_id: int) -> bool:
        """Return True if user_id belongs to the bootstrap admin."""
```

---

## 6. View Layer Design

### 6.1 LoginView

File: `pos/view/login_view.py` (new)

```python
"""Login view — username/password form with error display."""

import tkinter as tk
import customtkinter as ctk
from pos.view import theme


class LoginView(ctk.CTk):
    """Standalone login window displayed before MainWindow.

    Layout (centered, 400x300):
        ┌─────────────────────────────┐
        │     Sistema POS              │
        │                              │
        │  Usuario: [___________]      │
        │  Contrasena: [___________]   │
        │                              │
        │  [  Iniciar sesion  ]        │
        │                              │
        │  (error label, hidden)       │
        └─────────────────────────────┘

    Events:
        - "Iniciar sesion" button click → calls controller
        - Enter key in either field → calls controller
        - controller is set via set_controller(login_controller)
    """

    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 300

    def __init__(self) -> None:
        super().__init__()
        # Build UI widgets
        # Bind Enter key to _on_submit
        # Error label hidden by default

    def set_controller(self, controller) -> None:
        """Store reference to LoginController."""

    def show_error(self, message: str) -> None:
        """Display error label with message, focus username field."""

    def get_username(self) -> str:
        """Return stripped username from entry."""

    def get_password(self) -> str:
        """Return password from entry."""

    def _on_submit(self) -> None:
        """Called on button click or Enter key. Delegates to controller."""
```

The `LoginView` is a standalone `CTk` window (not a frame), similar to `MainWindow`. It is created and destroyed as needed during login/logout cycles.

### 6.2 UserManagementView

File: `pos/view/user_management_view.py` (new)

```python
"""User management view — admin-only user list and create/edit form."""

import customtkinter as ctk


class UserManagementView(ctk.CTkFrame):
    """Admin interface for user CRUD.

    Layout:
        ┌──────────────────────────────────────────┐
        │  [Crear usuario]                          │
        │                                           │
        │  ┌─────────────────────────────────────┐  │
        │  │ Username  │ Role      │ Estado      │  │
        │  │ admin     │ Admin     │ Activo      │  │
        │  │ gerente1  │ Gerente   │ Activo      │  │
        │  │ cajero1   │ Cajero    │ Inactivo    │  │
        │  └─────────────────────────────────────┘  │
        │                                           │
        │  [Editar] [Desactivar]                    │
        └──────────────────────────────────────────┘

    Create/edit form appears as a dialog or inline panel:
        - Username (text, required)
        - Password (text, required for create; optional for edit)
        - Role (dropdown: gerente, cajero, inventario — NOT admin)
    """

    COLUMNS = ("username", "role", "status")
    ROLE_DISPLAY = {
        "admin": "Administrador",
        "gerente": "Gerente",
        "cajero": "Cajero",
        "inventario": "Inventario",
    }

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)

    def set_controller(self, controller) -> None:
        """Store reference to UserManagementController."""

    def refresh_users(self) -> None:
        """Reload user list from controller."""

    def _on_create_clicked(self) -> None:
        """Show create form."""

    def _on_edit_clicked(self) -> None:
        """Show edit form for selected user. Disabled for admin bootstrap."""

    def _on_deactivate_clicked(self) -> None:
        """Toggle active status. Disabled for admin bootstrap."""
```

### 6.3 MainWindow Modifications

File: `pos/view/main_window.py` (modify existing)

**Changes:**

1. **Constructor accepts `PermissionContext`** (optional, defaults to None for backward compat):

```python
def __init__(self, permissions: PermissionContext | None = None) -> None:
```

2. **Top bar** — add user/role label and logout button between the resolution button and the tabview:

```python
# --- User display + logout (top-right area) ---
if permissions is not None:
    role_display = {"admin": "Administrador", "gerente": "Gerente",
                    "cajero": "Cajero", "inventario": "Inventario"}
    self._user_label = ctk.CTkLabel(
        self,
        text=f"{permissions.user.username} - {role_display[permissions.user.role]}",
        font=theme.scaled_font(13, weight="bold"),
    )
    self._user_label.place(relx=1.0, x=-180, y=15, anchor="ne")

    self._logout_btn = ctk.CTkButton(
        self, text="Cerrar sesion", width=120, height=32,
        font=theme.scaled_font(12, weight="bold"),
        fg_color="#8b1a1a", command=self._on_logout,
    )
    self._logout_btn.place(relx=1.0, x=-40, y=15, anchor="ne")
```

3. **Tab filtering** — replace `self.TABS` iteration with `permissions.allowed_tabs`:

```python
tabs_to_create = permissions.allowed_tabs if permissions else self.TABS
# Filter "Usuarios" out of tabview (it's a special tab)
tab_names = [t for t in tabs_to_create if t != "Usuarios"]

for name in tab_names:
    self._tabview.add(name)
    ...
```

4. **"Usuarios" tab** — if `permissions` includes "Usuarios", add it as a tab:

```python
if permissions and "Usuarios" in permissions.allowed_tabs:
    users_tab = self._tabview.add("Usuarios")
    frame = ctk.CTkFrame(users_tab)
    frame.pack(fill="both", expand=True)
    self._tab_frames["Usuarios"] = frame
```

5. **Logout callback** — stored as a callable set by `main.py`:

```python
self._on_logout_callback: Callable | None = None

def set_logout_callback(self, callback) -> None:
    self._on_logout_callback = callback

def _on_logout(self) -> None:
    if self._on_logout_callback:
        self._on_logout_callback()
```

6. **Window close handler** — override `protocol("WM_DELETE_WINDOW")` to close session before exit:

```python
self._on_close_callback: Callable | None = None

def set_close_callback(self, callback) -> None:
    self._on_close_callback = callback
    self.protocol("WM_DELETE_WINDOW", self._on_window_close)

def _on_window_close(self) -> None:
    if self._on_close_callback:
        self._on_close_callback()
    self.destroy()
```

### 6.4 CashRegisterView Modifications

File: `pos/view/cash_register_view.py` (modify existing)

**Changes:**

Constructor accepts optional `cash_register_mode` parameter:

```python
def __init__(self, master, callbacks=None, cash_register_mode: str = "full", **kwargs):
```

After building all widgets, apply mode-based visibility:

```python
def _apply_permission_mode(self, mode: str) -> None:
    if mode == "history_only":
        # Gerente: hide open/close buttons, outflow form
        # Keep: balance panel (read-only), history treeview, movement preview
        self._open_btn.pack_forget()
        self._close_btn.pack_forget()
        self._outflow_frame.grid_remove()
        # _preview_frame remains visible for viewing movements of selected register
    elif mode == "restricted":
        # Cajero: hide history, diferencia, esperado
        self._history_frame.grid_remove()
        # Hide "Esperado:" and "Diferencia:" labels and values
        for key in ("expected", "difference"):
            self._balance_labels[key].grid_remove()
            # Also remove the corresponding label (find by grid position)
    # mode == "full": no changes (admin)
```

The key insight: widgets are created normally, then hidden via `grid_remove()` / `pack_forget()`. This preserves all existing logic — no conditional branches in event handlers.

### 6.5 ProductView Modifications

File: `pos/view/product_view.py` (modify existing)

**Changes:**

Constructor accepts optional `role` parameter:

```python
def __init__(self, master, callbacks=None, role: str | None = None, **kwargs):
```

For `inventario` role, all CRUD buttons and features remain visible (identical to admin). No hiding needed — the permission is enforced at the tab level (only `inventario` and `admin`/`gerente` see the Productos tab).

The `role` parameter is stored for potential future field-level restrictions but currently requires no UI changes since `inventario` has full CRUD access to Productos.

---

## 7. Application Flow Design

### 7.1 Modified `main.py` Flow

```python
def main() -> None:
    conn = get_connection()
    try:
        init_db(conn)
        conn.commit()

        from pos.view.theme import load_font_scale
        load_font_scale(conn)

        # --- Auth setup ---
        from pos.controller.login_controller import LoginController
        login_ctrl = LoginController(conn)
        login_ctrl.bootstrap_admin()

        # --- Test mode bypass ---
        import os
        test_mode = os.environ.get("POS_TEST_MODE") == "1"

        if test_mode:
            _launch_with_user(conn, login_ctrl, synthetic_admin=True)
        else:
            _run_login_loop(conn, login_ctrl)
    finally:
        conn.close()


def _run_login_loop(conn, login_ctrl) -> None:
    """Show LoginView. On success, launch MainWindow. On logout, loop back."""
    from pos.view.login_view import LoginView

    while True:
        login_view = LoginView()
        login_view.set_controller(login_ctrl)

        # Block until login succeeds or window is closed
        result = _wait_for_login(login_view, login_ctrl)

        if result is None:
            break  # User closed login window

        user, permissions = result
        should_continue = _launch_with_user(conn, login_ctrl, user=user, permissions=permissions)

        if not should_continue:
            break  # User closed app (not just logout)


def _launch_with_user(conn, login_ctrl, *, user=None, permissions=None,
                       synthetic_admin=False) -> bool:
    """Launch MainWindow with authenticated user. Returns True if should loop back (logout)."""
    from pos.service.permission_service import PermissionService

    if synthetic_admin:
        from pos.model.user import User
        from pos.model.enums import UserRole
        user = User(id=0, username="admin", password="", role=UserRole.ADMIN)

    perm_service = PermissionService()
    permissions = perm_service.get_permissions(user)

    # --- Build MainWindow ---
    from pos.view.main_window import MainWindow
    app = MainWindow(permissions=permissions)
    app._apply_current_theme()

    # --- Wire controllers and views (filtered by permissions) ---
    _wire_views(conn, app, permissions)

    # --- Set logout callback ---
    def on_logout():
        login_ctrl.logout(user.id)
        app.destroy()

    def on_window_close():
        login_ctrl.logout(user.id)
        app.destroy()

    app.set_logout_callback(on_logout)
    app.set_close_callback(on_window_close)

    app.mainloop()
    return True  # Signal to re-enter login loop
```

### 7.2 View Wiring (Filtered)

```python
def _wire_views(conn, app, permissions) -> None:
    """Instantiate and wire controllers/views for permitted tabs only."""
    from pos.controller.sale_controller import SaleController
    from pos.controller.product_controller import ProductController
    from pos.controller.cash_register_controller import CashRegisterController
    from pos.controller.return_controller import ReturnController
    from pos.controller.report_controller import ReportController
    from pos.controller.user_management_controller import UserManagementController

    from pos.view.sale_view import SaleView
    from pos.view.product_view import ProductView
    from pos.view.return_view import ReturnView
    from pos.view.cash_register_view import CashRegisterView
    from pos.view.report_view import ReportView
    from pos.view.user_management_view import UserManagementView

    role = permissions.user.role
    cash_mode = permissions.cash_register_mode

    # Ventas
    if "Ventas" in permissions.allowed_tabs:
        sale_ctrl = SaleController(conn)
        sales_tab = app.get_tab_frame("Ventas")
        sale_view = SaleView(sales_tab)
        sale_view.pack(fill="both", expand=True)
        sale_view.set_controller(sale_ctrl)
        app.set_view("Ventas", sale_view)
        app.set_controller("Ventas", sale_ctrl)

    # Productos
    if "Productos" in permissions.allowed_tabs:
        product_ctrl = ProductController(conn)
        products_tab = app.get_tab_frame("Productos")
        product_view = ProductView(products_tab, role=role)
        product_view.pack(fill="both", expand=True)
        product_view.set_controller(product_ctrl)
        app.set_view("Productos", product_view)
        app.set_controller("Productos", product_ctrl)

    # Devoluciones
    if "Devoluciones" in permissions.allowed_tabs:
        return_ctrl = ReturnController(conn)
        returns_tab = app.get_tab_frame("Devoluciones")
        return_view = ReturnView(returns_tab)
        return_view.pack(fill="both", expand=True)
        return_view.set_controller(return_ctrl)
        app.set_view("Devoluciones", return_view)
        app.set_controller("Devoluciones", return_ctrl)

    # Caja
    if "Caja" in permissions.allowed_tabs:
        cash_register_ctrl = CashRegisterController(conn)
        cash_tab = app.get_tab_frame("Caja")
        cash_register_view = CashRegisterView(cash_tab, cash_register_mode=cash_mode)
        cash_register_view.pack(fill="both", expand=True)
        cash_register_view.set_controller(cash_register_ctrl)
        app.set_view("Caja", cash_register_view)
        app.set_controller("Caja", cash_register_ctrl)

    # Reportes
    if "Reportes" in permissions.allowed_tabs:
        report_ctrl = ReportController(conn)
        reports_tab = app.get_tab_frame("Reportes")
        report_view = ReportView(reports_tab)
        report_view.pack(fill="both", expand=True)
        report_view.set_controller(report_ctrl)
        app.set_view("Reportes", report_view)
        app.set_controller("Reportes", report_ctrl)

    # Usuarios (admin only)
    if "Usuarios" in permissions.allowed_tabs:
        user_mgmt_ctrl = UserManagementController(conn)
        users_tab = app.get_tab_frame("Usuarios")
        user_mgmt_view = UserManagementView(users_tab)
        user_mgmt_view.pack(fill="both", expand=True)
        user_mgmt_view.set_controller(user_mgmt_ctrl)
        app.set_view("Usuarios", user_mgmt_view)
        app.set_controller("Usuarios", user_mgmt_ctrl)

    # Cross-view wiring (only for views that exist)
    sale_view = app._views.get("Ventas")
    cash_view = app._views.get("Caja")
    return_view = app._views.get("Devoluciones")
    product_view = app._views.get("Productos")

    if sale_view and cash_view:
        sale_view._on_sale_completed = cash_view._controller_refresh
    if return_view and cash_view:
        return_view._on_return_completed = cash_view._controller_refresh
    if sale_view and product_view:
        sale_view._on_product_created = product_view._refresh_products
    if product_view:
        app.on_tab_change("Productos", product_view._refresh_products)
```

### 7.3 User Context Flow

```
LoginView → LoginController.validate()
    → AuthService.login() → UserRepo.find_by_username() → check password + is_active
    → SessionRepo.create_session()
    → PermissionService.get_permissions(user) → PermissionContext
    → return PermissionContext to main.py

main.py → MainWindow(permissions=PermissionContext)
    → MainWindow reads permissions.allowed_tabs to filter tabs
    → MainWindow displays permissions.user.username + role in top bar
    → main.py passes cash_register_mode to CashRegisterView
    → main.py passes role to ProductView
    → PermissionContext is the single source of truth for the session
```

---

## 8. Permission Enforcement Strategy

### 8.1 Tab Visibility

`MainWindow` receives `PermissionContext` at construction. The tab list is derived from `permissions.allowed_tabs`. Tabs not in the list are never added to the `CTkTabview`, so they cannot be rendered or focused.

### 8.2 Field-Level Restrictions

| View | Role | What changes | Mechanism |
|------|------|-------------|-----------|
| CashRegisterView | gerente | Hide open/close buttons, outflow form. Keep history + movement preview | `grid_remove()` / `pack_forget()` after widget creation |
| CashRegisterView | cajero | Hide history treeview, "Esperado" and "Diferencia" balance rows | `grid_remove()` after widget creation |
| ProductView | inventario | No changes — full CRUD visible | Tab-level restriction only |

### 8.3 Permission Context Delivery

Permissions flow via **constructor parameters**:
- `MainWindow(permissions=PermissionContext)` — tab filtering + user display
- `CashRegisterView(master, cash_register_mode="history_only")` — field hiding
- `ProductView(master, role="inventario")` — future-proofing (currently no UI changes)

This avoids service calls from within views. The view layer is "dumb" — it receives a mode string and applies visibility rules.

### 8.4 Edge Cases

**Permission changes mid-session**: Not handled. Permissions are snapshotted at login. If an admin changes a user's role while they're logged in, the change takes effect on next login. This is acceptable per spec ("the permission matrix reflects the new role on next login").

**Deactivated user mid-session**: Per spec, "Deactivating a user with an open session SHALL NOT terminate the session immediately (the session ends on next login attempt)." The deactivation blocks future logins, not the current session.

**Multiple concurrent sessions**: The spec allows one open session per user (`logout_time IS NULL`). If a user logs in from a second window, `SessionRepo.create_session` creates a second row. On logout, `close_session` closes ALL open sessions for that user (UPDATE WHERE user_id=? AND logout_time IS NULL).

---

## 9. Test Compatibility Strategy

### 9.1 Test Mode Flag

Two activation mechanisms (OR):
1. **Environment variable**: `POS_TEST_MODE=1` — checked in `main.py`
2. **Constructor parameter**: `LoginController(conn, test_mode=True)` — for programmatic use

When test mode is active:
- `main.py` skips `LoginView` entirely
- Creates a synthetic `User(id=0, username="admin", role=UserRole.ADMIN)`
- Creates a `PermissionContext` with all tabs allowed
- Launches `MainWindow` directly

### 9.2 Existing Tests Bypass

Existing tests in `conftest.py` use the `db` fixture which creates an in-memory SQLite with `DDL`. Since the new tables are added to `DDL`, they exist in test databases. However, existing tests never instantiate controllers that require auth — they test repos, services, and controllers directly.

**No changes needed to existing test files.** The 21 test files test:
- Repositories (direct SQL) — no auth dependency
- Services (business logic) — no auth dependency
- Controllers (cart, sale flow) — no auth dependency

The `DDL` string now includes `users` and `sessions` tables, but this is additive and doesn't affect existing table schemas.

### 9.3 conftest.py Update

The `db` fixture already runs `DDL`. Since `users` and `sessions` are added to `DDL`, they are automatically created in test databases. No fixture changes needed.

If future tests need a logged-in user, add a helper fixture:

```python
@pytest.fixture
def admin_user(db):
    """Insert admin user and return id."""
    cur = db.execute(
        "INSERT INTO users (username, password, role, is_active) VALUES (?, ?, ?, 1) RETURNING id",
        ("admin", "admin123", "admin"),
    )
    db.commit()
    return cur.fetchone()["id"]
```

---

## 10. File Organization

### 10.1 New Files (9 files)

| Path | Purpose |
|------|---------|
| `pos/model/user.py` | `User`, `Session`, `PermissionContext` dataclasses |
| `pos/repository/user_repo.py` | CRUD for `users` table |
| `pos/repository/session_repo.py` | Session lifecycle for `sessions` table |
| `pos/service/auth_service.py` | Login/logout/bootstrap logic |
| `pos/service/permission_service.py` | Hardcoded permission matrix |
| `pos/controller/login_controller.py` | Login flow orchestration |
| `pos/controller/user_management_controller.py` | Admin user CRUD |
| `pos/view/login_view.py` | Login form window |
| `pos/view/user_management_view.py` | Admin user management UI |

### 10.2 Modified Files (5 files)

| Path | Changes |
|------|---------|
| `pos/model/enums.py` | Add `UserRole` enum |
| `pos/model/database.py` | Add `users` + `sessions` to DDL + Migration 7 |
| `pos/main.py` | Login gate, test mode bypass, login loop, view wiring |
| `pos/view/main_window.py` | PermissionContext param, user label, logout button, tab filtering, close callback |
| `pos/view/cash_register_view.py` | `cash_register_mode` param, conditional visibility |
| `pos/view/product_view.py` | `role` param (stored, no UI change for now) |

### 10.3 Import Dependencies

```
pos/model/enums.py          ← UserRole (no deps)
pos/model/user.py           ← User, Session, PermissionContext (depends on enums)
pos/repository/user_repo.py ← UserRepo (depends on user, enums)
pos/repository/session_repo.py ← SessionRepo (depends on user)
pos/service/auth_service.py ← AuthService (depends on user_repo, session_repo)
pos/service/permission_service.py ← PermissionService (depends on user, enums)
pos/controller/login_controller.py ← LoginController (depends on auth_service, permission_service)
pos/controller/user_management_controller.py ← UserManagementController (depends on user_repo)
pos/view/login_view.py      ← LoginView (standalone CTk window)
pos/view/user_management_view.py ← UserManagementView (CTkFrame)
pos/view/main_window.py     ← MainWindow (accepts PermissionContext)
pos/view/cash_register_view.py ← CashRegisterView (accepts cash_register_mode)
pos/view/product_view.py    ← ProductView (accepts role)
pos/main.py                 ← Entry point (wires everything)
```

**No circular dependencies.** The dependency graph is strictly acyclic:
- Models → no internal deps
- Repos → Models
- Services → Repos, Models
- Controllers → Services, Repos, Models
- Views → (no direct dependency on controllers; use `set_controller()`)
- `main.py` → everything (top-level wiring)

---

## Sequence Diagrams

### Login Flow

```
User            LoginView           LoginController       AuthService          UserRepo         SessionRepo       PermissionService
 │                 │                      │                    │                   │                  │                  │
 │  enter creds    │                      │                    │                   │                  │                  │
 │────────────────>│                      │                    │                   │                  │                  │
 │                 │  validate(u, p)      │                    │                   │                  │                  │
 │                 │─────────────────────>│                    │                   │                  │                  │
 │                 │                      │  login(u, p)      │                   │                  │                  │
 │                 │                      │───────────────────>│                   │                  │                  │
 │                 │                      │                    │ find_by_username  │                  │                  │
 │                 │                      │                    │──────────────────>│                  │                  │
 │                 │                      │                    │     user row      │                  │                  │
 │                 │                      │                    │<──────────────────│                  │                  │
 │                 │                      │                    │ check password + is_active           │                  │
 │                 │                      │                    │ create_session    │                  │                  │
 │                 │                      │                    │─────────────────────────────────────>│                  │
 │                 │                      │                    │     session       │                  │                  │
 │                 │                      │                    │<─────────────────────────────────────│                  │
 │                 │                      │  get_permissions   │                   │                  │                  │
 │                 │                      │────────────────────────────────────────────────────────────────────────────>│
 │                 │                      │  PermissionContext │                   │                  │                  │
 │                 │                      │<────────────────────────────────────────────────────────────────────────────│
 │                 │  {success, data}     │                    │                   │                  │                  │
 │                 │<─────────────────────│                    │                   │                  │                  │
 │                 │                      │                    │                   │                  │                  │
 │                 │  close + return      │                    │                   │                  │                  │
 │  LoginView closes ──────────────────── main.py creates MainWindow(permissions) ──────────────────────────────────────>│
```

### Logout Flow

```
User            MainWindow          main.py              LoginController      AuthService        SessionRepo
 │                 │                    │                      │                   │                  │
 │  click logout   │                    │                      │                   │                  │
 │────────────────>│                    │                      │                   │                  │
 │                 │  on_logout_cb()    │                      │                   │                  │
 │                 │───────────────────>│                      │                   │                  │
 │                 │                    │  logout(user_id)     │                   │                  │
 │                 │                    │─────────────────────>│                   │                  │
 │                 │                    │                      │  close_session    │                  │
 │                 │                    │                      │───────────────────│─────────────────>│
 │                 │                    │                      │                   │  UPDATE logout_time
 │                 │  destroy()         │                      │                   │                  │
 │                 │───────────────────>│                      │                   │                  │
 │                 │                    │  (loop back)         │                   │                  │
 │                 │                    │  create LoginView    │                   │                  │
```

---

## Summary of Design Decisions

| Decision | Rationale |
|----------|-----------|
| PermissionContext as immutable snapshot | Avoids repeated service calls; views receive a simple data structure |
| Constructor parameter injection for views | Follows existing pattern (views receive callbacks via constructor) |
| `grid_remove()` for field hiding | Preserves all widget logic; no conditional branches in handlers |
| Login loop in `main.py` (while True) | Clean separation: login → main window → logout → login → ... |
| Synthetic admin for test mode | Zero changes to existing 21 test files |
| Admin bootstrap in `init_db` flow | Idempotent, runs on every start, no separate migration step |
| `UserRole(str, Enum)` | Follows existing pattern (`PaymentMethod`, `MovementType`) |
| No password hashing | Per spec — school project, intentional |
| Session per user (not per window) | Matches spec: "only one session row may have logout_time=NULL per user" |
