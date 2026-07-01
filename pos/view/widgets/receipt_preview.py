"""Receipt preview dialog — shows a sale summary after a successful transaction.

A ``CTkToplevel`` modal dialog that displays the sale ID, date, payment
method, line items, total, and change in a read-only format.  No editing
is permitted — this is an on-screen receipt only.
"""

import tkinter as tk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class ReceiptPreview(CenteredDialog):
    """Modal on-screen receipt displayed after a successful sale.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    sale_data : dict
        Controller response ``data`` field, expected to contain
        ``sale``, ``items``, and ``change``.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self, master: tk.Widget, sale_data: dict[str, Any], **kwargs
    ) -> None:
        super().__init__(master, width=500, height=560, title="Comprobante de venta", **kwargs)

        sale = sale_data.get("sale", {})
        items = sale_data.get("items", [])
        change = sale_data.get("change", 0)

        # --- header ---
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header_frame,
            text=f"Venta #{sale.get('id', '—')}",
            font=theme.scaled_font(22, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            header_frame,
            text=f"Fecha: {sale.get('created_at', '—')}",
            font=theme.scaled_font(13),
        ).pack(anchor="w", padx=10)

        ctk.CTkLabel(
            header_frame,
            text=f"Método de pago: {_format_method(sale.get('payment_method', '—'))}",
            font=theme.scaled_font(13),
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # --- separator ---
        ctk.CTkFrame(self, height=2, fg_color="#3b3b3b").pack(
            fill="x", padx=20, pady=5
        )

        # --- items ---
        # ========================================================
        # 1. ASEGURAR ELEMENTOS INFERIORES PRIMERO (De abajo hacia arriba)
        # ========================================================
        
        # Botón Cerrar (Fondo absoluto)
        ctk.CTkButton(
            self,
            text="Cerrar",
            width=120,
            command=self.destroy,
        ).pack(side="bottom", pady=(5, 20))

        # Totales (Se ancla arriba del botón cerrar)
        totals_frame = ctk.CTkFrame(self)
        totals_frame.pack(side="bottom", fill="x", padx=20, pady=(5, 10))

        sale_total = sale.get('total', 0)
        discount = sale.get('discount', 0)
        surcharge = sale.get('surcharge', 0)
        subtotal = sale_total + discount - surcharge

        if discount > 0 or surcharge > 0:
            ctk.CTkLabel(
                totals_frame,
                text=f"Subtotal:  ${subtotal:,}",
                font=theme.scaled_font(14),
                text_color="#a0a0a0",
            ).pack(anchor="e", padx=10, pady=(5, 0))

            if discount > 0:
                ctk.CTkLabel(
                    totals_frame,
                    text=f"Descuento:  -${discount:,}",
                    font=theme.scaled_font(14),
                    text_color="#2ecc71",
                ).pack(anchor="e", padx=10, pady=(2, 0))

            if surcharge > 0:
                ctk.CTkLabel(
                    totals_frame,
                    text=f"Recargo:  +${surcharge:,}",
                    font=theme.scaled_font(14),
                    text_color="#e74c3c",
                ).pack(anchor="e", padx=10, pady=(2, 0))

        ctk.CTkLabel(
            totals_frame,
            text=f"TOTAL:  ${sale_total:,}",
            font=theme.scaled_font(20, weight="bold"),
        ).pack(anchor="e", padx=10, pady=5)

        if change:
            ctk.CTkLabel(
                totals_frame,
                text=f"Vuelto:  ${change:,}",
                font=theme.scaled_font(16),
            ).pack(anchor="e", padx=10, pady=(0, 5))

        # Separador inferior (Se ancla arriba de los totales)
        ctk.CTkFrame(self, height=2, fg_color="#3b3b3b").pack(
            side="bottom", fill="x", padx=20, pady=5
        )

        # ========================================================
        # 2. ESPACIO CENTRAL FLEXIBLE (Tabla de productos)
        # ========================================================
        
        items_frame = ctk.CTkScrollableFrame(
            self, width=420, height=180, fg_color="transparent"
        )
        # ALERTA: expand=True y fill="both" evitan que se aplaste lo de abajo
        items_frame.pack(side="top", fill="both", expand=True, padx=20, pady=5)

        if items:
            for item in items:
                row = ctk.CTkFrame(items_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)
                row.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    row,
                    text=item.get("name", "—"),
                    font=theme.scaled_font(13),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkLabel(
                    row,
                    text=f"x{int(item.get('quantity', 1))}",
                    font=theme.scaled_font(13),
                    width=50,
                ).grid(row=0, column=1)

                ctk.CTkLabel(
                    row,
                    text=f"${item.get('subtotal', 0):,}",
                    font=theme.scaled_font(13),
                    width=80,
                    anchor="e",
                ).grid(row=0, column=2)
        else:
            ctk.CTkLabel(
                items_frame,
                text="Sin productos",
                font=theme.scaled_font(13),
            ).pack()


    # --------------------------------------------------------------- private ---


# --------------------------------------------------------------- helpers ---

def _format_method(method: str) -> str:
    """Translate internal payment method code to display label."""
    labels = {
        "cash": "Efectivo",
        "card": "Tarjeta",
        "transfer": "Transferencia",
    }
    return labels.get(method, method)
