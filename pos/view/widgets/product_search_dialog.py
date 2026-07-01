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
        self._all_products = products
        self._categories = categories or []
        
        # Build category lookup dict
        self._category_map = {cat['id']: cat['name'] for cat in self._categories}

        # Configure treeview style
        self._style = ttk.Style(self)
        self._style.theme_use("clam")
        self._style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="#dce4ee",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            font=theme.scaled_treeview_font(),
            rowheight=24 + theme.get_offset() * 2,
        )
        self._style.configure(
            "Treeview.Heading",
            background="#505050",
            foreground="#ffffff",
            relief="raised",
            borderwidth=1,
            font=theme.scaled_treeview_font("bold"),
        )
        self._style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#dce4ee")],
        )

        # Search bar
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(search_frame, text="Buscar:", font=theme.scaled_font(12)).pack(
            side="left", padx=(0, 5)
        )
        
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)
        self._search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self._search_var,
            placeholder_text="Nombre o categoría...",
            width=300
        )
        self._search_entry.pack(side="left", fill="x", expand=True)
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

    def _populate_tree(self, products: list[Product]) -> None:
        """Clear and repopulate the treeview with given products."""
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)
        
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
        search_text = self._search_var.get().strip().lower()
        
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

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        # Get the product from the visible (filtered) list
        visible_products = []
        for item in self._tree.get_children():
            values = self._tree.item(item, 'values')
            barcode = values[0] if values[0] != "—" else None
            # Find matching product
            for p in self._all_products:
                if (p.barcode or "—") == barcode:
                    visible_products.append(p)
                    break
        
        idx = self._tree.index(sel[0])
        if idx < len(visible_products):
            self._result = visible_products[idx]
            self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
