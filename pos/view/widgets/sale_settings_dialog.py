"""Sale settings dialog — global settings for payment surcharges."""

import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class SaleSettingsDialog(CenteredDialog):
    """Modal dialog to configure sales settings (surcharges)."""

    def __init__(self, master: tk.Widget, controller: Any, **kwargs) -> None:
        super().__init__(master, width=450, height=400, title="Ajustes de Venta", **kwargs)

        self._controller = controller
        self._applied = False

        # Load current settings
        result = controller.get_sale_settings()
        if result["success"]:
            settings = result["data"]
        else:
            settings = {"transfer_surcharge_pct": 0.0, "debit_surcharge_pct": 0.0, "credit_surcharge_pct": 0.0}

        # --- transfer surcharge ---
        ctk.CTkLabel(
            self,
            text="Recargo fijo por Transferencia (%):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(20, 5))

        self._transfer_entry = ctk.CTkEntry(self, width=150)
        self._transfer_entry.insert(0, str(settings.get("transfer_surcharge_pct", 0.0)))
        self._transfer_entry.pack(pady=(0, 10))

        # --- debit surcharge ---
        ctk.CTkLabel(
            self,
            text="Recargo fijo por Tarjeta de Débito (%):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(10, 5))

        self._debit_entry = ctk.CTkEntry(self, width=150)
        self._debit_entry.insert(0, str(settings.get("debit_surcharge_pct", 0.0)))
        self._debit_entry.pack(pady=(0, 10))

        # --- credit surcharge ---
        ctk.CTkLabel(
            self,
            text="Recargo fijo por Tarjeta de Crédito (%):",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(pady=(10, 5))

        self._credit_entry = ctk.CTkEntry(self, width=150)
        self._credit_entry.insert(0, str(settings.get("credit_surcharge_pct", 0.0)))
        self._credit_entry.pack(pady=(0, 20))

        # --- error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.pack()

        # --- buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 20))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=120,
            height=40,
            font=theme.scaled_font(14),
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=15)

        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=120,
            height=40,
            font=theme.scaled_font(14),
            command=self._confirm,
        ).pack(side="left", padx=15)

        self._transfer_entry.focus_set()
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    @property
    def applied(self) -> bool:
        return self._applied

    def _confirm(self) -> None:
        try:
            transfer_surcharge = float(self._transfer_entry.get().strip())
        except ValueError:
            self._error_label.configure(text="El recargo de transferencia debe ser válido")
            self._transfer_entry.focus_set()
            return
            
        if transfer_surcharge < 0:
            self._error_label.configure(text="El recargo no puede ser negativo")
            self._transfer_entry.focus_set()
            return

        try:
            debit_surcharge = float(self._debit_entry.get().strip())
        except ValueError:
            self._error_label.configure(text="El recargo de débito debe ser válido")
            self._debit_entry.focus_set()
            return
            
        if debit_surcharge < 0:
            self._error_label.configure(text="El recargo no puede ser negativo")
            self._debit_entry.focus_set()
            return

        try:
            credit_surcharge = float(self._credit_entry.get().strip())
        except ValueError:
            self._error_label.configure(text="El recargo de crédito debe ser válido")
            self._credit_entry.focus_set()
            return
            
        if credit_surcharge < 0:
            self._error_label.configure(text="El recargo no puede ser negativo")
            self._credit_entry.focus_set()
            return

        result = self._controller.apply_sale_settings(
            transfer_surcharge_pct=transfer_surcharge,
            debit_surcharge_pct=debit_surcharge,
            credit_surcharge_pct=credit_surcharge,
        )

        if result["success"]:
            self._applied = True
            messagebox.showinfo("Éxito", "Ajustes de venta guardados.")
            self.destroy()
        else:
            self._error_label.configure(text=result["error"])

    def _cancel(self) -> None:
        self._applied = False
        self.destroy()
