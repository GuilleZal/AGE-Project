"""POS Sales System — Entry point.

Initializes the SQLite database (schema creation is idempotent) and
launches the CustomTkinter main window with all controllers wired
to their respective views.

Usage:
    python -m pos.main
    python pos/main.py
"""

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `pos` is importable
# when executed as `python pos/main.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pos.model.database import get_connection, init_db


def main() -> None:
    """Bootstrap the application: init DB, instantiate controllers, launch UI."""
    conn = get_connection()
    try:
        init_db(conn)
        conn.commit()
        print("Database initialized successfully at pos/data/pos.db")

        from pos.view.theme import load_font_scale
        load_font_scale(conn)

        # --- Auth setup ---
        from pos.controller.login_controller import LoginController
        login_ctrl = LoginController(conn)
        login_ctrl.bootstrap_admin()

        # --- Test mode bypass ---
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
        
        # Track if login was successful
        login_success = False
        
        def on_login_success():
            nonlocal login_success
            login_success = True
        
        login_view.set_success_callback(on_login_success)

        # Block until login succeeds or window is closed
        login_view.mainloop()

        # If user closed window without logging in, exit
        if not login_success:
            break

        # Get validated user data from controller
        username = login_view.get_username()
        password = login_view.get_password()
        result = login_ctrl.validate(username, password)

        # Safely destroy login window
        try:
            if login_view.winfo_exists():
                login_view.destroy()
        except Exception:
            pass

        if not result["success"]:
            break

        user = result["data"]["user"]
        permissions = result["data"]["permissions"]
        should_continue = _launch_with_user(
            conn, login_ctrl, user=user, permissions=permissions
        )

        if not should_continue:
            break


def _launch_with_user(
    conn,
    login_ctrl,
    *,
    user=None,
    permissions=None,
    synthetic_admin=False,
) -> bool:
    """Launch MainWindow with authenticated user. Returns True if should loop back."""
    from pos.service.permission_service import PermissionService
    from pos.model.user import User
    from pos.model.enums import UserRole

    if synthetic_admin:
        user = User(id=0, username="admin", password="", role=UserRole.ADMIN)

    perm_service = PermissionService()
    permissions = perm_service.get_permissions(user)

    # --- Build MainWindow ---
    from pos.view.main_window import MainWindow
    app = MainWindow(permissions=permissions)

    # Apply saved theme (background color and contrast)
    app._apply_current_theme()

    # --- Wire controllers and views (filtered by permissions) ---
    _wire_views(conn, app, permissions)

    # --- Set logout callback ---
    def on_logout():
        if user.id and user.id > 0:
            login_ctrl.logout(user.id)
        try:
            if app.winfo_exists():
                app.destroy()
        except Exception:
            pass

    def on_window_close():
        if user.id and user.id > 0:
            login_ctrl.logout(user.id)
        try:
            if app.winfo_exists():
                app.destroy()
        except Exception:
            pass

    app.set_logout_callback(on_logout)
    app.set_close_callback(on_window_close)

    app.mainloop()
    return True


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
    role_val = role.value if hasattr(role, 'value') else role
    cash_mode = permissions.cash_register_mode

    # Ventas
    if "Ventas" in permissions.allowed_tabs:
        sale_ctrl = SaleController(conn)
        sales_tab = app.get_tab_frame("Ventas")
        if sales_tab is not None:
            sale_view = SaleView(sales_tab)
            sale_view.pack(fill="both", expand=True)
            sale_view.set_controller(sale_ctrl)
            app.set_view("Ventas", sale_view)
            app.set_controller("Ventas", sale_ctrl)

    # Productos
    if "Productos" in permissions.allowed_tabs:
        product_ctrl = ProductController(conn)
        products_tab = app.get_tab_frame("Productos")
        if products_tab is not None:
            product_view = ProductView(products_tab, role=role_val)
            product_view.pack(fill="both", expand=True)
            product_view.set_controller(product_ctrl)
            app.set_view("Productos", product_view)
            app.set_controller("Productos", product_ctrl)

    # Devoluciones
    if "Devoluciones" in permissions.allowed_tabs:
        return_ctrl = ReturnController(conn)
        returns_tab = app.get_tab_frame("Devoluciones")
        if returns_tab is not None:
            return_view = ReturnView(returns_tab)
            return_view.pack(fill="both", expand=True)
            return_view.set_controller(return_ctrl)
            app.set_view("Devoluciones", return_view)
            app.set_controller("Devoluciones", return_ctrl)

    # Caja
    if "Caja" in permissions.allowed_tabs:
        cash_register_ctrl = CashRegisterController(conn)
        cash_tab = app.get_tab_frame("Caja")
        if cash_tab is not None:
            cash_register_view = CashRegisterView(cash_tab, cash_register_mode=cash_mode)
            cash_register_view.pack(fill="both", expand=True)
            cash_register_view.set_controller(cash_register_ctrl)
            app.set_view("Caja", cash_register_view)
            app.set_controller("Caja", cash_register_ctrl)

    # Reportes
    if "Reportes" in permissions.allowed_tabs:
        report_ctrl = ReportController(conn)
        reports_tab = app.get_tab_frame("Reportes")
        if reports_tab is not None:
            report_view = ReportView(reports_tab)
            report_view.pack(fill="both", expand=True)
            report_view.set_controller(report_ctrl)
            app.set_view("Reportes", report_view)
            app.set_controller("Reportes", report_ctrl)

    # Usuarios (admin only)
    if "Usuarios" in permissions.allowed_tabs:
        user_mgmt_ctrl = UserManagementController(conn)
        users_tab = app.get_tab_frame("Usuarios")
        if users_tab is not None:
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


if __name__ == "__main__":
    main()
