"""Assign category dialog — bulk assign a category to multiple products."""

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk


# Checkbox symbols
_CHECKBOX_OFF = "☐"
_CHECKBOX_ON = "☑"


class AssignCategoryDialog(ctk.CTkToplevel):
    """Modal dialog to assign a category to multiple products at once.

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
        super().__init__(master, **kwargs)
        self.title("Asignar categoría a productos")
        self.geometry("650x500")
        self.resizable(True, True)

        self.grab_set()
        self.transient(master)

        self._products = products
        self._categories = categories
        self._selected_product_ids: list[int] = []
        self._selected_category_id: int | None = None

        # Build category name map
        self._category_map = {c["id"]: c["name"] for c in categories}

        # --- category selection ---
        cat_frame = ctk.CTkFrame(self)
        cat_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            cat_frame,
            text="Seleccionar categoría:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        category_names = [c["name"] for c in categories]
        self._category_var = tk.StringVar(value=category_names[0] if category_names else "")
        self._category_menu = ctk.CTkOptionMenu(
            cat_frame,
            values=category_names,
            variable=self._category_var,
            width=200,
        )
        self._category_menu.pack(side="left", padx=5)

        # --- product list as treeview with checkboxes ---
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Treeview frame
        tree_frame = ctk.CTkFrame(list_frame)
        tree_frame.pack(fill="both", expand=True, pady=(5, 5))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Create treeview with checkbox column + two data columns
        cols = ("sel", "nombre", "categoria")
        self._tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            selectmode="none",
            height=15,
        )
        self._tree.heading("sel", text="")
        self._tree.heading("nombre", text="Nombre")
        self._tree.heading("categoria", text="Categoría actual")
        self._tree.column("sel", width=40, anchor="center", stretch=False)
        self._tree.column("nombre", width=320, anchor="w")
        self._tree.column("categoria", width=200, anchor="w")

        # Configure style for dark theme
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="#dce4ee",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            rowheight=28,
        )
        style.configure(
            "Treeview.Heading",
            background="#505050",
            foreground="#ffffff",
            relief="raised",
            borderwidth=1,
            font=("Segoe UI", 10, "bold"),
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

        # Populate treeview with products (all unchecked)
        for product in products:
            pid = getattr(product, "id", None)
            name = getattr(product, "name", "")
            category_id = getattr(product, "category_id", None)
            current_cat = self._category_map.get(category_id, "Sin categoría")

            self._tree.insert(
                "",
                "end",
                iid=str(pid),
                values=(_CHECKBOX_OFF, name, current_cat),
            )

        # Bind click on checkbox column to toggle
        self._tree.bind("<ButtonRelease-1>", self._on_tree_click)

        # --- selection buttons ---
        select_frame = ctk.CTkFrame(self)
        select_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            select_frame,
            text="Seleccionar todos",
            width=120,
            command=self._select_all,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            select_frame,
            text="Deseleccionar todos",
            width=120,
            command=self._deselect_all,
        ).pack(side="left", padx=5)

        # --- action buttons ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=120,
            height=35,
            fg_color="gray",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._cancel,
        ).pack(side="right", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Asignar",
            width=120,
            height=35,
            fg_color="#1f538d",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._confirm,
        ).pack(side="right", padx=10)

    @property
    def result(self) -> dict[str, Any] | None:
        """Return selected category_id and list of product_ids, or None if cancelled."""
        if self._selected_category_id is None or not self._selected_product_ids:
            return None
        return {
            "category_id": self._selected_category_id,
            "product_ids": self._selected_product_ids,
        }

    # ------------------------------------------------------ checkbox handling

    def _on_tree_click(self, event: tk.Event) -> None:
        """Toggle checkbox when user clicks on the checkbox column."""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        col = self._tree.identify_column(event.x)
        # Column #1 is the first column (sel)
        if col != "#1":
            return

        item = self._tree.identify_row(event.y)
        if not item:
            return

        # Toggle the checkbox
        values = list(self._tree.item(item, "values"))
        if values[0] == _CHECKBOX_OFF:
            values[0] = _CHECKBOX_ON
        else:
            values[0] = _CHECKBOX_OFF
        self._tree.item(item, values=values)

    def _set_all_checkboxes(self, checked: bool) -> None:
        """Set all checkboxes to checked or unchecked."""
        symbol = _CHECKBOX_ON if checked else _CHECKBOX_OFF
        for item in self._tree.get_children():
            values = list(self._tree.item(item, "values"))
            values[0] = symbol
            self._tree.item(item, values=values)

    def _select_all(self) -> None:
        """Check all product checkboxes."""
        self._set_all_checkboxes(True)

    def _deselect_all(self) -> None:
        """Uncheck all product checkboxes."""
        self._set_all_checkboxes(False)

    def _get_checked_product_ids(self) -> list[int]:
        """Return list of product IDs that have checked checkboxes."""
        checked = []
        for item in self._tree.get_children():
            values = self._tree.item(item, "values")
            if values[0] == _CHECKBOX_ON:
                checked.append(int(item))
        return checked

    # --------------------------------------------------------- confirm / cancel

    def _confirm(self) -> None:
        """Confirm the category assignment."""
        # Get selected category
        category_name = self._category_var.get()
        category_id = None
        for cat in self._categories:
            if cat["name"] == category_name:
                category_id = cat["id"]
                break

        if category_id is None:
            from tkinter import messagebox
            messagebox.showwarning(
                "Sin categoría",
                "Debe seleccionar una categoría.",
                parent=self,
            )
            return

        # Get checked products
        selected_ids = self._get_checked_product_ids()
        if not selected_ids:
            from tkinter import messagebox
            messagebox.showwarning(
                "Sin productos",
                "Debe seleccionar al menos un producto.",
                parent=self,
            )
            return

        self._selected_category_id = category_id
        self._selected_product_ids = selected_ids
        self.destroy()

    def _cancel(self) -> None:
        """Cancel the dialog."""
        self._selected_category_id = None
        self._selected_product_ids = []
        self.destroy()
