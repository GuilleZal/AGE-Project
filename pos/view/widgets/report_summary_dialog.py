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

    def __init__(self, master: tk.Widget, report_data: dict[str, Any], role: str = "", **kwargs) -> None:
        dialog_width = 620 if role in ("gerente", "admin") else 480
        dialog_height = 540 if role in ("gerente", "admin") else 320
        super().__init__(
            master,
            width=dialog_width,
            height=dialog_height,
            title="Resumen de Egresos e Ingresos",
            resizable=(False, False),
            **kwargs
        )
        self._report_data = report_data
        self._role = role

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        if self._role in ("gerente", "admin"):
            self._build_gerente_ui()
        else:
            self._build_standard_ui()

    def _build_gerente_ui(self) -> None:
        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Action buttons frame (pinned to the bottom)
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(10, 0))

        # Export PDF button
        ctk.CTkButton(
            btn_frame,
            text="Exportar (PDF)",
            height=35,
            fg_color="#a83232",
            hover_color="#8c2727",
            command=self._export_summary_pdf,
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Close button
        ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            height=35,
            fg_color="#3b3b3b",
            command=self.destroy,
        ).pack(side="right", padx=(5, 0))

        # Scrollable content frame (fills the top area)
        scroll_frame = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        # Title
        ctk.CTkLabel(
            scroll_frame,
            text="Resumen de Ingresos y Egresos",
            font=theme.scaled_font(18, weight="bold"),
        ).pack(anchor="w", pady=(0, 2))

        # Subtitle with dates
        period = self._report_data.get("period") or {}
        start_display = period.get("start", "").split(" ")[0] if period.get("start") else ""
        end_display = period.get("end", "").split(" ")[0] if period.get("end") else ""

        ctk.CTkLabel(
            scroll_frame,
            text=f"Período: {start_display} hasta {end_display}",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).pack(anchor="w", pady=(0, 15))

        # Metrics frame
        bg_color = "#1e1e1e" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0"
        metrics_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=8)
        metrics_frame.pack(fill="both", expand=True, pady=10, ipady=10)

        sales = self._report_data.get("sales") or {}
        total_sales = sales.get("total", 0)

        profit_data = self._report_data.get("profit") or {}
        cost = profit_data.get("cost", 0)

        expenses = self._report_data.get("expenses") or {}
        purchases = expenses.get("purchases", 0)
        operating = expenses.get("operating_expenses", 0)
        returns_total = expenses.get("returns_total", 0)
        returns_broken = expenses.get("returns_broken", 0)
        returns_expired = expenses.get("returns_expired", 0)
        returns_good_condition = expenses.get("returns_good_condition", 0)

        # Calculate values
        ganancia_bruta = total_sales - cost
        ganancia_neta = ganancia_bruta - returns_total

        # Grid configuration inside metrics frame
        metrics_frame.grid_columnconfigure(0, weight=1)
        metrics_frame.grid_columnconfigure(1, weight=1)

        row_idx = 0

        # Section 1: Ingresos
        ctk.CTkLabel(
            metrics_frame,
            text="1: Ingresos",
            font=theme.scaled_font(14, weight="bold"),
        ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 2))
        row_idx += 1

        ctk.CTkLabel(
            metrics_frame,
            text="Ventas Totales:",
            font=theme.scaled_font(13),
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=2)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(total_sales):,.2f}",
            font=theme.scaled_font(13),
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=2)
        row_idx += 1

        # Section 2: Costo de Mercadería Vendida
        ctk.CTkLabel(
            metrics_frame,
            text="2: Costo de Mercadería Vendida",
            font=theme.scaled_font(14, weight="bold"),
        ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 2))
        row_idx += 1

        ctk.CTkLabel(
            metrics_frame,
            text="(-) Costo de Mercadería Vendida:",
            font=theme.scaled_font(13),
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=2)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(cost):,.2f}",
            font=theme.scaled_font(13),
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=2)
        row_idx += 1

        # Separator line
        ctk.CTkLabel(
            metrics_frame,
            text="--------------------------------------------------------------------------------",
            font=theme.scaled_font(11),
            text_color="#555555",
        ).grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=15, pady=2)
        row_idx += 1

        # Ganancia Bruta
        bruta_color = "#4CAF50" if ganancia_bruta >= 0 else "#f44336"
        ctk.CTkLabel(
            metrics_frame,
            text="(=) Ganancia Bruta:",
            font=theme.scaled_font(13, weight="bold"),
        ).grid(row=row_idx, column=0, sticky="w", padx=15, pady=2)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${int(float(ganancia_bruta)):,}",
            font=theme.scaled_font(13, weight="bold"),
            text_color=bruta_color,
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=2)
        row_idx += 1

        # Section 3: Perdidas
        ctk.CTkLabel(
            metrics_frame,
            text="3: Perdidas",
            font=theme.scaled_font(14, weight="bold"),
        ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 2))
        row_idx += 1

        # Devoluciones
        ctk.CTkLabel(
            metrics_frame,
            text="(-) Devoluciones Totales:",
            font=theme.scaled_font(13, weight="bold"),
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=2)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(returns_total):,.2f}",
            font=theme.scaled_font(13, weight="bold"),
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=2)
        row_idx += 1

        # Sub-item 1: Rotos
        ctk.CTkLabel(
            metrics_frame,
            text="   Rotos:",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=1)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(returns_broken):,.2f}",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=1)
        row_idx += 1

        # Sub-item 2: Vencidos
        ctk.CTkLabel(
            metrics_frame,
            text="   Vencidos:",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=1)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(returns_expired):,.2f}",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=1)
        row_idx += 1

        # Sub-item 3: En buen estado
        ctk.CTkLabel(
            metrics_frame,
            text="   En buen estado:",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=0, sticky="w", padx=25, pady=1)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${float(returns_good_condition):,.2f}",
            font=theme.scaled_font(12),
            text_color="#888888",
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=1)
        row_idx += 1

        # Separator line
        ctk.CTkLabel(
            metrics_frame,
            text="--------------------------------------------------------------------------------",
            font=theme.scaled_font(11),
            text_color="#555555",
        ).grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=15, pady=2)
        row_idx += 1

        # Ganancia Neta
        neta_color = "#4CAF50" if ganancia_neta >= 0 else "#f44336"
        ctk.CTkLabel(
            metrics_frame,
            text="(=) Ganancia Neta:",
            font=theme.scaled_font(14, weight="bold"),
        ).grid(row=row_idx, column=0, sticky="w", padx=15, pady=4)

        ctk.CTkLabel(
            metrics_frame,
            text=f"${int(float(ganancia_neta)):,}",
            font=theme.scaled_font(14, weight="bold"),
            text_color=neta_color,
        ).grid(row=row_idx, column=1, sticky="e", padx=15, pady=4)
        row_idx += 1

    def _export_summary_excel(self) -> None:
        """Export the summary numbers to an Excel file using the controller."""
        period = self._report_data.get("period") or {}
        start_display = period.get("start", "").split(" ")[0] if period.get("start") else ""
        end_display = period.get("end", "").split(" ")[0] if period.get("end") else ""

        filepath = filedialog.asksaveasfilename(
            title="Exportar Resumen a Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"Resumen_Reporte_{start_display}_a_{end_display}" if start_display else "Resumen_Reporte",
            parent=self,
        )
        if not filepath:
            return

        sales = self._report_data.get("sales") or {}
        total_sales = sales.get("total", 0)

        profit_data = self._report_data.get("profit") or {}
        cost = profit_data.get("cost", 0)

        expenses = self._report_data.get("expenses") or {}
        purchases = expenses.get("purchases", 0)
        operating = expenses.get("operating_expenses", 0)
        returns_total = expenses.get("returns_total", 0)
        returns_broken = expenses.get("returns_broken", 0)
        returns_expired = expenses.get("returns_expired", 0)
        returns_good_condition = expenses.get("returns_good_condition", 0)

        ganancia_bruta = total_sales - cost
        ganancia_neta = ganancia_bruta - returns_total

        export_data = [
            {"Concepto": "Ventas Totales", "Monto": f"${total_sales:,}"},
            {"Concepto": "(-) Costo de Mercadería Vendida", "Monto": f"${cost:,}"},
            {"Concepto": "Ganancia Bruta", "Monto": f"${int(float(ganancia_bruta)):,}"},
            {"Concepto": "(-) Devoluciones Totales", "Monto": f"${returns_total:,}"},
            {"Concepto": "   Rotos", "Monto": f"${returns_broken:,}"},
            {"Concepto": "   Vencidos", "Monto": f"${returns_expired:,}"},
            {"Concepto": "   En buen estado", "Monto": f"${returns_good_condition:,}"},
            {"Concepto": "Ganancia Neta", "Monto": f"${int(float(ganancia_neta)):,}"},
        ]

        controller = getattr(self.master, "_controller", None)
        if controller is not None:
            res = controller.export_to_excel(export_data, filepath, start_display, end_display, title="Resumen de Ingresos y Egresos")
            if res["success"]:
                messagebox.showinfo(
                    "Exportación exitosa",
                    f"Se exportó el resumen a:\n{res['data']}",
                    parent=self,
                )
            else:
                messagebox.showerror(
                    "Error de exportación",
                    f"No se pudo exportar:\n{res['error']}",
                    parent=self,
                )
        else:
            messagebox.showerror(
                "Error",
                "El controlador no está disponible.",
                parent=self,
            )

    def _export_summary_pdf(self) -> None:
        """Export the summary numbers to a PDF file using the controller."""
        period = self._report_data.get("period") or {}
        start_display = period.get("start", "").split(" ")[0] if period.get("start") else ""
        end_display = period.get("end", "").split(" ")[0] if period.get("end") else ""

        filepath = filedialog.asksaveasfilename(
            title="Exportar Resumen a PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Resumen_Reporte_{start_display}_a_{end_display}" if start_display else "Resumen_Reporte",
            parent=self,
        )
        if not filepath:
            return

        sales = self._report_data.get("sales") or {}
        total_sales = sales.get("total", 0)

        profit_data = self._report_data.get("profit") or {}
        cost = profit_data.get("cost", 0)

        expenses = self._report_data.get("expenses") or {}
        purchases = expenses.get("purchases", 0)
        operating = expenses.get("operating_expenses", 0)
        returns_total = expenses.get("returns_total", 0)
        returns_broken = expenses.get("returns_broken", 0)
        returns_expired = expenses.get("returns_expired", 0)
        returns_good_condition = expenses.get("returns_good_condition", 0)

        ganancia_bruta = total_sales - cost
        ganancia_neta = ganancia_bruta - returns_total

        export_data = [
            {"Concepto": "Ventas Totales", "Monto": f"${total_sales:,}"},
            {"Concepto": "(-) Costo de Mercadería Vendida", "Monto": f"${cost:,}"},
            {"Concepto": "Ganancia Bruta", "Monto": f"${int(float(ganancia_bruta)):,}"},
            {"Concepto": "(-) Devoluciones Totales", "Monto": f"${returns_total:,}"},
            {"Concepto": "   Rotos", "Monto": f"${returns_broken:,}"},
            {"Concepto": "   Vencidos", "Monto": f"${returns_expired:,}"},
            {"Concepto": "   En buen estado", "Monto": f"${returns_good_condition:,}"},
            {"Concepto": "Ganancia Neta", "Monto": f"${int(float(ganancia_neta)):,}"},
        ]

        controller = getattr(self.master, "_controller", None)
        if controller is not None:
            res = controller.export_to_pdf(export_data, filepath, start_display, end_display, title="Resumen de Ingresos y Egresos")
            if res["success"]:
                messagebox.showinfo(
                    "Exportación exitosa",
                    f"Se exportó el resumen a:\n{res['data']}",
                    parent=self,
                )
            else:
                messagebox.showerror(
                    "Error de exportación",
                    f"No se pudo exportar:\n{res['error']}",
                    parent=self,
                )
        else:
            messagebox.showerror(
                "Error",
                "El controlador no está disponible.",
                parent=self,
            )

    def _build_standard_ui(self) -> None:
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
