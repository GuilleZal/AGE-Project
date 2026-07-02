"""Assign category dialog — bulk assign a category to multiple products."""

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


class AssignCategoryDialog(CenteredDialog):
    """Modal dialog to assign a category to multiple products at once.

    Products are selected via native treeview multi-selection (Ctrl+click,
    Shift+click) — same mechanism as the product management table.
    Two filter controls narrow the visible product list:
      * Name search — free-text filter on product name.
      * Category filter — dropdown to show only products of a given category.
    A separate "Nueva categoría" dropdown chooses the category to assign.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    products : list[Any]
        List of all products to choose from.
    categories : list[dict[str, Any]]
        List of categories with keys 'id' and 'name'.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self,
        master: tk.Widget,
        products: list[Any],
        categories: list[dict[str, Any]],
        **kwargs,
    ) -> None:
        super().__init__(master, width=700, height=600, title="Asignar categoría a productos", resizable=(True, True), **kwargs)

        self._products = products
        self._categories = categories
        self._selected_product_ids: list[int] = []
        self._selected_category_id: int | None = None

        # Build category name map
        self._category_map: dict[int | None, str] = {c["id"]: c["name"] for c in categories}
        self._category_map[None] = "Sin categoría"
        # Reverse map: name -> id for filtering
        self._category_name_to_id: dict[str, int | None] = {c["name"]: c["id"] for c in categories}
        self._category_name_to_id["Sin categoría"] = None
        self._category_name_to_id["Todas"] = None  # sentinel — means no filter

        # --- filter row (name + category) ---
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(fill="x", padx=10, pady=(10, 5))
        filter_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            filter_frame,
            text="Buscar:",
            font=theme.scaled_font(13),
        ).grid(row=0, column=0, padx=(0, 5), pady=5)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_filter_change)
        ctk.CTkEntry(
            filter_frame,
            textvariable=self._search_var,
            placeholder_text="Filtrar por nombre...",
            width=250,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        ctk.CTkLabel(
            filter_frame,
            text="Categoría:",
            font=theme.scaled_font(13),
        ).grid(row=0, column=2, padx=(0, 5), pady=5)

        filter_cat_names = ["Todas"] + [c["name"] for c in categories] + ["Sin categoría"]
        self._filter_cat_var = tk.StringVar(value=filter_cat_names[0])
        self._filter_cat_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=filter_cat_names,
            variable=self._filter_cat_var,
            width=180,
            command=self._on_filter_change,
        )
        self._filter_cat_menu.grid(row=0, column=3, padx=(0, 5), pady=5)

        # --- assign category row ---
        assign_frame = ctk.CTkFrame(self)
        assign_frame.pack(fill="x", padx=10, pady=(0, 5))

        ctk.CTkLabel(
            assign_frame,
            text="Nueva categoría:",
            font=theme.scaled_font(13, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        assign_cat_names = ["Sin categoría"] + [c["name"] for c in categories]
        self._assign_cat_var = tk.StringVar(value=assign_cat_names[0])
        self._assign_cat_menu = ctk.CTkOptionMenu(
            assign_frame,
            values=assign_cat_names,
            variable=self._assign_cat_var,
            width=200,
        )
        self._assign_cat_menu.pack(side="left", padx=5)

        # Help button
        ctk.CTkButton(
            assign_frame,
            text="?",
            width=30,
            height=30,
            fg_color="#505050",
            hover_color="#606060",
            font=theme.scaled_font(14, weight="bold"),
            command=self._show_help,
        ).pack(side="left", padx=(10, 0))

        # --- product treeview (multi-select, no checkboxes) ---
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        cols = ("nombre", "categoria")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            selectmode="extended",
            height=12,
        )
        self._tree.heading("nombre", text="Nombre")
        self._tree.heading("categoria", text="Categoría actual")
        self._tree.column("nombre", width=350, anchor="w")
        self._tree.column("categoria", width=200, anchor="w")

        # Configure style for dark theme
        contrast = theme.get_contrast_map()
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=contrast["treeview_bg"],
            foreground=contrast["treeview_fg"],
            fieldbackground=contrast["treeview_bg"],
            borderwidth=0,
            font=theme.scaled_treeview_font(),
            rowheight=24 + theme.get_offset() * 2,
        )
        style.configure(
            "Treeview.Heading",
            background=contrast["treeview_header"],
            foreground=contrast["treeview_fg"],
            relief="raised",
            borderwidth=1,
            font=theme.scaled_treeview_font("bold"),
        )

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self._tree.yview,
        )
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Add sorting to both columns
        add_sorting_to_treeview(
            self._tree,
            list(cols),
            column_types={"nombre": "str", "categoria": "str"},
        )

        # Populate treeview
        self._apply_filters()

        # --- action buttons ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=120,
            height=35,
            fg_color="gray",
            font=theme.scaled_font(13, weight="bold"),
            command=self._cancel,
        ).pack(side="right", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Asignar",
            width=120,
            height=35,
            fg_color="#1f538d",
            font=theme.scaled_font(13, weight="bold"),
            command=self._confirm,
        ).pack(side="right", padx=10)
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    # ---------------------------------------------------------- filtering

    def _on_filter_change(self, *_args: Any) -> None:
        """Re-apply filters when name search or category filter changes."""
        self._apply_filters()

    def _apply_filters(self) -> None:
        """Clear and repopulate the treeview based on current filters."""
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)

        name_query = self._search_var.get().strip().lower()
        filter_cat_name = self._filter_cat_var.get()

        # Determine category filter
        if filter_cat_name == "Todas":
            filter_category_id: int | None | _AllSentinel = _ALL_CATEGORIES
        else:
            filter_category_id = self._category_name_to_id.get(filter_cat_name)

        for product in self._products:
            pid = getattr(product, "id", None)
            name = getattr(product, "name", "")
            category_id = getattr(product, "category_id", None)

            # Name filter
            if name_query and name_query not in name.lower():
                continue

            # Category filter
            if filter_category_id is not _ALL_CATEGORIES and category_id != filter_category_id:
                continue

            current_cat = self._category_map.get(category_id, "Sin categoría")
            self._tree.insert(
                "",
                "end",
                iid=str(pid),
                values=(name, current_cat),
            )

    def _show_help(self) -> None:
        """Show help dialog explaining multi-selection controls."""
        help_text = (
            "Cómo seleccionar productos:\n\n"
            "• Click simple: Selecciona un producto (deselecciona los demás).\n\n"
            "• Ctrl + Click: Agrega o quita productos individuales de la selección.\n"
            "  Úselo para seleccionar productos no consecutivos.\n\n"
            "• Shift + Click: Selecciona un rango completo desde el último\n"
            "  producto seleccionado hasta el actual.\n\n"
            "Ejemplo:\n"
            "1. Haga click en un producto.\n"
            "2. Mantenga Ctrl y haga click en otros para agregarlos.\n"
            "3. O use Shift + click para seleccionar todos entre dos puntos.\n\n"
            "Los productos seleccionados recibirán la categoría elegida al presionar 'Asignar'."
        )
        from tkinter import messagebox
        messagebox.showinfo(
            "Ayuda — Selección múltiple",
            help_text,
            parent=self,
        )

    # ------------------------------------------------------------ result

    @property
    def result(self) -> dict[str, Any] | None:
        """Return selected category_id and list of product_ids, or None if cancelled."""
        if not self._selected_product_ids:
            return None
        return {
            "category_id": self._selected_category_id,
            "product_ids": self._selected_product_ids,
        }

    # --------------------------------------------------------- confirm / cancel

    def _confirm(self) -> None:
        """Confirm the category assignment."""
        # Get the NEW category to assign
        assign_cat_name = self._assign_cat_var.get()
        category_id: int | None = None
        if assign_cat_name != "Sin categoría":
            for cat in self._categories:
                if cat["name"] == assign_cat_name:
                    category_id = cat["id"]
                    break

        # Get selected products from treeview selection
        selected_items = self._tree.selection()
        if not selected_items:
            from tkinter import messagebox
            messagebox.showwarning(
                "Sin productos",
                "Debe seleccionar al menos un producto.\n"
                "Use Ctrl+click para selección múltiple o Shift+click para un rango.",
                parent=self,
            )
            return

        selected_ids = [int(item) for item in selected_items]

        self._selected_category_id = category_id
        self._selected_product_ids = selected_ids
        self.destroy()

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self._selected_category_id = None
        self._selected_product_ids = []
        self.destroy()


# Sentinel object to represent "all categories" (no filter)
_ALL_CATEGORIES = object()
_AllSentinel = type(_ALL_CATEGORIES)
