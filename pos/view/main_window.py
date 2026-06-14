"""Main application window with tab-based navigation.

Uses ``CTkTabview`` to provide five tabs: Ventas, Productos,
Devoluciones, Caja, Reportes.  Each tab holds a ``CTkFrame`` ready
for its corresponding view to be embedded.

Defaults to dark theme at 1200×800 with the Sales tab active.
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

    def __init__(self) -> None:
        super().__init__()

        self.title("Sistema POS")
        self.geometry("1200x800")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- tab container ---
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self._tab_frames: dict[str, ctk.CTkFrame] = {}

        for name in self.TABS:
            self._tabview.add(name)
            frame = ctk.CTkFrame(self._tabview.tab(name))
            frame.pack(fill="both", expand=True)
            self._tab_frames[name] = frame

        # Set "Ventas" (Sales) as the default active tab
        self._tabview.set("Ventas")

    # ---------------------------------------------------------------- public ---

    def get_tab_frame(self, tab_name: str) -> ctk.CTkFrame | None:
        """Return the container frame for *tab_name* so views can embed."""
        return self._tab_frames.get(tab_name)
