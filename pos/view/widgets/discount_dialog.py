"""Discount dialog — modal for applying a percentage discount to the sale."""

import tkinter as tk

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class DiscountDialog(CenteredDialog):
    """Modal dialog to apply a percentage discount to the current sale.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    subtotal : int
        Current cart subtotal in whole ARS pesos.
    current_discount_pct : float
        Currently applied discount percentage (0-100).
    **kwargs :
        Forwarded to ``CenteredDialog``.
    """

    def __init__(
        self,
        master: tk.Widget,
        subtotal: int,
        current_discount_pct: float = 0.0,
        **kwargs,
    ) -> None:
        super().__init__(master, width=350, height=280, title="Aplicar descuento", **kwargs)

        self._subtotal = subtotal
        self._result: float | None = None

        # --- subtitle ---
        ctk.CTkLabel(
            self,
            text=f"Subtotal: ${subtotal:,}",
            font=theme.scaled_font(14),
            text_color="#a0a0a0",
        ).pack(pady=(20, 5))

        # --- percentage entry ---
        ctk.CTkLabel(
            self,
            text="Porcentaje de descuento (%):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(10, 5))

        self._pct_entry = ctk.CTkEntry(
            self,
            width=150,
            height=40,
            font=theme.scaled_font(18),
            placeholder_text="Ej: 10",
        )
        self._pct_entry.insert(0, str(int(current_discount_pct)) if current_discount_pct > 0 else "")
        self._pct_entry.pack(pady=(0, 10))
        self._pct_entry.focus_set()

        # --- preview label ---
        self._preview_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.scaled_font(13),
            text_color="#2ecc71",
        )
        self._preview_label.pack(pady=(0, 10))
        self._pct_entry.bind("<KeyRelease>", self._update_preview)

        # --- error label ---
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="red",
            font=theme.scaled_font(12),
        )
        self._error_label.pack()

        # --- buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 20))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=100,
            height=35,
            fg_color="#52525b",
            hover_color="#71717a",
            font=theme.scaled_font(13, weight="bold"),
            command=self._cancel,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Aplicar",
            width=100,
            height=35,
            fg_color="#0078d4",
            hover_color="#106ebe",
            font=theme.scaled_font(13, weight="bold"),
            command=self._confirm,
        ).pack(side="left", padx=5)

        self._pct_entry.bind("<Return>", lambda _e: self._confirm())
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    @property
    def result(self) -> float | None:
        """Discount percentage (0-100) on confirm, ``None`` on cancel."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _update_preview(self, _event: tk.Event | None = None) -> None:
        """Update the preview label as the user types."""
        raw = self._pct_entry.get().strip()
        self._error_label.configure(text="")

        if not raw:
            self._preview_label.configure(text="")
            return

        try:
            pct = float(raw)
        except ValueError:
            self._preview_label.configure(text="")
            return

        if pct < 0:
            self._preview_label.configure(text="El porcentaje no puede ser negativo", text_color="red")
            return
        if pct > 100:
            self._preview_label.configure(text="El porcentaje no puede superar 100%", text_color="red")
            return

        discount_amount = int(self._subtotal * pct / 100)
        final_total = self._subtotal - discount_amount
        self._preview_label.configure(
            text=f"Descuento: ${discount_amount:,} → Total: ${final_total:,}",
            text_color="#2ecc71",
        )

    def _confirm(self) -> None:
        """Validate and return the discount percentage."""
        raw = self._pct_entry.get().strip()

        if not raw:
            self._result = 0.0
            self.destroy()
            return

        try:
            pct = float(raw)
        except ValueError:
            self._error_label.configure(text="Ingrese un porcentaje válido")
            self._pct_entry.focus_set()
            return

        if pct < 0:
            self._error_label.configure(text="El porcentaje no puede ser negativo")
            self._pct_entry.focus_set()
            return

        if pct > 100:
            self._error_label.configure(text="El porcentaje no puede superar 100%")
            self._pct_entry.focus_set()
            return

        self._result = pct
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
