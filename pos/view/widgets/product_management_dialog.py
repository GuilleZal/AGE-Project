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
        super().__init__(master, width=750, height=550, title="Gestionar productos y categorías", resizable=(True, True), **kwargs)

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

        ctk.CTkLabel(search_frame, text="Nombre:", font=theme.scaled_font(13)).grid(
            row=0, column=0, padx=(10, 5)
        )
        self._prod_search_var = tk.StringVar()
        self._prod_search_var.trace_add("write", self._on_product_search_changed)
        ctk.CTkEntry(
            search_frame, textvariable=self._prod_search_var,
            placeholder_text="Filtrar por nombre...", width=250,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)

        # Checkbox to show inactive products
        self._show_inactive_var = tk.BooleanVar(value=False)
        self._show_inactive_check = ctk.CTkCheckBox(
            search_frame,
            text="Mostrar desactivados",
            variable=self._show_inactive_var,
            command=self._on_show_inactive_changed,
            font=theme.scaled_font(12),
        )
        self._show_inactive_check.grid(row=0, column=2, padx=(10, 5))

        # Help button
        ctk.CTkButton(
            search_frame,
            text="?",
            width=30,
            height=30,
            fg_color="#505050",
            hover_color="#606060",
            font=theme.scaled_font(14, weight="bold"),
            command=self._show_products_help,
        ).grid(row=0, column=3, padx=(5, 10))

        # Treeview
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 0))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        cols = ("nombre", "categoria", "codigo", "precio", "stock")
        self._prod_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="extended", height=15,
        )
        self._prod_tree.heading("nombre", text="Nombre")
        self._prod_tree.heading("categoria", text="Categoría")
        self._prod_tree.heading("codigo", text="Código")
        self._prod_tree.heading("precio", text="Precio")
        self._prod_tree.heading("stock", text="Stock")
        self._prod_tree.column("nombre", width=180)
        self._prod_tree.column("categoria", width=120)
        self._prod_tree.column("codigo", width=100, anchor="center")
        self._prod_tree.column("precio", width=80, anchor="e")
        self._prod_tree.column("stock", width=60, anchor="center")

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
                "categoria": "str",
                "codigo": "str",
                "precio": "int",
                "stock": "int",
            }
        )

        # Red tag for low-stock rows
        self._prod_tree.tag_configure("low_stock", foreground="#e74c3c")
        # Gray tag for inactive products
        self._prod_tree.tag_configure("inactive", foreground="#888888")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._prod_tree.yview)
        self._prod_tree.configure(yscrollcommand=sb.set)
        self._prod_tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # Bind selection event to update button states
        self._prod_tree.bind("<<TreeviewSelect>>", self._on_product_select)

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

        self._deactivate_btn = ctk.CTkButton(
            btn_frame, text="🚫 Desactivar", width=120,
            fg_color="#8b1a1a", command=self._delete_product,
        )
        self._deactivate_btn.pack(side="left", padx=5)

        self._activate_btn = ctk.CTkButton(
            btn_frame, text="✅ Activar", width=120,
            fg_color="#2d7d2d", command=self._reactivate_product,
        )
        self._activate_btn.pack(side="left", padx=5)
        self._activate_btn.pack_forget()  # Hide by default

        self._bulk_delete_btn = ctk.CTkButton(
            btn_frame, text="🗑️ Eliminar Selección", width=150,
            fg_color="#5a1a1a", command=self._bulk_smart_delete,
        )
        self._bulk_delete_btn.pack(side="left", padx=5)

    # ==================================================== categories tab

    def _build_categories_tab(self, parent: tk.Widget) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(parent)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5))
        search_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(search_frame, text="Buscar:", font=theme.scaled_font(13)).grid(
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

        ctk.CTkButton(
            btn_frame, text="📋 Asignar categoría", width=150,
            fg_color="#2d5a3d", command=self._assign_category,
        ).pack(side="left", padx=5)
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

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
            "unit_type": getattr(product, "unit_type", "Unidad"),
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
        """Deactivate one or more products."""
        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione al menos un producto de la lista."
            )
            return

        count = len(sel)
        
        # Get product names for confirmation message
        product_names = []
        product_ids = []
        for item_id in sel:
            item = self._prod_tree.item(item_id)
            pid = int(item["tags"][0])
            name = item["values"][0]
            # Remove [DESACTIVADO] prefix if present
            if name.startswith("[DESACTIVADO] "):
                name = name[13:]
            product_names.append(name)
            product_ids.append(pid)

        if count == 1:
            confirm_msg = f'¿Desactivar el producto "{product_names[0]}"?\n\n'
        else:
            confirm_msg = f"¿Desactivar {count} productos seleccionados?\n\n"
        
        confirm_msg += "El producto dejará de aparecer en la lista pero mantendrá su historial."

        confirm = messagebox.askyesno(
            "Confirmar desactivación",
            confirm_msg,
        )
        if not confirm:
            return

        # Deactivate all selected products
        success_count = 0
        errors = []
        for pid in product_ids:
            res = self._controller.delete_product(pid)
            if res["success"]:
                success_count += 1
            else:
                errors.append(f"Producto ID {pid}: {res['error']}")

        if success_count > 0:
            self._changed = True
            self._refresh_products()
            
            if count == 1:
                messagebox.showinfo("Desactivado", "Producto desactivado correctamente")
            else:
                msg = f"✅ {success_count} producto(s) desactivado(s) correctamente"
                if errors:
                    msg += f"\n\n❌ {len(errors)} error(es):"
                    for error in errors[:5]:
                        msg += f"\n  • {error}"
                    if len(errors) > 5:
                        msg += f"\n  ... y {len(errors) - 5} error(es) más"
                messagebox.showinfo("Desactivación completada", msg)
        elif errors:
            messagebox.showerror("Error", "\n".join(errors))

    def _reactivate_product(self) -> None:
        """Reactivate one or more deactivated products."""
        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione al menos un producto de la lista."
            )
            return

        count = len(sel)
        
        # Get product names for confirmation message
        product_names = []
        product_ids = []
        for item_id in sel:
            item = self._prod_tree.item(item_id)
            pid = int(item["tags"][0])
            name = item["values"][0]
            # Remove [DESACTIVADO] prefix if present
            if name.startswith("[DESACTIVADO] "):
                name = name[13:]
            product_names.append(name)
            product_ids.append(pid)

        if count == 1:
            confirm_msg = f'¿Activar el producto "{product_names[0]}"?\n\n'
        else:
            confirm_msg = f"¿Activar {count} productos seleccionados?\n\n"
        
        confirm_msg += "Los productos volverán a aparecer en la lista de productos activos."

        confirm = messagebox.askyesno(
            "Confirmar activación",
            confirm_msg,
        )
        if not confirm:
            return

        # Reactivate all selected products
        success_count = 0
        errors = []
        for pid in product_ids:
            res = self._controller.reactivate_product(pid)
            if res["success"]:
                success_count += 1
            else:
                errors.append(f"Producto ID {pid}: {res['error']}")

        if success_count > 0:
            self._changed = True
            self._refresh_products()
            
            if count == 1:
                messagebox.showinfo("Activado", "Producto activado correctamente")
            else:
                msg = f"✅ {success_count} producto(s) activado(s) correctamente"
                if errors:
                    msg += f"\n\n❌ {len(errors)} error(es):"
                    for error in errors[:5]:
                        msg += f"\n  • {error}"
                    if len(errors) > 5:
                        msg += f"\n  ... y {len(errors) - 5} error(es) más"
                messagebox.showinfo("Activación completada", msg)
        elif errors:
            messagebox.showerror("Error", "\n".join(errors))

    def _bulk_smart_delete(self) -> None:
        """Intelligently delete multiple selected products.
        
        For each selected product:
        - If NO transaction history: performs hard delete (DELETE).
        - If HAS transaction history: performs soft delete (UPDATE is_active = 0).
        """
        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning(
                "Seleccionar", "Seleccione al menos un producto de la lista."
            )
            return

        count = len(sel)
        confirm = messagebox.askyesno(
            "Confirmar eliminación masiva",
            f"¿Está seguro de eliminar {count} producto(s) seleccionado(s)?\n\n"
            "⚠️ ADVERTENCIA:\n"
            "• Productos SIN historial de ventas: serán eliminados permanentemente.\n"
            "• Productos CON historial de ventas: serán desactivados (baja lógica).\n\n"
            "Esta acción no se puede deshacer.",
        )
        if not confirm:
            return

        # Extract product IDs from selection
        product_ids = []
        for item_id in sel:
            item = self._prod_tree.item(item_id)
            pid = int(item["tags"][0])
            product_ids.append(pid)

        res = self._controller.smart_delete_products(product_ids)
        if res["success"]:
            self._changed = True
            self._refresh_products()
            
            data = res["data"]
            hard_deleted = data.get("hard_deleted", 0)
            soft_deleted = data.get("soft_deleted", 0)
            errors = data.get("errors", [])
            
            msg_parts = []
            if hard_deleted > 0:
                msg_parts.append(f"✅ {hard_deleted} producto(s) eliminado(s) permanentemente")
            if soft_deleted > 0:
                msg_parts.append(f"🚫 {soft_deleted} producto(s) desactivado(s)")
            if errors:
                msg_parts.append(f"\n❌ {len(errors)} error(es):")
                for error in errors[:5]:  # Show first 5 errors
                    msg_parts.append(f"  • {error}")
                if len(errors) > 5:
                    msg_parts.append(f"  ... y {len(errors) - 5} error(es) más")
            
            messagebox.showinfo(
                "Eliminación completada",
                "\n".join(msg_parts)
            )
        else:
            messagebox.showerror("Error", res["error"])

    def _on_product_select(self, event: tk.Event) -> None:
        """Update button states based on selected product."""
        sel = self._prod_tree.selection()
        if not sel:
            return

        inactive_count = 0
        for sid in sel:
            tags = self._prod_tree.item(sid).get("tags", ())
            if "inactive" in tags:
                inactive_count += 1

        total = len(sel)
        all_inactive = inactive_count == total
        all_active = inactive_count == 0

        if all_inactive:
            self._deactivate_btn.pack_forget()
            self._activate_btn.pack(side="left", padx=5)
        elif all_active:
            self._activate_btn.pack_forget()
            self._deactivate_btn.pack(side="left", padx=5)
        else:
            self._activate_btn.pack(side="left", padx=5)
            self._deactivate_btn.pack(side="left", padx=5)

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

    def _on_product_search_changed(self, *_args: Any) -> None:
        """Filter products by name as user types."""
        query = self._prod_search_var.get().strip().lower()
        self._populate_products(query)

    def _on_show_inactive_changed(self) -> None:
        """Refresh products when show inactive checkbox changes."""
        self._refresh_products()
        # Reset button to default state (show deactivate, hide activate)
        self._activate_btn.pack_forget()
        self._deactivate_btn.pack(side="left", padx=5)

    def _on_category_search_changed(self, *_args: Any) -> None:
        """Filter categories by name as user types."""
        query = self._cat_search_var.get().strip().lower()
        self._populate_categories(query)

    def _refresh_products(self) -> None:
        include_inactive = self._show_inactive_var.get()
        res = self._controller.list_products({"include_inactive": include_inactive})
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
            is_active = getattr(p, "is_active", True)
            category_id = getattr(p, "category_id", None)
            category_name = cat_map.get(category_id, "")

            # Check if low stock
            is_low = isinstance(stock, (int, float)) and isinstance(threshold, (int, float)) and stock <= threshold
            
            # Build tags
            tags = [str(pid)]
            if is_low:
                tags.append("low_stock")
            if not is_active:
                tags.append("inactive")
                name = f"[DESACTIVADO] {name}"
            unit_type = getattr(p, "unit_type", "Unidad")
            
            try:
                f_stock = float(stock)
                formatted_stock = f"{f_stock:.2f}".rstrip('0').rstrip('.') if not f_stock.is_integer() else str(int(f_stock))
            except ValueError:
                formatted_stock = str(stock)
                
            stock_display = f"{formatted_stock} Kg" if unit_type == "Kg" else f"{formatted_stock} u."

            self._prod_tree.insert(
                "", "end", iid=str(pid),
                values=(name, category_name, barcode, f"${price:,}", stock_display),
                tags=tuple(tags),
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
