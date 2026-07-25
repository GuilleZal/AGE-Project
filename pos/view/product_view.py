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
from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


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

    COLUMNS = ("codigo", "nombre", "categoria", "costo", "precio", "ganancia", "stock")
    COLUMN_LABELS = {
        "codigo": "Código",
        "nombre": "Nombre",
        "categoria": "Categoría",
        "costo": "Costo",
        "precio": "Precio",
        "ganancia": "Ganancia %",
        "stock": "Stock/Kg",
    }

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        role: str | None = None,
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}
        self._role = role

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
        self._on_search: Callable[[dict[str, Any]], None] | None = (
            callbacks.get("on_search")
        )
        self._on_create_category: Callable[[str], None] | None = callbacks.get(
            "on_create_category"
        )
        self._on_preferences: Callable[[], None] | None = callbacks.get(
            "on_preferences"
        )

        self._categories: list[dict[str, Any]] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # treeview row stretches
        self.grid_rowconfigure(2, weight=0)  # action bar fixed

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
        self._tree.tag_configure("low_stock", foreground="#e74c3c")
        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COLUMN_LABELS[col])

        self._tree.column("codigo", width=150, minwidth=150, anchor="center")
        self._tree.column("nombre", width=350, minwidth=350) # Espacio gigante para los nombres
        self._tree.column("categoria", width=160, minwidth=160)
        self._tree.column("costo", width=120, minwidth=120, anchor="e")
        self._tree.column("precio", width=120, minwidth=120, anchor="e")
        self._tree.column("ganancia", width=120, minwidth=120, anchor="center")
        self._tree.column("stock", width=100, minwidth=100, anchor="center")

        # Cargamos solo la funcionalidad de ordenamiento (Eliminamos la carga de anchos guardados)
        add_sorting_to_treeview(
            self._tree,
            list(self.COLUMNS),
            column_types={
                "codigo": "str",
                "nombre": "str",
                "categoria": "str",
                "costo": "int",
                "precio": "int",
                "ganancia": "float",
                "stock": "int",
            }
        )

        # Bloqueamos el redimensionamiento manual
        self._tree.bind("<Button-1>", self._prevent_resize)
        self._tree.bind("<B1-Motion>", self._prevent_resize)

        # Scrollbars (Vertical y Horizontal)
        self._vscrollbar = ttk.Scrollbar(
            self._tree_frame,
            orient="vertical",
            command=self._tree.yview,
        )
        self._hscrollbar = ttk.Scrollbar(
            self._tree_frame,
            orient="horizontal",
            command=self._tree.xview,
        )
        self._tree.configure(
            yscrollcommand=self._vscrollbar.set,
            xscrollcommand=self._hscrollbar.set
        )

        # Ajustamos el grid interno para acomodar la nueva barra horizontal
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self._tree_frame.grid_rowconfigure(1, weight=0)
        self._tree_frame.grid_columnconfigure(0, weight=1)
        self._tree_frame.grid_columnconfigure(1, weight=0)

        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vscrollbar.grid(row=0, column=1, sticky="ns")
        self._hscrollbar.grid(row=1, column=0, sticky="ew")

        self._tree.bind("<Double-1>", self._handle_double_click)
        self._tree.bind("<Delete>", self._handle_delete_key)

        # --- row 2: action bar ---
        self._action_frame = ctk.CTkFrame(self)
        self._action_frame.grid(
            row=2, column=0, sticky="ew", padx=10, pady=(5, 10)
        )

        row0_frame = ctk.CTkFrame(self._action_frame, fg_color="transparent")
        row0_frame.pack(fill="x", expand=True, pady=2)

        row1_frame = ctk.CTkFrame(self._action_frame, fg_color="transparent")
        row1_frame.pack(fill="x", expand=True, pady=2)

        ctk.CTkButton(
            row0_frame,
            text="＋ Nuevo Producto",
            width=150,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#28a745",
            command=self._controller_create,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            row0_frame,
            text="✎ Editar",
            width=100,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#1f538d",
            command=self._handle_edit_btn,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            row0_frame,
            text="🗑 Eliminar",
            width=100,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#8b1a1a",
            command=self._handle_delete_btn,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            row0_frame,
            text="📋 Gestionar Categorías",
            width=170,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#1f538d",
            command=self._handle_management,
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            row1_frame,
            text="📥 Importar Excel",
            width=140,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#3b3b3b",
            command=self._handle_import,
        ).pack(side="left", padx=3)

        # --- preferences button ---
        ctk.CTkButton(
            row1_frame,
            text="⚙ Preferencias",
            width=130,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#4a4a4a",
            command=self._handle_preferences,
        ).pack(side="left", padx=3)

        # --- refresh button ---
        ctk.CTkButton(
            row1_frame,
            text="🔄 Actualizar",
            width=120,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#3b3b3b",
            command=self._refresh_products,
        ).pack(side="right", padx=3)

    # ---------------------------------------------------------------- public ---

    def update_products(self, products: list[dict[str, Any]]) -> None:
        """Refresh the treeview with *products*.

        Each dict should have keys: ``id``, ``barcode``, ``name``,
        ``cost_price``, ``sale_price``, ``stock``, and optionally a nested
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

            if isinstance(p, dict):
                barcode = p.get("barcode", "") or ""
                name = p.get("name", "")
                cost_price = p.get("cost_price", 0)
                price = p.get("sale_price", 0)
                stock = p.get("stock", 0)
                unit_type = p.get("unit_type", "Unidad")
                low_stock_threshold = p.get("low_stock_threshold", 5)
                pid = p.get("id")
            else:
                barcode = getattr(p, "barcode", "") or ""
                name = getattr(p, "name", "")
                cost_price = getattr(p, "cost_price", 0)
                price = getattr(p, "sale_price", 0)
                stock = getattr(p, "stock", 0)
                unit_type = getattr(p, "unit_type", "Unidad")
                low_stock_threshold = getattr(p, "low_stock_threshold", 5)
                pid = getattr(p, "id", None)

            # Calculate margin percentage
            margin_pct = 0.0
            if cost_price > 0:
                margin_pct = ((price - cost_price) / cost_price) * 100

            # Format stock with warning icon if low and unit
            try:
                f_stock = float(stock)
                if f_stock < 0:
                    phys_stock = 0.0
                    deficit = abs(f_stock)
                    formatted_deficit = f"{deficit:.2f}".rstrip('0').rstrip('.') if not deficit.is_integer() else str(int(deficit))
                    stock_display = f"0 Kg (Faltante: {formatted_deficit})" if unit_type == "Kg" else f"0 u. (Faltante: {formatted_deficit})"
                else:
                    formatted_stock = f"{f_stock:.2f}".rstrip('0').rstrip('.') if not f_stock.is_integer() else str(int(f_stock))
                    stock_display = f"{formatted_stock} Kg" if unit_type == "Kg" else f"{formatted_stock} u."
            except ValueError:
                stock_display = str(stock)
            
            is_low_stock = False
            if isinstance(stock, (int, float)) and isinstance(low_stock_threshold, (int, float)):
                if stock <= low_stock_threshold:
                    stock_display = f"⚠ {stock_display}"
                    is_low_stock = True

            row_tags = (str(pid),)
            if is_low_stock:
                row_tags = (str(pid), "low_stock")

            self._tree.insert(
                "",
                "end",
                iid=str(pid),
                values=(
                    barcode,
                    name,
                    category_name,
                    f"${cost_price:,}",
                    f"${price:,}",
                    f"{margin_pct:.1f}%",
                    stock_display,
                ),
                tags=row_tags,
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
        self, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        """Wire the search callback (receives filters dict)."""
        self._on_search = callback
        self._search_bar.set_on_search(callback)

    def set_on_create_category(
        self, callback: Callable[[str], None]
    ) -> None:
        """Wire the create-category callback (receives category name)."""
        self._on_create_category = callback

    def set_on_preferences(self, callback: Callable[[], None]) -> None:
        """Wire the preferences callback."""
        self._on_preferences = callback

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

        # Initial load - categories first, then products (products need category names)
        self._refresh_categories()
        self._refresh_products()

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
            "unit_type": getattr(product, "unit_type", "Unidad"),
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
        from pos.view.widgets.import_result_dialog import ImportResultDialog
        
        filepath = filedialog.askopenfilename(
            title="Importar productos desde Excel",
            filetypes=[("Excel", "*.xlsx")],
        )
        if filepath:
            result = self._controller.import_from_excel(filepath)
            if result["success"]:
                data = result.get("data", {})
                # Show detailed import result dialog
                dialog = ImportResultDialog(self, data)
                self.wait_window(dialog)
                self._refresh_products()
                self._refresh_categories()  # Import may create new categories
            else:
                messagebox.showerror("Error", result["error"])

    def _controller_search(self, filters: dict[str, Any]) -> None:
        """Search products via controller and update the treeview."""
        result = self._controller.list_products(filters)
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
    def _prevent_resize(self, event: Any) -> str | None:
        """Evita que el usuario cambie el tamaño de las columnas arrastrando el separador."""
        if event.widget.identify_region(event.x, event.y) == "separator":
            return "break"
        return None
        
    def _configure_style(self) -> None:
        """Configure ttk styles to blend with CTk dark theme."""
        self._style.theme_use("clam")

        contrast = theme.get_contrast_map()
        bg = contrast["treeview_bg"]
        fg = contrast["treeview_fg"]
        select_bg = "#1f538d"

        self._style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
            font=theme.scaled_treeview_font(),
            rowheight=24 + theme.get_offset() * 2,
        )
        self._style.configure(
            "Treeview.Heading",
            background=contrast["treeview_header"],
            foreground=fg,
            relief="raised",
            borderwidth=1,
            font=theme.scaled_treeview_font("bold"),
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

    def _handle_search(self, filters: dict[str, Any]) -> None:
        if self._on_search is not None:
            self._on_search(filters)

    def _handle_barcode_search(self, barcode: str) -> None:
        # Treat barcode as a search-by-barcode action
        if self._on_search is not None:
            self._on_search({"search": "", "category_id": None, "barcode": barcode})

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
            "¿Está seguro de que desea eliminar este producto?",
        )
        if confirm and self._on_delete is not None:
            self._on_delete(pid)

    def _handle_delete_key(self, _event: tk.Event) -> None:
        self._handle_delete_btn()

    def _handle_double_click(self, event: tk.Event) -> None:
        """Handle double click on treeview - only edit if clicked on a row, not headers."""
        # Check if the click was on a row (not on headers)
        row_id = self._tree.identify_row(event.y)
        if row_id:  # Only proceed if clicked on an actual row
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

    def _handle_preferences(self) -> None:
        """Open the preferences dialog."""
        from pos.view.widgets.preferences_dialog import PreferencesDialog

        if not hasattr(self, "_controller") or self._controller is None:
            messagebox.showerror("Error", "Controller no disponible")
            return

        dialog = PreferencesDialog(self, self._controller)
        self.wait_window(dialog)
        if dialog.applied:
            self._refresh_products()

    def _handle_management(self) -> None:
        """Open the unified product & category management dialog."""
        from pos.view.widgets.product_management_dialog import (
            ProductManagementDialog,
        )

        if not hasattr(self, "_controller") or self._controller is None:
            messagebox.showerror("Error", "Controller no disponible")
            return

        dialog = ProductManagementDialog(self, self._controller)
        self.wait_window(dialog)
        if dialog.changed:
            self._refresh_products()
            self._refresh_categories()


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
            font=theme.scaled_font(14),
        ).pack(pady=(20, 10))

        self._entry = ctk.CTkEntry(self, width=250, placeholder_text="Ej: Vinos")
        self._entry.pack(padx=20, pady=5)
        self._entry.bind("<Return>", lambda _e: self._confirm())
        self._entry.focus_set()

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
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
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

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
