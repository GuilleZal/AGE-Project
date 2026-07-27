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
from pos.view.widgets.centered_dialog import CenteredDialog


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

        self._qty_var = tk.StringVar(value="1")

        # 2. Reason Frame 
        self._reason_frame = ctk.CTkFrame(self._left_col, fg_color="transparent", border_width=2, border_color=border_color)
        self._reason_frame.grid(row=1, column=0, sticky="ew", pady=(0, 0))

        ctk.CTkLabel(
            self._reason_frame, text="Motivo de la Devolución", font=theme.scaled_font(14, "bold")
        ).pack(anchor="w", padx=15, pady=(6, 1))

        self._reason_var = tk.StringVar(value="Producto en buenas condiciones")
        
        ctk.CTkRadioButton(
            self._reason_frame, text="Producto en buenas condiciones", variable=self._reason_var, 
            value="Producto en buenas condiciones"
        ).pack(anchor="w", padx=15, pady=1)
        
        ctk.CTkRadioButton(
            self._reason_frame, text="Producto Vencido", variable=self._reason_var, 
            value="Producto Vencido"
        ).pack(anchor="w", padx=15, pady=1)
        
        ctk.CTkRadioButton(
            self._reason_frame, text="Producto Dañado", variable=self._reason_var, 
            value="Producto Dañado"
        ).pack(anchor="w", padx=15, pady=(1, 10))

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

        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=0)
        details_frame.grid_columnconfigure(2, weight=0)

        # Subtotal
        ctk.CTkLabel(details_frame, text="Subtotal:", font=theme.scaled_font(13)).grid(row=0, column=0, sticky="w", pady=1)
        self._summary_subtotal_lbl = ctk.CTkLabel(details_frame, text="$0", font=theme.scaled_font(13))
        self._summary_subtotal_lbl.grid(row=0, column=1, sticky="e", padx=(5, 0), pady=1)

        # Cantidad
        ctk.CTkLabel(details_frame, text="Cantidad:", font=theme.scaled_font(13)).grid(row=1, column=0, sticky="w", pady=1)
        self._summary_qty_lbl = ctk.CTkLabel(details_frame, text="1", font=theme.scaled_font(13))
        self._summary_qty_lbl.grid(row=1, column=1, sticky="e", padx=(5, 5), pady=1)

        self._modify_qty_btn = ctk.CTkButton(
            details_frame,
            text="✏️ Modificar",
            width=90,
            height=26,
            font=theme.scaled_font(11, "bold"),
            border_width=1,
            border_color="#3498db",
            fg_color="transparent",
            hover_color="#1f538d",
            text_color="#3498db",
            command=self._handle_modify_qty,
            state="disabled"
        )
        self._modify_qty_btn.grid(row=1, column=2, sticky="e", pady=1)

        # Sep
        sep = ctk.CTkFrame(details_frame, height=2, fg_color="#555555")
        sep.grid(row=2, column=0, columnspan=3, sticky="ew", pady=4)

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
        self.clear_error()
        self._current_product = product
        self._product_name_lbl.configure(text=product.get("name", "—"))
        
        # Fix: Show "—" if the product has no barcode
        barcode = product.get("barcode")
        if not barcode or barcode == "None":
            self._barcode_val_lbl.configure(text="—")
        else:
            self._barcode_val_lbl.configure(text=str(barcode))
            
        self._price_val_lbl.configure(text=f"${product.get('sale_price', 0):,}")
        self._confirm_btn.configure(state="normal")
        self._modify_qty_btn.configure(state="normal")
        
        # Default quantity to 1 (since quantity module is removed)
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
        self._modify_qty_btn.configure(state="disabled")

    def clear_form(self) -> None:
        """Clear all form fields (quantity and reason)."""
        self._qty_var.set("1")
        self._reason_var.set("Producto en buenas condiciones")
        
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
            
            dialog = ReturnSuccessDialog(self, refund)
            self.wait_window(dialog)
            
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
        reason = self._reason_var.get()

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

    def _handle_modify_qty(self) -> None:
        if self._current_product is None:
            return

        unit_type = self._current_product.get("unit_type", "Unidad")
        is_kg = unit_type.lower() in ("kg", "weight_kg")
        
        # Get current quantity
        current_val = self._qty_var.get().strip()
        
        dialog = ReturnQuantityDialog(
            self,
            product_name=self._current_product.get("name", ""),
            is_kg=is_kg,
            current_qty=current_val
        )
        self.wait_window(dialog)
        
        if dialog.result is not None:
            if is_kg:
                self._qty_var.set(f"{dialog.result:.3f}".rstrip("0").rstrip("."))
            else:
                self._qty_var.set(str(int(dialog.result)))
            self._update_refund()


