"""Assign category dialog — bulk assign a category to multiple products."""

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk


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
        self.geometry("600x500")
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

        # --- product list with checkboxes ---
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(
            list_frame,
            text="Seleccionar productos:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(5, 5))

        # Scrollable frame for checkboxes
        self._scrollable_frame = ctk.CTkScrollableFrame(list_frame)
        self._scrollable_frame.pack(fill="both", expand=True, pady=(0, 5))

        # Create checkboxes for each product
        self._checkbox_vars: dict[int, tk.BooleanVar] = {}
        for product in products:
            pid = getattr(product, "id", None)
            name = getattr(product, "name", "")
            barcode = getattr(product, "barcode", "") or ""
            category_id = getattr(product, "category_id", None)
            current_cat = self._category_map.get(category_id, "Sin categoría")

            var = tk.BooleanVar(value=False)
            self._checkbox_vars[pid] = var

            # Format: [ ] Product Name (Barcode) - Current Category
            text = f"{name} ({barcode}) - {current_cat}"
            cb = ctk.CTkCheckBox(
                self._scrollable_frame,
                text=text,
                variable=var,
                font=ctk.CTkFont(size=12),
            )
            cb.pack(anchor="w", pady=2, padx=5)

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
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=self._cancel,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Asignar",
            width=100,
            fg_color="#1f538d",
            command=self._confirm,
        ).pack(side="right", padx=5)

    @property
    def result(self) -> dict[str, Any] | None:
        """Return selected category_id and list of product_ids, or None if cancelled."""
        if self._selected_category_id is None or not self._selected_product_ids:
            return None
        return {
            "category_id": self._selected_category_id,
            "product_ids": self._selected_product_ids,
        }

    def _select_all(self) -> None:
        """Select all product checkboxes."""
        for var in self._checkbox_vars.values():
            var.set(True)

    def _deselect_all(self) -> None:
        """Deselect all product checkboxes."""
        for var in self._checkbox_vars.values():
            var.set(False)

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

        # Get selected products
        selected_ids = [
            pid for pid, var in self._checkbox_vars.items() if var.get()
        ]

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
