"""Import result dialog — modal dialog to display detailed import results."""

import tkinter as tk
from typing import Any

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view import theme


class ImportResultDialog(CenteredDialog):
    """Modal dialog to display detailed import results with errors.
    
    Parameters
    ----------
    master : tk.Widget
        Parent window.
    result : dict
        Import result dict with keys: created, updated, errors, error_details.
    **kwargs :
        Forwarded to ``ctk.CTkToplevel``.
    """

    def __init__(
        self,
        master: tk.Widget,
        result: dict,
        **kwargs,
    ) -> None:
        super().__init__(master, width=600, height=500, title="Resultado de Importación", resizable=(True, True), **kwargs)

        self._result = result

        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Summary section
        summary_frame = ctk.CTkFrame(main_frame)
        summary_frame.pack(fill="x", pady=(0, 15))

        created = result.get("created", 0)
        updated = result.get("updated", 0)
        error_count = result.get("errors", 0)

        # Success summary
        if created > 0 or updated > 0:
            success_label = ctk.CTkLabel(
                summary_frame,
                text=f"✅ {created + updated} productos procesados correctamente",
                font=theme.scaled_font(14, weight="bold"),
                text_color="#2ecc71",
            )
            success_label.pack(anchor="w", pady=(0, 5))

            details_label = ctk.CTkLabel(
                summary_frame,
                text=f"   • {created} productos creados\n   • {updated} productos actualizados",
                font=theme.scaled_font(12),
                justify="left",
            )
            details_label.pack(anchor="w")

        # Error summary
        if error_count > 0:
            error_header = ctk.CTkLabel(
                summary_frame,
                text=f"\n❌ {error_count} errores encontrados",
                font=theme.scaled_font(14, weight="bold"),
                text_color="#e74c3c",
            )
            error_header.pack(anchor="w", pady=(10, 5))

            # Scrollable error list
            error_frame = ctk.CTkScrollableFrame(main_frame, height=250)
            error_frame.pack(fill="both", expand=True, pady=(0, 15))

            error_details = result.get("error_details", [])
            for error in error_details:
                row_num = error.get("row", "?")
                field = error.get("field", "")
                error_msg = error.get("error", "")
                
                error_text = f"Fila {row_num}"
                if field and field != "general":
                    error_text += f" ({field})"
                error_text += f": {error_msg}"
                
                error_label = ctk.CTkLabel(
                    error_frame,
                    text=error_text,
                    font=theme.scaled_font(11),
                    text_color="#e74c3c",
                    justify="left",
                    anchor="w",
                )
                error_label.pack(anchor="w", pady=2, padx=5)

        # Close button
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            width=120,
            height=35,
            command=self.destroy,
        )
        close_btn.pack(side="right")

        # Configure style
        self._configure_style()

    def _configure_style(self) -> None:
        """Configure dialog appearance."""
        self.configure(fg_color="#2b2b2b")
