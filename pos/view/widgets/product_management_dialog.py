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

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


class ProductManagementDialog(CenteredDialog):
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
        super().__init__(master, width=600, height=500, title="Gestionar Categorías", resizable=(True, True), **kwargs)

        self._controller = controller
        self._changed = False
        self._all_products: list[Any] = []
        self._all_categories: list[dict[str, Any]] = []

        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_categories_tab(main_frame)

        # Load data
        self._refresh_products()
        self._refresh_categories()

    @property
    def changed(self) -> bool:
        """True if any product or category was created/edited/deleted."""
        return self._changed

    # ===================================================== products tab



    # ==================================================== categories tab

    def _build_categories_tab(self, parent: tk.Widget) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(parent)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Nombre:", font=theme.scaled_font(13)).grid(
            row=0, column=0, padx=(10, 5)
        )
        self._cat_search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Filtrar por nombre...", width=250,
        )
        self._cat_search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
        self._cat_search_entry.bind("<KeyRelease>", self._on_category_search_changed)

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
        self._cat_tree.column("nombre", width=250, stretch=True)
        self._cat_tree.column("productos", width=100, anchor="center", stretch=False)

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

        ctk.CTkButton(
            btn_frame, text="📋 Asignar categoría", width=150,
            fg_color="#2d5a3d", command=self._assign_category,
        ).pack(side="left", padx=5)
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    # ======================================== messagebox.showerror("Error", res["error"])



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
            confirm = messagebox.askyesno(
                "Confirmar eliminación",
                f'La categoría "{name}" tiene {product_count} producto(s) asignado(s).\n'
                f'Si la elimina, esos productos quedarán automáticamente "Sin categoría".\n\n'
                f'¿Eliminar la categoría "{name}" de todas formas?',
            )
        else:
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

    def _assign_category(self) -> None:
        """Open dialog to assign a category to multiple products."""
        from pos.view.widgets.assign_category_dialog import AssignCategoryDialog

        if not self._all_products:
            messagebox.showwarning(
                "Sin productos",
                "No hay productos disponibles para asignar categoría.",
            )
            return

        if not self._all_categories:
            messagebox.showwarning(
                "Sin categorías",
                "No hay categorías disponibles. Cree una categoría primero.",
            )
            return

        dialog = AssignCategoryDialog(
            self,
            products=self._all_products,
            categories=self._all_categories,
        )
        self.wait_window(dialog)
        result = dialog.result

        if result is None:
            return

        category_id = result["category_id"]
        product_ids = result["product_ids"]

        # Find category name for confirmation message
        if category_id is None:
            category_name = "Sin categoría"
        else:
            category_name = next(
                (c["name"] for c in self._all_categories if c["id"] == category_id),
                "desconocida"
            )

        # Confirm assignment
        if category_id is None:
            confirm_msg = f"¿Quitar la categoría a {len(product_ids)} producto(s)?"
        else:
            confirm_msg = f"¿Asignar la categoría '{category_name}' a {len(product_ids)} producto(s)?"
        
        confirm = messagebox.askyesno(
            "Confirmar asignación",
            confirm_msg,
        )
        if not confirm:
            return

        # Update each product
        updated_count = 0
        errors = []
        for pid in product_ids:
            res = self._controller.update_product(pid, {"category_id": category_id})
            if res["success"]:
                updated_count += 1
            else:
                errors.append(f"Producto ID {pid}: {res['error']}")

        if updated_count > 0:
            self._changed = True
            self._refresh_products()
            self._refresh_categories()
            if category_id is None:
                messagebox.showinfo(
                    "Asignación completada",
                    f"Se quitó la categoría a {updated_count} producto(s).",
                )
            else:
                messagebox.showinfo(
                    "Asignación completada",
                    f"Se asignó la categoría '{category_name}' a {updated_count} producto(s).",
                )

        if errors:
            messagebox.showerror(
                "Errores",
                f"Ocurrieron errores al actualizar algunos productos:\n\n" +
                "\n".join(errors[:5]) +  # Show first 5 errors
                (f"\n\n... y {len(errors) - 5} error(es) más." if len(errors) > 5 else ""),
            )

    # ======================================================== helpers

    def _show_products_help(self) -> None:
        """Show help dialog explaining product table selection controls."""
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
            "Los productos seleccionados se pueden editar, desactivar o eliminar\n"
            "en conjunto usando los botones correspondientes."
        )
        messagebox.showinfo(
            "Ayuda — Selección múltiple",
            help_text,
            parent=self,
        )

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

    def _on_product_search_changed(self, event: Any = None) -> None:
        """Filter products by name as user types."""
        query = self._prod_search_entry.get().strip().lower()
        self._populate_products(query)

    def _on_category_search_changed(self, event: Any = None) -> None:
        """Filter categories by name as user types."""
        query = self._cat_search_entry.get().strip().lower()
        self._populate_categories(query)

    def _refresh_products(self) -> None:
        res = self._controller.list_products()
        if not res["success"]:
            return
        self._all_products = res["data"]

    def _refresh_categories(self) -> None:
        res = self._controller.list_categories()
        if not res["success"]:
            return
        self._all_categories = res["data"]
        query = self._cat_search_entry.get().strip().lower()
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
