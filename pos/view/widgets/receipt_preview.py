"""Receipt preview dialog — shows a sale summary after a successful transaction.

A ``CTkToplevel`` modal dialog that displays the sale ID, date, payment
method, line items, total, and change in a read-only format.  No editing
is permitted — this is an on-screen receipt only.
"""

import tkinter as tk
from typing import Any

import customtkinter as ctk


class ReceiptPreview(ctk.CTkToplevel):
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
        super().__init__(master, **kwargs)
        self.title("Comprobante de venta")
        self.resizable(False, False)

        self.grab_set()
        self.transient(master)

        sale = sale_data.get("sale", {})
        items = sale_data.get("items", [])
        change = sale_data.get("change", 0)

        # --- header ---
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            header_frame,
            text=f"Venta #{sale.get('id', '—')}",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(5, 0))

        ctk.CTkLabel(
            header_frame,
            text=f"Fecha: {sale.get('created_at', '—')}",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=10)

        ctk.CTkLabel(
            header_frame,
            text=f"Método de pago: {_format_method(sale.get('payment_method', '—'))}",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=10, pady=(0, 5))

        # --- separator ---
        ctk.CTkFrame(self, height=2, fg_color="#3b3b3b").pack(
            fill="x", padx=20, pady=5
        )

        # --- items ---
        items_frame = ctk.CTkScrollableFrame(
            self, width=420, height=180, fg_color="transparent"
        )
        items_frame.pack(fill="x", padx=20, pady=5)

        if items:
            for item in items:
                row = ctk.CTkFrame(items_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)
                row.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    row,
                    text=item.get("name", "—"),
                    font=ctk.CTkFont(size=13),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkLabel(
                    row,
                    text=f"x{item.get('quantity', 1)}",
                    font=ctk.CTkFont(size=13),
                    width=50,
                ).grid(row=0, column=1)

                ctk.CTkLabel(
                    row,
                    text=f"${item.get('subtotal', 0):,}",
                    font=ctk.CTkFont(size=13),
                    width=80,
                    anchor="e",
                ).grid(row=0, column=2)
        else:
            ctk.CTkLabel(
                items_frame,
                text="Sin productos",
                font=ctk.CTkFont(size=13),
            ).pack()

        # --- separator ---
        ctk.CTkFrame(self, height=2, fg_color="#3b3b3b").pack(
            fill="x", padx=20, pady=5
        )

        # --- totals ---
        totals_frame = ctk.CTkFrame(self)
        totals_frame.pack(fill="x", padx=20, pady=(5, 10))

        ctk.CTkLabel(
            totals_frame,
            text=f"TOTAL:  ${sale.get('total', 0):,}",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="e", padx=10, pady=5)

        if change:
            ctk.CTkLabel(
                totals_frame,
                text=f"Vuelto:  ${change:,}",
                font=ctk.CTkFont(size=16),
            ).pack(anchor="e", padx=10, pady=(0, 5))

        # --- close button ---
        ctk.CTkButton(
            self,
            text="Cerrar",
            width=120,
            command=self.destroy,
        ).pack(pady=(5, 20))

        # --- calculate geometry: center relative to master ---
        self.update_idletasks()
        w = max(500, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        self.minsize(w, h)
        self._center_on_master(master, w, h)

    # --------------------------------------------------------------- private ---

    def _center_on_master(
        self, master: tk.Widget, width: int, height: int
    ) -> None:
        """Position the dialog centered relative to *master*."""
        mw, mh = master.winfo_width(), master.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        x = mx + (mw - width) // 2
        y = my + (mh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")


# --------------------------------------------------------------- helpers ---

def _format_method(method: str) -> str:
    """Translate internal payment method code to display label."""
    labels = {
        "cash": "Efectivo",
        "card": "Tarjeta",
        "transfer": "Transferencia",
    }
    return labels.get(method, method)
