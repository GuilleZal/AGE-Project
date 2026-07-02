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

        # Barcode
        ctk.CTkLabel(body, text="Código de barras", font=theme.scaled_font(12)).grid(
            row=row, column=0, sticky="w", padx=15, pady=(10, 0)
        )
        row += 1
        self._barcode_entry = ctk.CTkEntry(
            body, width=400, placeholder_text="Opcional"
        )
        self._barcode_entry.insert(0, prev_barcode)
        self._barcode_entry.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 5))
        row += 1

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

        # Sale price + Cost price (side by side)
        price_frame = ctk.CTkFrame(body, fg_color="transparent")
        price_frame.grid(row=row, column=0, sticky="ew", padx=15, pady=5)
        price_frame.grid_columnconfigure(0, weight=1)
        price_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ctk.CTkLabel(price_frame, text="Precio venta ($) *", font=theme.scaled_font(12)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ctk.CTkLabel(price_frame, text="Precio costo ($) *", font=theme.scaled_font(12)).grid(
            row=0, column=1, sticky="w", padx=(5, 0)
        )

        self._sale_price_entry = ctk.CTkEntry(
            price_frame, width=180, placeholder_text="0"
        )
        self._sale_price_entry.insert(0, prev_sale)
        self._sale_price_entry.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(2, 0))

        self._cost_price_entry = ctk.CTkEntry(
            price_frame, width=180, placeholder_text="0"
        )
        self._cost_price_entry.insert(0, prev_cost)
        self._cost_price_entry.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(2, 0))

        # Stock + Low stock threshold (side by side)
        stock_frame = ctk.CTkFrame(body, fg_color="transparent")
        stock_frame.grid(row=row, column=0, sticky="ew", padx=15, pady=5)
        stock_frame.grid_columnconfigure(0, weight=1)
        stock_frame.grid_columnconfigure(1, weight=1)
        row += 1

        ctk.CTkLabel(stock_frame, text="Stock inicial", font=theme.scaled_font(12)).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        ctk.CTkLabel(stock_frame, text="Umbral stock bajo", font=theme.scaled_font(12)).grid(
            row=0, column=1, sticky="w", padx=(5, 0)
        )

        self._stock_entry = ctk.CTkEntry(
            stock_frame, width=180, placeholder_text="0"
        )
        self._stock_entry.insert(0, prev_stock)
        self._stock_entry.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(2, 0))

        self._low_stock_entry = ctk.CTkEntry(
            stock_frame, width=180, placeholder_text="5"
        )
        self._low_stock_entry.insert(0, prev_threshold)
        self._low_stock_entry.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(2, 0))

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

        # Stock
        stock_raw = self._stock_entry.get().strip() or "0"
        try:
            stock = int(stock_raw)
        except ValueError:
            self._error_label.configure(text="Stock inválido")
            self._stock_entry.focus_set()
            return
        if stock < 0:
            self._error_label.configure(text="El stock no puede ser negativo")
            self._stock_entry.focus_set()
            return

        # Low stock threshold
        threshold_raw = self._low_stock_entry.get().strip() or "5"
        try:
            low_stock_threshold = int(threshold_raw)
        except ValueError:
            self._error_label.configure(text="Umbral de stock inválido")
            self._low_stock_entry.focus_set()
            return

        # Barcode
        barcode = self._barcode_entry.get().strip() or None

        # Category
        cat_name = self._category_var.get()
        category_id = self._cat_map.get(cat_name, None)

        # Description
        description = self._desc_entry.get().strip() or None

        self._error_label.configure(text="")
        self._result = {
            "barcode": barcode,
            "name": name,
            "category_id": category_id,
            "sale_price": sale_price,
            "cost_price": cost_price,
            "stock": stock,
            "description": description,
            "low_stock_threshold": low_stock_threshold,
        }
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
