"""Preferences dialog — global settings for low-stock threshold and profit margin."""

import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog


class PreferencesDialog(CenteredDialog):
    """Modal dialog to configure global preferences.

    Allows setting the global low-stock threshold and profit margin percentage.
    Optionally applies these values to products, filtered by category.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    controller : Any
        ProductController instance with get_settings, apply_settings, and list_categories methods.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(self, master: tk.Widget, controller: Any, **kwargs) -> None:
        super().__init__(master, width=500, height=550, title="Preferencias", **kwargs)

        self._controller = controller
        self._applied = False

        # Load current settings
        result = controller.get_settings()
        if result["success"]:
            settings = result["data"]
        else:
            settings = {"low_stock_threshold": 5, "profit_margin_pct": 30.0}

        # Load categories
        cat_result = controller.list_categories()
        if cat_result["success"]:
            self._categories = cat_result["data"]
        else:
            self._categories = []

        # Build category options: "Todas" + list of category names
        self._category_options = ["Todas las categorías"]
        self._category_ids: list[int | None] = [None]  # None = all categories
        for cat in self._categories:
            self._category_options.append(cat["name"])
            self._category_ids.append(cat["id"])

        # --- low stock threshold ---
        ctk.CTkLabel(
            self,
            text="Umbral de stock bajo:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="Productos con stock igual o inferior a este valor se marcarán como stock bajo.",
            font=ctk.CTkFont(size=11),
            text_color="#888",
        ).pack(padx=20)

        self._threshold_entry = ctk.CTkEntry(self, width=150)
        self._threshold_entry.insert(0, str(settings["low_stock_threshold"]))
        self._threshold_entry.pack(pady=(5, 5))

        # Category selector for threshold
        ctk.CTkLabel(
            self,
            text="Aplicar a categoría:",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(5, 0))

        self._threshold_cat_var = tk.StringVar(value=self._category_options[0])
        self._threshold_cat_menu = ctk.CTkOptionMenu(
            self,
            values=self._category_options,
            variable=self._threshold_cat_var,
            width=250,
        )
        self._threshold_cat_menu.pack(pady=(0, 10))

        # --- profit margin ---
        ctk.CTkLabel(
            self,
            text="Porcentaje de ganancia (%):",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            self,
            text="Se aplicará para recalcular el precio de venta.",
            font=ctk.CTkFont(size=11),
            text_color="#888",
        ).pack(padx=20)

        self._margin_entry = ctk.CTkEntry(self, width=150)
        self._margin_entry.insert(0, str(settings["profit_margin_pct"]))
        self._margin_entry.pack(pady=(5, 5))

        # Category selector for margin
        ctk.CTkLabel(
            self,
            text="Aplicar a categoría:",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(5, 0))

        self._margin_cat_var = tk.StringVar(value=self._category_options[0])
        self._margin_cat_menu = ctk.CTkOptionMenu(
            self,
            values=self._category_options,
            variable=self._margin_cat_var,
            width=250,
        )
        self._margin_cat_menu.pack(pady=(0, 15))

        # --- apply to products checkbox ---
        self._apply_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Aplicar cambios a productos existentes",
            variable=self._apply_var,
            font=ctk.CTkFont(size=12),
        ).pack(pady=(5, 10))

        # --- error label ---
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
        )
        self._error_label.pack()

        # --- buttons ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(10, 20))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=15)

        ctk.CTkButton(
            btn_frame,
            text="Guardar",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14),
            command=self._confirm,
        ).pack(side="left", padx=15)

        self._threshold_entry.focus_set()

    @property
    def applied(self) -> bool:
        """True if settings were saved and applied."""
        return self._applied

    # --------------------------------------------------------------- private ---

    def _get_category_id(self, category_name: str) -> int | None:
        """Get category ID from name. Returns None for 'Todas las categorías'."""
        try:
            idx = self._category_options.index(category_name)
            return self._category_ids[idx]
        except (ValueError, IndexError):
            return None

    def _confirm(self) -> None:
        # Validate threshold
        try:
            threshold = float(self._threshold_entry.get().strip())
        except ValueError:
            self._error_label.configure(
                text="El umbral debe ser un número válido"
            )
            self._threshold_entry.focus_set()
            return

        if threshold < 0:
            self._error_label.configure(
                text="El umbral no puede ser negativo"
            )
            self._threshold_entry.focus_set()
            return

        # Validate margin
        try:
            margin = float(self._margin_entry.get().strip())
        except ValueError:
            self._error_label.configure(
                text="El porcentaje debe ser un número válido"
            )
            self._margin_entry.focus_set()
            return

        if margin < 0:
            self._error_label.configure(
                text="El porcentaje no puede ser negativo"
            )
            self._margin_entry.focus_set()
            return

        # Get selected categories
        threshold_cat_name = self._threshold_cat_var.get()
        margin_cat_name = self._margin_cat_var.get()
        threshold_category_id = self._get_category_id(threshold_cat_name)
        margin_category_id = self._get_category_id(margin_cat_name)

        # Build confirmation message
        apply_to_products = self._apply_var.get()
        if apply_to_products:
            threshold_scope = "todas las categorías" if threshold_category_id is None else f"categoría '{threshold_cat_name}'"
            margin_scope = "todas las categorías" if margin_category_id is None else f"categoría '{margin_cat_name}'"

            confirm = messagebox.askyesno(
                "Confirmar",
                "¿Está seguro de aplicar estos cambios?\n\n"
                f"• Umbral stock bajo: {threshold} → {threshold_scope}\n"
                f"• Margen ganancia: {margin}% → {margin_scope}\n\n"
                "Esto actualizará los productos seleccionados.",
            )
            if not confirm:
                return

        # Apply settings
        result = self._controller.apply_settings(
            low_stock_threshold=threshold,
            profit_margin_pct=margin,
            apply_to_products=apply_to_products,
            threshold_category_id=threshold_category_id,
            margin_category_id=margin_category_id,
        )

        if result["success"]:
            self._applied = True
            updated = result["data"]["products_updated"]
            if apply_to_products and updated > 0:
                messagebox.showinfo(
                    "Éxito",
                    f"Preferencias guardadas.\n{updated} producto(s) actualizado(s).",
                )
            else:
                messagebox.showinfo("Éxito", "Preferencias guardadas.")
            self.destroy()
        else:
            self._error_label.configure(text=result["error"])

    def _cancel(self) -> None:
        self._applied = False
        self.destroy()
