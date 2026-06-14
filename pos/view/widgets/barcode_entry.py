"""Barcode entry widget with keyboard-wedge support and debounce.

Binds ``<Return>`` to a scan callback, strips whitespace, validates that
the input contains only numeric characters, and debounces rapid
hardware-scanner events (< 300 ms between scans).  After each scan the
widget clears and re-focuses itself automatically.
"""

import time
import tkinter as tk
from typing import Callable

import customtkinter as ctk


class BarcodeEntry(ctk.CTkEntry):
    """Entry widget optimised for barcode scanner input.

    Parameters
    ----------
    master : tk.Widget
        Parent widget.
    on_scan : Callable[[str], None] | None
        Callback invoked with the scanned (trimmed, validated) barcode
        when the user presses ``<Return>`` and the debounce check passes.
    **kwargs :
        Forwarded to ``ctk.CTkEntry``.
    """

    def __init__(
        self,
        master: tk.Widget,
        on_scan: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_scan: Callable[[str], None] | None = on_scan
        self._last_scan_time: float = 0.0
        self._debounce_ms: int = 300

        self.bind("<Return>", self._handle_scan)

        if not kwargs.get("placeholder_text"):
            self.configure(placeholder_text="Escanear código de barras...")

    # ---------------------------------------------------------------- public ---

    def set_callback(self, on_scan: Callable[[str], None]) -> None:
        """Replace the scan callback at runtime."""
        self._on_scan = on_scan

    # --------------------------------------------------------------- private ---

    def _handle_scan(self, _event: tk.Event | None = None) -> None:
        raw = self.get().strip()

        # --- clear immediately so the widget is ready for the next scan ---
        self.delete(0, "end")

        if not raw:
            self.focus_set()
            return

        # --- validate numeric ---
        if not raw.isdigit():
            self.focus_set()
            return

        # --- debounce ---
        now = time.time()
        elapsed_ms = (now - self._last_scan_time) * 1000
        if elapsed_ms < self._debounce_ms:
            self.focus_set()
            return
        self._last_scan_time = now

        if self._on_scan is not None:
            self._on_scan(raw)

        self.focus_set()
