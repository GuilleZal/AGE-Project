"""Cart treeview widget — displays the current sale cart in a ttk.Treeview
styled to match the CustomTkinter dark theme.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


class CartTreeview(ctk.CTkFrame):
    """A styled ttk.Treeview displaying cart items.

    Columns: Producto, Cantidad, Precio Unit., Subtotal.

    Parameters
    ----------
    master : tk.Widget
        Parent widget.
    on_delete : Callable[[int], None] | None
        Called when the user presses Delete on a selected row, receiving
        the ``product_id`` stored in the hidden first tag.
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    COLUMNS = ("producto", "cantidad", "precio_unit", "subtotal")
    COLUMN_LABELS = {
        "producto": "Producto",
        "cantidad": "Cantidad",
        "precio_unit": "Precio Unit.",
        "subtotal": "Subtotal",
    }

    def __init__(
        self,
        master: tk.Widget,
        on_delete: Callable[[int], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_delete: Callable[[int], None] | None = on_delete

        # --- dark style for ttk widgets inside a CTk frame ---
        self._style = ttk.Style(self)
        self._configure_style()

        # --- treeview ---
        self._tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COLUMN_LABELS[col])

        self._tree.column("producto", width=280, stretch=True)
        self._tree.column("cantidad", width=80, anchor="center")
        self._tree.column("precio_unit", width=100, anchor="e")
        self._tree.column("subtotal", width=120, anchor="e")

        # Bind resize event to automatically make columns responsive
        self._tree.bind("<Configure>", self._on_resize)

        # Add column sorting
        add_sorting_to_treeview(
            self._tree,
            list(self.COLUMNS),
            column_types={
                "producto": "str",
                "cantidad": "int",
                "precio_unit": "int",
                "subtotal": "int",
            }
        )

        # --- scrollbar ---
        self._scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=self._scrollbar.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- key bindings ---
        self._tree.bind("<Delete>", self._on_delete_key)

    # ---------------------------------------------------------------- public ---

    def update_cart(self, items: list[dict]) -> None:
        """Refresh the treeview with current cart *items*.

        Each item dict should have keys: ``product_id``, ``name``,
        ``quantity``, ``unit_price``, ``subtotal``.
        """
        for child in self._tree.get_children():
            self._tree.delete(child)

        for item in items:
            self._tree.insert(
                "",
                "end",
                iid=str(item["product_id"]),
                values=(
                    item["name"],
                    int(item["quantity"]),
                    f"${item['unit_price']:,}",
                    f"${item['subtotal']:,}",
                ),
                tags=(str(item["product_id"]),),
            )

    def get_selected_item(self) -> dict[str, Any] | None:
        """Return the currently selected row data or ``None``.

        Returns:
            Dict with keys ``product_id``, ``name``, ``quantity``,
            ``unit_price``, ``subtotal``, or ``None``.
        """
        sel = self._tree.selection()
        if not sel:
            return None
        values = self._tree.item(sel[0], "values")
        tags = self._tree.item(sel[0], "tags")
        if not values or not tags:
            return None
        return {
            "product_id": int(tags[0]),
            "name": values[0],
            "quantity": float(values[1]),
            "unit_price": self._parse_currency(values[2]),
            "subtotal": self._parse_currency(values[3]),
        }

    def set_on_delete(self, callback: Callable[[int], None]) -> None:
        """Set or replace the delete callback."""
        self._on_delete = callback

    # --------------------------------------------------------------- private ---

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

    def _on_delete_key(self, _event: tk.Event) -> None:
        """Handle Delete key press on a selected row."""
        sel = self._tree.selection()
        if not sel:
            return
        tags = self._tree.item(sel[0], "tags")
        if tags and self._on_delete is not None:
            self._on_delete(int(tags[0]))

    def _on_resize(self, event: tk.Event) -> None:
        """Dynamically resize treeview columns proportionally to fit window size."""
        total_width = event.width
        if total_width <= 100:
            return

        # Deduct scrollbar width (approx 20px)
        net_width = total_width - 20
        if net_width <= 100:
            return

        # Proportions: producto (48%), cantidad (14%), precio_unit (17%), subtotal (21%)
        w_prod = int(net_width * 0.48)
        w_qty = int(net_width * 0.14)
        w_price = int(net_width * 0.17)
        w_sub = int(net_width * 0.21)

        self._tree.column("producto", width=w_prod, minwidth=150)
        self._tree.column("cantidad", width=w_qty, minwidth=60)
        self._tree.column("precio_unit", width=w_price, minwidth=80)
        self._tree.column("subtotal", width=w_sub, minwidth=90)

    @staticmethod
    def _parse_currency(val: str) -> int:
        """Parse a formatted currency string like ``"$1,500"`` back to int."""
        return int(val.replace("$", "").replace(",", "").strip() or "0")
