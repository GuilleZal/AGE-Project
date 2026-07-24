"""Report view — modular dashboard layout with KPIs, top products,
low stock, payment methods chart, and expense summary.

Provides a period filter (Today, Week, Month, Custom range), metric
cards (total sales, operations, purchases, gross profit, margin %),
top products treeview with configurable limit, low stock treeview,
a reserved frame for payment methods chart, and an expense summary
ticket-style panel.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import customtkinter as ctk
from tkcalendar import DateEntry

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme
from pos.view.theme import get_offset


class ReportView(ctk.CTkFrame):
    """Reports dashboard — KPIs, top products, low stock, chart, and exports.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Reportes" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_generate`` (receives ``{start, end}``),
        ``on_export_diario`` (no arguments), ``on_export_top`` (no arguments),
        and ``on_export_faltantes`` (no arguments).
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

    TOP_PRODUCT_LIMITS = ["5", "10", "20", "30"]

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}

        self._on_generate: (
            Callable[[str, str], None] | None
        ) = callbacks.get("on_generate")
        self._on_export_diario: Callable[[], None] | None = callbacks.get(
            "on_export_diario"
        )
        self._on_export_top: Callable[[], None] | None = callbacks.get(
            "on_export_top"
        )
        self._on_export_faltantes: Callable[[], None] | None = callbacks.get(
            "on_export_faltantes"
        )

        # Cache the last report data for CSV exports
        self._report_data: dict[str, Any] = {}

        # Theme-aware border color for module separation
        self._border_color = theme.get_contrast_map()["search_border"]

        # Configure main grid: 3 rows, 2 columns
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=0)   # top bar
        self.grid_rowconfigure(1, weight=0)   # KPIs
        self.grid_rowconfigure(2, weight=1)   # data panel

        # --- Row 0: Top bar (period selector + buttons) ---
        self._build_top_bar()

        # --- Row 1: KPI cards ---
        self._build_kpi_panel()

        # --- Row 2: Data panel (2 columns) ---
        self._build_data_panel()

    # ------------------------------------------------------------------ UI builders ---

    def _build_top_bar(self) -> None:
        """Build the top bar with period selector and export button."""
        top_bar = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        top_bar.grid_columnconfigure(1, weight=1)  # spacer

        # Left side: period selector
        selector_frame = ctk.CTkFrame(top_bar, fg_color="transparent", border_width=0)
        selector_frame.grid(row=0, column=0, sticky="w", padx=5, pady=8)

        ctk.CTkLabel(
            selector_frame,
            text="Período:",
            font=theme.scaled_font(14, weight="bold"),
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

        # Custom date range
        self._custom_frame = ctk.CTkFrame(selector_frame, fg_color="transparent", border_width=0)
        self._custom_frame.pack(side="left", padx=10)

        ctk.CTkLabel(
            self._custom_frame, text="Desde:", font=theme.scaled_font(12)
        ).pack(side="left", padx=2)
        self._start_entry = DateEntry(
            self._custom_frame,
            width=11,
            background="#2d5a3d",
            foreground="white",
            borderwidth=1,
            bordercolor="#505050",
            arrowcolor="#2d5a3d",
            date_pattern="yyyy-mm-dd",
            locale="es_AR",
        )
        self._start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(
            self._custom_frame, text="Hasta:", font=theme.scaled_font(12)
        ).pack(side="left", padx=(5, 2))
        self._end_entry = DateEntry(
            self._custom_frame,
            width=11,
            background="#2d5a3d",
            foreground="white",
            borderwidth=1,
            bordercolor="#505050",
            arrowcolor="#2d5a3d",
            date_pattern="yyyy-mm-dd",
            locale="es_AR",
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

        # Right side: export diario button
        self._export_diario_btn = ctk.CTkButton(
            top_bar,
            text="Exportar Libro Diario (CSV)",
            width=200,
            height=35,
            fg_color="#3b3b3b",
            command=self._handle_export_diario,
        )
        self._export_diario_btn.grid(row=0, column=2, sticky="e", padx=(10, 15), pady=8)

    def _build_kpi_panel(self) -> None:
        """Build the KPI cards row with 5 metric cards."""
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        kpi_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        # Configure 5 equal columns
        for col in range(5):
            kpi_frame.grid_columnconfigure(col, weight=1)

        self._metric_cards: dict[str, ctk.CTkLabel] = {}

        card_defs = [
            ("Ventas Totales", "total_ventas", 0, "$0", "#2b2b2b"),
            ("Operaciones", "operaciones", 1, "0", "#2b2b2b"),
            ("Compras a Proveedores", "compras", 2, "$0", "#2b2b2b"),
            ("Ganancia Bruta", "ganancia_bruta", 3, "$0", "#2b2b2b"),
            ("Margen Bruto", "margen_bruto", 4, "0%", "#2b2b2b"),
        ]

        for label, key, col, default, color in card_defs:
            card = ctk.CTkFrame(
                kpi_frame,
                fg_color=color,
                corner_radius=8,
            )
            card.grid(row=0, column=col, padx=5, pady=10, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=label,
                font=theme.scaled_font(11),
                text_color="#888",
            ).pack(pady=(8, 2))

            value_lbl = ctk.CTkLabel(
                card,
                text=default,
                font=theme.scaled_font(20, weight="bold"),
            )
            value_lbl.pack(pady=(0, 8))
            self._metric_cards[key] = value_lbl

    def _build_data_panel(self) -> None:
        """Build the data panel with 2 columns: left (unified table) and right (chart + summary)."""
        # Left column: Unified table (Top products / Low stock)
        left_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        left_frame.grid(row=2, column=0, sticky="nsew", padx=(10, 5), pady=5)
        
        # Blindaje de grilla: Columna 0 (Tabla) se expande, Columna 1 (Scroll Vertical) reserva su espacio fijo
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=0)
        
        left_frame.grid_rowconfigure(1, weight=1)  # unified table
        left_frame.grid_rowconfigure(2, weight=0)  # H scrollbar

        # Table header section
        self._table_header = ctk.CTkFrame(left_frame, fg_color="transparent", border_width=2, border_color=self._border_color)
        self._table_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        self._table_header.grid_columnconfigure(2, weight=1) # Spacer pushes export button

        # Table selector combobox
        self._table_type_var = tk.StringVar(value="Top productos más vendidos")
        self._table_selector = ctk.CTkComboBox(
            self._table_header,
            values=["Top productos más vendidos", "Productos bajo stock"],
            variable=self._table_type_var,
            width=220,
            height=28,
            state="readonly",
            command=self._handle_table_type_changed,
        )
        self._table_selector.grid(row=0, column=0, sticky="w", padx=10, pady=8)

        # Ver Top Controls frame
        self._top_controls_frame = ctk.CTkFrame(self._table_header, fg_color="transparent")
        self._top_controls_frame.grid(row=0, column=1, sticky="w", padx=5)

        ctk.CTkLabel(
            self._top_controls_frame,
            text="Ver Top:",
            font=theme.scaled_font(12),
        ).pack(side="left", padx=2)

        # Limit selector
        self._top_limit_var = tk.StringVar(value="10")
        self._top_limit_combo = ctk.CTkComboBox(
            self._top_controls_frame,
            values=self.TOP_PRODUCT_LIMITS,
            variable=self._top_limit_var,
            width=70,
            height=26,
            state="readonly",
            command=self._handle_top_limit_changed,
        )
        self._top_limit_combo.pack(side="left", padx=5)

        # Export button
        self._export_table_btn = ctk.CTkButton(
            self._table_header,
            text="Exportar CSV",
            width=130,
            height=28,
            fg_color="#3b3b3b",
            command=self._handle_export_table,
        )
        self._export_table_btn.grid(row=0, column=3, sticky="e", padx=(10, 10), pady=8)

        # Treeview styling
        self._style = ttk.Style(left_frame)
        self._configure_style()

        # Unified treeview
        self._report_columns = ("col0", "col1", "col2", "col3")
        self._report_tree = ttk.Treeview(
            left_frame,
            columns=self._report_columns,
            show="headings",
            selectmode="none",
            height=10,
        )

        self._report_tree.bind("<Button-1>", self._prevent_resize)
        self._report_tree.bind("<B1-Motion>", self._prevent_resize)

        self._report_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self._report_tree.yview)
        self._report_hscroll = ttk.Scrollbar(left_frame, orient="horizontal", command=self._report_tree.xview)
        self._report_tree.configure(yscrollcommand=self._report_scroll.set, xscrollcommand=self._report_hscroll.set)

        self._report_tree.grid(row=1, column=0, sticky="nsew")
        self._report_scroll.grid(row=1, column=1, sticky="ns")
        self._report_hscroll.grid(row=2, column=0, columnspan=2, sticky="ew")

        # Right column: Expense summary
        right_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        right_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 10), pady=5)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)

        # Expense summary (DISEÑO INTEGRADO RESPONSIVO DE ALTO COMPLETO)
        summary_frame = ctk.CTkFrame(right_frame, fg_color="transparent", border_width=0)
        summary_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Dos columnas exactas al 50% para que los montos tengan máximo espacio
        summary_frame.grid_columnconfigure(0, weight=1, uniform="sum")
        summary_frame.grid_columnconfigure(1, weight=1, uniform="sum")
        
        # Hacemos que la fila del spacer (fila 5) tome todo el espacio sobrante
        summary_frame.grid_rowconfigure(5, weight=1)

        # Título en fila propia, ocupando todo el ancho
        ctk.CTkLabel(
            summary_frame,
            text="Resumen de Egresos y Pérdidas",
            font=theme.scaled_font(14, weight="bold"),
            wraplength=350, # Evita estallar con fuentes gigantes
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 15))

        self._summary_labels: dict[str, ctk.CTkLabel] = {}
        summary_items = [
            ("Proveedores:", "compras", "$0", "#888"),
            ("Pérdidas:", "mermas", "$0", "#888"),
            ("Gastos:", "gastos", "$0", "#888"),
            ("Ganancias:", "ganancia_neta", "$0", "#4CAF50"),
        ]

        # Textos alineados a la izq y derecha con su propio espacio de 50/50
        for idx, (label, key, default, color) in enumerate(summary_items, start=1):
            font_size = 18 if key == "ganancia_neta" else 13
            font_weight = "bold" if key == "ganancia_neta" else "normal"

            ctk.CTkLabel(
                summary_frame,
                text=label,
                font=theme.scaled_font(font_size, weight=font_weight),
            ).grid(row=idx, column=0, sticky="w", padx=5, pady=6)

            value_lbl = ctk.CTkLabel(
                summary_frame,
                text=default,
                font=theme.scaled_font(font_size, weight=font_weight),
                text_color=color,
            )
            value_lbl.grid(row=idx, column=1, sticky="e", padx=5, pady=6)
            self._summary_labels[key] = value_lbl

        # Fila 5: Fila vacía que sirve de espaciador empujando el botón al fondo
        ctk.CTkFrame(summary_frame, fg_color="transparent", height=1).grid(row=5, column=0, columnspan=2, sticky="nsew")

        # Botón de exportar en fila propia al fondo, estirado ocupando todo el ancho
        self._export_resumen_btn = ctk.CTkButton(
            summary_frame,
            text="Exportar CSV",
            height=32,
            fg_color="#3b3b3b",
            command=self._handle_export_diario,
        )
        self._export_resumen_btn.grid(row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=(10, 5))

    # ---------------------------------------------------------------- public ---

    def update_report(self, data: dict[str, Any]) -> None:
        """Refresh metrics, trees, and summary with report *data*."""
        self._report_data = data
        sales = data.get("sales") or {}
        profit = data.get("profit") or {}
        expenses = data.get("expenses") or {}

        # Update KPI cards
        self._metric_cards["total_ventas"].configure(
            text=f"${sales.get('total', 0):,}"
        )
        self._metric_cards["operaciones"].configure(
            text=str(sales.get("count", 0))
        )
        # Compras a Proveedores KPI = same as expenses summary
        self._metric_cards["compras"].configure(
            text=f"${expenses.get('purchases', 0):,}"
        )
        self._metric_cards["ganancia_bruta"].configure(
            text=f"${int(float(profit.get('profit', 0))):,}"
        )
        margin = profit.get("margin_pct", 0)
        self._metric_cards["margen_bruto"].configure(
            text=f"{margin:.1f}%"
        )

        # Update unified table
        self._populate_table()

        # Update expense summary
        self._summary_labels["compras"].configure(
            text=f"${expenses.get('purchases', 0):,}"
        )
        self._summary_labels["mermas"].configure(
            text=f"${expenses.get('shrinkage', 0):,}"
        )
        self._summary_labels["gastos"].configure(
            text=f"${expenses.get('operating_expenses', 0):,}"
        )
        net_profit = expenses.get("net_profit", 0)
        self._summary_labels["ganancia_neta"].configure(
            text=f"${int(float(net_profit)):,}"
        )

    def _update_payment_chart(self, payment_methods: list[dict]) -> None:
        """Update the payment methods pie chart (No-op after chart removal)."""
        pass
        

    # ----------------------------------------------------------- callbacks ----

    def set_on_generate(
        self, callback: Callable[[str, str], None]
    ) -> None:
        """Wire the generate-report callback."""
        self._on_generate = callback

    def set_on_export_diario(self, callback: Callable[[], None]) -> None:
        """Wire the daily book CSV export callback."""
        self._on_export_diario = callback

    def set_on_export_top(self, callback: Callable[[], None]) -> None:
        """Wire the top products CSV export callback."""
        self._on_export_top = callback

    def set_on_export_faltantes(self, callback: Callable[[], None]) -> None:
        """Wire the low stock CSV export callback."""
        self._on_export_faltantes = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``ReportController`` instance and set up all event handlers.

        After calling this, report generation and CSV exports are
        automatically routed to the controller.
        """
        self._controller = controller

        # Wire internal handlers
        self._on_generate = self._controller_generate
        self._on_export_diario = self._controller_export_diario
        self._on_export_top = self._controller_export_top
        self._on_export_faltantes = self._controller_export_faltantes

    # ---------------------------------------------------- controller handlers ---

    def _controller_generate(self, start: str, end: str) -> None:
        """Generate a sales report via controller and update the UI."""
        # Get the top limit from the ComboBox
        limit_str = self._top_limit_combo.get() if getattr(self, "_top_limit_combo", None) else "10"
        top_limit = int(limit_str) if limit_str.isdigit() else 10

        result = self._controller.generate_sales_report(start, end, top_limit)
        if result["success"]:
            data = result["data"]
            self._report_data = data
            self.update_report(data)
            self._update_payment_chart(data.get("payment_methods", []))
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_export_diario(self) -> None:
        """Export the daily book to CSV via file dialog."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Exportar Libro Diario",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        # TODO: Implement daily book export logic
        messagebox.showinfo(
            "Exportación",
            "Función de exportación de Libro Diario en desarrollo.",
        )

    def _controller_export_top(self) -> None:
        """Export top products to CSV via file dialog."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Exportar Top Productos",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        # TODO: Implement top products export logic
        messagebox.showinfo(
            "Exportación",
            "Función de exportación de Top Productos en desarrollo.",
        )

    def _controller_export_faltantes(self) -> None:
        """Export low stock products to CSV via file dialog."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        filepath = filedialog.asksaveasfilename(
            title="Exportar Productos Bajo Stock",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not filepath:
            return

        # TODO: Implement low stock export logic
        messagebox.showinfo(
            "Exportación",
            "Función de exportación de Productos Bajo Stock en desarrollo.",
        )

    # --------------------------------------------------------------- private ---
    def _prevent_resize(self, event: Any) -> str | None:
        """Evita que el usuario cambie el tamaño de las columnas arrastrando el separador."""
        if event.widget.identify_region(event.x, event.y) == "separator":
            return "break"
        return None
        
    def _configure_style(self) -> None:
        """Configure Treeview style for dark theme."""
        self._style.theme_use("clam")
        contrast = theme.get_contrast_map()
        bg = contrast["treeview_bg"]
        fg = contrast["treeview_fg"]
        select_bg = "#1f538d"
        self._style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            borderwidth=0,
            font=theme.scaled_treeview_font(),
            rowheight=24 + theme.get_offset() * 2,
        )
        self._style.configure(
            "Treeview.Heading",
            background=contrast["treeview_header"],
            foreground=fg,
            relief="raised",
            borderwidth=1,
            font=theme.scaled_treeview_font("bold"),
        )
        self._style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", fg)],
        )

    def _handle_period_changed(self, value: str) -> None:
        """Show/hide custom date range based on period selection."""
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
            start_date = self._start_entry.get_date()
            end_date = self._end_entry.get_date()
            start_raw = start_date.strftime("%Y-%m-%d")
            end_raw = end_date.strftime("%Y-%m-%d")
            return start_raw, f"{end_raw} 23:59:59"
        return None

    def _handle_generate(self) -> None:
        """Handle generate report button click."""
        date_range = self._get_date_range()
        if date_range is None:
            return
        start, end = date_range
        if self._on_generate is not None:
            self._on_generate(start, end)

    def _handle_export_diario(self) -> None:
        """Handle export daily book button click."""
        if self._on_export_diario is not None:
            self._on_export_diario()

    def _handle_export_top(self) -> None:
        """Handle export top products button click."""
        if self._on_export_top is not None:
            self._on_export_top()

    def _handle_export_faltantes(self) -> None:
        """Handle export low stock button click."""
        if self._on_export_faltantes is not None:
            self._on_export_faltantes()

    def _handle_top_limit_changed(self, value: str) -> None:
        """Regenerate report when top limit changes."""
        # Only regenerate if we have a date range
        date_range = self._get_date_range()
        if date_range is not None and self._on_generate is not None:
            start, end = date_range
            self._on_generate(start, end)

    def _handle_table_type_changed(self, value: str) -> None:
        """Redraw headings and reload data when table selection changes."""
        self._populate_table()

    def _handle_export_table(self) -> None:
        """Handle export button click dynamically based on selected table type."""
        table_type = self._table_selector.get()
        if table_type == "Top productos más vendidos":
            self._handle_export_top()
        else:
            self._handle_export_faltantes()

    def _populate_table(self) -> None:
        """Populate the unified treeview based on the selected option."""
        # Clear existing items
        for child in self._report_tree.get_children():
            self._report_tree.delete(child)

        table_type = self._table_selector.get()
        if table_type == "Top productos más vendidos":
            # Show top limit selector
            self._top_controls_frame.grid()

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Producto")
            self._report_tree.heading("col2", text="Cantidad")
            self._report_tree.heading("col3", text="Monto total")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=50, anchor="center")
            self._report_tree.column("col1", width=250, minwidth=250, stretch=True, anchor="w")
            self._report_tree.column("col2", width=100, minwidth=100, anchor="center")
            self._report_tree.column("col3", width=140, minwidth=140, anchor="e")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "int", "col3": "int"}
            add_sorting_to_treeview(self._report_tree, list(self._report_columns), column_types)

            # Populate data
            top_products = self._report_data.get("top_products") or []
            for idx, item in enumerate(top_products, 1):
                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("name", "—"),
                        int(item.get("total_quantity", 0)),
                        f"${item.get('total_amount', 0):,}",
                    ),
                )
        else:
            # Hide top limit selector
            self._top_controls_frame.grid_remove()

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Producto")
            self._report_tree.heading("col2", text="Stock Actual")
            self._report_tree.heading("col3", text="Ubicación")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=50, anchor="center")
            self._report_tree.column("col1", width=250, minwidth=250, stretch=True, anchor="w")
            self._report_tree.column("col2", width=110, minwidth=110, anchor="center")
            self._report_tree.column("col3", width=160, minwidth=160, anchor="w")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "float", "col3": "str"}
            add_sorting_to_treeview(self._report_tree, list(self._report_columns), column_types)

            # Populate data (Always fetch latest real-time low stock products!)
            low_stock = []
            if getattr(self, "_controller", None) is not None:
                result = self._controller.get_low_stock()
                if result["success"]:
                    low_stock = result["data"]
            
            # Fallback to report cache if controller is not wired or failed
            if not low_stock and self._report_data:
                low_stock = self._report_data.get("low_stock") or []

            for idx, item in enumerate(low_stock, 1):
                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("name", "—"),
                        item.get("stock", 0.0),
                        item.get("location") or "—",
                    ),
                )

