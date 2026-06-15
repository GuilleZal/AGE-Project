"""Sale view — POS terminal layout for the main sales screen.

Embeds the barcode entry widget, cart treeview, running total, and
payment-method buttons.  All business logic lives in
``SaleController`` — this view only emits callbacks.
"""

import tkinter as tk
from tkinter import messagebox
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
        self._on_sale_completed: Callable[[], None] | None = callbacks.get(
            "on_sale_completed"
        )

        self._total: int = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # cart row stretches

        # --- row 0: top bar (barcode entry + search button) ---
        self._top_frame = ctk.CTkFrame(self)
        self._top_frame.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )
        self._top_frame.grid_columnconfigure(0, weight=1)

        # --- barcode entry (always visible, always focused) ---
        self._barcode_entry = BarcodeEntry(
            self._top_frame,
            on_scan=self._handle_scan,
            on_search=self._handle_search,
            height=45,
            font=ctk.CTkFont(size=18),
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
            font=ctk.CTkFont(size=18),
            command=self._handle_search_button,
        )
        self._search_btn.grid(row=0, column=1, sticky="e")

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

        self._remove_btn = ctk.CTkButton(
            self._bottom_frame,
            text="Eliminar",
            width=100,
            fg_color="#993333",
            hover_color="#772222",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._handle_remove_button,
        )
        self._remove_btn.grid(row=0, column=1, sticky="e", padx=(10, 5), pady=10)

        self._payment_frame = ctk.CTkFrame(self._bottom_frame)
        self._payment_frame.grid(row=0, column=2, sticky="e", padx=10, pady=10)

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

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``SaleController`` instance and set up all event handlers.

        This is a convenience method that replaces manual callback wiring.
        After calling this, all view events are automatically routed to
        the controller and the cart view is refreshed.
        """
        self._controller = controller

        self._on_scan = self._controller_scan
        self._on_update_qty = self._controller_update_qty
        self._on_remove_item = self._controller_remove_item
        self._on_payment = self._controller_payment
        self._controller_search = self._controller.search_products

        self._update_cart()

    # ---------------------------------------------------- controller handlers ---

    def _controller_scan(self, barcode: str) -> None:
        """Handle barcode scan by looking up product via controller."""
        from pos.view.widgets.quick_create_dialog import QuickCreateDialog

        result = self._controller.add_by_barcode(barcode)
        if result["success"]:
            self._update_cart()
            return

        # Check if it is the "not found" flow (not an error)
        data = result.get("data") or {}
        if data.get("barcode") == barcode and result.get("error") is None:
            # Product not found — open QuickCreateDialog
            dialog = QuickCreateDialog(self, barcode)
            self.wait_window(dialog)
            product_data = dialog.result
            if product_data:
                create_result = self._controller.create_quick_product(
                    barcode=barcode,
                    name=product_data["name"],
                    sale_price=product_data["sale_price"],
                )
                if create_result["success"]:
                    self._update_cart()
                else:
                    messagebox.showerror("Error", create_result["error"])
        else:
            messagebox.showerror("Error", result.get("error", "Error desconocido"))

        self._barcode_entry.focus_set()

    def _controller_update_qty(self, product_id: int, quantity: float) -> None:
        """Handle quantity update via controller."""
        result = self._controller.update_item_quantity(product_id, quantity)
        if result["success"]:
            self._update_cart()
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_remove_item(self, product_id: int) -> None:
        """Handle item removal via controller."""
        result = self._controller.remove_item(product_id)
        if result["success"]:
            self._update_cart()
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_payment(self, method: str, received: int) -> None:
        """Process payment via controller and show receipt on success."""
        from pos.view.widgets.receipt_preview import ReceiptPreview

        result = self._controller.complete_sale(
            payment_method=method,
            amount_received=received,
        )
        if result["success"]:
            # Show receipt preview
            ReceiptPreview(self, result["data"])
            self._clear_cart()
            # Notify other views (e.g., cash register) that a sale completed
            if self._on_sale_completed is not None:
                self._on_sale_completed()
        else:
            messagebox.showerror("Error", result["error"])

    def _update_cart(self) -> None:
        """Refresh cart treeview and total label from controller."""
        cart_result = self._controller.get_cart()
        if cart_result["success"]:
            items = cart_result["data"]["items"]
            total = cart_result["data"]["total"]
            self.update_cart(items)
            self.update_total(total)

    def _clear_cart(self) -> None:
        """Clear the cart via controller and reset UI."""
        self._controller.clear_cart()
        self.update_cart([])
        self.update_total(0)
        self._barcode_entry.focus_set()

    # --------------------------------------------------------------- private ---

    def _handle_scan(self, barcode: str) -> None:
        if self._on_scan is not None:
            self._on_scan(barcode)

    def _handle_search(self, query: str) -> None:
        if not hasattr(self, "_controller_search") or self._controller_search is None:
            return
        result = self._controller_search(query)
        if not result["success"]:
            messagebox.showerror("Error", result.get("error", "Error desconocido"))
            self._barcode_entry.focus_set()
            return
        products = result["data"]
        if not products:
            messagebox.showinfo("Buscar", "No se encontraron productos")
            self._barcode_entry.focus_set()
            return
        if len(products) == 1:
            add_result = self._controller.add_by_barcode(products[0].barcode)
            if add_result["success"]:
                self._update_cart()
            else:
                messagebox.showerror("Error", add_result.get("error", "Error desconocido"))
            self._barcode_entry.focus_set()
            return
        from pos.view.widgets.product_search_dialog import ProductSearchDialog
        categories = self._get_categories()
        dialog = ProductSearchDialog(self, products, categories)
        self.wait_window(dialog)
        selected = dialog.result
        if selected is not None:
            add_result = self._controller.add_by_barcode(selected.barcode)
            if add_result["success"]:
                self._update_cart()
            else:
                messagebox.showerror("Error", add_result.get("error", "Error desconocido"))
        self._barcode_entry.focus_set()

    def _handle_search_button(self) -> None:
        """Open search dialog with all products for manual browsing."""
        if not hasattr(self, "_controller_search") or self._controller_search is None:
            return
        # Search with empty query to get all products
        result = self._controller_search("")
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
            add_result = self._controller.add_by_barcode(selected.barcode)
            if add_result["success"]:
                self._update_cart()
            else:
                messagebox.showerror("Error", add_result.get("error", "Error desconocido"))
        self._barcode_entry.focus_set()

    def _get_categories(self) -> list:
        """Fetch categories from controller for the search dialog."""
        if hasattr(self, "_controller") and hasattr(self._controller, "list_categories"):
            result = self._controller.list_categories()
            if result["success"]:
                return result["data"]
        return []

    def _handle_remove(self, product_id: int) -> None:
        if self._on_remove_item is not None:
            self._on_remove_item(product_id)

    def _handle_remove_button(self) -> None:
        selected = self._cart_tree.get_selected_item()
        if selected is None:
            messagebox.showwarning("Eliminar", "Seleccione un producto del carrito")
            return
        self._handle_remove(selected["product_id"])

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
