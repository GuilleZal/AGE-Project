"""Report view — period selector, metrics cards, top-10 treeview, and
CSV export.

Provides a period filter (Today, Week, Month, Custom range), a set of
metric cards (total sales, count, average ticket, profit, margin %),
a top-10 products treeview, and an export-to-CSV button.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview


class ReportView(ctk.CTkFrame):
    """Reports tab — metrics, top products, and export.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Reportes" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_generate`` (receives ``{start, end}``),
        and ``on_export`` (no arguments).
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    PERIOD_OPTIONS = {
        "Hoy": ("today",),
        "Esta semana": ("week",),
        "Este mes": ("month",),
        "Personalizado": ("custom",),
    }

    PERIOD_OPTIONS_ORDER = [
        "Hoy",
        "Esta semana",
        "Este mes",
        "Personalizado",
    ]

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        callbacks = callbacks or {}

        self._on_generate: (
            Callable[[str, str], None] | None
        ) = callbacks.get("on_generate")
        self._on_export: Callable[[], None] | None = callbacks.get(
            "on_export"
        )

        # Cache the last report data for CSV export
        self._report_data: dict[str, Any] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # treeview row

        # --- row 0: period selector ---
        selector_frame = ctk.CTkFrame(self)
        selector_frame.grid(
            row=0, column=0, sticky="ew", padx=10, pady=(10, 5)
        )

        ctk.CTkLabel(
            selector_frame,
            text="Período:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=(15, 5))

        self._period_var = tk.StringVar(value="Hoy")
        self._period_menu = ctk.CTkOptionMenu(
            selector_frame,
            values=self.PERIOD_OPTIONS_ORDER,
            variable=self._period_var,
            width=140,
            command=self._handle_period_changed,
        )
        self._period_menu.pack(side="left", padx=5)

        # Custom date range — shown only when "Personalizado" is selected
        self._custom_frame = ctk.CTkFrame(selector_frame)
        self._custom_frame.pack(side="left", padx=10)

        ctk.CTkLabel(
            self._custom_frame, text="Desde:", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=2)
        self._start_entry = ctk.CTkEntry(
            self._custom_frame,
            width=110,
            placeholder_text="YYYY-MM-DD",
        )
        self._start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(
            self._custom_frame, text="Hasta:", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(5, 2))
        self._end_entry = ctk.CTkEntry(
            self._custom_frame,
            width=110,
            placeholder_text="YYYY-MM-DD",
        )
        self._end_entry.pack(side="left", padx=2)

        # Hide custom frame by default
        self._custom_frame.pack_forget()

        # Generate button
        ctk.CTkButton(
            selector_frame,
            text="Generar reporte",
            width=130,
            command=self._handle_generate,
        ).pack(side="left", padx=(15, 10))

        # --- row 1: metrics cards ---
        self._metrics_frame = ctk.CTkFrame(self)
        self._metrics_frame.grid(
            row=1, column=0, sticky="ew", padx=10, pady=5
        )

        self._metric_cards: dict[str, ctk.CTkLabel] = {}
        card_defs = [
            ("Total ventas", "total", 0, "$0"),
            ("Operaciones", "count", 1, "0"),
            ("Ganancia", "profit", 2, "$0"),
            ("Margen", "margin", 3, "0%"),
        ]
        for label, key, col, default in card_defs:
            card = ctk.CTkFrame(
                self._metrics_frame,
                fg_color="#2b2b2b",
                corner_radius=8,
            )
            card.grid(
                row=0, column=col, padx=5, pady=10, sticky="nsew"
            )
            self._metrics_frame.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color="#888",
            ).pack(pady=(8, 2))

            value_lbl = ctk.CTkLabel(
                card,
                text=default,
                font=ctk.CTkFont(size=20, weight="bold"),
            )
            value_lbl.pack(pady=(0, 8))
            self._metric_cards[key] = value_lbl

        # --- row 2: top-10 treeview ---
        self._tree_frame = ctk.CTkFrame(self)
        self._tree_frame.grid(
            row=2, column=0, sticky="nsew", padx=10, pady=5
        )
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self._tree_frame.grid_columnconfigure(0, weight=1)

        self._style = ttk.Style(self._tree_frame)
        self._configure_style()

        self._top_columns = ("pos", "producto", "cantidad", "monto")
        self._top_tree = ttk.Treeview(
            self._tree_frame,
            columns=self._top_columns,
            show="headings",
            selectmode="none",
            height=10,
        )
        self._top_tree.heading("pos", text="#")
        self._top_tree.heading("producto", text="Producto")
        self._top_tree.heading("cantidad", text="Cantidad")
        self._top_tree.heading("monto", text="Monto total")

        self._top_tree.column("pos", width=40, anchor="center")
        self._top_tree.column("producto", width=240, stretch=True)
        self._top_tree.column("cantidad", width=80, anchor="center")
        self._top_tree.column("monto", width=130, anchor="e")

        # Load saved column widths
        saved_widths = load_column_widths("report_view")
        self._top_tree._view_name = "report_view"
        apply_treeview_widths(self._top_tree, saved_widths)

        # Add column sorting
        add_sorting_to_treeview(
            self._top_tree,
            list(self._top_columns),
            column_types={
                "pos": "int",
                "producto": "str",
                "cantidad": "int",
                "monto": "int",
            }
        )

        self._top_scroll = ttk.Scrollbar(
            self._tree_frame,
            orient="vertical",
            command=self._top_tree.yview,
        )
        self._top_tree.configure(yscrollcommand=self._top_scroll.set)
        self._top_tree.grid(row=0, column=0, sticky="nsew")
        self._top_scroll.grid(row=0, column=1, sticky="ns")

        # --- row 3: export button ---
        self._export_btn = ctk.CTkButton(
            self,
            text="📥 Exportar CSV",
            width=140,
            height=35,
            fg_color="#3b3b3b",
            command=self._handle_export,
        )
        self._export_btn.grid(
            row=3, column=0, sticky="e", padx=10, pady=(5, 10)
        )

    # ---------------------------------------------------------------- public ---

    def update_report(self, data: dict[str, Any]) -> None:
        """Refresh metrics and top-10 treeview with report *data*.

        Expected keys:
            ``sales``: {total, count, avg_ticket}
            ``profit``: {revenue, cost, profit, margin_pct}
            ``top_products``: [{name, total_quantity, total_amount}, ...]
        """
        sales = data.get("sales") or {}
        profit = data.get("profit") or {}
        top = data.get("top_products") or []

        self._metric_cards["total"].configure(
            text=f"${sales.get('total', 0):,}"
        )
        self._metric_cards["count"].configure(
            text=str(sales.get("count", 0))
        )
        self._metric_cards["profit"].configure(
            text=f"${profit.get('profit', 0):,}"
        )
        margin = profit.get("margin_pct", 0)
        self._metric_cards["margin"].configure(
            text=f"{margin:.1f}%"
        )

        # Update top-10
        for child in self._top_tree.get_children():
            self._top_tree.delete(child)

        for idx, item in enumerate(top, 1):
            self._top_tree.insert(
                "",
                "end",
                values=(
                    idx,
                    item.get("name", "—"),
                    item.get("total_quantity", 0),
                    f"${item.get('total_amount', 0):,}",
                ),
            )

    # ----------------------------------------------------------- callbacks ----

    def set_on_generate(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Wire the generate-report callback."""
        self._on_generate = callback

    def set_on_export(self, callback: Callable[[], None]) -> None:
        """Wire the CSV export callback."""
        self._on_export = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``ReportController`` instance and set up all event handlers.

        After calling this, report generation and CSV export are
        automatically routed to the controller.
        """
        self._controller = controller

        # Wire internal handlers
        self._on_generate = self._controller_generate
        self._on_export = self._controller_export

    # ---------------------------------------------------- controller handlers ---

    def _controller_generate(self, start: str, end: str) -> None:
        """Generate a sales report via controller and update the UI."""
        result = self._controller.generate_sales_report(start, end)
        if result["success"]:
            data = result["data"]
            self._report_data = data
            self.update_report(data)
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_export(self) -> None:
        """Export the last report to CSV via file dialog."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Exportar reporte",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        # Build exportable data from the cached report
        top_products = self._report_data.get("top_products", [])
        if not top_products:
            messagebox.showwarning(
                "Sin datos",
                "No hay datos de productos para exportar.",
            )
            return

        result = self._controller.export_to_csv(top_products, filepath)
        if result["success"]:
            messagebox.showinfo("Exportación", "Reporte exportado correctamente")
        else:
            messagebox.showerror("Error", result["error"])

    # --------------------------------------------------------------- private ---

    def _configure_style(self) -> None:
        self._style.theme_use("clam")
        bg, fg, select_bg = "#2b2b2b", "#dce4ee", "#1f538d"
        self._style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
        )
        self._style.configure(
            "Treeview.Heading",
            background="#505050",
            foreground="#ffffff",
            relief="raised",
            borderwidth=1,
            font=("Segoe UI", 10, "bold"),
        )
        self._style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", fg)],
        )

    def _handle_period_changed(self, value: str) -> None:
        if value == "Personalizado":
            self._custom_frame.pack(side="left", padx=10)
        else:
            self._custom_frame.pack_forget()

    def _get_date_range(self) -> tuple[str, str] | None:
        """Resolve the selected period to (start, end) ISO datetime strings.

        The end date always includes ``23:59:59`` so that records with a
        time component on the last day are not excluded by the SQL
        ``created_at <= ?`` comparison.

        Returns ``None`` if the user chose "Personalizado" but entered
        invalid or empty dates.
        """
        from datetime import datetime, timedelta

        today = datetime.now().date()
        period = self._period_var.get()

        if period == "Hoy":
            iso = today.isoformat()
            return iso, f"{iso} 23:59:59"
        elif period == "Esta semana":
            start = today - timedelta(days=today.weekday())
            return start.isoformat(), f"{today.isoformat()} 23:59:59"
        elif period == "Este mes":
            start = today.replace(day=1)
            return start.isoformat(), f"{today.isoformat()} 23:59:59"
        elif period == "Personalizado":
            start_raw = self._start_entry.get().strip()
            end_raw = self._end_entry.get().strip()
            if not start_raw or not end_raw:
                messagebox.showwarning(
                    "Fechas requeridas",
                    "Ingrese las fechas de inicio y fin (YYYY-MM-DD).",
                )
                return None
            try:
                datetime.strptime(start_raw, "%Y-%m-%d")
                datetime.strptime(end_raw, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning(
                    "Formato inválido",
                    "Las fechas deben tener el formato YYYY-MM-DD.",
                )
                return None
            return start_raw, f"{end_raw} 23:59:59"
        return None

    def _handle_generate(self) -> None:
        date_range = self._get_date_range()
        if date_range is None:
            return
        start, end = date_range
        if self._on_generate is not None:
            self._on_generate(start, end)

    def _handle_export(self) -> None:
        if self._on_export is not None:
            self._on_export()
