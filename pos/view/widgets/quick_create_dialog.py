"""Quick-create dialog for unknown barcodes during a sale."""

import tkinter as tk
from typing import Any

import customtkinter as ctk


class QuickCreateDialog(ctk.CTkToplevel):
    """Modal dialog to register a new product when a barcode is not found.

    Pre-fills the scanned barcode (read-only) and prompts for the product
    name and sale price.  On confirm, returns a dict with the product data.
    On cancel, returns ``None``.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    barcode : str
        Pre-filled (read-only) barcode value.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(self, master: tk.Widget, barcode: str, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Nuevo producto")
        self.geometry("400x380")
        self.resizable(False, False)

        self.grab_set()
        self.transient(master)

        self._result: dict[str, Any] | None = None

        # --- barcode (visible, read-only) ---
        ctk.CTkLabel(self, text="Código de barras:").pack(pady=(20, 0))
        barcode_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=6)
        barcode_frame.pack(pady=(5, 15))
        ctk.CTkLabel(
            barcode_frame,
            text=f"  {barcode}  ",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#dce4ee",
        ).pack(pady=8, padx=12)

        # --- name ---
        ctk.CTkLabel(self, text="Nombre del producto *").pack()
        self._name_entry = ctk.CTkEntry(
            self, width=250, placeholder_text="Ej: Coca-Cola 2L"
        )
        self._name_entry.pack(pady=(5, 10))

        # --- sale price ---
        ctk.CTkLabel(self, text="Precio de venta ($) *").pack()
        self._price_entry = ctk.CTkEntry(
            self, width=250, placeholder_text="Ej: 2500"
        )
        self._price_entry.pack(pady=(5, 15))

        # --- error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
        )
        self._error_label.pack()

        # --- buttons ---
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

        self._name_entry.focus_set()

    @property
    def result(self) -> dict[str, Any] | None:
        """``{"name": str, "sale_price": int}`` on confirm, ``None`` on cancel."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _confirm(self) -> None:
        name = self._name_entry.get().strip()
        price_str = self._price_entry.get().strip()

        # --- validate name ---
        if not name:
            self._error_label.configure(text="El nombre es obligatorio")
            self._name_entry.focus_set()
            return

        # --- validate price ---
        try:
            price = int(price_str)
        except ValueError:
            self._error_label.configure(
                text="Ingrese un precio válido (número entero)"
            )
            self._price_entry.focus_set()
            return

        if price < 0:
            self._error_label.configure(text="El precio no puede ser negativo")
            self._price_entry.focus_set()
            return

        self._error_label.configure(text="")
        self._result = {"name": name, "sale_price": price}
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
