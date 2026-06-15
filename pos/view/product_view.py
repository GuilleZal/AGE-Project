"""Product view — CRUD management screen with search, treeview, and actions.

Embeds the ``ProductSearch`` widget, a styled ``ttk.Treeview`` for the
product list, and action buttons (New, Edit, Delete, Import Excel).
Category CRUD is available inline via a dropdown that includes a
"＋ Nueva categoría" option.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.product_search import ProductSearch


class ProductView(ctk.CTkFrame):
    """Product management tab — search, treeview, and CRUD actions.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Productos" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_create``, ``on_edit``, ``on_delete``,
        ``on_import``, ``on_search``, ``on_create_category``.
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    COLUMNS = ("codigo", "nombre", "categoria", "precio", "stock")
    COLUMN_LABELS = {
        "codigo": "Código",
        "nombre": "Nombre",
        "categoria": "Categoría",
        "precio": "Precio",
        "stock": "Stock",
    }

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        callbacks = callbacks or {}

        # --- callback slots ---
        self._on_create: Callable[[], None] | None = callbacks.get(
            "on_create"
        )
        self._on_edit: Callable[[int], None] | None = callbacks.get(
            "on_edit"
        )
        self._on_delete: Callable[[int], None] | None = callbacks.get(
            "on_delete"
        )
        self._on_import: Callable[[], None] | None = callbacks.get(
            "on_import"
        )
        self._on_search: Callable[[str, int | None], None] | None = (
            callbacks.get("on_search")
        )
        self._on_create_category: Callable[[str], None] | None = callbacks.get(
            "on_create_category"
        )

        self._categories: list[dict[str, Any]] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # treeview row stretches

        # --- row 0: search bar ---
        self._search_bar = ProductSearch(
            self,
            categories=[],
            on_search=self._handle_search,
            on_barcode=self._handle_barcode_search,
        )
        self._search_bar.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )

        # --- row 1: product treeview ---
        self._tree_frame = ctk.CTkFrame(self)
        self._tree_frame.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=5
        )
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self._tree_frame.grid_columnconfigure(0, weight=1)

        self._style = ttk.Style(self._tree_frame)
        self._configure_style()

        self._tree = ttk.Treeview(
            self._tree_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COLUMN_LABELS[col])

        self._tree.column("codigo", width=120, anchor="center")
        self._tree.column("nombre", width=240, stretch=True)
        self._tree.column("categoria", width=140)
        self._tree.column("precio", width=100, anchor="e")
        self._tree.column("stock", width=80, anchor="center")

        self._scrollbar = ttk.Scrollbar(
            self._tree_frame,
            orient="vertical",
            command=self._tree.yview,
        )
        self._tree.configure(yscrollcommand=self._scrollbar.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")

        self._tree.bind("<Double-1>", self._handle_double_click)
        self._tree.bind("<Delete>", self._handle_delete_key)

        # --- row 2: action bar ---
        self._action_frame = ctk.CTkFrame(self)
        self._action_frame.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(5, 10)
        )

        ctk.CTkButton(
            self._action_frame,
            text="＋ Nuevo Producto",
            width=140,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_create,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            self._action_frame,
            text="✎ Editar",
            width=100,
            fg_color="#1f538d",
            command=self._handle_edit_btn,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            self._action_frame,
            text="🗑 Eliminar",
            width=100,
            fg_color="#8b1a1a",
            command=self._handle_delete_btn,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            self._action_frame,
            text="📥 Importar Excel",
            width=140,
            fg_color="#3b3b3b",
            command=self._handle_import,
        ).pack(side="left", padx=3)

        # --- category/tag management ---
        ctk.CTkButton(
            self._action_frame,
            text="＋ Nueva etiqueta",
            width=140,
            fg_color="#2d5a3d",
            command=self._prompt_new_category,
        ).pack(side="left", padx=3)

        # --- refresh button ---
        ctk.CTkButton(
            self._action_frame,
            text="🔄 Actualizar",
            width=120,
            fg_color="#3b3b3b",
            command=self._refresh_products,
        ).pack(side="right", padx=3)

    # ---------------------------------------------------------------- public ---

    def update_products(self, products: list[dict[str, Any]]) -> None:
        """Refresh the treeview with *products*.

        Each dict should have keys: ``id``, ``barcode``, ``name``,
        ``sale_price``, ``stock``, and optionally a nested
        ``category`` dict with ``name``.
        """
        for child in self._tree.get_children():
            self._tree.delete(child)

        for p in products:
            category_name = ""
            if hasattr(p, "category_id") and p.category_id:
                # Look up category name from internal cache
                category_name = self._get_category_name(p.category_id)
            elif isinstance(p, dict) and p.get("category"):
                category_name = p["category"].get("name", "")
            elif isinstance(p, dict):
                category_name = self._get_category_name(
                    p.get("category_id")
                )

            barcode = getattr(p, "barcode", "") or p.get("barcode", "") or ""
            name = getattr(p, "name", "") or p.get("name", "")
            price = getattr(p, "sale_price", 0) or p.get("sale_price", 0)
            stock = getattr(p, "stock", 0) if not isinstance(p, dict) else p.get("stock", 0)
            pid = getattr(p, "id", None) or p.get("id")

            self._tree.insert(
                "",
                "end",
                iid=str(pid),
                values=(
                    barcode,
                    name,
                    category_name,
                    f"${price:,}",
                    int(stock) if isinstance(stock, (int, float)) else stock,
                ),
                tags=(str(pid),),
            )

    def set_categories(self, categories: list[dict[str, Any]]) -> None:
        """Refresh the category data used for the dropdown and lookup.

        Each dict should have keys: ``id``, ``name``.
        """
        self._categories = categories
        # Update search bar dropdown
        self._search_bar.set_categories(categories)

    def get_selected_product_id(self) -> int | None:
        """Return the product ID of the selected row, or ``None``."""
        sel = self._tree.selection()
        if not sel:
            return None
        tags = self._tree.item(sel[0], "tags")
        if tags:
            return int(tags[0])
        return None

    # ----------------------------------------------------------- callbacks ----

    def set_on_create(self, callback: Callable[[], None]) -> None:
        """Wire the create callback."""
        self._on_create = callback

    def set_on_edit(self, callback: Callable[[int], None]) -> None:
        """Wire the edit callback (receives product_id)."""
        self._on_edit = callback

    def set_on_delete(self, callback: Callable[[int], None]) -> None:
        """Wire the delete callback (receives product_id)."""
        self._on_delete = callback

    def set_on_import(self, callback: Callable[[], None]) -> None:
        """Wire the Excel import callback."""
        self._on_import = callback

    def set_on_search(
        self, callback: Callable[[str, int | None], None]
    ) -> None:
        """Wire the search callback (receives query, category_id)."""
        self._on_search = callback
        self._search_bar.set_on_search(callback)

    def set_on_create_category(
        self, callback: Callable[[str], None]
    ) -> None:
        """Wire the create-category callback (receives category name)."""
        self._on_create_category = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``ProductController`` instance and set up all event handlers.

        After calling this, all view events are automatically routed to
        the controller, and the initial product list is loaded.
        """
        self._controller = controller

        # Wire internal handlers to callback slots
        self._on_create = self._controller_create
        self._on_edit = self._controller_edit
        self._on_delete = self._controller_delete
        self._on_import = self._controller_import
        self._on_search = self._controller_search
        self._on_create_category = self._controller_create_category

        # Update search bar callback so live typing hits the controller
        self._search_bar.set_on_search(self._controller_search)

        # Initial load
        self._refresh_products()
        self._refresh_categories()

    # ---------------------------------------------------- controller handlers ---

    def _controller_create(self) -> None:
        """Open product form dialog for creation."""
        from pos.view.widgets.product_form_dialog import ProductFormDialog

        dialog = ProductFormDialog(self, categories=self._categories)
        self.wait_window(dialog)
        product_data = dialog.result
        if product_data:
            result = self._controller.create_product(product_data)
            if result["success"]:
                self._refresh_products()
            else:
                messagebox.showerror("Error", result["error"])

    def _controller_edit(self, product_id: int) -> None:
        """Open product form dialog pre-filled for editing."""
        from pos.view.widgets.product_form_dialog import ProductFormDialog

        get_result = self._controller.get_product(product_id)
        if not get_result["success"]:
            messagebox.showerror("Error", get_result["error"])
            return

        product = get_result["data"]
        # Convert domain object to dict for the dialog
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
            self, product=product_dict, categories=self._categories
        )
        self.wait_window(dialog)
        product_data = dialog.result
        if product_data:
            result = self._controller.update_product(product_id, product_data)
            if result["success"]:
                self._refresh_products()
            else:
                messagebox.showerror("Error", result["error"])

    def _controller_delete(self, product_id: int) -> None:
        """Delete the selected product via controller."""
        result = self._controller.delete_product(product_id)
        if result["success"]:
            self._refresh_products()
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_import(self) -> None:
        """Open file dialog and trigger Excel import via controller."""
        filepath = filedialog.askopenfilename(
            title="Importar productos desde Excel",
            filetypes=[("Excel", "*.xlsx")],
        )
        if filepath:
            result = self._controller.import_from_excel(filepath)
            if result["success"]:
                data = result.get("data", {})
                created = data.get("created", 0)
                updated = data.get("updated", 0)
                errors = data.get("errors", [])
                msg = f"Importados: {created}, Actualizados: {updated}"
                if errors:
                    msg += f"\nErrores: {len(errors)} fila(s)"
                messagebox.showinfo("Importación completada", msg)
                self._refresh_products()
            else:
                messagebox.showerror("Error", result["error"])

    def _controller_search(self, query: str, category_id: int | None = None) -> None:
        """Search products via controller and update the treeview."""
        result = self._controller.list_products({
            "search": query,
            "category_id": category_id,
        })
        if result["success"]:
            self.update_products(result["data"])
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_create_category(self, name: str) -> None:
        """Create a new category via controller and refresh the dropdown."""
        result = self._controller.create_category(name)
        if result["success"]:
            self._refresh_categories()
        else:
            messagebox.showerror("Error", result["error"])

    def _refresh_products(self) -> None:
        """Reload the full product list from the controller."""
        result = self._controller.list_products()
        if result["success"]:
            self.update_products(result["data"])

    def _refresh_categories(self) -> None:
        """Reload categories from the controller and update dropdowns."""
        result = self._controller.list_categories()
        if result["success"]:
            self.set_categories(result["data"])

    # --------------------------------------------------------------- private ---

    def _configure_style(self) -> None:
        """Configure ttk styles to blend with CTk dark theme."""
        self._style.theme_use("clam")

        bg = "#2b2b2b"
        fg = "#dce4ee"
        select_bg = "#1f538d"

        self._style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
        )
        self._style.configure(
            "Treeview.Heading",
            background="#3b3b3b",
            foreground=fg,
            relief="flat",
        )
        self._style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", fg)],
        )
        self._style.configure(
            "Vertical.TScrollbar",
            background=bg,
            troughcolor=bg,
            borderwidth=0,
            arrowcolor=fg,
        )

    def _get_category_name(self, category_id: int | None) -> str:
        """Look up a category name by ID from the internal cache."""
        if category_id is None:
            return ""
        for cat in self._categories:
            if cat["id"] == category_id:
                return cat["name"]
        return ""

    # ------------------------------------------------------- event handlers ---

    def _handle_search(self, query: str, category_id: int | None) -> None:
        if self._on_search is not None:
            self._on_search(query, category_id)

    def _handle_barcode_search(self, barcode: str) -> None:
        # Treat barcode as a search-by-barcode action
        if self._on_search is not None:
            self._on_search(barcode, None)

    def _handle_create(self) -> None:
        if self._on_create is not None:
            self._on_create()

    def _handle_edit_btn(self) -> None:
        pid = self.get_selected_product_id()
        if pid is None:
            messagebox.showwarning(
                "Seleccionar producto",
                "Seleccione un producto de la lista para editar.",
            )
            return
        if self._on_edit is not None:
            self._on_edit(pid)

    def _handle_delete_btn(self) -> None:
        pid = self.get_selected_product_id()
        if pid is None:
            messagebox.showwarning(
                "Seleccionar producto",
                "Seleccione un producto de la lista para eliminar.",
            )
            return
        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            "¿Está seguro de eliminar este producto?\n"
            "Esta acción no se puede deshacer si el producto "
            "no tiene transacciones asociadas.",
        )
        if confirm and self._on_delete is not None:
            self._on_delete(pid)

    def _handle_delete_key(self, _event: tk.Event) -> None:
        self._handle_delete_btn()

    def _handle_double_click(self, _event: tk.Event) -> None:
        self._handle_edit_btn()

    def _handle_import(self) -> None:
        if self._on_import is not None:
            self._on_import()

    def _prompt_new_category(self) -> None:
        """Show a small dialog to enter a new category name."""
        dialog = _CategoryCreateDialog(self)
        self.wait_window(dialog)
        name = dialog.result
        if name and self._on_create_category is not None:
            self._on_create_category(name)


# ----------------------------------------------------------------- helpers ---


class _CategoryCreateDialog(ctk.CTkToplevel):
    """Small modal dialog to prompt for a new category name."""

    def __init__(self, master: tk.Widget, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Nueva categoría")
        self.resizable(False, False)

        self.grab_set()
        self.transient(master)

        self._result: str | None = None

        ctk.CTkLabel(
            self,
            text="Nombre de la nueva categoría:",
            font=ctk.CTkFont(size=14),
        ).pack(pady=(20, 10))

        self._entry = ctk.CTkEntry(self, width=250, placeholder_text="Ej: Vinos")
        self._entry.pack(padx=20, pady=5)
        self._entry.bind("<Return>", lambda _e: self._confirm())
        self._entry.focus_set()

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
        )
        self._error_label.pack()

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(10, 20))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Crear",
            width=100,
            command=self._confirm,
        ).pack(side="left", padx=5)

        self.geometry("350x200")
        self._center_on_master(master)

    @property
    def result(self) -> str | None:
        """Category name on confirm, ``None`` on cancel."""
        return self._result

    def _confirm(self) -> None:
        name = self._entry.get().strip()
        if not name:
            self._error_label.configure(text="El nombre es obligatorio")
            self._entry.focus_set()
            return
        self._result = name
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()

    def _center_on_master(self, master: tk.Widget) -> None:
        self.update_idletasks()
        mw, mh = master.winfo_width(), master.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"+{x}+{y}")
