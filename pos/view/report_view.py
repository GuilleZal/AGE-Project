"""Report view — modular dashboard layout with KPIs, top products,
low stock, payment methods chart, and expense summary.

Provides a period filter (Today, Week, Month, Custom range), metric
cards (total sales, operations, purchases, gross profit, margin %),
top products treeview with configurable limit, low stock treeview,
a reserved frame for payment methods chart, and an expense summary
ticket-style panel.
"""

import tkinter as tk
import unicodedata
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
from pos.view.widgets.report_summary_dialog import ReportSummaryDialog


def _normalize_category_name(name: str) -> str:
    """Normalize string by converting to lowercase and stripping accents."""
    if not name:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', name)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip()


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
        role: str = "",
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}
        self._role = role

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
        self._generated_start_date: str = ""
        self._generated_end_date: str = ""

        # Theme-aware border color for module separation
        self._border_color = theme.get_contrast_map()["search_border"]
        self._is_compact = (theme.get_resolution() == "800x600")

        # Configure main grid: 4 rows, 2 columns
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=0)   # top bar
        self.grid_rowconfigure(1, weight=0)   # report title label (if admin/gerente)
        self.grid_rowconfigure(2, weight=0)   # KPIs
        self.grid_rowconfigure(3, weight=1)   # data panel

        # --- Row 0: Top bar (period selector + buttons) ---
        self._build_top_bar()

        # --- Row 1: Report Title Label ---
        self._report_title_label = ctk.CTkLabel(
            self,
            text="",
            font=theme.scaled_font(13, weight="bold"),
            text_color="#4CAF50",
        )
        pady_title = (2, 2) if self._is_compact else (5, 5)
        self._report_title_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=pady_title)
        self._report_title_label.grid_remove()

        # --- Row 2: KPI cards ---
        self._build_kpi_panel()

        # --- Row 3: Data panel (2 columns) ---
        self._build_data_panel()

        # Populate initial placeholder table state
        self._populate_table()

    # ------------------------------------------------------------------ UI builders ---

    def _build_top_bar(self) -> None:
        """Build the top bar with period selector and export button."""
        top_bar = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        pady_top = (5, 2) if self._is_compact else (10, 5)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=pady_top)
        top_bar.grid_columnconfigure(1, weight=1)  # spacer

        # Left side: period selector
        selector_frame = ctk.CTkFrame(top_bar, fg_color="transparent", border_width=0)
        pady_selector = 4 if self._is_compact else 8
        selector_frame.grid(row=0, column=0, sticky="w", padx=5, pady=pady_selector)

        ctk.CTkLabel(
            selector_frame,
            text="Período:",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(side="left", padx=(15 if not self._is_compact else 5, 5))

        self._period_var = tk.StringVar(value="Hoy")
        self._period_menu = ctk.CTkOptionMenu(
            selector_frame,
            values=self.PERIOD_OPTIONS_ORDER,
            variable=self._period_var,
            width=110 if self._is_compact else 140,
            command=self._handle_period_changed,
        )
        self._period_menu.pack(side="left", padx=5)

        # Custom date range
        self._custom_frame = ctk.CTkFrame(selector_frame, fg_color="transparent", border_width=0)
        self._custom_frame.pack(side="left", padx=4 if self._is_compact else 10)

        ctk.CTkLabel(
            self._custom_frame, text="Desde:", font=theme.scaled_font(12)
        ).pack(side="left", padx=1 if self._is_compact else 2)
        self._start_entry = DateEntry(
            self._custom_frame,
            width=9 if self._is_compact else 11,
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
        ).pack(side="left", padx=(2, 1) if self._is_compact else (5, 2))
        self._end_entry = DateEntry(
            self._custom_frame,
            width=9 if self._is_compact else 11,
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
            width=110 if self._is_compact else 130,
            command=self._handle_generate,
        ).pack(side="left", padx=(10, 5) if self._is_compact else (15, 10))

        # Right side: view/export summary button
        self._view_resumen_btn = ctk.CTkButton(
            top_bar,
            text="Ver/Exportar resumen",
            width=145 if self._is_compact else 200,
            height=30 if self._is_compact else 35,
            font=theme.scaled_font(12, weight="bold") if self._is_compact else theme.scaled_font(13, weight="bold"),
            fg_color="#3b3b3b",
            command=self._handle_view_summary,
        )
        self._view_resumen_btn.grid(row=0, column=2, sticky="e", padx=(10, 15), pady=pady_selector)

    def _build_kpi_panel(self) -> None:
        """Build the KPI cards row with 5 metric cards."""
        kpi_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        pady_kpi = 2 if self._is_compact else 5
        kpi_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=pady_kpi)

        # Configure 5 equal columns
        for col in range(5):
            kpi_frame.grid_columnconfigure(col, weight=1)

        self._metric_cards: dict[str, ctk.CTkLabel] = {}

        avg_exp_title = "Monto Promedio por Venta" if getattr(self, "_role", "") == "gerente" else "Gasto Promedio"
        
        role = getattr(self, "_role", "")
        if role in ("gerente", "admin"):
            profit_title = "Ganancia Neta"
            margin_title = "Margen Neto"
        else:
            profit_title = "Ganancia Bruta"
            margin_title = "Margen Bruto"

        card_defs = [
            ("Ventas Totales", "total_ventas", 0, "$0", "#2b2b2b"),
            ("Operaciones", "operaciones", 1, "0", "#2b2b2b"),
            (avg_exp_title, "gasto_promedio", 2, "$0", "#2b2b2b"),
            (profit_title, "ganancia_bruta", 3, "$0", "#2b2b2b"),
            (margin_title, "margen_bruto", 4, "0%", "#2b2b2b"),
        ]

        pady_card = 4 if self._is_compact else 10
        for label, key, col, default, color in card_defs:
            card = ctk.CTkFrame(
                kpi_frame,
                fg_color=color,
                corner_radius=8,
            )
            card.grid(row=0, column=col, padx=5, pady=pady_card, sticky="nsew")

            pady_lbl_top = (4, 1) if self._is_compact else (8, 2)
            ctk.CTkLabel(
                card,
                text=label,
                font=theme.scaled_font(11),
                text_color="#888",
            ).pack(pady=pady_lbl_top)

            pady_lbl_bottom = (0, 4) if self._is_compact else (0, 8)
            value_lbl = ctk.CTkLabel(
                card,
                text=default,
                font=theme.scaled_font(20, weight="bold"),
            )
            value_lbl.pack(pady=pady_lbl_bottom)
            self._metric_cards[key] = value_lbl

    def _build_data_panel(self) -> None:
        """Build the data panel with a full-width unified table."""
        # Full-width unified table (Top products / Low stock)
        left_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=2, border_color=self._border_color)
        pady_data = 2 if self._is_compact else 5
        left_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=pady_data)
        
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
        self._table_type_var = tk.StringVar(value="Seleccionar reporte")
        self._table_selector = ctk.CTkComboBox(
            self._table_header,
            values=[
                "Seleccionar reporte",
                "Top productos más vendidos",
                "Productos bajo stock",
                "Ventas por método de pago",
                "Ventas por categoría",
                "Historial de devoluciones",
                "Resumen de cajas cerradas",
            ],
            variable=self._table_type_var,
            width=180 if self._is_compact else 220,
            height=28,
            state="readonly",
            command=self._handle_table_type_changed,
        )
        self._table_selector.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self._table_selector.set("Seleccionar reporte")

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

        # Category controls frame (manager & admin only)
        if getattr(self, "_role", "") in ("gerente", "admin"):
            self._category_controls_frame = ctk.CTkFrame(self._table_header, fg_color="transparent")
            self._category_controls_frame.grid(row=0, column=2, sticky="w", padx=5)
            self._category_controls_frame.grid_remove()

            ctk.CTkLabel(
                self._category_controls_frame,
                text="Categoría:",
                font=theme.scaled_font(12),
            ).pack(side="left", padx=2)

            self._category_var = tk.StringVar(value="Todas")
            self._category_selector = ctk.CTkComboBox(
                self._category_controls_frame,
                values=["Todas"],
                variable=self._category_var,
                width=150,
                height=26,
                state="readonly",
                command=self._handle_category_filter_changed,
            )
            self._category_selector.pack(side="left", padx=5)

        # Export button (CSV)
        self._export_table_btn = ctk.CTkButton(
            self._table_header,
            text="Exportar CSV",
            width=100 if self._is_compact else 130,
            height=28,
            fg_color="#3b3b3b",
            command=self._handle_export_table,
        )

        # Export Excel button
        self._export_excel_btn = ctk.CTkButton(
            self._table_header,
            text="Exportar Excel",
            width=100 if self._is_compact else 130,
            height=28,
            fg_color="#1f6f3a",
            command=self._handle_export_excel_click,
        )

        # Export PDF button
        self._export_pdf_btn = ctk.CTkButton(
            self._table_header,
            text="Exportar PDF",
            width=100 if self._is_compact else 130,
            height=28,
            fg_color="#c0392b",
            command=self._handle_export_pdf_click,
        )

        self._table_header.grid_columnconfigure(3, weight=1) # Spacer pushes export button

        if getattr(self, "_role", "") == "admin":
            self._export_table_btn.grid(row=0, column=4, sticky="e", padx=(10, 5), pady=8)
        if getattr(self, "_role", "") in ("gerente", "admin"):
            self._export_excel_btn.grid(row=0, column=5, sticky="e", padx=(5, 5), pady=8)
            self._export_pdf_btn.grid(row=0, column=6, sticky="e", padx=(5, 10), pady=8)

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
            height=5 if self._is_compact else 10,
        )

        self._report_tree.bind("<B1-Motion>", self._on_resize_motion)
        self._report_tree.bind("<ButtonRelease-1>", self._on_resize_release)

        self._report_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self._report_tree.yview)
        self._report_hscroll = ttk.Scrollbar(left_frame, orient="horizontal", command=self._report_tree.xview)
        self._report_tree.configure(yscrollcommand=self._report_scroll.set, xscrollcommand=self._report_hscroll.set)

        self._report_tree.grid(row=1, column=0, sticky="nsew")
        self._report_scroll.grid(row=1, column=1, sticky="ns")
        self._report_hscroll.grid(row=2, column=0, columnspan=2, sticky="ew")

    # ---------------------------------------------------------------- public ---

    def update_report(self, data: dict[str, Any]) -> None:
        """Refresh metrics and trees with report *data*."""
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
        # Gasto Promedio KPI
        self._metric_cards["gasto_promedio"].configure(
            text=f"${int(float(sales.get('avg_ticket', 0))):,}"
        )
        role = getattr(self, "_role", "")
        if role in ("gerente", "admin"):
            total_sales = sales.get("total", 0)
            cost = profit.get("cost", 0)
            returns_total = expenses.get("returns_total", 0)
            ganancia_bruta = total_sales - cost
            ganancia_neta = ganancia_bruta - returns_total
            margin = (ganancia_neta / total_sales * 100) if total_sales > 0 else 0.0

            self._metric_cards["ganancia_bruta"].configure(
                text=f"${int(float(ganancia_neta)):,}"
            )
            self._metric_cards["margen_bruto"].configure(
                text=f"{margin:.1f}%"
            )
        else:
            self._metric_cards["ganancia_bruta"].configure(
                text=f"${int(float(profit.get('profit', 0))):,}"
            )
            margin = profit.get("margin_pct", 0)
            self._metric_cards["margen_bruto"].configure(
                text=f"{margin:.1f}%"
            )

        # Update unified table
        self._populate_table()

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

    def refresh_report(self) -> None:
        """Regenerate the report using the currently selected or generated dates."""
        self._handle_generate()

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

        # Populate category filter values if role is gerente/admin
        if getattr(self, "_role", "") in ("gerente", "admin"):
            self._update_categories_filter()

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
            self._generated_start_date = start.split(" ")[0]
            self._generated_end_date = end.split(" ")[0]
            self.update_report(data)
            self._update_payment_chart(data.get("payment_methods", []))

            # Update title label for admin/gerente
            if getattr(self, "_role", "") in ("admin", "gerente"):
                start_date = self._generated_start_date
                end_date = self._generated_end_date
                self._report_title_label.configure(text=f"Reporte desde: {start_date} hasta: {end_date}")
                self._report_title_label.grid()
            else:
                self._report_title_label.configure(text="")
                self._report_title_label.grid_remove()
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

    def _controller_export_top(self, export_format: str = "csv") -> None:
        """Export top products to CSV, Excel or PDF via file dialog."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        top_products = self._report_data.get("top_products") or []
        if not top_products:
            messagebox.showwarning(
                "Sin datos",
                "No hay datos de productos más vendidos para exportar.",
            )
            return

        title_text = "Exportar Top Productos"
        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        init_file = f"Top_Productos_{start_date}_a_{end_date}" if start_date else "Top_Productos"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        export_data = []
        for idx, item in enumerate(top_products, 1):
            qty = float(item.get("total_quantity", 0.0))
            unit_type = item.get("unit_type", "Unidad")
            if unit_type == "Kg":
                qty_val = f"{qty:.2f} kg"
            else:
                qty_val = f"{int(qty)} u."

            export_data.append({
                "Nro": idx,
                "Producto": item.get("name", "—"),
                "Cantidad": qty_val,
                "Monto Total": f"${item.get('total_amount', 0):,}",
            })

        self._execute_export(export_data, filepath, "Top Productos")

    def _controller_export_faltantes(self, export_format: str = "csv") -> None:
        """Export low stock products to CSV, Excel or PDF via file dialog."""
        low_stock = []
        if getattr(self, "_controller", None) is not None:
            result = self._controller.get_low_stock()
            if result["success"]:
                low_stock = result["data"]
        
        if not low_stock and self._report_data:
            low_stock = self._report_data.get("low_stock") or []

        if not low_stock:
            messagebox.showwarning(
                "Sin datos",
                "No hay productos bajo stock para exportar.",
            )
            return

        title_text = "Exportar Productos Bajo Stock"
        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        init_file = f"Productos_Bajo_Stock_{start_date}_a_{end_date}" if start_date else "Productos_Bajo_Stock"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        # Format low stock data for export
        export_data = []
        for idx, item in enumerate(low_stock, 1):
            stock_val = item.get("stock", 0.0)
            unit_type = item.get("unit_type", "Unidad")
            unit_suffix = "u." if unit_type == "Unidad" else "Kg"
            
            phys_stock = max(0.0, stock_val)
            deficit = abs(stock_val) if stock_val < 0 else 0.0
            
            if unit_type == "Unidad":
                phys_stock_str = f"{int(phys_stock)} {unit_suffix}"
                deficit_str = f"{int(deficit)} {unit_suffix}" if deficit > 0 else f"0 {unit_suffix}"
            else:
                phys_stock_str = f"{phys_stock:.2f} {unit_suffix}".rstrip('0').rstrip('.')
                deficit_str = f"{deficit:.2f} {unit_suffix}".rstrip('0').rstrip('.') if deficit > 0 else f"0 {unit_suffix}"

            export_data.append({
                "Nro": idx,
                "Producto": item.get("name", "—"),
                "Stock Actual": phys_stock_str,
                "Faltante": deficit_str,
                "Ubicación": item.get("location") or "—",
            })

        self._execute_export(export_data, filepath, "Productos Bajo Stock")

    # --------------------------------------------------------------- private ---
    def _on_resize_motion(self, event: Any) -> None:
        self.after(10, self._adjust_column_widths)

    def _on_resize_release(self, event: Any) -> None:
        self._adjust_column_widths()

    def _adjust_column_widths(self) -> None:
        if not hasattr(self, "_prev_widths") or not self._prev_widths:
            self._save_current_widths()
            return

        cols = self._report_tree["columns"]
        changed_col_idx = None
        diff = 0
        for i, c in enumerate(cols):
            try:
                curr_w = self._report_tree.column(c, "width")
            except Exception:
                continue
            prev_w = self._prev_widths.get(c, curr_w)
            if curr_w != prev_w:
                changed_col_idx = i
                diff = curr_w - prev_w
                break

        if changed_col_idx is None or diff == 0:
            return

        if changed_col_idx < len(cols) - 1:
            target_idx = changed_col_idx + 1
        else:
            target_idx = changed_col_idx - 1

        c = cols[changed_col_idx]
        target_c = cols[target_idx]

        curr_w = self._report_tree.column(c, "width")
        target_w = self._report_tree.column(target_c, "width")
        
        new_target_w = target_w - diff
        min_target_w = self._report_tree.column(target_c, "minwidth") or 20
        
        if new_target_w < min_target_w:
            new_target_w = min_target_w
            actual_diff = target_w - new_target_w
            new_curr_w = self._prev_widths[c] + actual_diff
        else:
            new_curr_w = curr_w

        try:
            self._report_tree.column(c, width=new_curr_w)
            self._report_tree.column(target_c, width=new_target_w)
        except Exception:
            pass

        self._save_current_widths()

    def _save_current_widths(self) -> None:
        try:
            cols = self._report_tree["columns"]
            self._prev_widths = {c: self._report_tree.column(c, "width") for c in cols}
        except Exception:
            self._prev_widths = {}
        
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

    def _handle_view_summary(self) -> None:
        """Open the modal dialog displaying the income and expense summary."""
        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de ver el resumen.",
                parent=self,
            )
            return
        
        dialog = ReportSummaryDialog(self, self._report_data, role=getattr(self, "_role", ""))
        self.wait_window(dialog)

    def _handle_export_top(self, export_format: str = "csv") -> None:
        """Handle export top products button click."""
        if self._on_export_top is not None:
            try:
                self._on_export_top(export_format)
            except TypeError:
                self._on_export_top()

    def _handle_export_faltantes(self, export_format: str = "csv") -> None:
        """Handle export low stock button click."""
        if self._on_export_faltantes is not None:
            try:
                self._on_export_faltantes(export_format)
            except TypeError:
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
        if value == "Ventas por categoría" and getattr(self, "_role", "") in ("gerente", "admin"):
            self._update_categories_filter()
        self._populate_table()

    def _handle_category_filter_changed(self, value: str) -> None:
        """Redraw/reload table data when category filter changes."""
        self._populate_table()

    def _update_categories_filter(self) -> None:
        """Fetch categories and populate the category selector."""
        if not hasattr(self, "_category_selector") or not self._category_selector:
            return
            
        categories = []
        if getattr(self, "_controller", None) is not None:
            res = self._controller.get_categories()
            if res["success"]:
                categories = res["data"]
        
        self._categories_list = categories
        
        self._category_name_to_id = {"Todas": "all"}
        combo_values = ["Todas"]
        seen_normalized = set()
        for c in categories:
            name = c["name"]
            norm_name = _normalize_category_name(name)
            self._category_name_to_id[name] = c["id"]
            if norm_name not in seen_normalized:
                seen_normalized.add(norm_name)
                combo_values.append(name)
            
        self._category_name_to_id["Sin categoría"] = None
        combo_values.append("Sin categoría")
        
        # Temporarily disconnect callback to avoid infinite loop
        original_command = self._category_selector.cget("command")
        self._category_selector.configure(command=None)
        
        current_val = self._category_selector.get()
        self._category_selector.configure(values=combo_values)
        if current_val in combo_values:
            self._category_selector.set(current_val)
        else:
            self._category_selector.set("Todas")
            
        # Reconnect callback
        self._category_selector.configure(command=original_command)

    def _handle_export_table(self) -> None:
        """Handle export button click dynamically based on selected table type."""
        table_type = self._table_selector.get()
        if table_type == "Seleccionar reporte":
            messagebox.showwarning(
                "Seleccione un reporte",
                "Por favor seleccione un reporte válido antes de exportar.",
            )
            return

        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        if table_type == "Top productos más vendidos":
            self._handle_export_top(export_format="csv")
        elif table_type == "Productos bajo stock":
            self._handle_export_faltantes(export_format="csv")
        elif table_type == "Ventas por método de pago":
            self._handle_export_payment_methods(export_format="csv")
        elif table_type == "Ventas por categoría":
            self._handle_export_category_sales(export_format="csv")
        elif table_type == "Historial de devoluciones":
            self._handle_export_returns_history(export_format="csv")
        elif table_type == "Resumen de cajas cerradas":
            self._handle_export_closed_registers(export_format="csv")

    def _handle_export_excel_click(self) -> None:
        """Handle Excel export button click dynamically based on selected table type."""
        table_type = self._table_selector.get()
        if table_type == "Seleccionar reporte":
            messagebox.showwarning(
                "Seleccione un reporte",
                "Por favor seleccione un reporte válido antes de exportar.",
            )
            return

        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        # Double check role permission (only for gerente and admin)
        if getattr(self, "_role", "") not in ("gerente", "admin"):
            messagebox.showerror(
                "Error de Permisos",
                "El rol actual no tiene permitida la función de exportación a Excel.",
            )
            return

        if table_type == "Top productos más vendidos":
            self._handle_export_top(export_format="excel")
        elif table_type == "Productos bajo stock":
            self._handle_export_faltantes(export_format="excel")
        elif table_type == "Ventas por método de pago":
            self._handle_export_payment_methods(export_format="excel")
        elif table_type == "Ventas por categoría":
            self._handle_export_category_sales(export_format="excel")
        elif table_type == "Historial de devoluciones":
            self._handle_export_returns_history(export_format="excel")
        elif table_type == "Resumen de cajas cerradas":
            self._handle_export_closed_registers(export_format="excel")

    def _handle_export_pdf_click(self) -> None:
        """Handle PDF export button click dynamically based on selected table type."""
        table_type = self._table_selector.get()
        if table_type == "Seleccionar reporte":
            messagebox.showwarning(
                "Seleccione un reporte",
                "Por favor seleccione un reporte válido antes de exportar.",
            )
            return

        if not self._report_data:
            messagebox.showwarning(
                "Sin datos",
                "Genere un reporte antes de exportar.",
            )
            return

        # Double check role permission (only for gerente and admin)
        if getattr(self, "_role", "") not in ("gerente", "admin"):
            messagebox.showerror(
                "Error de Permisos",
                "El rol actual no tiene permitida la función de exportación a PDF.",
            )
            return

        if table_type == "Top productos más vendidos":
            self._handle_export_top(export_format="pdf")
        elif table_type == "Productos bajo stock":
            self._handle_export_faltantes(export_format="pdf")
        elif table_type == "Ventas por método de pago":
            self._handle_export_payment_methods(export_format="pdf")
        elif table_type == "Ventas por categoría":
            self._handle_export_category_sales(export_format="pdf")
        elif table_type == "Historial de devoluciones":
            self._handle_export_returns_history(export_format="pdf")
        elif table_type == "Resumen de cajas cerradas":
            self._handle_export_closed_registers(export_format="pdf")

    def _handle_export_payment_methods(self, export_format: str = "csv") -> None:
        """Export payment methods to CSV, Excel or PDF via file dialog."""
        payment_methods = self._report_data.get("payment_methods") or []
        if not payment_methods:
            messagebox.showwarning(
                "Sin datos",
                "No hay datos de métodos de pago para exportar.",
            )
            return

        title_text = "Exportar Ventas por Método de Pago"
        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        init_file = f"Ventas_Metodo_Pago_{start_date}_a_{end_date}" if start_date else "Ventas_Metodo_Pago"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        export_data = []
        for idx, item in enumerate(payment_methods, 1):
            export_data.append({
                "Nro": idx,
                "Método de Pago": item.get("payment_method", "—"),
                "Operaciones": int(item.get("sale_count", 0)),
                "Monto Total": f"${item.get('total_amount', 0):,}",
                "Porcentaje": f"{item.get('percentage', 0.0):.1f}%",
            })

        self._execute_export(export_data, filepath, "Ventas por Método de Pago")

    def _handle_export_category_sales(self, export_format: str = "csv") -> None:
        """Export category sales to CSV, Excel or PDF via file dialog."""
        selected_cat = self._category_selector.get() if hasattr(self, "_category_selector") else "Todas"
        
        if selected_cat == "Todas":
            cat_id = "all"
        elif selected_cat == "Sin categoría":
            cat_id = None
        else:
            target_norm = _normalize_category_name(selected_cat)
            matching_ids = []
            categories_list = getattr(self, "_categories_list", [])
            for c in categories_list:
                if _normalize_category_name(c["name"]) == target_norm:
                    matching_ids.append(c["id"])
            
            if len(matching_ids) == 1:
                cat_id = matching_ids[0]
            else:
                cat_id = matching_ids

        if cat_id != "all":
            # Export Top Products of this Category
            start_date = getattr(self, "_generated_start_date", "")
            end_date = getattr(self, "_generated_end_date", "")
            limit = int(self._top_limit_var.get())

            top_products = []
            if getattr(self, "_controller", None) is not None:
                res = self._controller.get_top_products_by_category(start_date, end_date, cat_id, limit)
                if res["success"]:
                    top_products = res["data"]

            if not top_products:
                messagebox.showwarning(
                    "Sin datos",
                    f"No hay datos de productos más vendidos para la categoría '{selected_cat}' para exportar.",
                )
                return

            title_text = f"Exportar Más Vendidos - {selected_cat}"
            if export_format == "excel":
                ext = ".xlsx"
                ftypes = [("Excel", "*.xlsx")]
            elif export_format == "pdf":
                ext = ".pdf"
                ftypes = [("PDF", "*.pdf")]
            else:
                ext = ".csv"
                ftypes = [("CSV", "*.csv")]

            init_file = f"Mas_Vendidos_{selected_cat.replace(' ', '_')}_{start_date}_a_{end_date}" if start_date else f"Mas_Vendidos_{selected_cat.replace(' ', '_')}"

            filepath = filedialog.asksaveasfilename(
                title=title_text,
                defaultextension=ext,
                filetypes=ftypes,
                initialfile=init_file,
            )
            if not filepath:
                return

            export_data = []
            for idx, item in enumerate(top_products, 1):
                qty = float(item.get("total_quantity", 0.0))
                unit_type = item.get("unit_type", "Unidad")
                if unit_type == "Kg":
                    qty_str = f"{qty:.2f} kg"
                else:
                    qty_str = f"{int(qty)} u."

                export_data.append({
                    "Nro": idx,
                    "Producto": item.get("name", "—"),
                    "Cantidad": qty_str,
                    "Monto Total": f"${item.get('total_amount', 0):,}",
                })

            self._execute_export(export_data, filepath, f"Productos Más Vendidos - {selected_cat}")
            return

        sales_by_category = self._report_data.get("sales_by_category") or []
        if not sales_by_category:
            messagebox.showwarning(
                "Sin datos",
                "No hay datos de ventas por categoría para exportar.",
            )
            return

        title_text = "Exportar Ventas por Categoría"
        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        init_file = f"Ventas_Categoria_{start_date}_a_{end_date}" if start_date else "Ventas_Categoria"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        export_data = []
        for idx, item in enumerate(sales_by_category, 1):
            qty_unit = item.get("qty_unit", 0)
            qty_kg = item.get("qty_kg", 0.0)
            
            qty_unit_display = str(int(qty_unit))
            qty_kg_display = f"{qty_kg:.2f}".rstrip('0').rstrip('.') if not float(qty_kg).is_integer() else str(int(qty_kg))
            
            export_data.append({
                "Nro": idx,
                "Categoría": item.get("category_name", "—"),
                "Cant. Unidades": qty_unit_display,
                "Cant. Kg": qty_kg_display,
                "Monto Total": f"${item.get('total_amount', 0):,}",
            })

        self._execute_export(export_data, filepath, "Ventas por Categoría")

    def _handle_export_returns_history(self, export_format: str = "csv") -> None:
        """Export returns history to CSV, Excel or PDF via file dialog."""
        returns_history = self._report_data.get("returns_history") or []
        if not returns_history:
            messagebox.showwarning(
                "Sin datos",
                "No hay historial de devoluciones para exportar.",
            )
            return

        title_text = "Exportar Historial de Devoluciones"
        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        init_file = f"Historial_Devoluciones_{start_date}_a_{end_date}" if start_date else "Historial_Devoluciones"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        export_data = []
        for idx, item in enumerate(returns_history, 1):
            qty = item.get("quantity", 0)
            qty_display = f"{qty:.2f}".rstrip('0').rstrip('.') if not float(qty).is_integer() else str(int(qty))
            export_data.append({
                "Nro": idx,
                "Fecha/Hora": item.get("created_at", "—"),
                "Producto": item.get("product_name", "—"),
                "Cantidad": qty_display,
                "Reembolso": f"${item.get('refund_amount', 0):,}",
                "Motivo": item.get("reason") or "—",
            })

        self._execute_export(export_data, filepath, "Historial de Devoluciones")

    def _handle_export_closed_registers(self, export_format: str = "csv") -> None:
        """Export closed registers summary to CSV, Excel or PDF via file dialog."""
        closed_registers = self._report_data.get("closed_registers") or []
        if not closed_registers:
            messagebox.showwarning(
                "Sin datos",
                "No hay datos de cajas cerradas para exportar.",
            )
            return

        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")
        title_text = "Exportar Resumen de Cajas Cerradas"

        if export_format == "excel":
            ext = ".xlsx"
            ftypes = [("Excel", "*.xlsx")]
        elif export_format == "pdf":
            ext = ".pdf"
            ftypes = [("PDF", "*.pdf")]
        else:
            ext = ".csv"
            ftypes = [("CSV", "*.csv")]

        init_file = f"Resumen_Cajas_{start_date}_a_{end_date}" if start_date else "Resumen_Cajas"

        filepath = filedialog.asksaveasfilename(
            title=title_text,
            defaultextension=ext,
            filetypes=ftypes,
            initialfile=init_file,
        )
        if not filepath:
            return

        export_data = []
        is_admin_or_gerente = getattr(self, "_role", "") in ("admin", "gerente")
        decimals = 0 if is_admin_or_gerente else 2
        for idx, item in enumerate(closed_registers, 1):
            export_data.append({
                "Nro": idx,
                "Caja ID": item.get("id"),
                "Apertura": item.get("opening_time", "—"),
                "Cierre": item.get("closing_time", "—"),
                "Ventas": item.get("sales_count", 0),
                "Ganancia Neta": f"${float(item.get('profit', 0)):,.{decimals}f}",
            })

        self._execute_export(export_data, filepath, "Resumen de Cajas Cerradas")

    def _execute_export(self, export_data: list[dict], filepath: str, title: str) -> None:
        """Helper to run the export logic via the controller."""
        start_date = getattr(self, "_generated_start_date", "")
        end_date = getattr(self, "_generated_end_date", "")

        if getattr(self, "_controller", None) is not None:
            if filepath.lower().endswith(".xlsx"):
                res = self._controller.export_to_excel(export_data, filepath, start_date, end_date, title=title)
            elif filepath.lower().endswith(".pdf"):
                res = self._controller.export_to_pdf(export_data, filepath, start_date, end_date, title=title)
            else:
                res = self._controller.export_to_csv(export_data, filepath, start_date, end_date, title=title)
            
            if res["success"]:
                messagebox.showinfo(
                    "Exportación exitosa",
                    f"Se exportó el reporte '{title}' a:\n{res['data']}",
                )
            else:
                messagebox.showerror(
                    "Error de exportación",
                    f"No se pudo exportar:\n{res['error']}",
                )
        else:
            messagebox.showerror(
                "Error",
                "El controlador no está disponible.",
            )

    def _populate_table(self) -> None:
        """Populate the unified treeview based on the selected option."""
        # Clear existing items
        for child in self._report_tree.get_children():
            self._report_tree.delete(child)

        table_type = self._table_selector.get()
        
        # Hide/Show top controls frame
        if hasattr(self, "_top_controls_frame") and self._top_controls_frame:
            show_top_limit = False
            if table_type == "Top productos más vendidos":
                show_top_limit = True
            elif table_type == "Ventas por categoría":
                selected_cat = self._category_selector.get() if hasattr(self, "_category_selector") else "Todas"
                if selected_cat != "Todas":
                    show_top_limit = True

            if show_top_limit:
                self._top_controls_frame.grid()
            else:
                self._top_controls_frame.grid_remove()

        # Hide/Show category controls frame
        if hasattr(self, "_category_controls_frame") and self._category_controls_frame:
            if table_type == "Ventas por categoría":
                self._category_controls_frame.grid()
            else:
                self._category_controls_frame.grid_remove()

        if table_type == "Seleccionar reporte":
            # Reconfigure treeview for placeholder message
            self._report_tree.configure(columns=("col0",))
            self._report_tree.heading("col0", text="Seleccionar reporte")
            self._report_tree.column("col0", width=600, minwidth=200, anchor="center")
            self._report_tree.insert(
                "",
                "end",
                values=("Seleccione un tipo de reporte de la lista de arriba y haga clic en 'Generar reporte'.",)
            )
            return

        elif table_type == "Top productos más vendidos":
            columns = ("col0", "col1", "col2", "col3")
            self._report_tree.configure(columns=columns)
            
            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Producto")
            self._report_tree.heading("col2", text="Cantidad")
            self._report_tree.heading("col3", text="Monto total")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
            self._report_tree.column("col1", width=250, minwidth=50, stretch=True, anchor="w")
            self._report_tree.column("col2", width=100, minwidth=30, anchor="center")
            self._report_tree.column("col3", width=140, minwidth=40, anchor="e")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "float", "col3": "int"}
            add_sorting_to_treeview(self._report_tree, list(columns), column_types)

            # Populate data
            top_products = self._report_data.get("top_products") or []
            for idx, item in enumerate(top_products, 1):
                qty = float(item.get("total_quantity", 0.0))
                unit_type = item.get("unit_type", "Unidad")
                if unit_type == "Kg":
                    qty_str = f"{qty:.2f} kg"
                else:
                    qty_str = f"{int(qty)} u."

                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("name", "—"),
                        qty_str,
                        f"${item.get('total_amount', 0):,}",
                    ),
                )

        elif table_type == "Productos bajo stock":
            columns = ("col0", "col1", "col2", "col3")
            self._report_tree.configure(columns=columns)

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Producto")
            self._report_tree.heading("col2", text="Stock Actual")
            self._report_tree.heading("col3", text="Ubicación")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
            self._report_tree.column("col1", width=250, minwidth=50, stretch=True, anchor="w")
            self._report_tree.column("col2", width=110, minwidth=30, anchor="center")
            self._report_tree.column("col3", width=160, minwidth=40, anchor="w")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "float", "col3": "str"}
            add_sorting_to_treeview(self._report_tree, list(columns), column_types)

            # Populate data
            low_stock = []
            if getattr(self, "_controller", None) is not None:
                result = self._controller.get_low_stock()
                if result["success"]:
                    low_stock = result["data"]
            
            if not low_stock and self._report_data:
                low_stock = self._report_data.get("low_stock") or []

            for idx, item in enumerate(low_stock, 1):
                stock_val = item.get("stock", 0.0)
                unit_type = item.get("unit_type", "Unidad")
                unit_suffix = "u." if unit_type == "Unidad" else "Kg"
                
                try:
                    f_stock = float(stock_val)
                    if f_stock < 0:
                        phys_stock = 0.0
                        deficit = abs(f_stock)
                        formatted_deficit = f"{deficit:.2f}".rstrip('0').rstrip('.') if not deficit.is_integer() else str(int(deficit))
                        stock_display = f"0 {unit_suffix} (Faltante: {formatted_deficit})"
                    else:
                        formatted_stock = f"{f_stock:.2f}".rstrip('0').rstrip('.') if not f_stock.is_integer() else str(int(f_stock))
                        stock_display = f"{formatted_stock} {unit_suffix}"
                except ValueError:
                    stock_display = str(stock_val)

                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("name", "—"),
                        stock_display,
                        item.get("location") or "—",
                    ),
                )

        elif table_type == "Ventas por método de pago":
            columns = ("col0", "col1", "col2", "col3", "col4")
            self._report_tree.configure(columns=columns)

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Método de Pago")
            self._report_tree.heading("col2", text="Operaciones")
            self._report_tree.heading("col3", text="Monto total")
            self._report_tree.heading("col4", text="Porcentaje")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
            self._report_tree.column("col1", width=200, minwidth=50, stretch=True, anchor="w")
            self._report_tree.column("col2", width=100, minwidth=30, anchor="center")
            self._report_tree.column("col3", width=140, minwidth=40, anchor="e")
            self._report_tree.column("col4", width=100, minwidth=30, anchor="center")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "int", "col3": "int", "col4": "float"}
            add_sorting_to_treeview(self._report_tree, list(columns), column_types)

            # Populate data
            payment_methods = self._report_data.get("payment_methods") or []
            for idx, item in enumerate(payment_methods, 1):
                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("payment_method", "—"),
                        int(item.get("sale_count", 0)),
                        f"${item.get('total_amount', 0):,}",
                        f"{item.get('percentage', 0.0):.1f}%",
                    ),
                )

        elif table_type == "Ventas por categoría":
            selected_cat = self._category_selector.get() if hasattr(self, "_category_selector") else "Todas"
            
            if selected_cat == "Todas":
                cat_id = "all"
            elif selected_cat == "Sin categoría":
                cat_id = None
            else:
                target_norm = _normalize_category_name(selected_cat)
                matching_ids = []
                categories_list = getattr(self, "_categories_list", [])
                for c in categories_list:
                    if _normalize_category_name(c["name"]) == target_norm:
                        matching_ids.append(c["id"])
                
                if len(matching_ids) == 1:
                    cat_id = matching_ids[0]
                else:
                    cat_id = matching_ids

            if cat_id == "all":
                columns = ("col0", "col1", "col2", "col3", "col4")
                self._report_tree.configure(columns=columns)

                # Set headings
                self._report_tree.heading("col0", text="#")
                self._report_tree.heading("col1", text="Categoría")
                self._report_tree.heading("col2", text="Cant. Unidades")
                self._report_tree.heading("col3", text="Cant. Kg")
                self._report_tree.heading("col4", text="Monto total")

                # Set column widths & alignments
                self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
                self._report_tree.column("col1", width=200, minwidth=50, stretch=True, anchor="w")
                self._report_tree.column("col2", width=120, minwidth=30, anchor="center")
                self._report_tree.column("col3", width=120, minwidth=30, anchor="center")
                self._report_tree.column("col4", width=140, minwidth=40, anchor="e")

                # Setup sorting
                column_types = {"col0": "int", "col1": "str", "col2": "int", "col3": "float", "col4": "int"}
                add_sorting_to_treeview(self._report_tree, list(columns), column_types)

                # Populate data
                sales_by_category = self._report_data.get("sales_by_category") or []
                for idx, item in enumerate(sales_by_category, 1):
                    qty_unit = item.get("qty_unit", 0)
                    qty_kg = item.get("qty_kg", 0.0)
                    
                    qty_unit_display = str(int(qty_unit))
                    qty_kg_display = f"{qty_kg:.2f}".rstrip('0').rstrip('.') if not float(qty_kg).is_integer() else str(int(qty_kg))
                    
                    self._report_tree.insert(
                        "",
                        "end",
                        values=(
                            idx,
                            item.get("category_name", "—"),
                            qty_unit_display,
                            qty_kg_display,
                            f"${item.get('total_amount', 0):,}",
                        ),
                    )
            else:
                # Top products for selected category
                columns = ("col0", "col1", "col2", "col3")
                self._report_tree.configure(columns=columns)
                
                # Set headings
                self._report_tree.heading("col0", text="#")
                self._report_tree.heading("col1", text="Producto")
                self._report_tree.heading("col2", text="Cantidad")
                self._report_tree.heading("col3", text="Monto total")

                # Set column widths & alignments
                self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
                self._report_tree.column("col1", width=250, minwidth=50, stretch=True, anchor="w")
                self._report_tree.column("col2", width=100, minwidth=30, anchor="center")
                self._report_tree.column("col3", width=140, minwidth=40, anchor="e")

                # Setup sorting
                column_types = {"col0": "int", "col1": "str", "col2": "float", "col3": "int"}
                add_sorting_to_treeview(self._report_tree, list(columns), column_types)

                # Fetch and populate data
                start_date = self._generated_start_date or (self._report_data.get("period") or {}).get("start", "")
                end_date = self._generated_end_date or (self._report_data.get("period") or {}).get("end", "")
                limit = int(self._top_limit_var.get())

                top_products = []
                if getattr(self, "_controller", None) is not None:
                    res = self._controller.get_top_products_by_category(start_date, end_date, cat_id, limit)
                    if res["success"]:
                        top_products = res["data"]

                for idx, item in enumerate(top_products, 1):
                    qty = float(item.get("total_quantity", 0.0))
                    unit_type = item.get("unit_type", "Unidad")
                    if unit_type == "Kg":
                        qty_str = f"{qty:.2f} kg"
                    else:
                        qty_str = f"{int(qty)} u."

                    self._report_tree.insert(
                        "",
                        "end",
                        values=(
                            idx,
                            item.get("name", "—"),
                            qty_str,
                            f"${item.get('total_amount', 0):,}",
                        ),
                    )

        elif table_type == "Historial de devoluciones":
            columns = ("col0", "col1", "col2", "col3", "col4", "col5")
            self._report_tree.configure(columns=columns)

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Fecha/Hora")
            self._report_tree.heading("col2", text="Producto")
            self._report_tree.heading("col3", text="Cantidad")
            self._report_tree.heading("col4", text="Reembolso")
            self._report_tree.heading("col5", text="Motivo")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
            self._report_tree.column("col1", width=140, minwidth=40, anchor="center")
            self._report_tree.column("col2", width=220, minwidth=50, stretch=True, anchor="w")
            self._report_tree.column("col3", width=90, minwidth=30, anchor="center")
            self._report_tree.column("col4", width=100, minwidth=30, anchor="e")
            self._report_tree.column("col5", width=160, minwidth=40, anchor="w")

            # Setup sorting
            column_types = {"col0": "int", "col1": "str", "col2": "str", "col3": "float", "col4": "int", "col5": "str"}
            add_sorting_to_treeview(self._report_tree, list(columns), column_types)

            # Populate data
            returns_history = self._report_data.get("returns_history") or []
            for idx, item in enumerate(returns_history, 1):
                qty = item.get("quantity", 0)
                qty_display = f"{qty:.2f}".rstrip('0').rstrip('.') if not float(qty).is_integer() else str(int(qty))
                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("created_at", "—"),
                        item.get("product_name", "—"),
                        qty_display,
                        f"${item.get('refund_amount', 0):,}",
                        item.get("reason") or "—",
                    ),
                )

        elif table_type == "Resumen de cajas cerradas":
            columns = ("col0", "col1", "col2", "col3", "col4", "col5")
            self._report_tree.configure(columns=columns)

            # Set headings
            self._report_tree.heading("col0", text="#")
            self._report_tree.heading("col1", text="Caja ID")
            self._report_tree.heading("col2", text="Apertura")
            self._report_tree.heading("col3", text="Cierre")
            self._report_tree.heading("col4", text="Ventas")
            self._report_tree.heading("col5", text="Ganancia Neta")

            # Set column widths & alignments
            self._report_tree.column("col0", width=50, minwidth=20, anchor="center")
            self._report_tree.column("col1", width=80, minwidth=30, anchor="center")
            self._report_tree.column("col2", width=180, minwidth=100, anchor="center")
            self._report_tree.column("col3", width=180, minwidth=100, anchor="center")
            self._report_tree.column("col4", width=80, minwidth=30, anchor="center")
            self._report_tree.column("col5", width=130, minwidth=50, anchor="e")

            # Setup sorting
            column_types = {
                "col0": "int",
                "col1": "int",
                "col2": "str",
                "col3": "str",
                "col4": "int",
                "col5": "int",
            }
            add_sorting_to_treeview(self._report_tree, list(columns), column_types)

            # Populate data
            closed_registers = self._report_data.get("closed_registers") or []
            is_admin_or_gerente = getattr(self, "_role", "") in ("admin", "gerente")
            decimals = 0 if is_admin_or_gerente else 2
            for idx, item in enumerate(closed_registers, 1):
                self._report_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        item.get("id"),
                        item.get("opening_time", "—"),
                        item.get("closing_time", "—"),
                        item.get("sales_count", 0),
                        f"${float(item.get('profit', 0)):,.{decimals}f}",
                    ),
                )

        self._save_current_widths()

