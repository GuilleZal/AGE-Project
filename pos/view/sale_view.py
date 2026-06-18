"""Sale view — POS terminal layout for the main sales screen.

Two-column layout matching the reference design:
- Left column: barcode search, product table, delete button
- Right column: payment sidebar with totals, payment methods, and action buttons

All business logic lives in ``SaleController`` — this view only emits callbacks.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.barcode_entry import BarcodeEntry
from pos.view.widgets.cart_treeview import CartTreeview


class SaleView(ctk.CTkFrame):
    """POS terminal — two-column layout with integrated payment sidebar.

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

    PAYMENT_METHODS: list[tuple[str, str]] = [
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
        self._selected_payment_method: str = "cash"

        # --- main two-column layout ---
        self.grid_columnconfigure(0, weight=1)  # left column stretches
        self.grid_columnconfigure(1, weight=0)  # right column fixed width
        self.grid_rowconfigure(0, weight=1)

        # ============================================================
        # LEFT COLUMN: Sales area
        # ============================================================
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)  # cart row stretches

        # --- row 0: top bar (barcode entry + settings button) ---
        self._top_frame = ctk.CTkFrame(left_frame)
        self._top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self._top_frame.grid_columnconfigure(0, weight=1)

        # --- barcode entry (always visible, always focused) ---
        self._barcode_entry = BarcodeEntry(
            self._top_frame,
            on_scan=self._handle_scan,
            on_search=self._handle_search,
            height=45,
            font=ctk.CTkFont(size=16),
        )
        self._barcode_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # --- search button (magnifying glass) ---
        self._search_btn = ctk.CTkButton(
            self._top_frame,
            text="🔍",
            width=50,
            height=45,
            font=ctk.CTkFont(size=18),
            fg_color="#2b2b2b",
            hover_color="#3b3b3b",
            command=self._handle_search_button,
        )
        self._search_btn.grid(row=0, column=1, sticky="e")

        # --- row 1: cart treeview ---
        self._cart_tree = CartTreeview(
            left_frame,
            on_delete=self._handle_remove,
        )
        self._cart_tree.grid(row=1, column=0, sticky="nsew")

        # --- row 2: delete button (bottom left) ---
        self._delete_btn = ctk.CTkButton(
            left_frame,
            text="Eliminar",
            width=120,
            height=40,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._handle_remove_button,
        )
        self._delete_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

        # ============================================================
        # RIGHT COLUMN: Payment sidebar
        # ============================================================
        self._payment_sidebar = ctk.CTkFrame(self, width=320)
        self._payment_sidebar.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=(10, 10))
        self._payment_sidebar.grid_columnconfigure(0, weight=1)
        self._payment_sidebar.grid_rowconfigure(2, weight=1)  # payment methods stretch

        # --- Totals section ---
        totals_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        totals_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(5, 10))
        totals_frame.grid_columnconfigure(0, weight=1)
        totals_frame.grid_columnconfigure(1, weight=0)

        # Title
        ctk.CTkLabel(
            totals_frame,
            text="Pago",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Separator line
        separator = ctk.CTkFrame(totals_frame, height=2, fg_color="#3e3e3e")
        separator.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Subtotal row
        ctk.CTkLabel(
            totals_frame,
            text="Subtotal:",
            font=ctk.CTkFont(size=16),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=2)
        self._subtotal_label = ctk.CTkLabel(
            totals_frame,
            text="$0",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="e",
        )
        self._subtotal_label.grid(row=2, column=1, sticky="e", pady=2, padx=(20, 0))

        # Discount row
        ctk.CTkLabel(
            totals_frame,
            text="Descuento:",
            font=ctk.CTkFont(size=16),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=2)
        self._discount_label = ctk.CTkLabel(
            totals_frame,
            text="$0",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="e",
        )
        self._discount_label.grid(row=3, column=1, sticky="e", pady=2, padx=(20, 0))

        # Total box
        total_box = ctk.CTkFrame(totals_frame, fg_color="#2b2b2b", corner_radius=8)
        total_box.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        total_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            total_box,
            text="TOTAL A PAGAR",
            font=ctk.CTkFont(size=11),
            text_color="#a0a0a0",
        ).grid(row=0, column=0, pady=(10, 0))
        self._total_label = ctk.CTkLabel(
            total_box,
            text="$0",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#ffffff",
        )
        self._total_label.grid(row=1, column=0, pady=(0, 10))

        # --- Payment method selection ---
        payment_methods_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        payment_methods_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(10, 10))
        payment_methods_frame.grid_columnconfigure(0, weight=1)

        # Title for payment methods
        ctk.CTkLabel(
            payment_methods_frame,
            text="Método de pago",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._payment_method_var = tk.StringVar(value="cash")
        self._method_frames: dict[str, ctk.CTkFrame] = {}

        for idx, (label, method) in enumerate(self.PAYMENT_METHODS):
            method_frame = ctk.CTkFrame(
                payment_methods_frame,
                fg_color="#2b2b2b" if method == "cash" else "transparent",
                border_width=2,
                border_color="#0078d4" if method == "cash" else "#3e3e3e",
                corner_radius=12,
                cursor="hand2",
            )
            method_frame.grid(row=idx + 1, column=0, sticky="ew", pady=3)
            method_frame.grid_columnconfigure(1, weight=1)
            self._method_frames[method] = method_frame

            # Radio button indicator
            radio_frame = ctk.CTkFrame(method_frame, fg_color="transparent", width=30)
            radio_frame.grid(row=0, column=0, padx=(10, 5))

            ctk.CTkRadioButton(
                radio_frame,
                text="",
                variable=self._payment_method_var,
                value=method,
                command=lambda m=method: self._on_payment_method_changed(m),
                width=20,
                height=20,
            ).pack(pady=5)

            # Label
            ctk.CTkLabel(
                method_frame,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold" if method == "cash" else "normal"),
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=10)

            # Bind click on entire frame to select this method
            method_frame.bind("<Button-1>", lambda e, m=method: self._select_payment_method(m))
            # Also bind on child widgets so clicks propagate
            for child in method_frame.winfo_children():
                child.bind("<Button-1>", lambda e, m=method: self._select_payment_method(m))

        # --- Amount received ---
        self._amount_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        self._amount_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 10))
        self._amount_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._amount_frame,
            text="Monto recibido ($):",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a0",
        ).grid(row=0, column=0, pady=(0, 5))

        self._received_entry = ctk.CTkEntry(
            self._amount_frame,
            placeholder_text="Ej: 5000",
            height=40,
            font=ctk.CTkFont(size=16),
        )
        self._received_entry.grid(row=1, column=0, sticky="ew")
        self._received_entry.bind("<KeyRelease>", self._on_received_changed)

        # Change display
        change_frame = ctk.CTkFrame(self._amount_frame, fg_color="transparent")
        change_frame.grid(row=2, column=0, pady=(10, 0))

        ctk.CTkLabel(
            change_frame,
            text="Vuelto:",
            font=ctk.CTkFont(size=16),
            text_color="#a0a0a0",
        ).pack(side="left", padx=(0, 5))
        self._change_label = ctk.CTkLabel(
            change_frame,
            text="$0",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._change_label.pack(side="left")

        # --- Action buttons ---
        buttons_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        buttons_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(20, 15))
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self._cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancelar",
            height=40,
            fg_color="#52525b",
            hover_color="#71717a",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._handle_cancel,
        )
        self._cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self._confirm_btn = ctk.CTkButton(
            buttons_frame,
            text="Confirmar",
            height=40,
            fg_color="#0078d4",
            hover_color="#106ebe",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._handle_confirm,
        )
        self._confirm_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # --- auto-focus barcode entry whenever the frame is mapped ---
        self.bind("<Map>", lambda _e: self._barcode_entry.focus_set())

    # ---------------------------------------------------------------- public ---

    def update_cart(self, items: list[dict[str, Any]]) -> None:
        """Refresh the cart treeview with the given *items*."""
        self._cart_tree.update_cart(items)

    def update_total(self, total: int) -> None:
        """Update the displayed cart total and related fields."""
        self._total = total
        self._total_label.configure(text=f"${total:,}")
        self._subtotal_label.configure(text=f"${total:,}")
        self._on_received_changed()  # Recalculate change

    def focus_barcode(self) -> None:
        """Force focus onto the barcode entry widget."""
        self._barcode_entry.focus_set()

    def show_receipt(self, sale_data: dict[str, Any]) -> None:
        """Display an on-screen receipt preview after a successful sale.

        *sale_data* is the controller response ``data`` field, expected
        to contain ``sale``, ``items``, and ``change``.
        """
        from pos.view.widgets.receipt_preview import ReceiptPreview

        ReceiptPreview(self, sale_data)

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
            # Check if product exists but is inactive
            if data.get("inactive"):
                product = data.get("product")
                product_name = product.name if product else "producto"
                confirm = messagebox.askyesno(
                    "Producto desactivado",
                    f'El producto "{product_name}" está desactivado.\n\n'
                    "¿Desea reactivarlo y agregarlo al carrito?",
                )
                if confirm:
                    reactivate_result = self._controller.reactivate_and_add(
                        product.id, 1.0
                    )
                    if reactivate_result["success"]:
                        self._update_cart()
                        messagebox.showinfo(
                            "Producto reactivado",
                            f'El producto "{product_name}" ha sido reactivado y agregado al carrito.',
                        )
                    else:
                        messagebox.showerror("Error", reactivate_result["error"])
                # Whether they confirm or not, return focus to barcode entry
                self._barcode_entry.focus_set()
                return
            
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
        result = self._controller.complete_sale(
            payment_method=method,
            amount_received=received,
        )
        if result["success"]:
            # Show receipt preview
            self.show_receipt(result["data"])
            self._clear_cart()
            # Reset payment sidebar
            self._received_entry.delete(0, tk.END)
            self._change_label.configure(text="$0")
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

    def _select_payment_method(self, method: str) -> None:
        """Select a payment method when clicking on its frame."""
        self._payment_method_var.set(method)
        self._on_payment_method_changed(method)

    def _on_payment_method_changed(self, method: str) -> None:
        """Update visual state when payment method changes."""
        self._selected_payment_method = method
        # Update border colors and backgrounds to show selection
        for m, frame in self._method_frames.items():
            if m == method:
                frame.configure(
                    fg_color="#2b2b2b",
                    border_color="#0078d4",
                )
            else:
                frame.configure(
                    fg_color="transparent",
                    border_color="#3e3e3e",
                )
        
        # Show/hide amount received field based on payment method
        if method == "cash":
            self._amount_frame.grid()
        else:
            self._amount_frame.grid_remove()

    def _on_received_changed(self, event: tk.Event | None = None) -> None:
        """Recalculate change as the user types the received amount."""
        raw = self._received_entry.get().strip()
        if not raw:
            self._change_label.configure(text="$0")
            return
        try:
            received = int(raw)
        except ValueError:
            self._change_label.configure(text="$0")
            return

        change = received - self._total
        if change >= 0:
            self._change_label.configure(text=f"${change:,}")
        else:
            self._change_label.configure(text=f"-${abs(change):,}")

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
            # If the input looks like a barcode (all digits), treat it the
            # same as a scanner hit — open QuickCreateDialog so the user
            # can register the product on the spot.
            if query.isdigit():
                self._controller_scan(query)
            else:
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

    def _handle_cancel(self) -> None:
        """Cancel the current sale and clear the cart."""
        if self._total > 0:
            confirm = messagebox.askyesno(
                "Cancelar venta",
                "¿Está seguro de cancelar la venta actual?\n\nSe perderán todos los productos del carrito.",
            )
            if not confirm:
                return
        
        self._clear_cart()
        self._received_entry.delete(0, tk.END)
        self._change_label.configure(text="$0")

    def _handle_confirm(self) -> None:
        """Process the payment with the selected method and received amount."""
        if self._total == 0:
            messagebox.showwarning("Pago", "No hay productos en el carrito")
            return

        method = self._payment_method_var.get()
        
        if method == "cash":
            raw = self._received_entry.get().strip()
            try:
                received = int(raw)
            except ValueError:
                messagebox.showerror("Error", "Ingrese un monto válido")
                self._received_entry.focus_set()
                return

            if received < self._total:
                messagebox.showerror("Error", "Monto insuficiente")
                self._received_entry.focus_set()
                return
        else:
            received = 0

        if self._on_payment is not None:
            self._on_payment(method, received)
