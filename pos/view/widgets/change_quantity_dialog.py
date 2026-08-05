"""Change quantity dialog — modal to edit the quantity of a cart item."""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class ChangeQuantityDialog(CenteredDialog):
    """Modal dialog to change the quantity of an item already in the cart.

    Supports float quantities for 'Kg' products and integer quantities for 'Unidad' products.
    """

    def __init__(
        self,
        master: tk.Widget,
        product_name: str,
        current_qty: float,
        unit_type: str = "Unidad",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=380,
            height=240,
            title="Modificar Cantidad",
            **kwargs,
        )

        self._product_name = product_name
        self._unit_type = unit_type
        self._result: float | None = None

        # --- Title ---
        ctk.CTkLabel(
            self,
            text=f"Modificar cantidad - {product_name}",
            font=theme.scaled_font(14, weight="bold"),
            wraplength=340,
            justify="center",
        ).pack(pady=(20, 5))

        # --- Label & Entry ---
        label_text = "Cantidad (Kg):" if unit_type == "Kg" else "Cantidad (Unidades):"
        ctk.CTkLabel(
            self,
            text=label_text,
            font=theme.scaled_font(13),
            text_color="#a0a0a0",
        ).pack(pady=(5, 5))

        self._qty_entry = ctk.CTkEntry(
            self,
            width=150,
            height=36,
            font=theme.scaled_font(16),
        )
        # Prefill and select all
        if unit_type == "Kg":
            qty_str = str(current_qty)
        else:
            qty_str = str(int(current_qty))
            
        self._qty_entry.insert(0, qty_str)
        self._qty_entry.pack(pady=(0, 10))
        self._qty_entry.focus_set()
        self._qty_entry.select_range(0, tk.END)

        # --- Error label ---
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#ef4444",
            font=theme.scaled_font(12),
        )
        self._error_label.pack()

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 15))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            height=35,
            fg_color="#52525b",
            hover_color="#71717a",
            font=theme.scaled_font(13, weight="bold"),
            command=self._cancel,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=100,
            height=35,
            fg_color="#0078d4",
            hover_color="#106ebe",
            font=theme.scaled_font(13, weight="bold"),
            command=self._confirm,
        ).pack(side="left", padx=8)

        self._qty_entry.bind("<Return>", lambda _e: self._confirm())
        self._qty_entry.bind("<Escape>", lambda _e: self._cancel())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self.update_idletasks()
        self._center_on_parent(master)

    @property
    def result(self) -> float | None:
        """The validated quantity float on confirm, or ``None`` on cancel."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _confirm(self) -> None:
        raw = self._qty_entry.get().strip().replace(",", ".")
        if not raw:
            self._error_label.configure(text="Ingrese un valor")
            self._qty_entry.focus_set()
            return

        try:
            val = float(raw)
        except ValueError:
            self._error_label.configure(text="Ingrese un número válido")
            self._qty_entry.focus_set()
            return

        if val <= 0:
            self._error_label.configure(text="El valor debe ser mayor a 0")
            self._qty_entry.focus_set()
            return

        if self._unit_type == "Unidad":
            # Must be integer
            if not val.is_integer():
                self._error_label.configure(text="Debe ser un número entero")
                self._qty_entry.focus_set()
                return
            val = float(int(val))

        self._result = val
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