class ReturnQuantityDialog(CenteredDialog):
    """Modal dialog to input quantity for unit or weight return products."""

    def __init__(
        self,
        master: tk.Widget,
        product_name: str,
        is_kg: bool,
        current_qty: str,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=380,
            height=240,
            title="Modificar Cantidad",
            **kwargs,
        )

        self._result: float | None = None
        self._is_kg = is_kg

        # --- Header section ---
        ctk.CTkLabel(
            self,
            text="Modificar Cantidad a Devolver",
            font=theme.scaled_font(15, weight="bold"),
        ).pack(pady=(15, 2))

        ctk.CTkLabel(
            self,
            text=product_name,
            font=theme.scaled_font(13),
            text_color="#a0a0a0",
            wraplength=340,
        ).pack(pady=(0, 15))

        # --- Form/Input ---
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="x", padx=30, pady=5)
        form_frame.grid_columnconfigure(0, weight=0)
        form_frame.grid_columnconfigure(1, weight=1)

        label_text = "Cantidad (Kg):" if is_kg else "Cantidad (unidades):"
        ctk.CTkLabel(
            form_frame,
            text=label_text,
            font=theme.scaled_font(14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))

        self._qty_entry = ctk.CTkEntry(
            form_frame,
            height=36,
            font=theme.scaled_font(14),
        )
        self._qty_entry.grid(row=0, column=1, sticky="ew", pady=6)
        self._qty_entry.insert(0, current_qty)
        self._qty_entry.select_range(0, tk.END)

        # --- Error label ---
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#ef4444",
            font=theme.scaled_font(12),
        )
        self._error_label.pack(pady=(2, 5))

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(5, 15))

        ctk.CTkButton(
            btn_frame,
            text="Confirmar",
            width=120,
            height=34,
            font=theme.scaled_font(13, weight="bold"),
            command=self._confirm,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            height=34,
            fg_color="#52525b",
            hover_color="#3f3f46",
            font=theme.scaled_font(13, weight="bold"),
            command=self._cancel,
        ).pack(side="left", padx=8)

        # Binds
        self._qty_entry.bind("<Return>", lambda _e: self._confirm())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self._qty_entry.focus_set()

        # Center properly
        self.update_idletasks()
        self._center_on_parent(master)

    @property
    def result(self) -> float | None:
        return self._result

    def _confirm(self) -> None:
        val = self._qty_entry.get().strip().replace(",", ".")
        if not val:
            self._error_label.configure(text="Ingrese una cantidad")
            self._qty_entry.focus_set()
            return

        try:
            qty = float(val)
        except ValueError:
            self._error_label.configure(text="Ingrese una cantidad válida")
            self._qty_entry.focus_set()
            return

        if qty <= 0:
            self._error_label.configure(text="La cantidad debe ser mayor a 0")
            self._qty_entry.focus_set()
            return

        if not self._is_kg:
            if not qty.is_integer():
                self._error_label.configure(text="Ingrese un número entero")
                self._qty_entry.focus_set()
                return
            qty = float(int(qty))

        self._result = qty
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()


class ReturnSuccessDialog(CenteredDialog):
    """Custom success message dialog centered on the system window."""

    def __init__(self, master: tk.Widget, refund: int, **kwargs) -> None:
        super().__init__(
            master,
            width=360,
            height=180,
            title="Devolución Procesada",
            **kwargs,
        )

        # --- Icon/Header ---
        ctk.CTkLabel(
            self,
            text="✅ Devolución Procesada",
            font=theme.scaled_font(16, weight="bold"),
            text_color="#2ecc71",
        ).pack(pady=(20, 10))

        # --- Message ---
        message_text = f"Devolución registrada correctamente.\nReintegro: ${refund:,}"
        ctk.CTkLabel(
            self,
            text=message_text,
            font=theme.scaled_font(13),
            justify="center",
        ).pack(pady=(0, 20))

        # --- Close button ---
        ctk.CTkButton(
            self,
            text="Aceptar",
            width=100,
            height=32,
            font=theme.scaled_font(13, weight="bold"),
            command=self.destroy,
        ).pack(pady=(0, 15))

        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self.update_idletasks()
        self._center_on_parent(master)

        # Focus
        self.focus_set()