"""Percentage calculator dialog for the manager."""

import tkinter as tk

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class PercentageCalculatorDialog(CenteredDialog):
    """Modal dialog to calculate a percentage of a given amount."""

    def __init__(
        self,
        master: tk.Widget,
        **kwargs,
    ) -> None:
        super().__init__(master, width=350, height=350, title="Calculadora de Porcentaje", **kwargs)

        # --- amount entry ---
        ctk.CTkLabel(
            self,
            text="Monto base ($):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(20, 5))

        self._amount_entry = ctk.CTkEntry(
            self,
            width=200,
            height=40,
            font=theme.scaled_font(18),
            placeholder_text="Ej: 1500",
        )
        self._amount_entry.pack(pady=(0, 10))
        self._amount_entry.focus_set()
        
        # --- percentage entry ---
        ctk.CTkLabel(
            self,
            text="Porcentaje (%):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(10, 5))

        self._pct_entry = ctk.CTkEntry(
            self,
            width=200,
            height=40,
            font=theme.scaled_font(18),
            placeholder_text="Ej: 21",
        )
        self._pct_entry.pack(pady=(0, 10))

        # --- preview label ---
        self._preview_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.scaled_font(14, weight="bold"),
            text_color="#2ecc71",
        )
        self._preview_label.pack(pady=(10, 10))
        
        self._amount_entry.bind("<KeyRelease>", self._update_preview)
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
        btn_frame.pack(pady=(10, 20))

        ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            width=120,
            height=35,
            fg_color="#52525b",
            hover_color="#71717a",
            font=theme.scaled_font(13, weight="bold"),
            command=self.destroy,
        ).pack(side="top", padx=5)

        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    def _update_preview(self, _event: tk.Event | None = None) -> None:
        """Update the result label as the user types."""
        amount_raw = self._amount_entry.get().strip()
        pct_raw = self._pct_entry.get().strip()
        self._error_label.configure(text="")

        if not amount_raw or not pct_raw:
            self._preview_label.configure(text="")
            return

        try:
            amount = float(amount_raw)
            pct = float(pct_raw)
        except ValueError:
            self._preview_label.configure(text="")
            return

        if pct < 0:
            self._preview_label.configure(text="")
            self._error_label.configure(text="El porcentaje no puede ser negativo")
            return

        if pct >= 100:
            self._preview_label.configure(text="")
            self._error_label.configure(text="El porcentaje debe ser menor a 100%")
            return

        final_total = amount / (1 - pct / 100)
        result = final_total - amount
        self._preview_label.configure(
            text=f"Ganancia: ${result:,.2f}\nTotal con ganancia: ${final_total:,.2f}",
            text_color="#2ecc71",
        )
