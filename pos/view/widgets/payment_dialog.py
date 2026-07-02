"""Payment method selection and cash-tendered dialog."""

import tkinter as tk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class PaymentDialog(CenteredDialog):
    """Modal dialog for payment method selection and cash handling.

    Shows a "Monto recibido" field only when the payment method is cash.
    Calculates and displays change (vuelto) in real time.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    total : int
        Cart total in whole ARS pesos.
    payment_method : str
        Default payment method (``"cash"``, ``"card"``, ``"transfer"``,
        ``"mixed"``).  Defaults to ``"cash"``.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    METHODS: list[tuple[str, str]] = [
        ("Efectivo", "cash"),
        ("Tarjeta", "card"),
        ("Transferencia", "transfer"),
    ]

    def __init__(
        self,
        master: tk.Widget,
        total: int,
        payment_method: str = "cash",
        **kwargs,
    ) -> None:
        super().__init__(master, width=420, height=380, title="Pago", **kwargs)

        self._total = total
        self._result: dict[str, Any] | None = None

        # --- total display ---
        ctk.CTkLabel(
            self,
            text=f"Total a pagar: ${total:,}",
            font=theme.scaled_font(20, weight="bold"),
        ).pack(pady=(20, 15))

        # --- payment method radio buttons ---
        self._method_var = tk.StringVar(value=payment_method)
        radio_frame = ctk.CTkFrame(self)
        radio_frame.pack(pady=(0, 10))

        ctk.CTkLabel(radio_frame, text="Método de pago:").pack(
            anchor="w", padx=10, pady=(5, 0)
        )

        for label, value in self.METHODS:
            ctk.CTkRadioButton(
                radio_frame,
                text=label,
                variable=self._method_var,
                value=value,
                command=self._on_method_changed,
            ).pack(anchor="w", padx=20, pady=2)

        # --- cash received (shown only for cash) ---
        self._cash_frame = ctk.CTkFrame(self)

        ctk.CTkLabel(self._cash_frame, text="Monto recibido ($):").pack(
            pady=(5, 0)
        )
        self._received_entry = ctk.CTkEntry(
            self._cash_frame,
            width=200,
            placeholder_text="Ej: 5000",
        )
        self._received_entry.pack(pady=(5, 5))
        self._received_entry.bind("<KeyRelease>", self._on_received_changed)

        self._change_label = ctk.CTkLabel(
            self._cash_frame,
            text="Vuelto: $0",
            font=theme.scaled_font(16),
        )
        self._change_label.pack(pady=(0, 10))

        # --- error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
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
            text="Confirmar",
            width=100,
            command=self._confirm,
        ).pack(side="left", padx=5)

        # Initial state
        self._on_method_changed()
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    @property
    def result(self) -> dict[str, Any] | None:
        """``{"payment_method", "received", "change"}`` on confirm, ``None`` on cancel."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _on_method_changed(self) -> None:
        """Show/hide the cash-received frame based on selected method."""
        method = self._method_var.get()
        if method == "cash":
            self._cash_frame.pack(fill="x", padx=20, pady=5)
            self._received_entry.focus_set()
        else:
            self._cash_frame.pack_forget()
            self._error_label.configure(text="")

    def _on_received_changed(self, _event: tk.Event | None = None) -> None:
        """Recalculate change as the user types the received amount."""
        raw = self._received_entry.get().strip()
        if not raw:
            self._change_label.configure(text="Vuelto: —")
            return
        try:
            received = int(raw)
        except ValueError:
            self._change_label.configure(text="Vuelto: —")
            return

        change = received - self._total
        if change >= 0:
            self._change_label.configure(text=f"Vuelto: ${change:,}")
        else:
            self._change_label.configure(
                text=f"Falta: ${abs(change):,}"
            )

    def _confirm(self) -> None:
        """Validate and return the payment result."""
        method = self._method_var.get()

        if method == "cash":
            raw = self._received_entry.get().strip()
            try:
                received = int(raw)
            except ValueError:
                self._error_label.configure(text="Ingrese un monto válido")
                self._received_entry.focus_set()
                return

            if received < self._total:
                self._error_label.configure(text="Monto insuficiente")
                self._received_entry.focus_set()
                return

            change = received - self._total
        else:
            received = 0
            change = 0

        self._result = {
            "payment_method": method,
            "received": received,
            "change": change,
        }
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
