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
            _launch_test_mode(conn, login_ctrl)
        else:
            _run_login_loop(conn, login_ctrl)
    finally:
        conn.close()


def _run_login_loop(conn, login_ctrl) -> None:
    """Show LoginView. On success, launch MainWindow. On logout, loop back."""
    import customtkinter as ctk
    from pos.view.login_view import LoginView
    
    # Create a persistent root window that never gets destroyed
    # This prevents "no default root window" errors when recreating windows
    _root = ctk.CTk()
    _root.withdraw()  # Hide it - it's just a Tkinter root anchor

    # Silence Tcl background errors (e.g. pending animation timers firing on destroyed widgets)
    try:
        _root.tk.call("proc", "bgerror", "msg", "")
    except Exception:
        pass

    while True:
        # Create LoginView as a Toplevel of the persistent root
        login_view = LoginView(_root)
        login_view.set_controller(login_ctrl)
        
        # Track if login was successful
        login_success = False
        user_data = None
        
        def on_login_success(user, permissions):
            nonlocal login_success, user_data
            login_success = True
            user_data = {"user": user, "permissions": permissions}
        
        login_view.set_success_callback(on_login_success)

        # Wait for login window to close (uses wait_window instead of mainloop)
        login_view.grab_set()
        _root.wait_window(login_view)

        # If user closed window without logging in, exit
        if not login_success:
            break

        user = user_data["user"]
        permissions = user_data["permissions"]
        
        # Create MainWindow BEFORE destroying LoginView
        app = _create_main_window(conn, login_ctrl, user, permissions)
        
        # NOW destroy login window
        try:
            login_view.destroy()
        except Exception:
            pass
        
        # Run MainWindow
        app.mainloop()
        
        # After logout/close, destroy MainWindow
        try:
            app.update_idletasks()
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
    
    # Clean up the persistent root
    try:
        _root.destroy()
    except Exception:
        pass


