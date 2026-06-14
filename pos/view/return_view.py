"""Return view — product return form with barcode lookup.

Embeds a ``BarcodeEntry`` for product lookup, displays product information
once found, and provides quantity and reason fields with a confirm button.
"""

import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.barcode_entry import BarcodeEntry


class ReturnView(ctk.CTkFrame):
    """Return form — barcode lookup, product info, quantity, reason, confirm.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Devoluciones" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_search`` (receives barcode str),
        and ``on_return`` (receives ``{product_id, quantity, reason}``).
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        callbacks = callbacks or {}

        # --- callback slots ---
        self._on_search: Callable[[str], None] | None = callbacks.get(
            "on_search"
        )
        self._on_return: (
            Callable[[int, float, str | None], None] | None
        ) = callbacks.get("on_return")

        self._current_product: dict[str, Any] | None = None

        self.grid_columnconfigure(0, weight=1)

        # --- row 0: barcode entry ---
        self._barcode_entry = BarcodeEntry(
            self,
            on_scan=self._handle_scan,
            height=45,
            font=ctk.CTkFont(size=16),
            placeholder_text="Escanear código de barras para devolución...",
        )
        self._barcode_entry.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )

        # --- row 1: product info panel ---
        self._info_frame = ctk.CTkFrame(self)
        self._info_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=5
        )
        self._info_frame.grid_columnconfigure(0, weight=1)

        self._product_label = ctk.CTkLabel(
            self._info_frame,
            text="Producto: —",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        self._product_label.grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 2)
        )

        self._barcode_label = ctk.CTkLabel(
            self._info_frame,
            text="Código: —",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self._barcode_label.grid(
            row=1, column=0, sticky="w", padx=15, pady=(0, 2)
        )

        self._price_label = ctk.CTkLabel(
            self._info_frame,
            text="Precio: —",
            font=ctk.CTkFont(size=16),
            anchor="w",
        )
        self._price_label.grid(
            row=2, column=0, sticky="w", padx=15, pady=(0, 10)
        )

        # --- row 2: quantity ---
        qty_frame = ctk.CTkFrame(self)
        qty_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            qty_frame, text="Cantidad:", font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(15, 5))

        self._qty_var = tk.StringVar(value="1")
        self._qty_spin = ctk.CTkEntry(
            qty_frame,
            width=80,
            textvariable=self._qty_var,
            justify="center",
        )
        self._qty_spin.pack(side="left", padx=5)

        # Quick increment/decrement buttons
        ctk.CTkButton(
            qty_frame, text="−", width=30, command=self._decrement_qty
        ).pack(side="left", padx=1)
        ctk.CTkButton(
            qty_frame, text="＋", width=30, command=self._increment_qty
        ).pack(side="left", padx=1)

        # --- row 3: reason ---
        reason_frame = ctk.CTkFrame(self)
        reason_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            reason_frame,
            text="Motivo (opcional):",
            font=ctk.CTkFont(size=14),
        ).pack(side="left", padx=(15, 5))

        self._reason_entry = ctk.CTkEntry(
            reason_frame,
            width=300,
            placeholder_text="Ej: Producto vencido...",
        )
        self._reason_entry.pack(side="left", padx=5, fill="x", expand=True)

        # --- row 4: refund preview ---
        self._refund_label = ctk.CTkLabel(
            self,
            text="Devolución: $0",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._refund_label.grid(
            row=4, column=0, sticky="e", padx=20, pady=(10, 5)
        )

        # --- row 5: error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
        )
        self._error_label.grid(row=5, column=0, padx=10, pady=2)

        # --- row 6: confirm button ---
        self._confirm_btn = ctk.CTkButton(
            self,
            text="Confirmar devolución",
            width=200,
            height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._handle_confirm,
            state="disabled",
        )
        self._confirm_btn.grid(
            row=6, column=0, padx=10, pady=(5, 20)
        )

        # Auto-focus the barcode entry
        self.bind("<Map>", lambda _e: self._barcode_entry.focus_set())

    # ---------------------------------------------------------------- public ---

    def show_product(self, product: dict[str, Any]) -> None:
        """Display product information after a successful lookup.

        Expected keys: ``name``, ``barcode``, ``sale_price``, ``id``.
        """
        self._current_product = product
        self._product_label.configure(
            text=f"Producto: {product.get('name', '—')}"
        )
        self._barcode_label.configure(
            text=f"Código: {product.get('barcode', '—')}"
        )
        self._price_label.configure(
            text=f"Precio: ${product.get('sale_price', 0):,}"
        )
        self._confirm_btn.configure(state="normal")
        self._update_refund()

    def clear_product(self) -> None:
        """Clear the displayed product info."""
        self._current_product = None
        self._product_label.configure(text="Producto: —")
        self._barcode_label.configure(text="Código: —")
        self._price_label.configure(text="Precio: —")
        self._refund_label.configure(text="Devolución: $0")
        self._confirm_btn.configure(state="disabled")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        self._error_label.configure(text=message)

    def clear_error(self) -> None:
        """Clear the error message."""
        self._error_label.configure(text="")

    def focus_barcode(self) -> None:
        """Force focus onto the barcode entry."""
        self._barcode_entry.focus_set()

    # ----------------------------------------------------------- callbacks ----

    def set_on_search(self, callback: Callable[[str], None]) -> None:
        """Wire the barcode-search callback."""
        self._on_search = callback
        self._barcode_entry.set_callback(callback)

    def set_on_return(
        self,
        callback: Callable[[int, float, str | None], None],
    ) -> None:
        """Wire the confirm-return callback.

        Callback receives ``(product_id, quantity, reason)``.
        """
        self._on_return = callback

    # --------------------------------------------------------------- private ---

    def _handle_scan(self, barcode: str) -> None:
        self.clear_error()
        if self._on_search is not None:
            self._on_search(barcode)

    def _increment_qty(self) -> None:
        try:
            qty = float(self._qty_var.get())
        except ValueError:
            qty = 1.0
        qty += 1.0
        self._qty_var.set(
            str(int(qty)) if qty == int(qty) else f"{qty:.2f}"
        )
        self._update_refund()

    def _decrement_qty(self) -> None:
        try:
            qty = float(self._qty_var.get())
        except ValueError:
            qty = 1.0
        qty = max(0.0, qty - 1.0)
        self._qty_var.set(
            str(int(qty)) if qty == int(qty) else f"{qty:.2f}"
        )
        self._update_refund()

    def _update_refund(self) -> None:
        if self._current_product is None:
            self._refund_label.configure(text="Devolución: $0")
            return
        try:
            qty = float(self._qty_var.get())
        except ValueError:
            qty = 0.0
        price = self._current_product.get("sale_price", 0)
        refund = int(price * qty)
        self._refund_label.configure(text=f"Devolución: ${refund:,}")

    def _handle_confirm(self) -> None:
        if self._current_product is None:
            return

        try:
            qty = float(self._qty_var.get())
        except ValueError:
            self._error_label.configure(text="Ingrese una cantidad válida")
            return

        if qty <= 0:
            self._error_label.configure(
                text="La cantidad debe ser mayor a 0"
            )
            return

        reason = self._reason_entry.get().strip() or None
        self.clear_error()

        if self._on_return is not None:
            self._on_return(
                self._current_product["id"],
                qty,
                reason,
            )
