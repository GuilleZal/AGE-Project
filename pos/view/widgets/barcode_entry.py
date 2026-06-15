"""Barcode entry widget with keyboard-wedge support and debounce.

Binds ``<Return>`` to a scan callback, strips whitespace, validates that
the input contains only numeric characters, and debounces rapid
hardware-scanner events (< 300 ms between scans).  After each scan the
widget clears and re-focuses itself automatically.

Tracks inter-keypress timing to distinguish barcode scanners (fast burst,
< 50 ms gaps) from manual typing (> 50 ms gaps).  Scanner input fires
``on_scan`` automatically after a short inactivity timeout (no Enter
required); manual input on Enter fires ``on_search``.
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
        when a scanner burst is detected (auto-fired after inactivity)
        or when the user presses ``<Return>`` in scanner mode.
    on_search : Callable[[str], None] | None
        Callback invoked with the typed text when the user presses
        ``<Return>`` in manual-typing mode (slow input, > 50 ms gaps).
    **kwargs :
        Forwarded to ``ctk.CTkEntry``.
    """

    # Time (ms) of inactivity after the last scanner keypress before
    # the scan is auto-dispatched.  Scanners send bursts in < 100 ms
    # total, so 150 ms is safe — no human types that fast.
    _SCANNER_IDLE_MS: int = 150

    def __init__(
        self,
        master: tk.Widget,
        on_scan: Callable[[str], None] | None = None,
        on_search: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_scan: Callable[[str], None] | None = on_scan
        self._on_search: Callable[[str], None] | None = on_search
        self._last_scan_time: float = 0.0
        self._debounce_ms: int = 300
        self._last_key_time: float = 0.0
        self._scanner_threshold_ms: int = 50
        self._is_scanner_mode: bool = False
        self._idle_after_id: str | None = None

        self.bind("<KeyRelease>", self._handle_key_release)
        self.bind("<Return>", self._handle_return)
        self.bind("<FocusIn>", self._handle_focus_in)

        if not kwargs.get("placeholder_text"):
            self.configure(placeholder_text="Escanear código de barras...")

    # ---------------------------------------------------------------- public ---

    def set_callback(self, on_scan: Callable[[str], None]) -> None:
        """Replace the scan callback at runtime."""
        self._on_scan = on_scan

    def set_search_callback(self, on_search: Callable[[str], None]) -> None:
        """Replace the search callback at runtime."""
        self._on_search = on_search

    # --------------------------------------------------------------- private ---

    def _handle_focus_in(self, _event: tk.Event | None = None) -> None:
        self._last_key_time = 0.0
        self._is_scanner_mode = False
        self._cancel_idle_timer()

    def _handle_key_release(self, event: tk.Event | None = None) -> None:
        if event is None:
            return
        if event.keysym == "Return":
            return
        now = time.time()
        if self._last_key_time > 0:
            gap_ms = (now - self._last_key_time) * 1000
            if gap_ms < self._scanner_threshold_ms:
                self._is_scanner_mode = True
        self._last_key_time = now

        # In scanner mode, schedule an idle timer so the scan fires
        # automatically without waiting for Enter.
        if self._is_scanner_mode:
            self._schedule_idle_dispatch()

    def _handle_return(self, _event: tk.Event | None = None) -> str | None:
        self._cancel_idle_timer()
        raw = self.get().strip()
        self.delete(0, "end")

        if not raw:
            self.focus_set()
            return "break"

        if self._is_scanner_mode:
            self._dispatch_scan(raw)
        else:
            self._dispatch_search(raw)

        self._last_key_time = 0.0
        self._is_scanner_mode = False
        self.focus_set()
        return "break"

    def _dispatch_scan(self, raw: str) -> None:
        if not raw.isdigit():
            return

        now = time.time()
        elapsed_ms = (now - self._last_scan_time) * 1000
        if elapsed_ms < self._debounce_ms:
            return
        self._last_scan_time = now

        if self._on_scan is not None:
            self._on_scan(raw)

    def _dispatch_search(self, raw: str) -> None:
        if self._on_search is not None:
            self._on_search(raw)

    # -------------------------------------------------- idle timer (auto-scan) ---

    def _schedule_idle_dispatch(self) -> None:
        """(Re)schedule the scanner idle timer.

        Each new keypress in scanner mode resets the timer.  When it
        expires with no further input, the barcode is auto-dispatched.
        """
        self._cancel_idle_timer()
        self._idle_after_id = self.after(
            self._SCANNER_IDLE_MS, self._idle_dispatch
        )

    def _cancel_idle_timer(self) -> None:
        """Cancel a pending idle timer, if any."""
        if self._idle_after_id is not None:
            self.after_cancel(self._idle_after_id)
            self._idle_after_id = None

    def _idle_dispatch(self) -> None:
        """Called by the event loop when the scanner idle timer expires."""
        self._idle_after_id = None
        raw = self.get().strip()
        if not raw:
            return
        self.delete(0, "end")
        self._dispatch_scan(raw)
        self._last_key_time = 0.0
        self._is_scanner_mode = False
        self.focus_set()
