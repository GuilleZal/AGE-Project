"""POS Sales System — Entry point.

Initializes the SQLite database (schema creation is idempotent) and
launches the CustomTkinter main window.

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
    """Bootstrap the application: init DB, launch UI."""
    conn = get_connection()
    try:
        init_db(conn)
        conn.commit()
        print("Database initialized successfully at pos/data/pos.db")

        # --- Launch UI (views only — controller wiring in Batch 7) ---
        from pos.view.main_window import MainWindow
        from pos.view.sale_view import SaleView
        from pos.view.product_view import ProductView
        from pos.view.return_view import ReturnView
        from pos.view.cash_register_view import CashRegisterView
        from pos.view.report_view import ReportView

        app = MainWindow()

        # Embed all views into their respective tabs
        sales_tab = app.get_tab_frame("Ventas")
        if sales_tab is not None:
            SaleView(sales_tab).pack(fill="both", expand=True)

        products_tab = app.get_tab_frame("Productos")
        if products_tab is not None:
            ProductView(products_tab).pack(fill="both", expand=True)

        returns_tab = app.get_tab_frame("Devoluciones")
        if returns_tab is not None:
            ReturnView(returns_tab).pack(fill="both", expand=True)

        cash_tab = app.get_tab_frame("Caja")
        if cash_tab is not None:
            CashRegisterView(cash_tab).pack(fill="both", expand=True)

        reports_tab = app.get_tab_frame("Reportes")
        if reports_tab is not None:
            ReportView(reports_tab).pack(fill="both", expand=True)

        app.mainloop()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
