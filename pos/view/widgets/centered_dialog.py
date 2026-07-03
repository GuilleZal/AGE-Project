"""Base class for centered modal dialogs.

Provides automatic centering relative to parent window and consistent
modal behavior (grab_set, transient).
"""

import tkinter as tk

import customtkinter as ctk

from pos.view import theme


class CenteredDialog(ctk.CTkToplevel):
    """Base class for modal dialogs that center themselves on the parent window.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    width : int
        Dialog width in pixels.
    height : int
        Dialog height in pixels.
    title : str
        Dialog title.
    resizable : tuple[bool, bool]
        Whether the dialog is resizable (width, height). Defaults to (False, False).
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self,
        master: tk.Widget,
        width: int,
        height: int,
        title: str = "",
        resizable: tuple[bool, bool] = (False, False),
        **kwargs,
    ) -> None:
        # Set theme-aware background color before calling super().__init__
        contrast = theme.get_contrast_map()
        if "fg_color" not in kwargs:
            kwargs["fg_color"] = contrast["panel"]
        
        super().__init__(master, **kwargs)
        self.title(title)
        self._width = width
        self._height = height
        self.resizable(resizable[0], resizable[1])

        # Set modal behavior
        self.grab_set()
        self.transient(master)

        # Center the dialog
        self._center_on_parent(master)

    def _center_on_parent(self, master: tk.Widget) -> None:
        """Center the dialog relative to the parent window.

        Uses update_idletasks to ensure geometry is calculated correctly.
        """
        # Force geometry calculation
        self.update_idletasks()

        # Get parent window position and size
        if master.winfo_exists():
            parent_x = master.winfo_rootx()
            parent_y = master.winfo_rooty()
            parent_width = master.winfo_width()
            parent_height = master.winfo_height()
        else:
            # Fallback to screen center if parent doesn't exist
            parent_x = 0
            parent_y = 0
            parent_width = self.winfo_screenwidth()
            parent_height = self.winfo_screenheight()

        # Calculate center position
        x = parent_x + (parent_width - self._width) // 2
        y = parent_y + (parent_height - self._height) // 2

        # Apply geometry
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")


def center_window_on_screen(window: tk.Widget, width: int, height: int) -> None:
    """Center a window on the screen.

    Parameters
    ----------
    window : tk.Widget
        The window to center.
    width : int
        Window width in pixels.
    height : int
        Window height in pixels.
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")
