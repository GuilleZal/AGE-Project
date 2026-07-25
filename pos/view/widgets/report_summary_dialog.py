"""Modal dialog displaying the summary of income and expenses with export capability."""

import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any
import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme
from pos.service.report_service import ReportService


class ReportSummaryDialog(CenteredDialog):
    """Modal dialog displaying the summary of income and expenses."""

    def __init__(self, master: tk.Widget, report_data: dict[str, Any], **kwargs) -> None:
        super().__init__(
            master,
            width=420,
            height=320,
            title="Resumen de Egresos e Ingresos",
            resizable=(False, False),
            **kwargs
        )
        self._report_data = report_data

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(
            container,
            text="Resumen de Egresos y Pérdidas",
            font=theme.scaled_font(16, weight="bold"),
        ).pack(anchor="w", pady=(0, 15))

        # Metrics frame
        bg_color = "#1e1e1e" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        metrics_frame = ctk.CTkFrame(container, fg_color=bg_color, corner_radius=8)
        metrics_frame.pack(fill="x", pady=10, ipady=10)

        expenses = self._report_data.get("expenses") or {}
        purchases = expenses.get("purchases", 0)
        shrinkage = expenses.get("shrinkage", 0)
        operating = expenses.get("operating_expenses", 0)
        net_profit = expenses.get("net_profit", 0)

        summary_items = [
            ("Proveedores:", f"${purchases:,}", "#888"),
            ("Pérdidas:", f"${shrinkage:,}", "#888"),
            ("Gastos:", f"${operating:,}", "#888"),
            ("Ganancia Neta:", f"${int(float(net_profit)):,}", "#4CAF50" if net_profit >= 0 else "#f44336"),
        ]

        # Use grid layout for keys and values inside the metrics frame
        metrics_frame.grid_columnconfigure(0, weight=1)
        metrics_frame.grid_columnconfigure(1, weight=1)

        for idx, (label, val_str, color) in enumerate(summary_items):
            font_size = 15 if idx == 3 else 13
            font_weight = "bold" if idx == 3 else "normal"

            # Label
            ctk.CTkLabel(
                metrics_frame,
                text=label,
                font=theme.scaled_font(font_size, weight=font_weight),
            ).grid(row=idx, column=0, sticky="w", padx=15, pady=6)

            # Value
            ctk.CTkLabel(
                metrics_frame,
                text=val_str,
                font=theme.scaled_font(font_size, weight=font_weight),
                text_color=color,
            ).grid(row=idx, column=1, sticky="e", padx=15, pady=6)

        # Action buttons
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(15, 0))

        # Export button
        ctk.CTkButton(
            btn_frame,
            text="Exportar Resumen (CSV)",
            height=35,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._export_summary,
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Close button
        ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            height=35,
            fg_color="#3b3b3b",
            command=self.destroy,
        ).pack(side="right", padx=(5, 0))

    def _export_summary(self) -> None:
        """Export the summary numbers to a CSV file."""
        filepath = filedialog.asksaveasfilename(
            title="Exportar Resumen de Egresos e Ingresos",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        expenses = self._report_data.get("expenses") or {}
        purchases = expenses.get("purchases", 0)
        shrinkage = expenses.get("shrinkage", 0)
        operating = expenses.get("operating_expenses", 0)
        net_profit = expenses.get("net_profit", 0)

        # Format rows for export
        export_data = [
            {"Concepto": "Compras a Proveedores", "Monto": f"${purchases:,}"},
            {"Concepto": "Pérdidas", "Monto": f"${shrinkage:,}"},
            {"Concepto": "Gastos Operativos", "Monto": f"${operating:,}"},
            {"Concepto": "Ganancia Neta", "Monto": f"${int(float(net_profit)):,}"},
        ]

        try:
            ReportService.export_csv(export_data, filepath)
            messagebox.showinfo("Éxito", f"Resumen exportado exitosamente a:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el archivo:\n{e}")
