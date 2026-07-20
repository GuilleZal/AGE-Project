"""Product search dialog — lets the user pick from multiple search results."""

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from pos.model.product import Product
from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


class ProductSearchDialog(CenteredDialog):
    """Modal dialog showing search results for the user to select from.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    products : list[Product]
        Products to display in the selection list.
    categories : list[dict] | None
        Optional list of categories with keys 'id' and 'name'.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self, master: tk.Widget, products: list[Product], 
        categories: list[dict] | None = None, **kwargs
    ) -> None:
        super().__init__(master, width=600, height=450, title="Seleccionar producto", **kwargs)

        self._result: Product | None = None
        self._selected_quantity: float = 1.0
        self._all_products = products
        self._categories = categories or []
        self._visible_products: list[Product] = []

        # Build category lookup dict
        self._category_map = {cat['id']: cat['name'] for cat in self._categories}

        # Configure treeview style
        contrast = theme.get_contrast_map()
        self._style = ttk.Style(self)
        self._style.theme_use("clam")
        self._style.configure(
            "Treeview",
            background=contrast["treeview_bg"],
            foreground=contrast["treeview_fg"],
            fieldbackground=contrast["treeview_bg"],
            borderwidth=0,
            font=theme.scaled_treeview_font(),
            rowheight=24 + theme.get_offset() * 2,
        )
        self._style.configure(
            "Treeview.Heading",
            background=contrast["treeview_header"],
            foreground=contrast["treeview_fg"],
            relief="raised",
            borderwidth=1,
            font=theme.scaled_treeview_font("bold"),
        )
        self._style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", contrast["treeview_fg"])],
        )

        # Search bar
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(search_frame, text="Nombre:", font=theme.scaled_font(12)).pack(
            side="left", padx=(0, 5)
        )
        
        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Nombre o categoría...",
            width=300
        )
        self._search_entry.pack(side="left", fill="x", expand=True)
        self._search_entry.bind("<KeyRelease>", self._on_search_changed)
        self._search_entry.focus_set()

        # Treeview with category column
        columns = ("codigo", "nombre", "categoria", "precio")
        self._tree = ttk.Treeview(
            self, columns=columns, show="headings", height=12
        )
        self._tree.heading("codigo", text="Código")
        self._tree.heading("nombre", text="Nombre")
        self._tree.heading("categoria", text="Categoría")
        self._tree.heading("precio", text="Precio")
        self._tree.column("codigo", width=100, anchor="w")
        self._tree.column("nombre", width=200, anchor="w")
        self._tree.column("categoria", width=120, anchor="w")
        self._tree.column("precio", width=80, anchor="e")

        # Load saved column widths
        saved_widths = load_column_widths("product_search_dialog")
        self._tree._view_name = "product_search_dialog"
        apply_treeview_widths(self._tree, saved_widths)

        # Add column sorting
        add_sorting_to_treeview(
            self._tree,
            list(columns),
            column_types={
                "codigo": "str",
                "nombre": "str",
                "categoria": "str",
                "precio": "int",
            }
        )

        self._tree.bind("<Double-1>", self._on_select)
        self._tree.bind("<Return>", self._on_select)

        # 1. Aseguramos los botones en la base PRIMERO
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(side="bottom", pady=(5, 15))

        ctk.CTkButton(
            btn_frame,
            text="Seleccionar",
            width=120,
            command=self._on_select,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)

        # 2. Empaquetamos la tabla DESPUÉS para que respete a los botones
        self._tree.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        self._populate_tree(products)
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    def _populate_tree(self, products: list[Product]) -> None:
        """Clear and repopulate the treeview with given products."""
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)
        
        self._visible_products = list(products)

        # Insert new items
        for p in products:
            category_name = self._category_map.get(p.category_id, "") if p.category_id else ""
            self._tree.insert(
                "",
                "end",
                values=(p.barcode or "—", p.name, category_name, f"${p.sale_price:,}"),
            )

    def _on_search_changed(self, *args) -> None:
        """Filter products based on search text (name or category)."""
        search_text = self._search_entry.get().strip().lower()
        if search_text == "nombre o categoría...":
            search_text = ""
        
        if not search_text:
            # Show all products
            self._populate_tree(self._all_products)
            return
        
        # Filter products by name or category
        filtered = []
        for p in self._all_products:
            # Check name
            if search_text in p.name.lower():
                filtered.append(p)
                continue
            # Check category
            if p.category_id:
                category_name = self._category_map.get(p.category_id, "").lower()
                if search_text in category_name:
                    filtered.append(p)
        
        self._populate_tree(filtered)

    @property
    def result(self) -> Product | None:
        """The selected ``Product``, or ``None`` if cancelled."""
        return self._result

    @property
    def selected_quantity(self) -> float:
        """The selected quantity/weight in Kg (defaults to 1.0)."""
        return self._selected_quantity

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return

        idx = self._tree.index(sel[0])
        if idx < len(self._visible_products):
            selected_p = self._visible_products[idx]
            has_barcode = bool(selected_p.barcode and selected_p.barcode.strip() and selected_p.barcode != "—")

            if not has_barcode:
                from pos.view.widgets.weight_calculation_dialog import WeightCalculationDialog

                calc_dialog = WeightCalculationDialog(
                    self,
                    product_name=selected_p.name,
                    sale_price=selected_p.sale_price,
                )
                self.wait_window(calc_dialog)
                calc_result = calc_dialog.result

                if calc_result is not None:
                    self._result = selected_p
                    self._selected_quantity = calc_result
                    self.destroy()
            else:
                self._result = selected_p
                self._selected_quantity = 1.0
                self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._selected_quantity = 1.0
        self.destroy()
