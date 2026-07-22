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
        role: str = "",
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}
        self._role = role

        # --- callback slots ---
        self._on_search: Callable[[str], None] | None = callbacks.get("on_search")
        self._on_return: Callable[[int, float, str | None], None] | None = callbacks.get("on_return")
        self._on_return_completed: Callable[[], None] | None = callbacks.get("on_return_completed")

        self._current_product: dict[str, Any] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- row 0: barcode entry + search button ---
        self._top_frame = ctk.CTkFrame(self)
        self._top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self._top_frame.grid_columnconfigure(0, weight=1)

        self._barcode_entry = BarcodeEntry(
            self._top_frame,
            on_scan=self._handle_scan,
            height=45,
            font=theme.scaled_font(16),
            placeholder_text="Escanear código de barras para devolución...",
        )
        self._barcode_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

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

        # --- row 1: Content Split (Two Columns) ---
        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self._content_frame.grid_columnconfigure(0, weight=1, uniform="col")
        self._content_frame.grid_columnconfigure(1, weight=1, uniform="col")

        # ==========================================
        # LEFT COLUMN: Info, Quantity, and Reason
        # ==========================================
        self._left_col = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        # Colchón inferior de 10px para asegurar que nunca toque el fondo
        self._left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
        self._left_col.grid_columnconfigure(0, weight=1)

        # 1. Product Info Frame 
        self._info_frame = ctk.CTkFrame(self._left_col, fg_color="transparent", border_width=2, border_color=border_color)
        self._info_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5)) # Margen reducido
        self._info_frame.grid_columnconfigure(1, weight=1)

        # Product Row
        ctk.CTkLabel(
            self._info_frame, text="Producto:", font=theme.scaled_font(15, "bold")
        ).grid(row=0, column=0, sticky="nw", padx=(15, 5), pady=(8, 2)) # Súper compacto
        self._product_name_lbl = ctk.CTkLabel(
            self._info_frame, text="—", font=theme.scaled_font(15),
            justify="left", wraplength=250 
        )
        self._product_name_lbl.grid(row=0, column=1, sticky="w", padx=5, pady=(8, 2))

        # Barcode Row
        ctk.CTkLabel(
            self._info_frame, text="Código:", font=theme.scaled_font(14)
        ).grid(row=1, column=0, sticky="w", padx=(15, 5), pady=1)
        self._barcode_val_lbl = ctk.CTkLabel(
            self._info_frame, text="—", font=theme.scaled_font(14)
        )
        self._barcode_val_lbl.grid(row=1, column=1, sticky="w", padx=5, pady=1)

        # Price Row
        ctk.CTkLabel(
            self._info_frame, text="Precio Unit.:", font=theme.scaled_font(14)
        ).grid(row=2, column=0, sticky="w", padx=(15, 5), pady=(1, 8))
        self._price_val_lbl = ctk.CTkLabel(
            self._info_frame, text="—", font=theme.scaled_font(14)
        )
        self._price_val_lbl.grid(row=2, column=1, sticky="w", padx=5, pady=(1, 8))

        # 2. Quantity Frame 
        self._qty_frame = ctk.CTkFrame(self._left_col, fg_color="transparent", border_width=2, border_color=border_color)
        self._qty_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        ctk.CTkLabel(
            self._qty_frame, text="Cantidad a Devolver", font=theme.scaled_font(14, "bold")
        ).pack(anchor="w", padx=15, pady=(6, 1))

        qty_ctrl_frame = ctk.CTkFrame(self._qty_frame, fg_color="transparent")
        qty_ctrl_frame.pack(fill="x", padx=15, pady=(0, 6))
        qty_ctrl_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            qty_ctrl_frame, text="−", width=40, font=theme.scaled_font(16, "bold"),
            command=self._decrement_qty
        ).grid(row=0, column=0, padx=(0, 5))
        
        self._qty_var = tk.StringVar(value="1")
        self._qty_spin = ctk.CTkEntry(
            qty_ctrl_frame, textvariable=self._qty_var, justify="center", height=28, font=theme.scaled_font(14)
        )
        self._qty_spin.grid(row=0, column=1, sticky="ew", padx=5)
        
        ctk.CTkButton(
            qty_ctrl_frame, text="＋", width=40, font=theme.scaled_font(16, "bold"),
            command=self._increment_qty
        ).grid(row=0, column=2, padx=(5, 0))

        # 3. Reason Frame 
        self._reason_frame = ctk.CTkFrame(self._left_col, fg_color="transparent", border_width=2, border_color=border_color)
        self._reason_frame.grid(row=2, column=0, sticky="ew", pady=(0, 0))

        ctk.CTkLabel(
            self._reason_frame, text="Motivo de la Devolución", font=theme.scaled_font(14, "bold")
        ).pack(anchor="w", padx=15, pady=(6, 1))

        self._reason_var = tk.StringVar(value="Producto Vencido")
        
        ctk.CTkRadioButton(
            self._reason_frame, text="Producto Vencido", variable=self._reason_var, 
            value="Producto Vencido", command=self._on_reason_change
        ).pack(anchor="w", padx=15, pady=1)
        
        ctk.CTkRadioButton(
            self._reason_frame, text="Producto Dañado", variable=self._reason_var, 
            value="Producto Dañado", command=self._on_reason_change
        ).pack(anchor="w", padx=15, pady=1)

        ctk.CTkRadioButton(
            self._reason_frame, text="Otro", variable=self._reason_var, 
            value="Otro", command=self._on_reason_change
        ).pack(anchor="w", padx=15, pady=1)

        ctk.CTkLabel(
            self._reason_frame, text="Detalle del motivo:", font=theme.scaled_font(12)
        ).pack(anchor="w", padx=15, pady=(2, 0))
        
        self._reason_entry = ctk.CTkEntry(
            self._reason_frame, placeholder_text="Aclare el motivo...", state="disabled", height=28
        )
        self._reason_entry.pack(fill="x", padx=15, pady=(1, 8))

        # ==========================================
        # RIGHT COLUMN: Summary and Confirm
        # ==========================================
        self._right_col = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        # Ajustamos el margen inferior para protegerlo del borde maestro
        self._right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 15), pady=(0, 10))
        
        self._right_col.grid_columnconfigure(0, weight=1)
        self._right_col.grid_rowconfigure(0, weight=1) # Espacio fantasma
        self._right_col.grid_rowconfigure(1, weight=0) # Caja intocable
        
        # Summary & Confirm Frame
        self._summary_frame = ctk.CTkFrame(
            self._right_col, border_width=2, border_color="#0078d4"
        )
        self._summary_frame.grid(row=1, column=0, sticky="sew", pady=(0, 0))

        details_frame = ctk.CTkFrame(self._summary_frame, fg_color="transparent")
        details_frame.pack(fill="x", padx=10, pady=(6, 2)) 
        
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=0)

        # Subtotal
        ctk.CTkLabel(details_frame, text="Subtotal:", font=theme.scaled_font(13)).grid(row=0, column=0, sticky="w", pady=1)
        self._summary_subtotal_lbl = ctk.CTkLabel(details_frame, text="$0", font=theme.scaled_font(13))
        self._summary_subtotal_lbl.grid(row=0, column=1, sticky="e", padx=(5, 0), pady=1)

        # Cantidad
        ctk.CTkLabel(details_frame, text="Cantidad:", font=theme.scaled_font(13)).grid(row=1, column=0, sticky="w", pady=1)
        self._summary_qty_lbl = ctk.CTkLabel(details_frame, text="1", font=theme.scaled_font(13))
        self._summary_qty_lbl.grid(row=1, column=1, sticky="e", padx=(5, 0), pady=1)

        # Sep
        sep = ctk.CTkFrame(details_frame, height=2, fg_color="#555555")
        sep.grid(row=2, column=0, columnspan=2, sticky="ew", pady=4)

        # Total
        ctk.CTkLabel(
            details_frame, text="Total:", font=theme.scaled_font(15, "bold")
        ).grid(row=3, column=0, sticky="w", pady=1)
        self._refund_label = ctk.CTkLabel(
            details_frame, text="$0", font=theme.scaled_font(15, "bold"), text_color="#3498db"
        )
        self._refund_label.grid(row=3, column=1, sticky="e", padx=(5, 0), pady=1)

        # Confirm Button
        self._confirm_btn = ctk.CTkButton(
            self._summary_frame,
            text="Confirmar devolución",
            height=36,
            font=theme.scaled_font(14, "bold"),
            command=self._handle_confirm,
            state="disabled"
        )
        self._confirm_btn.pack(fill="x", padx=10, pady=(0, 10))

        # --- Error label (bottom) ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        # Reducimos su margen al mínimo absoluto para que no quite espacio vital
        self._error_label.grid(row=2, column=0, padx=10, pady=(0, 2))

        # Trace quantity changes to automatically update summary
        self._qty_var.trace_add("write", lambda *args: self._update_refund())

        # Auto-focus the barcode entry
        self.bind("<Map>", lambda _e: self._barcode_entry.focus_set())
        
    # ---------------------------------------------------------------- public ---

    def show_product(self, product: dict[str, Any]) -> None:
        """Display product information after a successful lookup."""
        self._current_product = product
        self._product_name_lbl.configure(text=product.get("name", "—"))
        self._barcode_val_lbl.configure(text=product.get("barcode", "—"))
        self._price_val_lbl.configure(text=f"${product.get('sale_price', 0):,}")
        self._confirm_btn.configure(state="normal")
        
        # Set quantity entry default based on unit type
        unit_type = product.get("unit_type", "Unidad")
        is_kg = unit_type.lower() in ("kg", "weight_kg")
        if is_kg:
            self._qty_var.set("")
        else:
            self._qty_var.set("1")
            
        self._update_refund()

    def clear_product(self) -> None:
        """Clear the displayed product info."""
        self._current_product = None
        self._product_name_lbl.configure(text="—")
        self._barcode_val_lbl.configure(text="—")
        self._price_val_lbl.configure(text="—")
        self._summary_subtotal_lbl.configure(text="$0")
        self._summary_qty_lbl.configure(text="0")
        self._refund_label.configure(text="$0")
        self._qty_var.set("1")
        self._confirm_btn.configure(state="disabled")

    def clear_form(self) -> None:
        """Clear all form fields (quantity and reason)."""
        self._qty_var.set("1")
        self._reason_var.set("Producto Vencido")
        
        # Habilitar temporalmente para borrar el texto y luego volver a bloquear
        self._reason_entry.configure(state="normal")
        self._reason_entry.delete(0, "end")
        self._reason_entry.configure(state="disabled")
        
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

    def set_on_return(self, callback: Callable[[int, float, str | None], None]) -> None:
        """Wire the confirm-return callback."""
        self._on_return = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``ReturnController`` instance and set up all event handlers."""
        self._controller = controller
        self._on_search = self._controller_search
        self._on_return = self._controller_confirm_return
        self._barcode_entry.set_callback(self._controller_search)

    # ---------------------------------------------------- controller handlers ---

    def _controller_search(self, barcode: str) -> None:
        """Look up product by barcode via controller."""
        self.clear_error()
        self.clear_product()

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
        if self._current_product is None:
            return
        unit_type = self._current_product.get("unit_type", "Unidad")
        is_kg = unit_type.lower() in ("kg", "weight_kg")
        step = 0.1 if is_kg else 1.0

        val = self._qty_var.get().strip()
        try:
            qty = float(val) if val else 0.0
        except ValueError:
            qty = 0.0
        qty += step
        if is_kg:
            self._qty_var.set(f"{qty:.2f}")
        else:
            self._qty_var.set(str(int(qty)))
        self._update_refund()

    def _decrement_qty(self) -> None:
        if self._current_product is None:
            return
        unit_type = self._current_product.get("unit_type", "Unidad")
        is_kg = unit_type.lower() in ("kg", "weight_kg")
        step = 0.1 if is_kg else 1.0

        val = self._qty_var.get().strip()
        try:
            qty = float(val) if val else 0.0
        except ValueError:
            qty = 0.0
        qty = max(0.0, qty - step)
        if is_kg:
            self._qty_var.set(f"{qty:.2f}")
        else:
            self._qty_var.set(str(int(qty)))
        self._update_refund()

    def _update_refund(self) -> None:
        # Prevent updates if widgets are not yet initialized during trace registration
        if not hasattr(self, "_summary_subtotal_lbl") or not hasattr(self, "_summary_qty_lbl") or not hasattr(self, "_refund_label"):
            return

        if self._current_product is None:
            self._summary_subtotal_lbl.configure(text="$0")
            self._summary_qty_lbl.configure(text="0")
            self._refund_label.configure(text="$0")
            return
            
        unit_type = self._current_product.get("unit_type", "Unidad")
        is_kg = unit_type.lower() in ("kg", "weight_kg")
        
        val = self._qty_var.get().strip()
        if not is_kg:
            # Clean non-digits (prevent floats for units)
            cleaned = "".join(c for c in val if c.isdigit())
            if cleaned != val:
                self._qty_var.set(cleaned)
                val = cleaned
        else:
            # Clean non-decimal chars (only allow digits and at most one dot)
            val_replaced = val.replace(",", ".")
            parts = val_replaced.split(".")
            if len(parts) > 2:
                val_replaced = parts[0] + "." + "".join(parts[1:])
            
            cleaned = "".join(c for c in val_replaced if c.isdigit() or c == ".")
            if cleaned != val:
                self._qty_var.set(cleaned)
                val = cleaned
            
        try:
            qty = float(val) if val else 0.0
        except ValueError:
            qty = 0.0
            
        price = self._current_product.get("sale_price", 0)
        total = int(price * qty)

        self._summary_subtotal_lbl.configure(text=f"${price:,}")
        
        if is_kg:
            qty_str = f"{qty} Kg"
        else:
            qty_str = f"{int(qty)} u."
            
        self._summary_qty_lbl.configure(text=qty_str)
        self._refund_label.configure(text=f"${total:,}")

    def _on_reason_change(self) -> None:
        """Enable text entry only when 'Otro' is selected."""
        if self._reason_var.get() == "Otro":
            self._reason_entry.configure(state="normal")
            self._reason_entry.focus_set()
        else:
            self._reason_entry.configure(state="disabled")
            self._reason_entry.delete(0, "end")

    def _handle_confirm(self) -> None:
        if self._current_product is None:
            return

        val = self._qty_var.get().strip()
        if not val:
            self._error_label.configure(text="Ingrese una cantidad válida")
            return

        try:
            qty = float(val)
        except ValueError:
            self._error_label.configure(text="Ingrese una cantidad válida")
            return

        if qty <= 0:
            self._error_label.configure(text="La cantidad debe ser mayor a 0")
            return

        # Procesar motivo de devolución
        selected_reason = self._reason_var.get()
        if selected_reason == "Otro":
            reason = self._reason_entry.get().strip()
            if not reason:
                self._error_label.configure(text="Por favor, aclare el motivo de la devolución")
                return
        else:
            reason = selected_reason

        self.clear_error()

        if self._on_return is not None:
            self._on_return(self._current_product["id"], qty, reason)


    def _handle_search_button(self) -> None:
        """Open search dialog with all products for manual selection."""
        if not hasattr(self, "_controller") or self._controller is None:
            return

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
        dialog = ProductSearchDialog(self, products, categories, role=self._role, is_return=True)
        self.wait_window(dialog)
        selected = dialog.result
        if selected is not None:
            self.show_product({
                "id": selected.id,
                "barcode": selected.barcode,
                "name": selected.name,
                "sale_price": selected.sale_price,
                "unit_type": selected.unit_type,
            })
        self._barcode_entry.focus_set()

    def _get_categories(self) -> list:
        """Fetch categories from controller for the search dialog."""
        if hasattr(self, "_controller") and hasattr(self._controller, "list_categories"):
            result = self._controller.list_categories()
            if result["success"]:
                return result["data"]
        return []