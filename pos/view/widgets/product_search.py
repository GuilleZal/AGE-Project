"""Product search bar — barcode entry, name search, and category filter.

A reusable ``CTkFrame`` widget that combines a barcode-style entry, a text
search entry, and a category dropdown into a compact toolbar.
"""

import tkinter as tk
from typing import Any, Callable

import customtkinter as ctk
from pos.view import theme


class ProductSearch(ctk.CTkFrame):
    """Search toolbar for the product CRUD view.

    Parameters
    ----------
    master : tk.Widget
        Parent widget.
    categories : list[dict] | None
        Category list with keys ``id`` and ``name``.  If provided, a
        category dropdown is displayed; otherwise only the text search
        entry is shown.
    on_search : Callable[[str, int | None], None] | None
        Callback invoked with ``(query, category_id)`` whenever the user
        types in the search entry or selects a category.
    on_barcode : Callable[[str], None] | None
        Callback invoked when a barcode is scanned (like ``BarcodeEntry``).
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    def __init__(
        self,
        master: tk.Widget,
        categories: list[dict[str, Any]] | None = None,
        on_search: Callable[[str, int | None], None] | None = None,
        on_barcode: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_search: Callable[[str, int | None], None] | None = on_search
        self._on_barcode: Callable[[str], None] | None = on_barcode

        self.grid_columnconfigure(1, weight=1)  # name entry stretches

        # --- barcode entry ---
        ctk.CTkLabel(self, text="Código:", font=theme.scaled_font(12)).grid(
            row=0, column=0, padx=(10, 2), pady=5
        )
        self._barcode_var = tk.StringVar()
        self._barcode_entry = ctk.CTkEntry(
            self,
            width=140,
            textvariable=self._barcode_var,
            placeholder_text="Escanear código...",
        )
        self._barcode_entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ew")
        self._barcode_entry.bind("<Return>", self._handle_barcode)

        # --- name search ---
        ctk.CTkLabel(self, text="Buscar:", font=theme.scaled_font(12)).grid(
            row=0, column=2, padx=(5, 2), pady=5
        )
        self._name_var = tk.StringVar()
        self._name_var.trace_add("write", self._handle_search)
        self._name_entry = ctk.CTkEntry(
            self,
            width=200,
            textvariable=self._name_var,
            placeholder_text="Nombre del producto...",
        )
        self._name_entry.grid(row=0, column=3, padx=(0, 5), pady=5, sticky="ew")

        # --- category filter ---
        ctk.CTkLabel(self, text="Categoría:", font=theme.scaled_font(12)).grid(
            row=0, column=4, padx=(5, 2), pady=5
        )
        self._category_options: dict[str, int | None] = {"Todas": None}
        if categories:
            for cat in categories:
                self._category_options[cat["name"]] = cat["id"]
        self._category_var = tk.StringVar(value="Todas")
        self._category_menu = ctk.CTkOptionMenu(
            self,
            values=list(self._category_options.keys()),
            variable=self._category_var,
            width=130,
            command=self._handle_category_changed,
        )
        self._category_menu.grid(row=0, column=5, padx=(0, 10), pady=5)

    # ---------------------------------------------------------------- public ---

    def set_categories(self, categories: list[dict[str, Any]]) -> None:
        """Refresh the category dropdown with *categories*."""
        current = self._category_var.get()
        self._category_options = {"Todas": None}
        for cat in categories:
            self._category_options[cat["name"]] = cat["id"]
        self._category_menu.configure(values=list(self._category_options.keys()))
        if current in self._category_options:
            self._category_var.set(current)
        else:
            self._category_var.set("Todas")

    def get_search_state(self) -> dict[str, Any]:
        """Return the current search state.

        Returns:
            Dict with ``query`` (str), ``category_id`` (int | None),
            and ``barcode`` (str).
        """
        return {
            "query": self._name_var.get().strip(),
            "category_id": self._category_options.get(
                self._category_var.get(), None
            ),
            "barcode": self._barcode_var.get().strip(),
        }

    def clear_barcode(self) -> None:
        """Clear the barcode entry field."""
        self._barcode_var.set("")

    def set_on_search(
        self, callback: Callable[[str, int | None], None]
    ) -> None:
        """Wire the search callback."""
        self._on_search = callback

    def set_on_barcode(self, callback: Callable[[str], None]) -> None:
        """Wire the barcode callback."""
        self._on_barcode = callback

    # --------------------------------------------------------------- private ---

    def _handle_search(self, *_args: Any) -> None:
        if self._on_search is not None:
            query = self._name_var.get().strip()
            cat_id = self._category_options.get(
                self._category_var.get(), None
            )
            self._on_search(query, cat_id)

    def _handle_category_changed(self, _value: str) -> None:
        if self._on_search is not None:
            query = self._name_var.get().strip()
            cat_id = self._category_options.get(
                self._category_var.get(), None
            )
            self._on_search(query, cat_id)

    def _handle_barcode(self, _event: tk.Event) -> None:
        barcode = self._barcode_var.get().strip()
        self._barcode_var.set("")
        if barcode and self._on_barcode is not None:
            self._on_barcode(barcode)
