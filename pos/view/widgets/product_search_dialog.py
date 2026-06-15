"""Product search dialog — lets the user pick from multiple search results."""

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from pos.model.product import Product


class ProductSearchDialog(ctk.CTkToplevel):
    """Modal dialog showing search results for the user to select from.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    products : list[Product]
        Products to display in the selection list.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self, master: tk.Widget, products: list[Product], **kwargs
    ) -> None:
        super().__init__(master, **kwargs)
        self.title("Seleccionar producto")
        self.geometry("500x400")
        self.resizable(False, False)

        self.grab_set()
        self.transient(master)

        self._result: Product | None = None
        self._products = products

        columns = ("codigo", "nombre", "precio")
        self._tree = ttk.Treeview(
            self, columns=columns, show="headings", height=12
        )
        self._tree.heading("codigo", text="Código")
        self._tree.heading("nombre", text="Nombre")
        self._tree.heading("precio", text="Precio")
        self._tree.column("codigo", width=120, anchor="w")
        self._tree.column("nombre", width=250, anchor="w")
        self._tree.column("precio", width=100, anchor="e")
        self._tree.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        for p in products:
            self._tree.insert(
                "",
                "end",
                values=(p.barcode or "—", p.name, f"${p.sale_price:,}"),
            )

        self._tree.bind("<Double-1>", self._on_select)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(5, 10))

        ctk.CTkButton(
            btn_frame,
            text="Seleccionar",
            width=120,
            command=self._on_select,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)

    @property
    def result(self) -> Product | None:
        """The selected ``Product``, or ``None`` if cancelled."""
        return self._result

    def _on_select(self, _event: tk.Event | None = None) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        self._result = self._products[idx]
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
