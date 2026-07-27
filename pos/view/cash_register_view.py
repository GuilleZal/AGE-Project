"""Cash register view — open/close lifecycle, balance panel, outflow
registration, and movement history.

Displays a live balance panel (opening amount, inflows, outflows, expected,
difference), open/close buttons, an outflow registration form, and a
history treeview of past cash register sessions.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import customtkinter as ctk
from tkcalendar import DateEntry

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme


class CashRegisterView(ctk.CTkFrame):
    """Cash register management tab.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Caja" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_open`` (amount), ``on_close``
        (amount, notes), ``on_outflow`` (type, amount, description),
        ``on_refresh``.
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    OUTFLOW_TYPES: list[tuple[str, str]] = [
        ("Pago a proveedor", "supplier_payment"),
        ("Gasto", "expense"),
    ]

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        cash_register_mode: str = "full",
        role: str = "",
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        callbacks = callbacks or {}
        self._cash_register_mode = cash_register_mode
        self._role = role

        self._on_open: Callable[[int], None] | None = callbacks.get(
            "on_open"
        )
        self._on_close: Callable[[int, str], None] | None = callbacks.get(
            "on_close"
        )
        self._on_outflow: (
            Callable[[str, int, str | None], None] | None
        ) = callbacks.get("on_outflow")
        self._on_refresh: Callable[[], None] | None = callbacks.get(
            "on_refresh"
        )

        self.grid_columnconfigure(0, weight=4, uniform="col")  # Panel izquierdo blindado (45%)
        self.grid_columnconfigure(1, weight=5, uniform="col")  # Panel derecho blindado (55%)
        self.grid_rowconfigure(0, weight=1)

        # =========================================================== left side

        contrast = theme.get_contrast_map()
        border_color = contrast["search_border"]

        self._left_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        # Colchón inferior asegurado para no chocar con el borde maestro
        self._left_frame.grid(
            row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 5)
        )
        self._left_frame.grid_columnconfigure(0, weight=1)

        # -- status header --
        self._status_label = ctk.CTkLabel(
            self._left_frame,
            text="CAJA CERRADA",
            font=theme.scaled_font(18, weight="bold"),
            text_color="#e74c3c",
        )
        self._status_label.grid(
            row=0, column=0, sticky="ew", padx=15, pady=(5, 2)
        )

        # -- balance panel --
        # -- balance container frame --
        self._balance_container = ctk.CTkFrame(self._left_frame, fg_color="transparent")
        self._balance_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        self._balance_container.grid_columnconfigure(0, weight=1)

        self._balance_labels: dict[str, ctk.CTkLabel] = {}

        # ----------------- Module 1: DATOS DE INICIO -----------------
        self._init_module_frame = ctk.CTkFrame(
            self._balance_container, fg_color="transparent", border_width=1, border_color=border_color
        )
        self._init_module_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self._init_module_frame.grid_columnconfigure(0, weight=1)
        self._init_module_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self._init_module_frame,
            text="DATOS DE INICIO",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            self._init_module_frame,
            text="Inicio efectivo",
            font=theme.scaled_font(12),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 8))

        self._balance_labels["initial"] = ctk.CTkLabel(
            self._init_module_frame,
            text="—",
            font=theme.scaled_font(12, weight="bold"),
            anchor="e",
        )
        self._balance_labels["initial"].grid(row=1, column=1, sticky="e", padx=12, pady=(2, 8))

        # ----------------- Module 2: FLUJO DE INGRESOS (Desglose) -----------------
        self._inflows_module_frame = ctk.CTkFrame(
            self._balance_container, fg_color="transparent", border_width=1, border_color=border_color
        )
        self._inflows_module_frame.grid(row=1, column=0, sticky="ew", pady=4)
        self._inflows_module_frame.grid_columnconfigure(0, weight=1)
        self._inflows_module_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self._inflows_module_frame,
            text="FLUJO DE INGRESOS (Desglose)",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        inflow_rows = [
            ("Efectivo", "inflow_cash"),
            ("Transferencia", "inflow_transfer"),
            ("Débito", "inflow_debit"),
            ("Crédito", "inflow_credit"),
        ]
        for idx, (lbl_txt, key) in enumerate(inflow_rows, start=1):
            pady_val = (2, 8) if idx == len(inflow_rows) else (2, 2)
            ctk.CTkLabel(
                self._inflows_module_frame,
                text=lbl_txt,
                font=theme.scaled_font(12),
                anchor="w",
            ).grid(row=idx, column=0, sticky="w", padx=12, pady=pady_val)

            self._balance_labels[key] = ctk.CTkLabel(
                self._inflows_module_frame,
                text="—",
                font=theme.scaled_font(12, weight="bold"),
                anchor="e",
            )
            self._balance_labels[key].grid(row=idx, column=1, sticky="e", padx=12, pady=pady_val)

        # ----------------- Module 3: FLUJO DE EGRESOS -----------------
        self._outflows_module_frame = ctk.CTkFrame(
            self._balance_container, fg_color="transparent", border_width=1, border_color=border_color
        )
        self._outflows_module_frame.grid(row=2, column=0, sticky="ew", pady=4)
        self._outflows_module_frame.grid_columnconfigure(0, weight=1)
        self._outflows_module_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self._outflows_module_frame,
            text="FLUJO DE EGRESOS",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        outflow_rows = [
            ("Pago a proveedores", "outflow_supplier"),
            ("Gastos", "outflow_expense"),
            ("Egresos Total", "outflow_total"),
        ]
        for idx, (lbl_txt, key) in enumerate(outflow_rows, start=1):
            pady_val = (2, 8) if idx == len(outflow_rows) else (2, 2)
            font_val = theme.scaled_font(12, weight="bold") if key == "outflow_total" else theme.scaled_font(12)
            
            ctk.CTkLabel(
                self._outflows_module_frame,
                text=lbl_txt,
                font=font_val,
                anchor="w",
            ).grid(row=idx, column=0, sticky="w", padx=12, pady=pady_val)

            self._balance_labels[key] = ctk.CTkLabel(
                self._outflows_module_frame,
                text="—",
                font=theme.scaled_font(12, weight="bold"),
                anchor="e",
            )
            self._balance_labels[key].grid(row=idx, column=1, sticky="e", padx=12, pady=pady_val)

        # ----------------- Module 4: ARQUEO EFECTIVO (Auditado) -----------------
        self._arqueo_module_frame = ctk.CTkFrame(
            self._balance_container, fg_color="transparent", border_width=1, border_color=border_color
        )
        self._arqueo_module_frame.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._arqueo_module_frame.grid_columnconfigure(0, weight=1)
        self._arqueo_module_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self._arqueo_module_frame,
            text="ARQUEO EFECTIVO (Auditado)",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            self._arqueo_module_frame,
            text="Esperado efectivo",
            font=theme.scaled_font(12),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(2, 2))

        self._balance_labels["expected_cash"] = ctk.CTkLabel(
            self._arqueo_module_frame,
            text="—",
            font=theme.scaled_font(12, weight="bold"),
            anchor="e",
        )
        self._balance_labels["expected_cash"].grid(row=1, column=1, sticky="e", padx=12, pady=(2, 2))

        ctk.CTkLabel(
            self._arqueo_module_frame,
            text="Final declarado efectivo",
            font=theme.scaled_font(12),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(2, 2))

        self._balance_labels["final_cash"] = ctk.CTkLabel(
            self._arqueo_module_frame,
            text="—",
            font=theme.scaled_font(12, weight="bold"),
            anchor="e",
        )
        self._balance_labels["final_cash"].grid(row=2, column=1, sticky="e", padx=12, pady=(2, 2))

        self._diff_cash_lbl_widget = ctk.CTkLabel(
            self._arqueo_module_frame,
            text="Diferencia efectivo",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
            text_color=theme.get_contrast_map()["text"],
        )
        self._diff_cash_lbl_widget._custom_theme_color = "skip"
        self._diff_cash_lbl_widget.grid(row=3, column=0, sticky="w", padx=12, pady=(2, 8))

        self._balance_labels["diff_cash"] = ctk.CTkLabel(
            self._arqueo_module_frame,
            text="—",
            font=theme.scaled_font(12, weight="bold"),
            anchor="e",
            text_color=theme.get_contrast_map()["text"],
        )
        self._balance_labels["diff_cash"]._custom_theme_color = "skip"
        self._balance_labels["diff_cash"].grid(row=3, column=1, sticky="e", padx=12, pady=(2, 8))

        # -- open / close buttons --
        btn_frame = ctk.CTkFrame(self._left_frame, fg_color="transparent", border_width=2, border_color=border_color)
        btn_frame.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")

        # Eliminados los width fijos. Ahora usan expand=True y fill="x" para adaptarse a cualquier fuente
        self._open_btn = ctk.CTkButton(
            btn_frame,
            text="🔓 Abrir caja",
            height=36,
            font=theme.scaled_font(14, weight="bold"),
            command=self._handle_open,
        )
        self._open_btn.pack(side="left", expand=True, fill="x", padx=(8, 4), pady=8)

        self._close_btn = ctk.CTkButton(
            btn_frame,
            text="🔒 Cerrar caja",
            height=36,
            font=theme.scaled_font(14, weight="bold"),
            fg_color="#8b1a1a",
            state="disabled",
            command=self._handle_close,
        )
        self._close_btn.pack(side="left", expand=True, fill="x", padx=(4, 8), pady=8)
        
        # -- outflow form --
        self._outflow_frame = ctk.CTkFrame(self._left_frame, fg_color="transparent", border_width=2, border_color=border_color)
        self._outflow_frame.grid(
            row=3, column=0, sticky="ew", padx=10, pady=(0, 5)
        )

        ctk.CTkLabel(
            self._outflow_frame,
            text="Registrar egreso manual:",
            font=theme.scaled_font(14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(6, 2))

        # Reemplazamos "expense" por "Gasto" para que coincida con la lista
        self._outflow_type_var = tk.StringVar(value="Gasto")
        ctk.CTkOptionMenu(
            self._outflow_frame,
            values=["Gasto", "Pago a proveedor"],
            variable=self._outflow_type_var,
        ).pack(fill="x", padx=10, pady=2)


        amount_row = ctk.CTkFrame(self._outflow_frame, fg_color="transparent")
        amount_row.pack(fill="x", padx=10, pady=(2, 4))
        amount_row.grid_columnconfigure(0, weight=1)
        amount_row.grid_columnconfigure(1, weight=2)

        # Fila superior: Etiquetas
        ctk.CTkLabel(
            amount_row, text="Monto ($):", font=theme.scaled_font(13)
        ).grid(row=0, column=0, sticky="w", padx=(0, 5), pady=(0, 1))
        
        ctk.CTkLabel(
            amount_row, text="Descripción:", font=theme.scaled_font(13)
        ).grid(row=0, column=1, sticky="w", padx=(5, 0), pady=(0, 1))
        
        # Fila inferior: Cajas de texto (Altura compactada a 28)
        self._outflow_amount_entry = ctk.CTkEntry(
            amount_row, placeholder_text="0", height=28
        )
        self._outflow_amount_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 4))

        self._outflow_desc_entry = ctk.CTkEntry(amount_row, height=28)
        self._outflow_desc_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 4))

        ctk.CTkButton(
            self._outflow_frame,
            text="Registrar",
            height=32,
            command=self._handle_outflow,
        ).pack(fill="x", padx=10, pady=(0, 10)) # Ocupa todo el ancho para proteger el texto
        
        # ========================================================== right side

        self._right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._right_frame.grid(
            row=0, column=1, sticky="nsew", padx=(5, 10), pady=(10, 5) 
        )
        # Invertimos los pesos: Ahora el historial (fila 1) empuja mucho más fuerte
        self._right_frame.grid_rowconfigure(0, weight=1)  # movement preview
        self._right_frame.grid_rowconfigure(1, weight=4)  # history (máxima prioridad)
        self._right_frame.grid_columnconfigure(0, weight=1)


        # -- movement preview panel (above history) --
        self._preview_frame = ctk.CTkFrame(self._right_frame, fg_color="transparent", border_width=2, border_color=border_color)
        self._preview_frame.grid(
            row=0, column=0, sticky="nsew", padx=10, pady=(0, 5)
        )
        self._preview_frame.grid_rowconfigure(1, weight=1)
        self._preview_frame.grid_columnconfigure(0, weight=1)

        self._preview_label = ctk.CTkLabel(
            self._preview_frame,
            text="Movimientos",
            font=theme.scaled_font(13, weight="bold"),
        )
        self._preview_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2), columnspan=2)

        self._preview_columns = ("tipo", "monto", "descripcion", "hora")
        self._preview_tree = ttk.Treeview(
            self._preview_frame,
            columns=self._preview_columns,
            show="headings",
            selectmode="browse",
            height=5, # <--- Reducido para cederle espacio a la tabla de abajo
        )
        
        self._preview_tree.heading("tipo", text="Tipo")
        self._preview_tree.heading("monto", text="Monto")
        self._preview_tree.heading("descripcion", text="Descripción")
        self._preview_tree.heading("hora", text="Hora")

        self._preview_tree.column("tipo", width=140, minwidth=140, anchor="w")
        self._preview_tree.column("monto", width=110, minwidth=110, anchor="e")
        self._preview_tree.column("descripcion", width=300, minwidth=300, anchor="w")
        self._preview_tree.column("hora", width=100, minwidth=100, anchor="center")
        
        # Cargamos solo la funcionalidad de ordenamiento (Eliminamos la carga de anchos guardados)
        add_sorting_to_treeview(
            self._preview_tree,
            list(self._preview_columns),
            column_types={
                "tipo": "str",
                "monto": "int",
                "descripcion": "str",
                "hora": "str",
            }
        )

        # Bloqueamos el redimensionamiento manual
        self._preview_tree.bind("<Button-1>", self._prevent_resize)
        self._preview_tree.bind("<B1-Motion>", self._prevent_resize)

        self._preview_vscroll = ttk.Scrollbar(
            self._preview_frame,
            orient="vertical",
            command=self._preview_tree.yview,
        )
        self._preview_hscroll = ttk.Scrollbar(
            self._preview_frame,
            orient="horizontal",
            command=self._preview_tree.xview,
        )
        self._preview_tree.configure(
            yscrollcommand=self._preview_vscroll.set,
            xscrollcommand=self._preview_hscroll.set,
        )
        self._preview_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 0))
        self._preview_vscroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 0))
        self._preview_hscroll.grid(row=2, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))
        
        # -- history treeview (below preview) --
        self._history_frame = ctk.CTkFrame(self._right_frame, fg_color="transparent", border_width=2, border_color=border_color)
        self._history_frame.grid(
            row=1, column=0, sticky="nsew", padx=10, pady=(0, 5)
        )
        self._history_frame.grid_rowconfigure(2, weight=1)
        self._history_frame.grid_columnconfigure(0, weight=1)

        # Title for history section
        ctk.CTkLabel(
            self._history_frame,
            text="Historial de cajas",
            font=theme.scaled_font(15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2), columnspan=2)

        # Date filter row
        filter_frame = ctk.CTkFrame(self._history_frame, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5), columnspan=2)
        
        # Le damos peso a la columna central para separar los botones a la derecha
        filter_frame.grid_columnconfigure(1, weight=1)

        # --- Fila 0: Desde + Calendario + Botón Filtrar ---
        ctk.CTkLabel(
            filter_frame,
            text="Desde:",
            font=theme.scaled_font(12),
        ).grid(row=0, column=0, sticky="w", padx=(5, 3), pady=(0, 2))

        self._start_date_entry = DateEntry(
            filter_frame,
            width=10, # Ancho en caracteres ajustado
            background="#2d5a3d",
            foreground="white",
            borderwidth=1,
            bordercolor="#505050",
            arrowcolor="#2d5a3d",
            date_pattern="yyyy-mm-dd",
            locale="es_AR",
        )
        self._start_date_entry.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=(0, 2)) # sticky="w" evita que se estire

        ctk.CTkButton(
            filter_frame,
            text="Filtrar",
            width=80,
            height=26,
            fg_color="#1f538d",
            font=theme.scaled_font(11, weight="bold"),
            command=self._apply_date_filter,
        ).grid(row=0, column=2, sticky="e", padx=(0, 3), pady=(0, 2)) # sticky="e" ancla a la derecha

        # --- Fila 1: Hasta + Calendario + Botón Limpiar ---
        ctk.CTkLabel(
            filter_frame,
            text="Hasta:",
            font=theme.scaled_font(12),
        ).grid(row=1, column=0, sticky="w", padx=(5, 3), pady=(2, 0))

        self._end_date_entry = DateEntry(
            filter_frame,
            width=10, # Ancho en caracteres ajustado
            background="#2d5a3d",
            foreground="white",
            borderwidth=1,
            bordercolor="#505050",
            arrowcolor="#2d5a3d",
            date_pattern="yyyy-mm-dd",
            locale="es_AR",
        )
        self._end_date_entry.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(2, 0)) # sticky="w" evita que se estire

        ctk.CTkButton(
            filter_frame,
            text="Limpiar",
            width=80,
            height=26,
            fg_color="#505050",
            font=theme.scaled_font(11, weight="bold"),
            command=self._clear_date_filter,
        ).grid(row=1, column=2, sticky="e", padx=(0, 3), pady=(2, 0)) # sticky="e" ancla a la derecha


        # Check if the role is admin or gerente
        is_admin_or_gerente = self._role in ("admin", "gerente")

        if is_admin_or_gerente:
            self._history_columns = (
                "id",
                "apertura",
                "cierre",
                "usuario",
                "motivo",
            )
        else:
            self._history_columns = (
                "id",
                "apertura",
                "cierre",
                "inicial",
                "final",
                "diferencia",
            )

        self._style = ttk.Style(self._history_frame)
        self._configure_style()

        self._history_tree = ttk.Treeview(
            self._history_frame,
            columns=self._history_columns,
            show="headings",
            selectmode="browse",
            height=10,
        )
        
        self._history_tree.heading("id", text="ID")
        self._history_tree.heading("apertura", text="Apertura")
        self._history_tree.heading("cierre", text="Cierre")
        
        if is_admin_or_gerente:
            self._history_tree.heading("usuario", text="Usuario")
            self._history_tree.heading("motivo", text="Motivo")

            self._history_tree.column("id", width=60, minwidth=60, anchor="center")
            self._history_tree.column("apertura", width=180, minwidth=180, anchor="center") 
            self._history_tree.column("cierre", width=180, minwidth=180, anchor="center")   
            self._history_tree.column("usuario", width=120, minwidth=120, anchor="center")
            self._history_tree.column("motivo", width=150, minwidth=150, anchor="w")
        else:
            self._history_tree.heading("inicial", text="Inicial")
            self._history_tree.heading("final", text="Final")
            self._history_tree.heading("diferencia", text="Dif.")

            self._history_tree.column("id", width=60, minwidth=60, anchor="center")
            self._history_tree.column("apertura", width=130, minwidth=130) 
            self._history_tree.column("cierre", width=130, minwidth=130)   
            self._history_tree.column("inicial", width=110, minwidth=110, anchor="e")
            self._history_tree.column("final", width=110, minwidth=110, anchor="e")
            self._history_tree.column("diferencia", width=100, minwidth=100, anchor="e")
        
        # Cargamos solo el ordenamiento (Eliminamos el filtro y la carga de anchos guardados)
        column_types = {
            "id": "int",
            "apertura": "str",
            "cierre": "str",
        }
        if is_admin_or_gerente:
            column_types["usuario"] = "str"
            column_types["motivo"] = "str"
        else:
            column_types["inicial"] = "int"
            column_types["final"] = "int"
            column_types["diferencia"] = "int"

        add_sorting_to_treeview(
            self._history_tree,
            list(self._history_columns),
            column_types=column_types
        )

        # Bloqueamos el redimensionamiento manual
        self._history_tree.bind("<Button-1>", self._prevent_resize)
        self._history_tree.bind("<B1-Motion>", self._prevent_resize)

        self._history_scroll = ttk.Scrollbar(
            self._history_frame,
            orient="vertical",
            command=self._history_tree.yview,
        )
        self._history_hscroll = ttk.Scrollbar(
            self._history_frame,
            orient="horizontal",
            command=self._history_tree.xview,
        )
        self._history_tree.configure(
            yscrollcommand=self._history_scroll.set,
            xscrollcommand=self._history_hscroll.set,
        )

        self._history_tree.grid(row=2, column=0, sticky="nsew", padx=(10, 0), pady=(0, 0))
        self._history_scroll.grid(row=2, column=1, sticky="ns", padx=(0, 10), pady=(0, 0))
        self._history_hscroll.grid(row=3, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))

        # Bind selection event to show movements preview
        self._history_tree.bind("<<TreeviewSelect>>", self._handle_history_select)

        # Apply permission-based visibility
        self._apply_permission_mode(self._cash_register_mode)

    # ---------------------------------------------------------------- public ---

    def update_register_status(self, status: dict[str, Any]) -> None:
        """Update the view based on the register status from the controller.

        Expected *status* dict::

            {
                "active": bool,
                "register": {id, opening_amount, opening_time, status} | None,
                "balance": {
                    "opening", "inflows", "outflows",
                    "expected", "difference"
                } | None,
            }
        """
        if not status.get("active"):
            self._status_label.configure(
                text="CAJA CERRADA", text_color="#e74c3c"
            )
            self._open_btn.configure(state="normal")
            self._close_btn.configure(state="disabled")
            self._set_balance_defaults()
            self._clear_preview()
        else:
            self._status_label.configure(
                text=f"CAJA ABIERTA — #{status['register']['id']}",
                text_color="#2ecc71",
            )
            self._open_btn.configure(state="disabled")
            self._close_btn.configure(state="normal")

            bal = status.get("balance") or {}
            self._balance_labels["initial"].configure(
                text=f"${bal.get('opening', 0):,}"
            )
            self._balance_labels["inflow_cash"].configure(
                text=f"${bal.get('inflow_cash', 0):,}"
            )
            self._balance_labels["inflow_transfer"].configure(
                text=f"${bal.get('inflow_transfer', 0):,}"
            )
            self._balance_labels["inflow_debit"].configure(
                text=f"${bal.get('inflow_debit', 0):,}"
            )
            self._balance_labels["inflow_credit"].configure(
                text=f"${bal.get('inflow_credit', 0):,}"
            )
            self._balance_labels["outflow_supplier"].configure(
                text=f"${bal.get('outflow_supplier', 0):,}"
            )
            self._balance_labels["outflow_expense"].configure(
                text=f"${bal.get('outflow_expense', 0):,}"
            )
            self._balance_labels["outflow_total"].configure(
                text=f"${bal.get('outflow_total', 0):,}"
            )
            self._balance_labels["expected_cash"].configure(
                text=f"${bal.get('expected_cash', 0):,}"
            )
            closing_val = bal.get("closing")
            self._balance_labels["final_cash"].configure(
                text=f"${closing_val:,}" if closing_val is not None else "—"
            )
            diff_val = bal.get("diff_cash")
            if diff_val is not None:
                if diff_val > 0:
                    self._balance_labels["diff_cash"].configure(
                        text=f"+ ${diff_val:,}",
                        text_color="#2ecc71"
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo (Sobrante)", text_color="#2ecc71")
                elif diff_val < 0:
                    self._balance_labels["diff_cash"].configure(
                        text=f"- ${abs(diff_val):,}",
                        text_color="#e74c3c"
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo (Faltante)", text_color="#e74c3c")
                else:
                    self._balance_labels["diff_cash"].configure(
                        text="$0",
                        text_color=theme.get_contrast_map()["text"]
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo", text_color=theme.get_contrast_map()["text"])
            else:
                self._balance_labels["diff_cash"].configure(text="—", text_color=theme.get_contrast_map()["text"])
                self._diff_cash_lbl_widget.configure(text="Diferencia efectivo", text_color=theme.get_contrast_map()["text"])

        # Notify MainWindow to refresh the register status badge
        try:
            toplevel = self.winfo_toplevel()
            if toplevel and hasattr(toplevel, "refresh_register_status"):
                toplevel.refresh_register_status()
        except Exception:
            pass

    def update_history(self, registers: list[dict[str, Any]]) -> None:
        """Refresh the history treeview with *registers*."""
        for child in self._history_tree.get_children():
            self._history_tree.delete(child)

        is_admin_or_gerente = self._role in ("admin", "gerente")

        for r in registers:
            if is_admin_or_gerente:
                self._history_tree.insert(
                    "",
                    "end",
                    iid=str(r["id"]),
                    values=(
                        r["id"],
                        _extract_date_time(r.get("opening_time", "—")),
                        _extract_date_time(r.get("closing_time", "—")),
                        r.get("username") or "—",
                        r.get("close_reason") or "—",
                    ),
                )
            else:
                self._history_tree.insert(
                    "",
                    "end",
                    iid=str(r["id"]),
                    values=(
                        r["id"],
                        _extract_date(r.get("opening_time", "—")),
                        _extract_date(r.get("closing_time", "—")),
                        f"${r.get('opening_amount', 0):,}",
                        f"${r.get('closing_amount', '—'):,}"
                        if r.get("closing_amount") is not None
                        else "—",
                        f"${r.get('difference', 0):,}"
                        if r.get("difference") is not None
                        else "—",
                    ),
                )


    def clear_outflow_form(self) -> None:
        """Reset the outflow form fields."""
        self._outflow_type_var.set("Gasto")  # Reinicia el selector por defecto
        self._outflow_amount_entry.delete(0, "end")
        self._outflow_desc_entry.delete(0, "end")

    # ----------------------------------------------------------- callbacks ----

    def set_on_open(self, callback: Callable[[int], None]) -> None:
        """Wire the open-register callback."""
        self._on_open = callback

    def set_on_close(self, callback: Callable[[int, str], None]) -> None:
        """Wire the close-register callback."""
        self._on_close = callback

    def set_on_outflow(
        self,
        callback: Callable[[str, int, str | None], None],
    ) -> None:
        """Wire the outflow registration callback."""
        self._on_outflow = callback

    def set_on_refresh(self, callback: Callable[[], None]) -> None:
        """Wire the refresh callback."""
        self._on_refresh = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``CashRegisterController`` instance and set up all handlers.

        After calling this, open/close/outflow/refresh actions are
        automatically routed to the controller, and the initial status
        and history are loaded.
        """
        self._controller = controller

        # Wire internal handlers
        self._on_open = self._controller_open
        self._on_close = self._controller_close
        self._on_outflow = self._controller_outflow
        self._on_refresh = self._controller_refresh

        # Initial load
        self._refresh_status()
        self._refresh_history()

    # ---------------------------------------------------- controller handlers ---

    def _controller_open(self, amount: int) -> None:
        """Open the cash register via controller."""
        result = self._controller.open_register(amount)
        if result["success"]:
            messagebox.showinfo("Caja", "Caja abierta correctamente", parent=self.winfo_toplevel())
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"], parent=self.winfo_toplevel())

    def _controller_close(self, amount: int, notes: str) -> None:
        """Close the cash register via controller."""
        result = self._controller.close_register(amount, notes)
        if result["success"]:
            role_str = (
                self._role.value
                if hasattr(self._role, "value")
                else str(self._role or "")
            ).lower()

            if role_str == "cajero" or self._cash_register_mode == "restricted":
                msg = "Caja cerrada correctamente."
            else:
                data = result["data"]
                diff = data.get("diff", 0)
                msg = f"Caja cerrada correctamente.\nDiferencia: ${diff:,}"

            messagebox.showinfo("Caja cerrada", msg, parent=self.winfo_toplevel())
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"], parent=self.winfo_toplevel())

    def _controller_outflow(
        self, type_: str, amount: int, description: str | None
    ) -> None:
        """Register a manual outflow via controller."""
        result = self._controller.register_outflow(type_, amount, description)
        if result["success"]:
            messagebox.showinfo("Egreso", "Egreso registrado correctamente", parent=self.winfo_toplevel())
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"], parent=self.winfo_toplevel())

    def _controller_refresh(self) -> None:
        """Refresh both status and history."""
        self._refresh_status()
        self._refresh_history()

    def _refresh_status(self) -> None:
        """Reload register status from controller and update UI."""
        result = self._controller.get_register_status()
        if result["success"]:
            self.update_register_status(result["data"])
        else:
            messagebox.showerror("Error", result["error"], parent=self.winfo_toplevel())

    def _refresh_history(self, start_date: str | None = None, end_date: str | None = None) -> None:
        """Reload register history from controller and update treeview.
        
        Args:
            start_date: Optional start date in 'YYYY-MM-DD' format.
            end_date: Optional end date in 'YYYY-MM-DD' format.
        """
        result = self._controller.get_history(start_date, end_date)
        if result["success"]:
            self.update_history(result["data"])
            # Auto-show movements for active register if one is open
            self._auto_preview_active_register()
        else:
            messagebox.showerror("Error", result["error"], parent=self.winfo_toplevel())

    def _apply_date_filter(self) -> None:
        """Apply date filter from the DateEntry widgets and refresh history."""
        start_date = self._start_date_entry.get_date().strftime("%Y-%m-%d")
        end_date = self._end_date_entry.get_date().strftime("%Y-%m-%d")
        self._refresh_history(start_date, end_date)

    def _clear_date_filter(self) -> None:
        """Clear date filters and show all history."""
        from datetime import date
        today = date.today()
        self._start_date_entry.set_date(today)
        self._end_date_entry.set_date(today)
        self._refresh_history()

    def _clear_preview(self) -> None:
        """Clear the movement preview panel."""
        self._preview_label.configure(text="Movimientos")
        for child in self._preview_tree.get_children():
            self._preview_tree.delete(child)

    def _auto_preview_active_register(self) -> None:
        """Show movements for the active register in the preview panel, or clear if closed."""
        result = self._controller.get_register_status()
        if result["success"] and result["data"]["active"]:
            register_id = result["data"]["register"]["id"]
            self._update_preview(register_id, label=f"Caja actual #{register_id}")
        else:
            self._clear_preview()

    def _handle_history_select(self, event: Any) -> None:
        """Handle selection in history treeview — show movements for selected register."""
        selection = self._history_tree.selection()
        if not selection:
            # Revert to active register status and balance
            self._refresh_status()
            return
            
        register_id = int(selection[0])
        self._update_preview(register_id, label=f"Caja #{register_id}")

        result = self._controller.get_register_balance(register_id)
        if result["success"]:
            bal = result["data"]
            self._balance_labels["initial"].configure(
                text=f"${bal.get('opening', 0):,}"
            )
            self._balance_labels["inflow_cash"].configure(
                text=f"${bal.get('inflow_cash', 0):,}"
            )
            self._balance_labels["inflow_transfer"].configure(
                text=f"${bal.get('inflow_transfer', 0):,}"
            )
            self._balance_labels["inflow_debit"].configure(
                text=f"${bal.get('inflow_debit', 0):,}"
            )
            self._balance_labels["inflow_credit"].configure(
                text=f"${bal.get('inflow_credit', 0):,}"
            )
            self._balance_labels["outflow_supplier"].configure(
                text=f"${bal.get('outflow_supplier', 0):,}"
            )
            self._balance_labels["outflow_expense"].configure(
                text=f"${bal.get('outflow_expense', 0):,}"
            )
            self._balance_labels["outflow_total"].configure(
                text=f"${bal.get('outflow_total', 0):,}"
            )
            self._balance_labels["expected_cash"].configure(
                text=f"${bal.get('expected_cash', 0):,}"
            )
            closing_val = bal.get("closing")
            self._balance_labels["final_cash"].configure(
                text=f"${closing_val:,}" if closing_val is not None else "—"
            )
            diff_val = bal.get("diff_cash")
            if diff_val is not None:
                if diff_val > 0:
                    self._balance_labels["diff_cash"].configure(
                        text=f"+ ${diff_val:,}",
                        text_color="#2ecc71"
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo (Sobrante)", text_color="#2ecc71")
                elif diff_val < 0:
                    self._balance_labels["diff_cash"].configure(
                        text=f"- ${abs(diff_val):,}",
                        text_color="#e74c3c"
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo (Faltante)", text_color="#e74c3c")
                else:
                    self._balance_labels["diff_cash"].configure(
                        text="$0",
                        text_color=theme.get_contrast_map()["text"]
                    )
                    self._diff_cash_lbl_widget.configure(text="Diferencia efectivo", text_color=theme.get_contrast_map()["text"])
            else:
                self._balance_labels["diff_cash"].configure(text="—", text_color=theme.get_contrast_map()["text"])
                self._diff_cash_lbl_widget.configure(text="Diferencia efectivo", text_color=theme.get_contrast_map()["text"])

    def _update_preview(self, register_id: int, label: str = "Movimientos") -> None:
        """Populate the movement preview panel for a specific register."""
        self._preview_label.configure(text=label)
        # Clear existing items
        for child in self._preview_tree.get_children():
            self._preview_tree.delete(child)

        result = self._controller.get_movements(register_id)
        if not result["success"]:
            return

        type_labels = {
            "sale_cash": "Venta (Efectivo)",
            "sale_card": "Venta (Tarjeta)",
            "sale_debit_card": "Venta (T. Débito)",
            "sale_credit_card": "Venta (T. Crédito)",
            "sale_transfer": "Venta (Transfer.)",
            "return": "Devolución",
            "supplier_payment": "Pago prov.",
            "expense": "Gasto",
        }
        for m in result["data"]:
            type_text = type_labels.get(m["type"], m["type"])
            time_text = _extract_time(m.get("created_at", ""))
            self._preview_tree.insert(
                "",
                "end",
                values=(
                    type_text,
                    f"${m['amount']:,}",
                    m.get("description") or "",
                    time_text,
                ),
            )


    # --------------------------------------------------------------- private ---
    def _apply_permission_mode(self, mode: str) -> None:
        """Apply role-based visibility to cash register widgets."""
        if mode == "history_only":
            # Gerente: hide open/close buttons and outflow form, but keep history and preview
            self._open_btn.pack_forget()
            self._close_btn.pack_forget()
            self._outflow_frame.grid_remove()
            # Keep _preview_frame visible so gerente can see movements of selected register
        elif mode == "restricted":
            # Cajero: hide history, inflows, outflows, and arqueo modules
            self._history_frame.grid_remove()
            self._inflows_module_frame.grid_remove()
            self._outflows_module_frame.grid_remove()
            self._arqueo_module_frame.grid_remove()
        # mode == "full": no changes (admin)

    def _prevent_resize(self, event: Any) -> str | None:
        """Evita que el usuario cambie el tamaño de las columnas arrastrando el separador."""
        if event.widget.identify_region(event.x, event.y) == "separator":
            return "break"
        return None
        
    def _configure_style(self) -> None:
        """Configure ttk styles to blend with CTk dark theme."""
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

    def _set_balance_defaults(self) -> None:
        """Reset the balance panel labels to default dashes."""
        for lbl in self._balance_labels.values():
            lbl.configure(text="—")
        self._diff_cash_lbl_widget.configure(text="Diferencia efectivo", text_color=theme.get_contrast_map()["text"])

    def _handle_open(self) -> None:
        dialog = _AmountDialog(
            self, title="Abrir caja", prompt="Monto inicial ($):"
        )
        self.wait_window(dialog)
        amount = dialog.result
        if amount is not None and self._on_open is not None:
            self._on_open(amount)

    def _handle_close(self) -> None:
        dialog = _CloseDialog(self)
        self.wait_window(dialog)
        result = dialog.result
        if result is not None and self._on_close is not None:
            self._on_close(result["amount"], result["notes"])

    def _handle_outflow(self) -> None:
        type_label = self._outflow_type_var.get()
        type_map = {"Gasto": "expense", "Pago a proveedor": "supplier_payment"}
        type_ = type_map.get(type_label, "expense")

        raw_amount = self._outflow_amount_entry.get().strip()
        try:
            amount = int(raw_amount)
        except ValueError:
            messagebox.showwarning(
                "Monto inválido", "Ingrese un monto válido (número entero)."
            )
            return

        if amount <= 0:
            messagebox.showwarning(
                "Monto inválido", "El monto debe ser mayor a 0."
            )
            return

        description = self._outflow_desc_entry.get().strip() or None

        if self._on_outflow is not None:
            self._on_outflow(type_, amount, description)
            self.clear_outflow_form()

    def _handle_refresh(self) -> None:
        if self._on_refresh is not None:
            self._on_refresh()


# ----------------------------------------------------------------- helpers ---


class _AmountDialog(CenteredDialog):
    """Prompt the user for an integer amount."""

    def __init__(
        self,
        master: tk.Widget,
        title: str = "Monto",
        prompt: str = "Monto ($):",
        **kwargs,
    ) -> None:
        super().__init__(master, width=320, height=180, title=title, **kwargs)
        self._result: int | None = None

        ctk.CTkLabel(
            self, text=prompt, font=theme.scaled_font(14)
        ).pack(pady=(20, 10))

        self._entry = ctk.CTkEntry(self, width=200, placeholder_text="0")
        self._entry.pack(padx=20, pady=5)
        self._entry.bind("<Return>", lambda _e: self._confirm())
        self.after(100, self._entry.focus_set)

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.pack()

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(10, 20))
        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100, fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Aceptar", width=100, command=self._confirm,
        ).pack(side="left", padx=5)

        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    @property
    def result(self) -> int | None:
        return self._result

    def _confirm(self) -> None:
        raw = self._entry.get().strip()
        if not raw:
            self._error_label.configure(text="Ingrese un monto")
            return
        try:
            amount = int(raw)
        except ValueError:
            self._error_label.configure(text="Ingrese un número entero válido")
            return
        if amount < 0:
            self._error_label.configure(text="El monto no puede ser negativo")
            return
        self._result = amount
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()


class _CloseDialog(CenteredDialog):
    """Prompt for closing amount and notes."""

    def __init__(self, master: tk.Widget, **kwargs) -> None:
        super().__init__(master, width=380, height=360, title="Cerrar caja", **kwargs)
        self._result: dict[str, Any] | None = None

        ctk.CTkLabel(
            self, text="Monto contado ($):", font=theme.scaled_font(14)
        ).pack(pady=(20, 10))
        self._amount_entry = ctk.CTkEntry(self, width=200, placeholder_text="0")
        self._amount_entry.pack(padx=20, pady=5)
        self._amount_entry.bind("<Return>", lambda _e: self._confirm())

        ctk.CTkLabel(
            self, text="Motivo de cierre:", font=theme.scaled_font(14)
        ).pack(pady=(10, 5))
        
        # Radio buttons for close reason
        self._reason_var = tk.StringVar(value="Fin de turno")
        reason_frame = ctk.CTkFrame(self, fg_color="transparent")
        reason_frame.pack(padx=20, pady=5, fill="x")
        
        ctk.CTkRadioButton(
            reason_frame, text="Fin de turno", variable=self._reason_var,
            value="Fin de turno", command=self._on_reason_change
        ).pack(anchor="w", pady=2)
        
        ctk.CTkRadioButton(
            reason_frame, text="Otro", variable=self._reason_var,
            value="Otro", command=self._on_reason_change
        ).pack(anchor="w", pady=2)
        
        # Text entry for "Otro" (initially disabled)
        self._notes_entry = ctk.CTkEntry(
            self, width=300, placeholder_text="Aclare el motivo...",
            state="disabled"
        )
        self._notes_entry.pack(padx=20, pady=5)
        self._notes_entry.bind("<Return>", lambda _e: self._confirm())

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.pack()

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=(10, 20))
        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100, fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Cerrar caja", width=120,
            fg_color="#8b1a1a", command=self._confirm,
        ).pack(side="left", padx=5)

        self.after(100, self._amount_entry.focus_set)
        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    @property
    def result(self) -> dict[str, Any] | None:
        return self._result

    def _on_reason_change(self) -> None:
        """Enable notes entry only when 'Otro' is selected."""
        if self._reason_var.get() == "Otro":
            self._notes_entry.configure(state="normal")
            self._notes_entry.focus_set()
        else:
            self._notes_entry.configure(state="disabled")
            self._notes_entry.delete(0, "end")

    def _confirm(self) -> None:
        raw_amount = self._amount_entry.get().strip()
        reason_choice = self._reason_var.get()
        
        # Build final notes based on selection
        if reason_choice == "Otro":
            notes = self._notes_entry.get().strip()
            if not notes:
                self._error_label.configure(
                    text="Aclare el motivo al seleccionar 'Otro'"
                )
                return
        else:
            notes = reason_choice
        
        if not raw_amount:
            self._error_label.configure(text="Ingrese el monto contado")
            return
        try:
            amount = int(raw_amount)
        except ValueError:
            self._error_label.configure(text="Ingrese un número entero válido")
            return
        if amount < 0:
            self._error_label.configure(text="El monto no puede ser negativo")
            return
        
        self._result = {"amount": amount, "notes": notes}
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()


# --------------------------------------------------------------- helpers ---


def _extract_date(ts: str) -> str:
    """Extract only the YYYY-MM-DD part from an ISO timestamp."""
    if ts and len(ts) >= 10:
        return ts[:10]
    return ts or "—"

def _extract_time(ts: str) -> str:
    """Extract only the HH:MM part from an ISO timestamp."""
    if ts and len(ts) >= 16:
        # Format is usually YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM:SS
        return ts[11:16]
    return ts or "—"

def _extract_date_time(ts: str) -> str:
    """Extract YYYY-MM-DD HH:MM from an ISO timestamp."""
    if ts and len(ts) >= 16:
        part = ts[:16]
        if 'T' in part:
            part = part.replace('T', ' ')
        return part
    return ts or "—"

