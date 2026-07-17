"""Main application window with tab-based navigation.

Uses ``CTkTabview`` to provide five tabs: Ventas, Productos,
Devoluciones, Caja, Reportes.  Each tab holds a ``CTkFrame`` ready
for its corresponding view to be embedded.

Defaults to dark theme at 1280x720, centered on screen, with the Sales tab active.
"""

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from pos.view import theme
from pos.model.user import PermissionContext


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

    def __init__(self, permissions: PermissionContext | None = None) -> None:
        super().__init__()

        self.title("Sistema POS")
        self._permissions = permissions
        
        # Apply saved resolution or default
        saved_resolution = theme.get_resolution()
        
        # Extraemos el ancho y alto para actualizar las variables dinámicamente
        width_str, height_str = saved_resolution.split('x')
        self.WINDOW_WIDTH = int(width_str)
        self.WINDOW_HEIGHT = int(height_str)
        
        # Lock window resizing and set absolute minimum
        self.minsize(800, 600)
        self.resizable(False, False)
        
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

        # --- Background color palette button ---
        self._color_btn = ctk.CTkButton(
            self,
            text="🎨",
            width=32,
            height=32,
            font=ctk.CTkFont(size=16),
            command=self._show_color_palette,
        )
        self._color_btn.place(x=165, y=15)

        # --- Color palette popup (hidden by default) ---
        self._color_popup = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        for color_name, color_hex in theme.BG_COLORS.items():
            self._color_popup.add_command(
                label=f"  {color_name}  ",
                command=lambda name=color_name: self._on_bg_color_changed(name),
                font=("Segoe UI", 10),
            )
        
        # --- Window resolution button ---
        # 1. Creamos un contenedor estricto de 32x32
        self._res_container = ctk.CTkFrame(self, width=32, height=32, fg_color="transparent")
        self._res_container.place(x=207, y=15)
        self._res_container.pack_propagate(False) # ¡Esta línea impide que el emoji estire la caja!

        # 2. Metemos el botón dentro del contenedor para que se adapte a ese tamaño exacto
        self._resolution_btn = ctk.CTkButton(
            self._res_container,
            text="💻",
            width=32,
            height=32,
            font=ctk.CTkFont(size=16),
            command=self._show_resolution_menu,
        )
        self._resolution_btn.pack(fill="both", expand=True)

        # --- Resolution popup menu ---
        self._resolution_popup = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        for res_name, res_value in theme.RESOLUTIONS.items():
            self._resolution_popup.add_command(
                label=f"  {res_value}  ",
                command=lambda value=res_value: self._on_resolution_changed(value),
                font=("Segoe UI", 10),
            )
        
        # --- User display + logout (top-right area) ---
        self._on_logout_callback: Callable | None = None
        self._on_close_callback: Callable | None = None
        
        if permissions is not None:
            role_display = {
                "admin": "Administrador",
                "gerente": "Gerente",
                "cajero": "Cajero",
                "inventario": "Inventario",
            }
            role_val = permissions.user.role.value if hasattr(permissions.user.role, 'value') else permissions.user.role
            role_text = role_display.get(role_val, role_val)
            
            self._user_label = ctk.CTkLabel(
                self,
                text=f"{permissions.user.username} - {role_text}",
                font=theme.scaled_font(13, weight="bold"),
            )
            self._user_label.place(relx=1.0, x=-180, y=15, anchor="ne")

            self._logout_btn = ctk.CTkButton(
                self,
                text="Cerrar sesion",
                width=120,
                height=32,
                font=theme.scaled_font(12, weight="bold"),
                fg_color="#8b1a1a",
                command=self._on_logout,
            )
            self._logout_btn.place(relx=1.0, x=-40, y=15, anchor="ne")
        
        # Set callback for theme propagation
        theme.set_on_change_callback(self._on_theme_changed)

        # --- tab container ---
        self._tabview = ctk.CTkTabview(self, command=self._on_tab_changed)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(50, 10))

        self._tab_frames: dict[str, ctk.CTkFrame] = {}

        # Determine which tabs to create based on permissions
        if permissions is not None:
            tabs_to_create = [t for t in permissions.allowed_tabs if t != "Usuarios"]
        else:
            tabs_to_create = list(self.TABS)

        for name in tabs_to_create:
            self._tabview.add(name)
            frame = ctk.CTkFrame(self._tabview.tab(name))
            frame.pack(fill="both", expand=True)
            self._tab_frames[name] = frame

        # Add "Usuarios" tab if admin
        if permissions is not None and "Usuarios" in permissions.allowed_tabs:
            self._tabview.add("Usuarios")
            frame = ctk.CTkFrame(self._tabview.tab("Usuarios"))
            frame.pack(fill="both", expand=True)
            self._tab_frames["Usuarios"] = frame

        # Set default active tab
        if tabs_to_create:
            first_tab = tabs_to_create[0]
            if self._tabview.get() != first_tab:
                try:
                    self._tabview.set(first_tab)
                except Exception:
                    pass

        # Tab-change callback (set by main.py after wiring views)
        self._on_tab_change_callbacks: dict[str, list] = {
            name: [] for name in self._tab_frames
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

    def set_logout_callback(self, callback: Callable) -> None:
        """Set callback for logout button."""
        self._on_logout_callback = callback

    def set_close_callback(self, callback: Callable) -> None:
        """Set callback for window close (WM_DELETE_WINDOW)."""
        self._on_close_callback = callback
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _on_logout(self) -> None:
        """Handle logout button click."""
        if self._on_logout_callback:
            # Añadimos un retraso de 200ms para que la animación del botón termine
            self.after(200, self._on_logout_callback)

    def _on_window_close(self) -> None:
        """Handle window manager close button."""
        def execute_close():
            if self._on_close_callback:
                self._on_close_callback()
            self.destroy()
            
        # Añadimos el retraso también al cierre total de la ventana
        self.after(200, execute_close)

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
        from pos.view.user_management_view import UserManagementView

        view_classes = {
            "Ventas": SaleView,
            "Productos": ProductView,
            "Devoluciones": ReturnView,
            "Caja": CashRegisterView,
            "Reportes": ReportView,
            "Usuarios": UserManagementView,
        }

        self._views.clear()

        for tab_name in self._tab_frames:
            frame = self._tab_frames[tab_name]
            view_class = view_classes.get(tab_name)
            if view_class is None:
                continue
            controller = self._controllers.get(tab_name)

            # Pass special kwargs for certain views
            kwargs = {}
            if tab_name == "Caja" and self._permissions:
                kwargs["cash_register_mode"] = self._permissions.cash_register_mode
            if tab_name == "Productos" and self._permissions:
                role_val = self._permissions.user.role
                kwargs["role"] = role_val.value if hasattr(role_val, 'value') else role_val
            if tab_name == "Ventas" and self._permissions:
                role_val = self._permissions.user.role
                kwargs["role"] = role_val.value if hasattr(role_val, 'value') else role_val

            view = view_class(frame, **kwargs)
            view.pack(fill="both", expand=True)
            if controller is not None:
                view.set_controller(controller)
            self._views[tab_name] = view

        # Re-establish cross-view wiring
        self._setup_cross_view_wiring()

        # Restore active tab
        try:
            self._tabview.set(active_tab)
        except Exception:
            pass

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

        if product_view is not None:
            self.on_tab_change("Productos", product_view._refresh_products)

    # --------------------------------------------------------------- private ---

    def _on_font_scale_changed(self, choice: str) -> None:
        """Handle font scale dropdown change."""
        level_map = {"Aa Normal": 0, "Aa Grande": 1, "Aa Muy grande": 2, "Aa Máximo": 3}
        level = level_map.get(choice, 0)
        theme.set_font_scale_level(level)
        self.refresh_all_views()
        self._apply_current_theme()

    def _show_color_palette(self) -> None:
        """Show color palette popup menu."""
        try:
            self._color_popup.tk_popup(
                self.winfo_rootx() + 165,
                self.winfo_rooty() + 50,
            )
        finally:
            self._color_popup.grab_release()

    def _on_bg_color_changed(self, color_name: str) -> None:
        """Handle background color change."""
        theme.set_bg_color(color_name)
        self._apply_current_theme()

    def _show_resolution_menu(self) -> None:
        """Show resolution popup menu."""
        try:
            self._resolution_popup.tk_popup(
                self.winfo_rootx() + 207,
                self.winfo_rooty() + 50,
            )
        finally:
            self._resolution_popup.grab_release()

    def _on_resolution_changed(self, resolution_value: str) -> None:
        """Handle window resolution change."""
        # Actualizamos las variables de la ventana con la nueva resolución elegida
        width_str, height_str = resolution_value.split('x')
        self.WINDOW_WIDTH = int(width_str)
        self.WINDOW_HEIGHT = int(height_str)
        
        # Centrar aplicará automáticamente las dimensiones actualizadas
        self._center_on_screen()
        
        # Find the name for persistence
        resolution_name = None
        for name, value in theme.RESOLUTIONS.items():
            if value == resolution_value:
                resolution_name = name
                break
        
        # Persist to database
        if resolution_name:
            from pos.model.database import get_connection
            conn = get_connection()
            try:
                theme.set_resolution(resolution_name, db=conn)
                conn.commit()
            finally:
                conn.close()

    def _on_theme_changed(self) -> None:
        """Handle any theme change (font scale or background color)."""
        self._apply_current_theme()

    def _apply_current_theme(self) -> None:
        """Apply the current theme settings to all widgets."""
        bg_color = theme.get_bg_color()
        contrast = theme.get_contrast_map()
        
        # Apply to root window
        self.configure(fg_color=bg_color)
        
        # Apply to tabview
        self._tabview.configure(fg_color=bg_color)
        
        # Apply to all tab frames
        for frame in self._tab_frames.values():
            frame.configure(fg_color=bg_color)
        
        # Update sale view search button if it exists
        sale_view = self._views.get("Ventas")
        if sale_view and hasattr(sale_view, 'update_theme'):
            sale_view.update_theme()
        
        # Recursively apply theme to all widgets
        theme.apply_theme_to_widget(self, contrast)

    def _on_tab_changed(self) -> None:
        """Handle tab change — fire registered callbacks for the active tab."""
        active = self._tabview.get()
        for cb in self._on_tab_change_callbacks.get(active, []):
            try:
                cb()
            except Exception:
                pass  # Never let a callback crash the tab switch

    def _center_on_screen(self) -> None:
        """Center the main window on the screen with exact requested dimensions."""
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Quitamos la restricción del 90%. Forzamos los píxeles exactos solicitados.
        width = self.WINDOW_WIDTH
        height = self.WINDOW_HEIGHT

        # Calculamos la posición para centrar
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Desbloqueamos para redimensionar
        self.resizable(True, True)
        
        # Aplicamos la geometría exacta
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # IMPORTANTE: Forzamos a Windows a procesar el cambio visual antes de volver a bloquear
        self.update()
        
        # Bloqueamos nuevamente
        self.resizable(False, False)