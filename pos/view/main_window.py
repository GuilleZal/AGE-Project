"""Main application window with tab-based navigation.

Uses ``CTkTabview`` to provide five tabs: Ventas, Productos,
Devoluciones, Caja, Reportes.  Each tab holds a ``CTkFrame`` ready
for its corresponding view to be embedded.

Defaults to dark theme at 1280x720, centered on screen, with the Sales tab active.
"""

import tkinter as tk

import customtkinter as ctk


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

        # --- tab container ---
        self._tabview = ctk.CTkTabview(self, command=self._on_tab_changed)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

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

    # ---------------------------------------------------------------- public ---

    def get_tab_frame(self, tab_name: str) -> ctk.CTkFrame | None:
        """Return the container frame for *tab_name* so views can embed."""
        return self._tab_frames.get(tab_name)

    def on_tab_change(self, tab_name: str, callback) -> None:
        """Register *callback* to run when *tab_name* becomes active."""
        self._on_tab_change_callbacks.setdefault(tab_name, []).append(callback)

    # --------------------------------------------------------------- private ---

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
