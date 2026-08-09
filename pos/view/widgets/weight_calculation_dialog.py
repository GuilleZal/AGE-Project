"""Weight calculation dialog — modal for calculating product quantity by weight/amount."""

import tkinter as tk
import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class WeightCalculationDialog(CenteredDialog):
    """Modal dialog to calculate weight (Kg) or amount ($) for barcode-less products.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    product_name : str
        Name of the selected product.
    sale_price : int
        Unit price per Kg in whole ARS pesos.
    initial_weight : float
        Default weight value in Kg (defaults to 0.5).
    **kwargs :
        Forwarded to ``CenteredDialog``.
    """

    def __init__(
        self,
        master: tk.Widget,
        product_name: str,
        sale_price: int,
        initial_weight: float = 0.5,
        role: str = "",
        **kwargs,
    ) -> None:
        dialog_height = 340 if role == "cajero" else 320
        super().__init__(
            master,
            width=420,
            height=dialog_height,
            title="Ingresar Peso o Monto",
            **kwargs,
        )

        self._product_name = product_name
        self._sale_price = sale_price
        self._role = role
        self._result: float | None = None
        self._updating = False
        self._exact_weight: float | None = None

        # --- Header section ---
        title_text = f"Ingresar Peso o Monto - {product_name}"
        self._title_label = ctk.CTkLabel(
            self,
            text=title_text,
            font=theme.scaled_font(16, weight="bold"),
            wraplength=380,
            justify="center",
        )
        self._title_label.pack(pady=(15, 2))

        self._price_label = ctk.CTkLabel(
            self,
            text=f"(${sale_price:,} / Kg)",
            font=theme.scaled_font(14),
            text_color="#d0d0d0",
        )
        self._price_label.pack(pady=(0, 15))

        # --- Form frame ---
        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="x", padx=30, pady=5)
        form_frame.grid_columnconfigure(0, weight=0)
        form_frame.grid_columnconfigure(1, weight=1)

        # Peso row
        ctk.CTkLabel(
            form_frame,
            text="Peso (Kg):",
            font=theme.scaled_font(14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))

        self._peso_entry = ctk.CTkEntry(
            form_frame,
            height=36,
            font=theme.scaled_font(14),
        )
        self._peso_entry.grid(row=0, column=1, sticky="ew", pady=6)
        self._peso_entry.bind("<KeyRelease>", self._on_peso_changed)

        # Monto row
        ctk.CTkLabel(
            form_frame,
            text="Monto ($):",
            font=theme.scaled_font(14, weight="bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))

        self._monto_entry = ctk.CTkEntry(
            form_frame,
            height=36,
            font=theme.scaled_font(14),
        )
        self._monto_entry.grid(row=1, column=1, sticky="ew", pady=6)
        self._monto_entry.bind("<KeyRelease>", self._on_monto_changed)

        # --- Initial values setup ---
        if self._role == "cajero":
            # Cashier role: leave fields empty
            pass
        elif initial_weight > 0:
            self._peso_entry.insert(0, str(initial_weight))
            monto_init = int(round(initial_weight * sale_price))
            self._monto_entry.insert(0, f"${monto_init:,}")

        # --- Explanatory note ---
        ctk.CTkLabel(
            self,
            text="Al ingresar un valor en un campo, el otro se calculará automáticamente.",
            font=theme.scaled_font(11),
            text_color="#a0a0a0",
            wraplength=360,
            justify="center",
        ).pack(pady=(8, 2))

        # Cashier role specific example note
        if self._role == "cajero":
            ctk.CTkLabel(
                self,
                text="Aclaración: 500 gramos equivale a 0.5 kg",
                font=theme.scaled_font(12, weight="bold"),
                text_color="#3498db",
                justify="center",
            ).pack(pady=(2, 8))

        # --- Error label ---
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#ef4444",
            font=theme.scaled_font(12),
        )
        self._error_label.pack(pady=(2, 5))

        # --- Buttons frame ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(5, 15))

        ctk.CTkButton(
            btn_frame,
            text="Agregar al Carrito",
            width=140,
            height=38,
            fg_color="#1f538d",
            hover_color="#164273",
            font=theme.scaled_font(13, weight="bold"),
            command=self._confirm,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=110,
            height=38,
            fg_color="#52525b",
            hover_color="#3f3f46",
            font=theme.scaled_font(13, weight="bold"),
            command=self._cancel,
        ).pack(side="left", padx=8)

        # Binds
        self._peso_entry.bind("<Return>", lambda _e: self._confirm())
        self._monto_entry.bind("<Return>", lambda _e: self._confirm())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self._peso_entry.focus_set()
        self._peso_entry.select_range(0, tk.END)

        # Ensure dialog size fits all content dynamically and is centered properly
        self.update_idletasks()
        req_height = self.winfo_reqheight()
        self._height = max(req_height, dialog_height)
        self._center_on_parent(master)

    @property
    def result(self) -> float | None:
        """Calculated weight in Kg on confirm, or ``None`` if cancelled."""
        return self._result

    # --------------------------------------------------------------- private ---

    def _on_peso_changed(self, _event: tk.Event | None = None) -> None:
        """Calculate amount when weight changes."""
        if self._updating:
            return

        self._exact_weight = None

        raw = self._peso_entry.get().strip().replace(",", ".")
        self._error_label.configure(text="")

        if not raw:
            self._updating = True
            self._monto_entry.delete(0, tk.END)
            self._updating = False
            return

        try:
            weight = float(raw)
            if weight >= 0:
                monto = int(round(weight * self._sale_price))
                self._updating = True
                self._monto_entry.delete(0, tk.END)
                self._monto_entry.insert(0, f"${monto:,}")
                self._updating = False
        except ValueError:
            pass

    def _on_monto_changed(self, _event: tk.Event | None = None) -> None:
        """Calculate weight when amount changes."""
        if self._updating:
            return

        raw = (
            self._monto_entry.get()
            .strip()
            .replace("$", "")
            .replace(".", "")
            .replace(",", "")
        )
        self._error_label.configure(text="")

        if not raw:
            self._updating = True
            self._peso_entry.delete(0, tk.END)
            self._exact_weight = None
            self._updating = False
            return

        try:
            monto = float(raw)
            if monto >= 0 and self._sale_price > 0:
                weight = monto / self._sale_price
                self._exact_weight = weight
                # Format to 3 decimal places without trailing zeros
                weight_str = f"{weight:.3f}".rstrip("0").rstrip(".")
                if not weight_str or weight_str == "":
                    weight_str = "0"
                self._updating = True
                self._peso_entry.delete(0, tk.END)
                self._peso_entry.insert(0, weight_str)
                self._updating = False
        except ValueError:
            self._exact_weight = None

    def _confirm(self) -> None:
        """Validate input and set result weight in Kg."""
        if self._exact_weight is not None:
            self._result = self._exact_weight
            self.destroy()
            return

        raw = self._peso_entry.get().strip().replace(",", ".")
        if not raw:
            self._error_label.configure(text="Ingrese un peso válido")
            self._peso_entry.focus_set()
            return

        try:
            weight = float(raw)
        except ValueError:
            self._error_label.configure(text="Ingrese un peso válido")
            self._peso_entry.focus_set()
            return

        if weight <= 0:
            self._error_label.configure(text="El peso debe ser mayor a 0")
            self._peso_entry.focus_set()
            return

        self._result = weight
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()
