"""Return view — product return form with barcode lookup.

Embeds a ``BarcodeEntry`` for product lookup, displays product information
once found, and provides quantity and reason fields with a confirm button.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.barcode_entry import BarcodeEntry
from pos.view import theme


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
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}

        # --- callback slots ---
        self._on_search: Callable[[str], None] | None = callbacks.get(
            "on_search"
        )
        self._on_return: (
            Callable[[int, float, str | None], None] | None
        ) = callbacks.get("on_return")
        self._on_return_completed: Callable[[], None] | None = callbacks.get(
            "on_return_completed"
        )

        self._current_product: dict[str, Any] | None = None

        self.grid_columnconfigure(0, weight=1)

        # --- row 0: barcode entry + search button ---
        self._top_frame = ctk.CTkFrame(self)
        self._top_frame.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )
        self._top_frame.grid_columnconfigure(0, weight=1)

        self._barcode_entry = BarcodeEntry(
            self._top_frame,
            on_scan=self._handle_scan,
            height=45,
            font=theme.scaled_font(16),
            placeholder_text="Escanear código de barras para devolución...",
        )
        self._barcode_entry.grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )

        # --- search button (magnifying glass) ---
        self._search_btn = ctk.CTkButton(
            self._top_frame,
            text="🔍",
            width=50,
            height=45,
            font=theme.scaled_font(18),
            command=self._handle_search_button,
        )
        self._search_btn.grid(row=0, column=1, sticky="e")

        # --- row 1: product info panel ---
        self._info_frame = ctk.CTkFrame(self)
        self._info_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=5
        )
        self._info_frame.grid_columnconfigure(0, weight=1)

        self._product_label = ctk.CTkLabel(
            self._info_frame,
            text="Producto: —",
            font=theme.scaled_font(18, weight="bold"),
            anchor="w",
        )
        self._product_label.grid(
            row=0, column=0, sticky="w", padx=15, pady=(10, 2)
        )

        self._barcode_label = ctk.CTkLabel(
            self._info_frame,
            text="Código: —",
            font=theme.scaled_font(13),
            anchor="w",
        )
        self._barcode_label.grid(
            row=1, column=0, sticky="w", padx=15, pady=(0, 2)
        )

        self._price_label = ctk.CTkLabel(
            self._info_frame,
            text="Precio: —",
            font=theme.scaled_font(16),
            anchor="w",
        )
        self._price_label.grid(
            row=2, column=0, sticky="w", padx=15, pady=(0, 10)
        )

        # --- row 2: quantity ---
        qty_frame = ctk.CTkFrame(self)
        qty_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            qty_frame, text="Cantidad:", font=theme.scaled_font(14)
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
            font=theme.scaled_font(14),
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
            font=theme.scaled_font(20, weight="bold"),
        )
        self._refund_label.grid(
            row=4, column=0, sticky="e", padx=20, pady=(10, 5)
        )

        # --- row 5: error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.grid(row=5, column=0, padx=10, pady=2)

        # --- row 6: confirm button ---
        self._confirm_btn = ctk.CTkButton(
            self,
            text="Confirmar devolución",
            width=200,
            height=40,
            font=theme.scaled_font(15, weight="bold"),
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

    def clear_form(self) -> None:
        """Clear all form fields (quantity and reason)."""
        self._qty_var.set("1")
        self._reason_entry.delete(0, "end")
        self.clear_error()

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

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``ReturnController`` instance and set up all event handlers.

        After calling this, the barcode search and return confirmation are
        automatically routed to the controller.
        """
        self._controller = controller

        # Wire internal handlers
        self._on_search = self._controller_search
        self._on_return = self._controller_confirm_return

        # Update barcode entry callback
        self._barcode_entry.set_callback(self._controller_search)

    # ---------------------------------------------------- controller handlers ---

    def _controller_search(self, barcode: str) -> None:
        """Look up product by barcode via controller (no direct repo access)."""
        self.clear_error()
        self.clear_product()

        # Delegate to controller — view has NO access to repositories
        result = self._controller.lookup_product(barcode)

        if not result["success"]:
            self.show_error(result["error"])
            self.focus_barcode()
            return

        product = result["data"]
        self.show_product(product)

    def _controller_confirm_return(
        self, product_id: int, quantity: float, reason: str | None
    ) -> None:
        """Process the return via controller and show the result."""
        result = self._controller.process_return(product_id, quantity, reason)
        if result["success"]:
            data = result["data"]
            refund = data.get("refund_amount", 0)
            messagebox.showinfo(
                "Devolución procesada",
                f"Devolución registrada correctamente.\nReintegro: ${refund:,}",
            )
            self.clear_product()
            self.clear_form()
            self.focus_barcode()
            # Notify other views (e.g., cash register) that a return was completed
            if self._on_return_completed is not None:
                self._on_return_completed()
        else:
            self.show_error(result["error"])

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

    def _handle_search_button(self) -> None:
        """Open search dialog with all products for manual selection."""
        if not hasattr(self, "_controller") or self._controller is None:
            return

        # Search with empty query to get all products
        result = self._controller.search_products("")
        if not result["success"]:
            messagebox.showerror("Error", result.get("error", "Error desconocido"))
            return
        products = result["data"]
        if not products:
            messagebox.showinfo("Buscar", "No hay productos disponibles")
            return

        from pos.view.widgets.product_search_dialog import ProductSearchDialog
        categories = self._get_categories()
        dialog = ProductSearchDialog(self, products, categories)
        self.wait_window(dialog)
        selected = dialog.result
        if selected is not None:
            # Show the selected product for return
            self.show_product({
                "id": selected.id,
                "barcode": selected.barcode,
                "name": selected.name,
                "sale_price": selected.sale_price,
            })
        self._barcode_entry.focus_set()

    def _get_categories(self) -> list:
        """Fetch categories from controller for the search dialog."""
        if hasattr(self, "_controller") and hasattr(self._controller, "list_categories"):
            result = self._controller.list_categories()
            if result["success"]:
                return result["data"]
        return []
