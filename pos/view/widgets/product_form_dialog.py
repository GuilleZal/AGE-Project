"""Product form dialog — create / edit product with full field set.

A ``CTkToplevel`` modal dialog that collects all product fields for
both creation and editing workflows.  When a *product* is passed (edit
mode) the fields are pre-populated; otherwise the form starts empty
(create mode).
"""

import tkinter as tk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class ProductFormDialog(CenteredDialog):
    """Modal dialog to create or edit a product.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    product : dict[str, Any] | None
        Existing product data for edit mode (must include keys like
        ``barcode``, ``name``, ``category_id``, ``sale_price``,
        ``cost_price``, ``stock``, ``description``,
        ``low_stock_threshold``).  ``None`` for create mode.
    categories : list[dict[str, Any]] | None
        Category list with keys ``id`` and ``name``.  If provided, a
        category dropdown is shown.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self,
        master: tk.Widget,
        product: dict[str, Any] | None = None,
        categories: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> None:
        title = "Editar producto" if product else "Nuevo producto"
        super().__init__(master, width=480, height=540, title=title, **kwargs)

        self._result: dict[str, Any] | None = None

        # Build category lookup
        if categories:
            self._cat_map: dict[str, int | None] = {"— Sin categoría —": None}
            for c in categories:
                self._cat_map[c["name"]] = c["id"]
        else:
            self._cat_map = {"— Sin categoría —": None}

        cat_names = list(self._cat_map.keys())

        # Determine current values for edit mode
        prev = product or {}
        prev_barcode = prev.get("barcode", "") or ""
        prev_name = prev.get("name", "") or ""
        prev_cat_name = "— Sin categoría —"
        if categories and prev.get("category_id"):
            for c in categories:
                if c["id"] == prev["category_id"]:
                    prev_cat_name = c["name"]
                    break
        prev_sale = str(prev.get("sale_price", ""))
        prev_cost = str(prev.get("cost_price", ""))
        prev_stock = str(prev.get("stock", ""))
        prev_desc = prev.get("description", "") or ""
        prev_threshold = str(prev.get("low_stock_threshold", "5"))

        # --- form body (scrollable if many fields) ---
        body = ctk.CTkScrollableFrame(self, width=450, height=380)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        body.grid_columnconfigure(0, weight=1)

        row = 0

        # Checkbox "Sin código de barras"
        self._no_barcode_var = tk.BooleanVar(value=not bool(prev_barcode))
        self._no_barcode_cb = ctk.CTkCheckBox(
            body,
            text="Sin código de barras",
            variable=self._no_barcode_var,
            font=theme.scaled_font(12),
            command=self._on_no_barcode_toggled,
        )
        self._no_barcode_cb.grid(row=row, column=0, sticky="w", padx=15, pady=(10, 5))
        row += 1

        # Barcode
        self._barcode_label = ctk.CTkLabel(body, text="Código de barras", font=theme.scaled_font(12))
        self._barcode_label.grid(row=row, column=0, sticky="w", padx=15, pady=(5, 0))
        row += 1
        self._barcode_entry = ctk.CTkEntry(
            body, width=400, placeholder_text="Ingrese o escanee el código"
        )
        self._barcode_entry.insert(0, prev_barcode)
        self._barcode_entry.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 5))
        row += 1
        self._on_no_barcode_toggled(set_focus=False)

        # Name
        ctk.CTkLabel(body, text="Nombre *", font=theme.scaled_font(12)).grid(
            row=row, column=0, sticky="w", padx=15, pady=(5, 0)
        )
        row += 1
        self._name_entry = ctk.CTkEntry(
            body, width=400, placeholder_text="Nombre del producto"
        )
        self._name_entry.insert(0, prev_name)
        self._name_entry.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 5))
        row += 1

        # Category
        ctk.CTkLabel(body, text="Categoría", font=theme.scaled_font(12)).grid(
            row=row, column=0, sticky="w", padx=15, pady=(5, 0)
        )
        row += 1
        self._category_var = tk.StringVar(value=prev_cat_name)
        self._category_menu = ctk.CTkOptionMenu(
            body,
            values=cat_names,
            variable=self._category_var,
            width=400,
        )
        self._category_menu.grid(row=row, column=0, sticky="w", padx=15, pady=(0, 5))
        row += 1

        # Calculate initial margin percentage if cost and sale are present
        prev_margin = ""
        if prev.get("cost_price") and prev.get("sale_price"):
            c = prev["cost_price"]
            s = prev["sale_price"]
            if s > 0:
                prev_margin = f"{((s - c) / s) * 100:.1f}".rstrip('0').rstrip('.')

        # Cost price + Margin % + Sale price (side by side)
        price_frame = ctk.CTkFrame(body, fg_color="transparent")
        price_frame.grid(row=row, column=0, sticky="ew", padx=15, pady=5)
        price_frame.grid_columnconfigure(0, weight=1)
        price_frame.grid_columnconfigure(1, weight=1)
        price_frame.grid_columnconfigure(2, weight=1)
        row += 1

        ctk.CTkLabel(price_frame, text="Precio costo ($) *", font=theme.scaled_font(12)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ctk.CTkLabel(price_frame, text="Ganancia (%)", font=theme.scaled_font(12)).grid(
            row=0, column=1, sticky="w", padx=(5, 5)
        )
        ctk.CTkLabel(price_frame, text="Precio venta ($) *", font=theme.scaled_font(12)).grid(
            row=0, column=2, sticky="w", padx=(5, 0)
        )

        self._cost_price_entry = ctk.CTkEntry(
            price_frame, width=120, placeholder_text="0"
        )
        self._cost_price_entry.insert(0, prev_cost)
        self._cost_price_entry.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(2, 0))
        self._cost_price_entry.bind("<KeyRelease>", self._on_cost_changed)

        self._margin_entry = ctk.CTkEntry(
            price_frame, width=120, placeholder_text="0"
        )
        self._margin_entry.insert(0, prev_margin)
        self._margin_entry.grid(row=1, column=1, sticky="w", padx=(5, 5), pady=(2, 0))
        self._margin_entry.bind("<KeyRelease>", self._on_margin_changed)

        self._sale_price_entry = ctk.CTkEntry(
            price_frame, width=120, placeholder_text="0"
        )
        self._sale_price_entry.insert(0, prev_sale)
        self._sale_price_entry.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(2, 0))
        self._sale_price_entry.bind("<KeyRelease>", self._on_sale_changed)

        # Stock + Low stock threshold + Unit type (side by side)
        stock_frame = ctk.CTkFrame(body, fg_color="transparent")
        stock_frame.grid(row=row, column=0, sticky="ew", padx=15, pady=5)
        stock_frame.grid_columnconfigure(0, weight=1)
        stock_frame.grid_columnconfigure(1, weight=1)
        stock_frame.grid_columnconfigure(2, weight=1)
        row += 1

        ctk.CTkLabel(stock_frame, text="Cantidad", font=theme.scaled_font(12)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ctk.CTkLabel(stock_frame, text="Tipo de Unidad", font=theme.scaled_font(12)).grid(
            row=0, column=1, sticky="w", padx=(5, 5)
        )
        ctk.CTkLabel(stock_frame, text="Alerta stock bajo", font=theme.scaled_font(12)).grid(
            row=0, column=2, sticky="w", padx=(5, 0)
        )

        self._stock_entry = ctk.CTkEntry(
            stock_frame, width=120, placeholder_text="0"
        )
        # Format stock as int if it's whole, otherwise float
        if prev_stock:
            try:
                f_stock = float(prev_stock)
                self._stock_entry.insert(0, str(int(f_stock)) if f_stock.is_integer() else str(f_stock))
            except ValueError:
                self._stock_entry.insert(0, prev_stock)
        self._stock_entry.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(2, 0))

        prev_unit_type = prev.get("unit_type", "Unidad")
        self._unit_type_var = tk.StringVar(value=prev_unit_type)
        self._unit_type_menu = ctk.CTkOptionMenu(
            stock_frame, values=["Unidad", "Kg"], variable=self._unit_type_var, width=120
        )
        self._unit_type_menu.grid(row=1, column=1, sticky="w", padx=(5, 5), pady=(2, 0))

        self._threshold_entry = ctk.CTkEntry(
            stock_frame, width=120, placeholder_text="5"
        )
        self._threshold_entry.insert(0, prev_threshold)
        self._threshold_entry.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(2, 0))

        # Description
        ctk.CTkLabel(body, text="Descripción", font=theme.scaled_font(12)).grid(
            row=row, column=0, sticky="w", padx=15, pady=(5, 0)
        )
        row += 1
        self._desc_entry = ctk.CTkEntry(
            body, width=400, placeholder_text="Opcional"
        )
        self._desc_entry.insert(0, prev_desc)
        self._desc_entry.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 5))
        row += 1

        # Error label
        self._error_label = ctk.CTkLabel(
            body, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.grid(row=row, column=0, padx=15, pady=(5, 0), sticky="w")
        row += 1

        # --- bottom buttons ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(5, 15))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=100,
            command=self._confirm,
        ).pack(side="right", padx=5)

        self._name_entry.focus_set()
        self._name_entry.bind("<Return>", lambda _e: self._confirm())
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    def _on_cost_changed(self, event: Any = None) -> None:
        cost_str = self._cost_price_entry.get().strip()
        margin_str = self._margin_entry.get().strip()
        sale_str = self._sale_price_entry.get().strip()

        try:
            cost = float(cost_str)
        except ValueError:
            return

        if cost <= 0:
            return

        # Case 1: If margin is filled, calculate selling price
        if margin_str:
            try:
                margin = float(margin_str)
                if margin < 100:
                    sale_price = int(cost / (1 - margin / 100))
                    self._sale_price_entry.delete(0, "end")
                    self._sale_price_entry.insert(0, str(sale_price))
            except ValueError:
                pass
        # Case 2: If margin is empty but selling price is filled, calculate margin
        elif sale_str:
            try:
                sale = float(sale_str)
                if sale > 0:
                    margin = ((sale - cost) / sale) * 100
                    self._margin_entry.delete(0, "end")
                    self._margin_entry.insert(0, f"{margin:.1f}".rstrip('0').rstrip('.'))
            except ValueError:
                pass

    def _on_margin_changed(self, event: Any = None) -> None:
        cost_str = self._cost_price_entry.get().strip()
        margin_str = self._margin_entry.get().strip()
        sale_str = self._sale_price_entry.get().strip()

        try:
            margin = float(margin_str)
        except ValueError:
            return

        # Case 1: If cost is filled, calculate selling price
        if cost_str:
            try:
                cost = float(cost_str)
                if margin < 100:
                    sale_price = int(cost / (1 - margin / 100))
                    self._sale_price_entry.delete(0, "end")
                    self._sale_price_entry.insert(0, str(sale_price))
            except ValueError:
                pass
        # Case 2: If cost is empty but selling price is filled, calculate cost price
        elif sale_str:
            try:
                sale = float(sale_str)
                cost_price = int(sale * (1 - margin / 100))
                self._cost_price_entry.delete(0, "end")
                self._cost_price_entry.insert(0, str(cost_price))
            except ValueError:
                pass

    def _on_sale_changed(self, event: Any = None) -> None:
        cost_str = self._cost_price_entry.get().strip()
        margin_str = self._margin_entry.get().strip()
        sale_str = self._sale_price_entry.get().strip()

        try:
            sale = float(sale_str)
        except ValueError:
            return

        # Case 1: If cost is filled, calculate margin %
        if cost_str:
            try:
                cost = float(cost_str)
                if sale > 0:
                    margin = ((sale - cost) / sale) * 100
                    self._margin_entry.delete(0, "end")
                    self._margin_entry.insert(0, f"{margin:.1f}".rstrip('0').rstrip('.'))
            except ValueError:
                pass
        # Case 2: If cost is empty but margin is filled, calculate cost price
        elif margin_str:
            try:
                margin = float(margin_str)
                cost_price = int(sale * (1 - margin / 100))
                self._cost_price_entry.delete(0, "end")
                self._cost_price_entry.insert(0, str(cost_price))
            except ValueError:
                pass

    @property
    def result(self) -> dict[str, Any] | None:
        """Product data dict on confirm, ``None`` on cancel."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _confirm(self) -> None:
        name = self._name_entry.get().strip()
        if not name:
            self._error_label.configure(text="El nombre es obligatorio")
            self._name_entry.focus_set()
            return

        # Sale price
        sale_raw = self._sale_price_entry.get().strip()
        try:
            sale_price = int(sale_raw)
        except ValueError:
            self._error_label.configure(text="Precio de venta inválido (entero)")
            self._sale_price_entry.focus_set()
            return
        if sale_price < 0:
            self._error_label.configure(text="El precio de venta no puede ser negativo")
            self._sale_price_entry.focus_set()
            return

        # Cost price
        cost_raw = self._cost_price_entry.get().strip()
        try:
            cost_price = int(cost_raw)
        except ValueError:
            self._error_label.configure(text="Precio de costo inválido (entero)")
            self._cost_price_entry.focus_set()
            return
        if cost_price < 0:
            self._error_label.configure(text="El precio de costo no puede ser negativo")
            self._cost_price_entry.focus_set()
            return

        # Unit type
        unit_type = self._unit_type_var.get()

        # Stock
        stock_raw = self._stock_entry.get().strip() or "0"
        try:
            if unit_type == "Unidad":
                # Only accept integers
                stock = float(int(stock_raw))
            else:
                stock = float(stock_raw)
        except ValueError:
            self._error_label.configure(text=f"Cantidad inválida (debe ser {'entero' if unit_type == 'Unidad' else 'número'})")
            self._stock_entry.focus_set()
            return
        if stock < 0:
            self._error_label.configure(text="La cantidad no puede ser negativa")
            self._stock_entry.focus_set()
            return

        # Low stock threshold
        threshold_raw = self._threshold_entry.get().strip() or "5"
        try:
            low_stock_threshold = int(threshold_raw)
        except ValueError:
            self._error_label.configure(text="Umbral de stock inválido")
            self._threshold_entry.focus_set()
            return

        # Barcode
        if self._no_barcode_var.get():
            barcode = None
        else:
            barcode = self._barcode_entry.get().strip()
            if not barcode:
                self._error_label.configure(text="Debe ingresar un código de barras o marcar 'Sin código de barras'")
                self._barcode_entry.focus_set()
                return

        # Category
        cat_name = self._category_var.get()
        category_id = self._cat_map.get(cat_name, None)


        self._result = {
            "barcode": barcode,
            "name": name,
            "category_id": category_id,
            "sale_price": sale_price,
            "cost_price": cost_price,
            "stock": stock,
            "unit_type": unit_type,
            "description": self._desc_entry.get().strip() or None,
            "low_stock_threshold": low_stock_threshold,
        }
        self.destroy()

    def _on_no_barcode_toggled(self, set_focus: bool = True) -> None:
        """Handle toggling of 'Sin código de barras' checkbox."""
        if self._no_barcode_var.get():
            # Disable barcode entry and clear it
            self._barcode_entry.delete(0, tk.END)
            self._barcode_entry.configure(state="disabled", placeholder_text="Producto sin código de barras")
        else:
            # Enable barcode entry
            self._barcode_entry.configure(state="normal", placeholder_text="Ingrese o escanee el código")
            if set_focus:
                self._barcode_entry.focus_set()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
