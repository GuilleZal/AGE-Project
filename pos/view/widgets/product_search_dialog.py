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
        categories: list[dict] | None = None, role: str = "", is_return: bool = False, **kwargs
    ) -> None:
        dialog_width = 750 if role == "cajero" else 600
        super().__init__(master, width=dialog_width, height=450, title="Seleccionar producto", **kwargs)

        self._result: Product | None = None
        self._selected_quantity: float = 1.0
        self._all_products = products
        self._categories = categories or []
        self._visible_products: list[Product] = []
        self._role = role
        self._is_return = is_return

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
        self.bind("<Map>", lambda e: self._search_entry.focus_set())

        # Category filter dropdown (only for cajero)
        if self._role == "cajero":
            ctk.CTkLabel(search_frame, text="Categoría:", font=theme.scaled_font(12)).pack(
                side="left", padx=(10, 2)
            )
            self._category_options: dict[str, int | None] = {"Todas": None}
            if self._categories:
                for cat in self._categories:
                    self._category_options[cat["name"]] = cat["id"]
            self._category_var = tk.StringVar(value="Todas")
            self._category_menu = ctk.CTkOptionMenu(
                search_frame,
                values=list(self._category_options.keys()),
                variable=self._category_var,
                width=130,
                command=self._on_category_changed,
            )
            self._category_menu.pack(side="left", padx=(0, 5))

        # Treeview container frame
        tree_frame = ctk.CTkFrame(self)
        
        # Treeview with category column
        columns = ("codigo", "nombre", "categoria", "precio")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=12
        )
        self._tree.heading("codigo", text="Código")
        self._tree.heading("nombre", text="Nombre")
        self._tree.heading("categoria", text="Categoría")
        self._tree.heading("precio", text="Precio")
        
        if self._role == "cajero":
            self._tree.column("codigo", width=140, minwidth=140, anchor="center")
            self._tree.column("nombre", width=250, minwidth=250, anchor="w")
            self._tree.column("categoria", width=160, minwidth=160, anchor="w")
            self._tree.column("precio", width=110, minwidth=110, anchor="e")
            
            # Bloqueamos el redimensionamiento manual
            self._tree.bind("<Button-1>", self._prevent_resize)
            self._tree.bind("<B1-Motion>", self._prevent_resize)
        else:
            self._tree.column("codigo", width=100, anchor="w")
            self._tree.column("nombre", width=200, anchor="w")
            self._tree.column("categoria", width=120, anchor="w")
            self._tree.column("precio", width=80, anchor="e")
            
            # Load saved column widths
            saved_widths = load_column_widths("product_search_dialog")
            self._tree._view_name = "product_search_dialog"
            apply_treeview_widths(self._tree, saved_widths)

        self._tree.grid(row=0, column=0, sticky="nsew")

        vscroll = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self._tree.yview,
        )
        vscroll.grid(row=0, column=1, sticky="ns")

        hscroll = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self._tree.xview,
        )
        hscroll.grid(row=1, column=0, sticky="ew")

        self._tree.configure(
            yscrollcommand=vscroll.set,
            xscrollcommand=hscroll.set,
        )
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

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
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))

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

    def _on_category_changed(self, _value: str) -> None:
        """Trigger search update when category changes."""
        self._on_search_changed()

    def _prevent_resize(self, event: Any) -> str | None:
        """Evita que el usuario cambie el tamaño de las columnas arrastrando el separador."""
        if event.widget.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    def _on_search_changed(self, *args) -> None:
        """Filter products based on search text (name or category) and selected category."""
        search_text = self._search_entry.get().strip().lower()
        if search_text == "nombre o categoría...":
            search_text = ""
        
        selected_cat_id = None
        if self._role == "cajero" and hasattr(self, "_category_var"):
            selected_cat_id = self._category_options.get(self._category_var.get())

        filtered = []
        for p in self._all_products:
            # 1. Filter by category
            if selected_cat_id is not None and p.category_id != selected_cat_id:
                continue

            # 2. Filter by search text (if any)
            if search_text:
                name_match = search_text in p.name.lower()
                category_name = self._category_map.get(p.category_id, "").lower() if p.category_id else ""
                cat_match = search_text in category_name
                if not (name_match or cat_match):
                    continue

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

            if not has_barcode and not self._is_return:
                from pos.view.widgets.weight_calculation_dialog import WeightCalculationDialog

                calc_dialog = WeightCalculationDialog(
                    self,
                    product_name=selected_p.name,
                    sale_price=selected_p.sale_price,
                    role=getattr(self.master, "_role", ""),
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
