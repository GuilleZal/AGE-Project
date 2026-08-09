"""Stock valuation dialog — displays total cost, total sales, and gross profit of positive stock."""

import tkinter as tk
import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class StockValuationDialog(CenteredDialog):
    """Modal dialog displaying total cost, total sales, and gross profit of the current stock.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    total_cost : float
        Sum of cost_price * stock for positive stock products.
    total_sales : float
        Sum of sale_price * stock for positive stock products.
    gross_profit : float
        total_sales - total_cost.
    **kwargs :
        Forwarded to ``CenteredDialog``.
    """

    def __init__(
        self,
        master: tk.Widget,
        total_cost: float,
        total_sales: float,
        gross_profit: float,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=420,
            height=280,
            title="Valorización de Inventario",
            **kwargs,
        )

        # Title
        self._title_label = ctk.CTkLabel(
            self,
            text="Valorización de Stock Actual",
            font=theme.scaled_font(16, weight="bold"),
            anchor="center",
        )
        self._title_label.pack(pady=(20, 15), padx=20, fill="x")

        # Container for the valuation card
        self._card_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._card_frame.pack(pady=10, padx=25, fill="both", expand=True)

        self._card_frame.grid_columnconfigure(0, weight=1)
        self._card_frame.grid_columnconfigure(1, weight=1)

        # 1. Total Cost
        self._lbl_cost_desc = ctk.CTkLabel(
            self._card_frame,
            text="Costo Total de Inventario:",
            font=theme.scaled_font(13, weight="normal"),
            anchor="w",
        )
        self._lbl_cost_desc.grid(row=0, column=0, sticky="w", padx=10, pady=8)

        self._lbl_cost_val = ctk.CTkLabel(
            self._card_frame,
            text=f"${total_cost:,.2f}",
            font=theme.scaled_font(13, weight="bold"),
            anchor="e",
        )
        self._lbl_cost_val.grid(row=0, column=1, sticky="e", padx=10, pady=8)

        # 2. Total Sales
        self._lbl_sales_desc = ctk.CTkLabel(
            self._card_frame,
            text="Venta Total Esperada:",
            font=theme.scaled_font(13, weight="normal"),
            anchor="w",
        )
        self._lbl_sales_desc.grid(row=1, column=0, sticky="w", padx=10, pady=8)

        self._lbl_sales_val = ctk.CTkLabel(
            self._card_frame,
            text=f"${total_sales:,.2f}",
            font=theme.scaled_font(13, weight="bold"),
            anchor="e",
        )
        self._lbl_sales_val.grid(row=1, column=1, sticky="e", padx=10, pady=8)

        # Separator line
        self._separator = ctk.CTkLabel(
            self._card_frame,
            text="------------------------------------------------------------------",
            font=theme.scaled_font(10),
            text_color="#555555",
            anchor="center",
        )
        self._separator.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=4)

        # 3. Estimated Gross Profit
        profit_color = "#2ecc71" if gross_profit >= 0 else "#e74c3c"
        self._lbl_profit_desc = ctk.CTkLabel(
            self._card_frame,
            text="Ganancia Bruta Estimada:",
            font=theme.scaled_font(14, weight="bold"),
            anchor="w",
        )
        self._lbl_profit_desc.grid(row=3, column=0, sticky="w", padx=10, pady=8)

        self._lbl_profit_val = ctk.CTkLabel(
            self._card_frame,
            text=f"${gross_profit:,.2f}",
            font=theme.scaled_font(14, weight="bold"),
            text_color=profit_color,
            anchor="e",
        )
        self._lbl_profit_val.grid(row=3, column=1, sticky="e", padx=10, pady=8)

        # Close button
        self._close_btn = ctk.CTkButton(
            self,
            text="Cerrar",
            width=120,
            command=self.destroy,
        )
        self._close_btn.pack(pady=(15, 20))

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
