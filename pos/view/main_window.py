"""Main application window with tab-based navigation.

Uses ``CTkTabview`` to provide five tabs: Ventas, Productos,
Devoluciones, Caja, Reportes.  Each tab holds a ``CTkFrame`` ready
for its corresponding view to be embedded.

Defaults to dark theme at 1280x720, centered on screen, with the Sales tab active.
"""

import tkinter as tk

import customtkinter as ctk

from pos.view import theme


class MainWindow(ctk.CTk):
    """Root window for the POS Sales System."""

    TABS: tuple[str, ...] = (
        "Ventas",
        "Productos",
        "Devoluciones",
        "Caja",
        "Reportes",
    )

    # Window dimensions optimized for modern displays (720p+)
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720

    def __init__(self) -> None:
        super().__init__()

        self.title("Sistema POS")

        # Center window on screen with optimized resolution
        self._center_on_screen()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- Font scale dropdown (top-left corner) ---
        self._font_dropdown = ctk.CTkOptionMenu(
            self,
            values=["Aa Normal", "Aa Grande", "Aa Muy grande", "Aa Máximo"],
            command=self._on_font_scale_changed,
            width=140,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self._font_dropdown.set(["Aa Normal", "Aa Grande", "Aa Muy grande", "Aa Máximo"][theme.get_font_scale_level()])
        self._font_dropdown.place(x=15, y=15)

        # --- tab container ---
        self._tabview = ctk.CTkTabview(self, command=self._on_tab_changed)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(50, 10))

        self._tab_frames: dict[str, ctk.CTkFrame] = {}

        for name in self.TABS:
            self._tabview.add(name)
            frame = ctk.CTkFrame(self._tabview.tab(name))
            frame.pack(fill="both", expand=True)
            self._tab_frames[name] = frame

        # Set "Ventas" (Sales) as the default active tab
        self._tabview.set("Ventas")

        # Tab-change callback (set by main.py after wiring views)
        self._on_tab_change_callbacks: dict[str, list] = {
            name: [] for name in self.TABS
        }

        # View instances and controllers (for refresh)
        self._views: dict[str, object] = {}
        self._controllers: dict[str, object] = {}

    # ---------------------------------------------------------------- public ---

    def get_tab_frame(self, tab_name: str) -> ctk.CTkFrame | None:
        """Return the container frame for *tab_name* so views can embed."""
        return self._tab_frames.get(tab_name)

    def on_tab_change(self, tab_name: str, callback) -> None:
        """Register *callback* to run when *tab_name* becomes active."""
        self._on_tab_change_callbacks.setdefault(tab_name, []).append(callback)

    def set_view(self, tab_name: str, view) -> None:
        """Store view reference for refresh."""
        self._views[tab_name] = view

    def set_controller(self, tab_name: str, controller) -> None:
        """Store controller reference for refresh."""
        self._controllers[tab_name] = controller

    def refresh_all_views(self) -> None:
        """Rebuild all views with new font scale."""
        active_tab = self._tabview.get()

        # Destroy all current views
        for tab_name, view in self._views.items():
            if view is not None and hasattr(view, 'destroy'):
                view.destroy()

        # Recreate views
        from pos.view.sale_view import SaleView
        from pos.view.product_view import ProductView
        from pos.view.return_view import ReturnView
        from pos.view.cash_register_view import CashRegisterView
        from pos.view.report_view import ReportView

        view_classes = {
            "Ventas": SaleView,
            "Productos": ProductView,
            "Devoluciones": ReturnView,
            "Caja": CashRegisterView,
            "Reportes": ReportView,
        }

        self._views.clear()

        for tab_name in self.TABS:
            frame = self._tab_frames[tab_name]
            view_class = view_classes[tab_name]
            controller = self._controllers.get(tab_name)

            view = view_class(frame)
            view.pack(fill="both", expand=True)
            if controller is not None:
                view.set_controller(controller)
            self._views[tab_name] = view

        # Re-establish cross-view wiring
        self._setup_cross_view_wiring()

        # Restore active tab
        self._tabview.set(active_tab)

    def _setup_cross_view_wiring(self) -> None:
        """Re-establish cross-view callbacks after refresh."""
        sale_view = self._views.get("Ventas")
        cash_view = self._views.get("Caja")
        return_view = self._views.get("Devoluciones")
        product_view = self._views.get("Productos")

        if sale_view is not None and cash_view is not None:
            sale_view._on_sale_completed = cash_view._controller_refresh

        if return_view is not None and cash_view is not None:
            return_view._on_return_completed = cash_view._controller_refresh

        if sale_view is not None and product_view is not None:
            sale_view._on_product_created = product_view._refresh_products

        self.on_tab_change("Productos", product_view._refresh_products)

    # --------------------------------------------------------------- private ---

    def _on_font_scale_changed(self, choice: str) -> None:
        """Handle font scale dropdown change."""
        level_map = {"Aa Normal": 0, "Aa Grande": 1, "Aa Muy grande": 2, "Aa Máximo": 3}
        level = level_map.get(choice, 0)
        theme.set_font_scale_level(level)
        self.refresh_all_views()

    def _on_tab_changed(self) -> None:
        """Handle tab change — fire registered callbacks for the active tab."""
        active = self._tabview.get()
        for cb in self._on_tab_change_callbacks.get(active, []):
            try:
                cb()
            except Exception:
                pass  # Never let a callback crash the tab switch

    def _center_on_screen(self) -> None:
        """Center the main window on the screen with optimized dimensions.

        Uses 1280x720 as the base resolution, which works well on modern displays.
        If the screen is smaller, adjusts to 90% of screen size.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Use optimal size or 90% of screen if screen is smaller
        width = min(self.WINDOW_WIDTH, int(screen_width * 0.9))
        height = min(self.WINDOW_HEIGHT, int(screen_height * 0.9))

        # Calculate center position
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
