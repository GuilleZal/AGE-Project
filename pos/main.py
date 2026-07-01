"""POS Sales System — Entry point.

Initializes the SQLite database (schema creation is idempotent) and
launches the CustomTkinter main window with all controllers wired
to their respective views.

Usage:
    python -m pos.main
    python pos/main.py
"""

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

        # ------- Controllers ------------------------------------------------
        from pos.controller.sale_controller import SaleController
        from pos.controller.product_controller import ProductController
        from pos.controller.cash_register_controller import CashRegisterController
        from pos.controller.return_controller import ReturnController
        from pos.controller.report_controller import ReportController

        sale_ctrl = SaleController(conn)
        product_ctrl = ProductController(conn)
        cash_register_ctrl = CashRegisterController(conn)
        return_ctrl = ReturnController(conn)
        report_ctrl = ReportController(conn)

        # ------- Views ------------------------------------------------------
        from pos.view.main_window import MainWindow
        from pos.view.sale_view import SaleView
        from pos.view.product_view import ProductView
        from pos.view.return_view import ReturnView
        from pos.view.cash_register_view import CashRegisterView
        from pos.view.report_view import ReportView

        app = MainWindow()

        # Embed and wire each view into its tab
        sales_tab = app.get_tab_frame("Ventas")
        if sales_tab is not None:
            sale_view = SaleView(sales_tab)
            sale_view.pack(fill="both", expand=True)
            sale_view.set_controller(sale_ctrl)
            app.set_view("Ventas", sale_view)
            app.set_controller("Ventas", sale_ctrl)

        products_tab = app.get_tab_frame("Productos")
        if products_tab is not None:
            product_view = ProductView(products_tab)
            product_view.pack(fill="both", expand=True)
            product_view.set_controller(product_ctrl)
            app.set_view("Productos", product_view)
            app.set_controller("Productos", product_ctrl)

        returns_tab = app.get_tab_frame("Devoluciones")
        if returns_tab is not None:
            return_view = ReturnView(returns_tab)
            return_view.pack(fill="both", expand=True)
            return_view.set_controller(return_ctrl)
            app.set_view("Devoluciones", return_view)
            app.set_controller("Devoluciones", return_ctrl)

        cash_tab = app.get_tab_frame("Caja")
        if cash_tab is not None:
            cash_register_view = CashRegisterView(cash_tab)
            cash_register_view.pack(fill="both", expand=True)
            cash_register_view.set_controller(cash_register_ctrl)
            app.set_view("Caja", cash_register_view)
            app.set_controller("Caja", cash_register_ctrl)

        reports_tab = app.get_tab_frame("Reportes")
        if reports_tab is not None:
            report_view = ReportView(reports_tab)
            report_view.pack(fill="both", expand=True)
            report_view.set_controller(report_ctrl)
            app.set_view("Reportes", report_view)
            app.set_controller("Reportes", report_ctrl)

        # --- Cross-view wiring ---
        # After a sale, refresh the cash register view to update balance
        if sales_tab is not None and cash_tab is not None:
            sale_view._on_sale_completed = cash_register_view._controller_refresh

        # After a return, refresh the cash register view to update balance
        if returns_tab is not None and cash_tab is not None:
            return_view._on_return_completed = cash_register_view._controller_refresh

        # After a quick-create product, refresh the products tab
        sale_view._on_product_created = product_view._refresh_products

        # Refresh products whenever the Productos tab becomes visible
        # (ensures treeview is always up-to-date after cross-view changes)
        app.on_tab_change("Productos", product_view._refresh_products)

        app.mainloop()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
