"""Sale view — POS terminal layout for the main sales screen.

Embeds the barcode entry widget, cart treeview, running total, and
payment-method buttons.  All business logic lives in
``SaleController`` — this view only emits callbacks.
"""

import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.barcode_entry import BarcodeEntry
from pos.view.widgets.cart_treeview import CartTreeview
from pos.view.widgets.payment_dialog import PaymentDialog


class SaleView(ctk.CTkFrame):
    """POS terminal — barcode entry, cart treeview, total, and payment.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Ventas" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_scan``, ``on_update_qty``,
        ``on_remove_item``, ``on_payment`` receiving callbacks.
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    PAYMENT_BUTTONS: list[tuple[str, str]] = [
        ("Efectivo", "cash"),
        ("Tarjeta", "card"),
        ("Transferencia", "transfer"),
        ("Mixto", "mixed"),
    ]

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        callbacks = callbacks or {}

        # Callback slots — wired by main_window.py during integration
        self._on_scan: Callable[[str], None] | None = callbacks.get("on_scan")
        self._on_update_qty: Callable[[int, float], None] | None = callbacks.get(
            "on_update_qty"
        )
        self._on_remove_item: Callable[[int], None] | None = callbacks.get(
            "on_remove_item"
        )
        self._on_payment: Callable[[str, int], None] | None = callbacks.get(
            "on_payment"
        )

        self._total: int = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # cart row stretches

        # --- row 0: barcode entry (always visible, always focused) ---
        self._barcode_entry = BarcodeEntry(
            self,
            on_scan=self._handle_scan,
            height=45,
            font=ctk.CTkFont(size=18),
        )
        self._barcode_entry.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )

        # --- row 1: cart treeview ---
        self._cart_tree = CartTreeview(
            self,
            on_delete=self._handle_remove,
        )
        self._cart_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # --- row 2: bottom bar (total + payment buttons) ---
        self._bottom_frame = ctk.CTkFrame(self)
        self._bottom_frame.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(5, 10)
        )
        self._bottom_frame.grid_columnconfigure(0, weight=1)

        self._total_label = ctk.CTkLabel(
            self._bottom_frame,
            text="Total: $0",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        self._total_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self._payment_frame = ctk.CTkFrame(self._bottom_frame)
        self._payment_frame.grid(row=0, column=1, sticky="e", padx=10, pady=10)

        for idx, (label, method) in enumerate(self.PAYMENT_BUTTONS):
            btn = ctk.CTkButton(
                self._payment_frame,
                text=label,
                width=130,
                font=ctk.CTkFont(size=14, weight="bold"),
                command=lambda m=method: self._handle_payment(m),
            )
            btn.grid(row=0, column=idx, padx=3)

        # --- auto-focus barcode entry whenever the frame is mapped ---
        self.bind("<Map>", lambda _e: self._barcode_entry.focus_set())

    # ---------------------------------------------------------------- public ---

    def update_cart(self, items: list[dict[str, Any]]) -> None:
        """Refresh the cart treeview with the given *items*."""
        self._cart_tree.update_cart(items)

    def update_total(self, total: int) -> None:
        """Update the displayed cart total."""
        self._total = total
        self._total_label.configure(text=f"Total: ${total:,}")

    def focus_barcode(self) -> None:
        """Force focus onto the barcode entry widget."""
        self._barcode_entry.focus_set()

    def show_receipt(self, sale_data: dict[str, Any]) -> None:
        """Display an on-screen receipt preview after a successful sale.

        *sale_data* is the controller response ``data`` field, expected
        to contain ``sale``, ``items``, and ``change``.
        """
        from tkinter import messagebox

        sale = sale_data.get("sale", {})
        items = sale_data.get("items", [])
        change = sale_data.get("change", 0)

        lines = [
            f"Venta #{sale.get('id', '—')}",
            f"Fecha: {sale.get('created_at', '—')}",
            f"Método: {sale.get('payment_method', '—')}",
            "",
            "--- Productos ---",
        ]
        for item in items:
            lines.append(
                f"  {item['name']}  x{item['quantity']}  "
                f"${item['unit_price']:,}  =  ${item['subtotal']:,}"
            )
        lines.append("")
        lines.append(f"TOTAL:  ${sale.get('total', 0):,}")
        if change:
            lines.append(f"Vuelto:  ${change:,}")

        messagebox.showinfo("Comprobante de venta", "\n".join(lines))

    # ----------------------------------------------------------- callbacks ----

    def set_on_scan(self, callback: Callable[[str], None]) -> None:
        """Wire the scan callback."""
        self._on_scan = callback

    def set_on_update_qty(self, callback: Callable[[int, float], None]) -> None:
        """Wire the quantity-update callback."""
        self._on_update_qty = callback

    def set_on_remove_item(self, callback: Callable[[int], None]) -> None:
        """Wire the remove-item callback."""
        self._on_remove_item = callback

    def set_on_payment(self, callback: Callable[[str, int], None]) -> None:
        """Wire the payment callback."""
        self._on_payment = callback

    # --------------------------------------------------------------- private ---

    def _handle_scan(self, barcode: str) -> None:
        if self._on_scan is not None:
            self._on_scan(barcode)

    def _handle_remove(self, product_id: int) -> None:
        if self._on_remove_item is not None:
            self._on_remove_item(product_id)

    def _handle_payment(self, method: str) -> None:
        """Open PaymentDialog and, if confirmed, invoke the on_payment callback."""
        dialog = PaymentDialog(
            self, total=self._total, payment_method=method
        )
        self.wait_window(dialog)
        result = dialog.result
        if result is not None and self._on_payment is not None:
            self._on_payment(
                result["payment_method"],
                result.get("received", 0),
            )
