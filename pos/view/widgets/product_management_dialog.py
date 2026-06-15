"""Product & category management dialog — unified CRUD hub.

A tabbed modal dialog that consolidates product and category management
into a single entry point.  The *Productos* tab lists all products with
New/Edit/Delete buttons and search; the *Categorías* tab lists categories
with New/Edit/Delete buttons and search.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview


class ProductManagementDialog(ctk.CTkToplevel):
    """Modal dialog for managing products and categories together.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    controller : Any
        ``ProductController`` instance for data access.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(self, master: tk.Widget, controller: Any, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Gestionar productos y categorías")
        self.geometry("750x550")
        self.resizable(True, True)

        self.grab_set()
        self.transient(master)

        self._controller = controller
        self._changed = False
        self._all_products: list[Any] = []
        self._all_categories: list[dict[str, Any]] = []

        # --- tabview ---
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

        products_tab = self._tabview.add("Productos")
        categories_tab = self._tabview.add("Categorías")

        self._build_products_tab(products_tab)
        self._build_categories_tab(categories_tab)

        # Load data
        self._refresh_products()
        self._refresh_categories()

    @property
    def changed(self) -> bool:
        """True if any product or category was created/edited/deleted."""
        return self._changed

    # ===================================================== products tab

    def _build_products_tab(self, parent: tk.Widget) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(parent)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Buscar:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5)
        )
        self._prod_search_var = tk.StringVar()
        self._prod_search_var.trace_add("write", self._on_product_search_changed)
        ctk.CTkEntry(
            search_frame, textvariable=self._prod_search_var,
            placeholder_text="Filtrar por nombre...", width=250,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        # Treeview
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        cols = ("nombre", "codigo", "precio", "stock")
        self._prod_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="browse", height=15,
        )
        self._prod_tree.heading("nombre", text="Nombre")
        self._prod_tree.heading("codigo", text="Código")
        self._prod_tree.heading("precio", text="Precio")
        self._prod_tree.heading("stock", text="Stock")
        self._prod_tree.column("nombre", width=200)
        self._prod_tree.column("codigo", width=120, anchor="center")
        self._prod_tree.column("precio", width=90, anchor="e")
        self._prod_tree.column("stock", width=70, anchor="center")

        # Load saved column widths
        saved_widths = load_column_widths("management_products")
        self._prod_tree._view_name = "management_products"
        apply_treeview_widths(self._prod_tree, saved_widths)

        # Add column sorting
        add_sorting_to_treeview(
            self._prod_tree,
            list(cols),
            column_types={
                "nombre": "str",
                "codigo": "str",
                "precio": "int",
                "stock": "int",
            }
        )

        # Red tag for low-stock rows
        self._prod_tree.tag_configure("low_stock", foreground="#e74c3c")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._prod_tree.yview)
        self._prod_tree.configure(yscrollcommand=sb.set)
        self._prod_tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # Buttons
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=8)

        ctk.CTkButton(
            btn_frame, text="＋ Nuevo", width=120,
            command=self._create_product,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="✎ Editar", width=120,
            fg_color="#1f538d", command=self._edit_product,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="🗑 Eliminar", width=120,
            fg_color="#8b1a1a", command=self._delete_product,
        ).pack(side="left", padx=5)

    # ==================================================== categories tab

    def _build_categories_tab(self, parent: tk.Widget) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(parent)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Buscar:", font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, padx=(10, 5)
        )
        self._cat_search_var = tk.StringVar()
        self._cat_search_var.trace_add("write", self._on_category_search_changed)
        ctk.CTkEntry(
            search_frame, textvariable=self._cat_search_var,
            placeholder_text="Filtrar por nombre...", width=250,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        # Treeview
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        cols = ("nombre", "productos")
        self._cat_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="browse", height=15,
        )
        self._cat_tree.heading("nombre", text="Nombre")
        self._cat_tree.heading("productos", text="Productos")
        self._cat_tree.column("nombre", width=250)
        self._cat_tree.column("productos", width=100, anchor="center")

        # Load saved column widths
        saved_widths = load_column_widths("management_categories")
        self._cat_tree._view_name = "management_categories"
        apply_treeview_widths(self._cat_tree, saved_widths)

        # Add column sorting
        add_sorting_to_treeview(
            self._cat_tree,
            list(cols),
            column_types={
                "nombre": "str",
                "productos": "int",
            }
        )

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._cat_tree.yview)
        self._cat_tree.configure(yscrollcommand=sb.set)
        self._cat_tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # Buttons
        btn_frame = ctk.CTkFrame(parent)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=8)

        ctk.CTkButton(
            btn_frame, text="＋ Nueva", width=120,
            command=self._create_category,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="✎ Editar", width=120,
            fg_color="#1f538d", command=self._edit_category,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="🗑 Eliminar", width=120,
            fg_color="#8b1a1a", command=self._delete_category,
        ).pack(side="left", padx=5)

    # ================================================ product actions

    def _create_product(self) -> None:
        from pos.view.widgets.product_form_dialog import ProductFormDialog

        dialog = ProductFormDialog(self, categories=self._get_categories())
        self.wait_window(dialog)
        result = dialog.result
        if result:
            res = self._controller.create_product(result)
            if res["success"]:
                self._changed = True
                self._refresh_products()
            else:
                messagebox.showerror("Error", res["error"])

    def _edit_product(self) -> None:
        from pos.view.widgets.product_form_dialog import ProductFormDialog

        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione un producto de la lista."
            )
            return

        pid = int(self._prod_tree.item(sel[0], "tags")[0])
        res = self._controller.get_product(pid)
        if not res["success"]:
            messagebox.showerror("Error", res["error"])
            return

        product = res["data"]
        product_dict = {
            "id": product.id,
            "barcode": product.barcode,
            "name": product.name,
            "category_id": product.category_id,
            "sale_price": product.sale_price,
            "cost_price": product.cost_price,
            "stock": product.stock,
            "unit_type": product.unit_type,
            "description": getattr(product, "description", None),
            "low_stock_threshold": getattr(product, "low_stock_threshold", 5),
        }

        dialog = ProductFormDialog(
            self, product=product_dict, categories=self._get_categories()
        )
        self.wait_window(dialog)
        data = dialog.result
        if data:
            res = self._controller.update_product(pid, data)
            if res["success"]:
                self._changed = True
                self._refresh_products()
            else:
                messagebox.showerror("Error", res["error"])

    def _delete_product(self) -> None:
        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione un producto de la lista."
            )
            return

        item = self._prod_tree.item(sel[0])
        pid = int(item["tags"][0])
        name = item["values"][0]

        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f'¿Eliminar el producto "{name}"?\n\n'
            "Esta acción no se puede deshacer si el producto "
            "no tiene transacciones asociadas.",
        )
        if not confirm:
            return

        res = self._controller.delete_product(pid)
        if res["success"]:
            self._changed = True
            self._refresh_products()
            messagebox.showinfo("Eliminado", "Producto eliminado correctamente")
        else:
            messagebox.showerror("Error", res["error"])

    # =============================================== category actions

    def _create_category(self) -> None:
        name = self._prompt_category_name("Nueva categoría")
        if name:
            res = self._controller.create_category(name)
            if res["success"]:
                self._changed = True
                self._refresh_categories()
            else:
                messagebox.showerror("Error", res["error"])

    def _edit_category(self) -> None:
        sel = self._cat_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione una categoría de la lista."
            )
            return

        item = self._cat_tree.item(sel[0])
        cat_id = int(item["tags"][0])
        old_name = item["values"][0]

        new_name = self._prompt_category_name(
            "Editar categoría", initial=str(old_name)
        )
        if new_name and new_name != old_name:
            res = self._controller.update_category(cat_id, new_name)
            if res["success"]:
                self._changed = True
                self._refresh_categories()
            else:
                messagebox.showerror("Error", res["error"])

    def _delete_category(self) -> None:
        sel = self._cat_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione una categoría de la lista."
            )
            return

        item = self._cat_tree.item(sel[0])
        cat_id = int(item["tags"][0])
        name = item["values"][0]
        product_count = item["values"][1]

        if product_count > 0:
            messagebox.showwarning(
                "Categoría en uso",
                f'La categoría "{name}" tiene {product_count} producto(s) asignado(s).\n'
                "Reasigne los productos antes de eliminarla.",
            )
            return

        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f'¿Eliminar la categoría "{name}"?',
        )
        if not confirm:
            return

        res = self._controller.delete_category(cat_id)
        if res["success"]:
            self._changed = True
            self._refresh_categories()
            messagebox.showinfo("Eliminada", "Categoría eliminada correctamente")
        else:
            messagebox.showerror("Error", res["error"])

    # ======================================================== helpers

    def _prompt_category_name(
        self, title: str, initial: str = ""
    ) -> str | None:
        """Small inline prompt for a category name."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self)

        result: str | None = None

        ctk.CTkLabel(dialog, text="Nombre:").pack(pady=(15, 5))
        entry = ctk.CTkEntry(dialog, width=250)
        entry.insert(0, initial)
        entry.pack(pady=5)
        entry.focus_set()

        def on_confirm() -> None:
            nonlocal result
            val = entry.get().strip()
            if not val:
                messagebox.showwarning(
                    "Validación", "El nombre es obligatorio", parent=dialog
                )
                return
            result = val
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100, fg_color="gray",
            command=on_cancel,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Aceptar", width=100, command=on_confirm,
        ).pack(side="left", padx=5)

        entry.bind("<Return>", lambda _e: on_confirm())
        self.wait_window(dialog)
        return result

    def _get_categories(self) -> list[dict[str, Any]]:
        res = self._controller.list_categories()
        if res["success"]:
            return res["data"]
        return []

    def _on_product_search_changed(self, *_args: Any) -> None:
        """Filter products by name as user types."""
        query = self._prod_search_var.get().strip().lower()
        self._populate_products(query)

    def _on_category_search_changed(self, *_args: Any) -> None:
        """Filter categories by name as user types."""
        query = self._cat_search_var.get().strip().lower()
        self._populate_categories(query)

    def _refresh_products(self) -> None:
        res = self._controller.list_products()
        if not res["success"]:
            return
        self._all_products = res["data"]
        query = self._prod_search_var.get().strip().lower()
        self._populate_products(query)

    def _populate_products(self, query: str) -> None:
        """Populate the product treeview with optional name filter."""
        for child in self._prod_tree.get_children():
            self._prod_tree.delete(child)

        categories = self._get_categories()
        cat_map = {c["id"]: c["name"] for c in categories}

        for p in self._all_products:
            name = getattr(p, "name", "")
            if query and query not in name.lower():
                continue

            pid = getattr(p, "id", None)
            barcode = getattr(p, "barcode", "") or ""
            price = getattr(p, "sale_price", 0)
            stock = getattr(p, "stock", 0)
            threshold = getattr(p, "low_stock_threshold", 5)

            # Check if low stock
            is_low = isinstance(stock, (int, float)) and isinstance(threshold, (int, float)) and stock <= threshold
            tags = (str(pid), "low_stock") if is_low else (str(pid),)

            self._prod_tree.insert(
                "", "end", iid=str(pid),
                values=(name, barcode, f"${price:,}", int(stock)),
                tags=tags,
            )

    def _refresh_categories(self) -> None:
        res = self._controller.list_categories()
        if not res["success"]:
            return
        self._all_categories = res["data"]
        query = self._cat_search_var.get().strip().lower()
        self._populate_categories(query)

    def _populate_categories(self, query: str) -> None:
        """Populate the category treeview with optional name filter."""
        for child in self._cat_tree.get_children():
            self._cat_tree.delete(child)

        for c in self._all_categories:
            name = c["name"]
            if query and query not in name.lower():
                continue

            self._cat_tree.insert(
                "", "end", iid=str(c["id"]),
                values=(name, c.get("product_count", 0)),
                tags=(str(c["id"]),),
            )