def _create_main_window(conn, login_ctrl, user, permissions):
    """Create and configure MainWindow with all controllers wired."""
    from pos.view.main_window import MainWindow
    
    # MainWindow is a CTk root window (independent from the manager root)
    app = MainWindow(permissions=permissions)
    
    # Silence background errors for this window's Tcl interpreter
    try:
        app.tk.call("proc", "bgerror", "msg", "")
    except Exception:
        pass
        
    _wire_views(conn, app, permissions)
    app._apply_current_theme()
    
    def check_active_register() -> bool:
        role_val = user.role.value if hasattr(user.role, 'value') else user.role
        if role_val == "cajero":
            from pos.repository.cash_register_repo import CashRegisterRepo
            register_repo = CashRegisterRepo(conn)
            active_reg = register_repo.find_active()
            if active_reg is not None:
                from tkinter import messagebox
                confirm = messagebox.askyesno(
                    "Turno de caja activo",
                    "Tienes un turno de caja activo. ¿Seguro que deseas salir del sistema sin realizar el cierre de la caja?",
                    parent=app
                )
                return confirm
        return True

    # Set callbacks - only quit mainloop, don't destroy
    def on_logout():
        if not check_active_register():
            return False
        if user.id and user.id > 0:
            login_ctrl.logout(user.id)
        app.quit()
    
    def on_window_close():
        if not check_active_register():
            return False
        if user.id and user.id > 0:
            login_ctrl.logout(user.id)
        app.quit()
    
    app.set_logout_callback(on_logout)
    app.set_close_callback(on_window_close)
    
    def check_and_handle_open_register():
        role_val = user.role.value if hasattr(user.role, 'value') else user.role
        if role_val != "cajero":
            return

        from pos.repository.cash_register_repo import CashRegisterRepo
        register_repo = CashRegisterRepo(conn)
        active_reg = register_repo.find_active()

        # If active register exists and is NOT owned by the current user
        if active_reg is not None and active_reg.user_id != user.id:
            from tkinter import messagebox
            # 1. Warn user that another user's register is open and must be closed
            messagebox.showwarning(
                "Caja abierta por otro usuario",
                f"La caja se encuentra abierta por el usuario '{active_reg.username or 'desconocido'}'. "
                "Para operar, debe realizar el cierre de esta caja.",
                parent=app
            )

            # 2. Show the close dialog
            from pos.view.cash_register_view import _CloseDialog
            close_dialog = _CloseDialog(app)
            app.wait_window(close_dialog)
            close_result = close_dialog.result

            if close_result is None:
                # Canceled close -> force logout
                messagebox.showerror(
                    "Cierre requerido",
                    "Debe cerrar la caja del otro usuario para operar. Se cerrará la sesión.",
                    parent=app
                )
                if user.id and user.id > 0:
                    login_ctrl.logout(user.id)
                app.quit()
                return

            # 3. Close the register via controller
            cash_register_ctrl = app._controllers.get("Caja")
            if cash_register_ctrl:
                close_res = cash_register_ctrl.close_register(close_result["amount"], close_result["notes"])
                if not close_res["success"]:
                    messagebox.showerror(
                        "Error al cerrar caja",
                        f"No se pudo cerrar la caja: {close_res['error']}. Se cerrará la sesión.",
                        parent=app
                    )
                    if user.id and user.id > 0:
                        login_ctrl.logout(user.id)
                    app.quit()
                    return

                # Refresh the CashRegisterView in the UI
                caja_view = app._views.get("Caja")
                if caja_view and hasattr(caja_view, "_controller_refresh"):
                    caja_view._controller_refresh()
                elif caja_view and hasattr(caja_view, "_refresh_status"):
                    caja_view._refresh_status()
                    caja_view._refresh_history()

                # 4. Ask to open new register with same amount
                monto_cierre = close_result["amount"]
                open_same = messagebox.askyesno(
                    "Abrir caja",
                    f"¿Desea abrir la caja con el mismo monto con el que cerró (${monto_cierre:,})?",
                    parent=app
                )

                if open_same:
                    open_res = cash_register_ctrl.open_register(monto_cierre)
                    if open_res["success"]:
                        messagebox.showinfo("Caja abierta", "Caja abierta correctamente.", parent=app)
                    else:
                        messagebox.showerror("Error al abrir caja", f"No se pudo abrir la caja: {open_res['error']}", parent=app)
                else:
                    # Modify amount -> show open dialog
                    from pos.view.cash_register_view import _AmountDialog
                    open_dialog = _AmountDialog(app, title="Abrir caja", prompt="Monto inicial ($):")
                    app.wait_window(open_dialog)
                    new_amount = open_dialog.result
                    if new_amount is not None:
                        open_res = cash_register_ctrl.open_register(new_amount)
                        if open_res["success"]:
                            messagebox.showinfo("Caja abierta", "Caja abierta correctamente.", parent=app)
                        else:
                            messagebox.showerror("Error al abrir caja", f"No se pudo abrir la caja: {open_res['error']}", parent=app)

                # Final refresh of status/views in UI
                caja_view = app._views.get("Caja")
                if caja_view and hasattr(caja_view, "_controller_refresh"):
                    caja_view._controller_refresh()
                elif caja_view and hasattr(caja_view, "_refresh_status"):
                    caja_view._refresh_status()
                    caja_view._refresh_history()

    app.after(100, check_and_handle_open_register)
    
    return app


def _launch_test_mode(conn, login_ctrl):
    """Launch MainWindow directly for testing (bypasses login)."""
    from pos.service.permission_service import PermissionService
    from pos.model.user import User
    from pos.model.enums import UserRole
    
    user = User(id=0, username="admin", password="", role=UserRole.ADMIN)
    perm_service = PermissionService()
    permissions = perm_service.get_permissions(user)
    
    app = _create_main_window(conn, login_ctrl, user, permissions)
    app.mainloop()
    
    try:
        app.destroy()
    except Exception:
        pass


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
            sale_view = SaleView(sales_tab, role=role_val)
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
            return_view = ReturnView(returns_tab, role=role_val)
            return_view.pack(fill="both", expand=True)
            return_view.set_controller(return_ctrl)
            app.set_view("Devoluciones", return_view)
            app.set_controller("Devoluciones", return_ctrl)

    # Caja
    if "Caja" in permissions.allowed_tabs:
        cash_register_ctrl = CashRegisterController(conn)
        cash_tab = app.get_tab_frame("Caja")
        if cash_tab is not None:
            cash_register_view = CashRegisterView(cash_tab, cash_register_mode=cash_mode, role=role_val)
            cash_register_view.pack(fill="both", expand=True)
            cash_register_view.set_controller(cash_register_ctrl)
            app.set_view("Caja", cash_register_view)
            app.set_controller("Caja", cash_register_ctrl)

    # Reportes
    if "Reportes" in permissions.allowed_tabs:
        report_ctrl = ReportController(conn)
        reports_tab = app.get_tab_frame("Reportes")
        if reports_tab is not None:
            report_view = ReportView(reports_tab, role=role_val)
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

    # Initial status refresh for the register badge if it exists
    if hasattr(app, "refresh_register_status"):
        app.refresh_register_status()


if __name__ == "__main__":
    main()
