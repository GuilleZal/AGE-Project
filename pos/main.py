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

        app = MainWindow()

        # Embed SaleView into the Ventas tab
        sales_tab = app.get_tab_frame("Ventas")
        if sales_tab is not None:
            sale_view = SaleView(sales_tab)
            sale_view.pack(fill="both", expand=True)

        app.mainloop()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
