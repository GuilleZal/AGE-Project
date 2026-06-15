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

from pos.view.widgets.column_persistence import (
    load_column_widths,
    save_column_widths,
    get_treeview_widths,
    apply_treeview_widths,
)
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview


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
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        callbacks = callbacks or {}

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

        self.grid_columnconfigure(0, weight=3)  # left panel
        self.grid_columnconfigure(1, weight=2)  # right panel
        self.grid_rowconfigure(0, weight=1)

        # =========================================================== left side

        self._left_frame = ctk.CTkFrame(self)
        self._left_frame.grid(
            row=0, column=0, sticky="nsew", padx=(10, 5), pady=10
        )
        self._left_frame.grid_columnconfigure(0, weight=1)

        # -- status header --
        self._status_label = ctk.CTkLabel(
            self._left_frame,
            text="CAJA CERRADA",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e74c3c",
        )
        self._status_label.grid(
            row=0, column=0, sticky="ew", padx=15, pady=(10, 5)
        )

        # -- balance panel --
        self._balance_frame = ctk.CTkFrame(
            self._left_frame, fg_color="#2b2b2b"
        )
        self._balance_frame.grid(
            row=1, column=0, sticky="ew", padx=15, pady=5
        )
        self._balance_frame.grid_columnconfigure(0, weight=1)

        self._balance_labels: dict[str, ctk.CTkLabel] = {}
        metrics = [
            ("Inicio:", "initial", "—"),
            ("Ingresos:", "inflows", "—"),
            ("Egresos:", "outflows", "—"),
            ("Esperado:", "expected", "—"),
            ("Diferencia:", "difference", "—"),
        ]
        for idx, (label, key, default) in enumerate(metrics):
            ctk.CTkLabel(
                self._balance_frame,
                text=label,
                font=ctk.CTkFont(size=13),
                anchor="w",
            ).grid(row=idx, column=0, sticky="w", padx=15, pady=3)
            lbl = ctk.CTkLabel(
                self._balance_frame,
                text=default,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="e",
            )
            lbl.grid(row=idx, column=1, sticky="e", padx=15, pady=3)
            self._balance_labels[key] = lbl

        # -- open / close buttons --
        btn_frame = ctk.CTkFrame(self._left_frame)
        btn_frame.grid(row=2, column=0, pady=10, padx=15, sticky="ew")

        self._open_btn = ctk.CTkButton(
            btn_frame,
            text="🔓 Abrir caja",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._handle_open,
        )
        self._open_btn.pack(side="left", padx=5)

        self._close_btn = ctk.CTkButton(
            btn_frame,
            text="🔒 Cerrar caja",
            width=140,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#8b1a1a",
            state="disabled",
            command=self._handle_close,
        )
        self._close_btn.pack(side="left", padx=5)

        # -- outflow form --
        self._outflow_frame = ctk.CTkFrame(self._left_frame)
        self._outflow_frame.grid(
            row=3, column=0, sticky="ew", padx=15, pady=10
        )

        ctk.CTkLabel(
            self._outflow_frame,
            text="Registrar egreso manual:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self._outflow_type_var = tk.StringVar(value="expense")
        ctk.CTkOptionMenu(
            self._outflow_frame,
            values=["Gasto", "Pago a proveedor"],
            variable=self._outflow_type_var,
            width=180,
        ).pack(padx=10, pady=2)

        amount_row = ctk.CTkFrame(self._outflow_frame)
        amount_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            amount_row, text="Monto ($):", font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 5))
        self._outflow_amount_entry = ctk.CTkEntry(
            amount_row, width=120, placeholder_text="0"
        )
        self._outflow_amount_entry.pack(side="left", padx=5)

        ctk.CTkLabel(
            amount_row, text="Descripción:", font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(10, 5))
        self._outflow_desc_entry = ctk.CTkEntry(amount_row, width=180)
        self._outflow_desc_entry.pack(side="left", padx=5, fill="x", expand=True)

        ctk.CTkButton(
            self._outflow_frame,
            text="Registrar",
            width=120,
            command=self._handle_outflow,
        ).pack(pady=(5, 10))

        # ========================================================== right side

        self._right_frame = ctk.CTkFrame(self)
        self._right_frame.grid(
            row=0, column=1, sticky="nsew", padx=(5, 10), pady=10
        )
        self._right_frame.grid_rowconfigure(0, weight=1)  # movement preview
        self._right_frame.grid_rowconfigure(1, weight=1)  # history
        self._right_frame.grid_columnconfigure(0, weight=1)

        # -- movement preview panel (above history) --
        self._preview_frame = ctk.CTkFrame(self._right_frame)
        self._preview_frame.grid(
            row=0, column=0, sticky="nsew", padx=15, pady=(0, 5)
        )
        self._preview_frame.grid_rowconfigure(1, weight=1)
        self._preview_frame.grid_columnconfigure(0, weight=1)

        self._preview_label = ctk.CTkLabel(
            self._preview_frame,
            text="Movimientos",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._preview_label.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2), columnspan=2)

        self._preview_columns = ("tipo", "monto", "descripcion", "hora")
        self._preview_tree = ttk.Treeview(
            self._preview_frame,
            columns=self._preview_columns,
            show="headings",
            selectmode="browse",
            height=5,
        )
        self._preview_tree.heading("tipo", text="Tipo")
        self._preview_tree.heading("monto", text="Monto")
        self._preview_tree.heading("descripcion", text="Descripción")
        self._preview_tree.heading("hora", text="Hora")

        self._preview_tree.column("tipo", width=120, anchor="w")
        self._preview_tree.column("monto", width=100, anchor="e")
        self._preview_tree.column("descripcion", width=250, anchor="w")
        self._preview_tree.column("hora", width=120, anchor="center")

        # Load saved column widths for movements
        saved_widths = load_column_widths("cash_register_movements")
        self._preview_tree._view_name = "cash_register_movements"
        apply_treeview_widths(self._preview_tree, saved_widths)

        # Add column sorting for movements
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
        self._preview_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 0))
        self._preview_vscroll.grid(row=1, column=1, sticky="ns", pady=(0, 0))
        self._preview_hscroll.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))

        # -- history treeview (below preview) --
        self._history_frame = ctk.CTkFrame(self._right_frame)
        self._history_frame.grid(
            row=1, column=0, sticky="nsew", padx=15, pady=(0, 10)
        )
        self._history_frame.grid_rowconfigure(1, weight=1)
        self._history_frame.grid_columnconfigure(0, weight=1)

        # Title for history section
        ctk.CTkLabel(
            self._history_frame,
            text="Historial de cajas",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2), columnspan=2)

        self._history_columns = (
            "id",
            "apertura",
            "cierre",
            "inicial",
            "final",
            "diferencia",
            "estado",
        )
        self._style = ttk.Style(self._history_frame)
        self._configure_style()

        self._history_tree = ttk.Treeview(
            self._history_frame,
            columns=self._history_columns,
            show="headings",
            selectmode="browse",
            height=8,
        )
        self._history_tree.heading("id", text="ID")
        self._history_tree.heading("apertura", text="Apertura")
        self._history_tree.heading("cierre", text="Cierre")
        self._history_tree.heading("inicial", text="Inicial")
        self._history_tree.heading("final", text="Final")
        self._history_tree.heading("diferencia", text="Dif.")
        self._history_tree.heading("estado", text="Estado")

        self._history_tree.column("id", width=40, anchor="center")
        self._history_tree.column("apertura", width=120)
        self._history_tree.column("cierre", width=120)
        self._history_tree.column("inicial", width=80, anchor="e")
        self._history_tree.column("final", width=80, anchor="e")
        self._history_tree.column("diferencia", width=70, anchor="e")
        self._history_tree.column("estado", width=60, anchor="center")

        # Load saved column widths for history
        saved_widths = load_column_widths("cash_register_history")
        self._history_tree._view_name = "cash_register_history"
        apply_treeview_widths(self._history_tree, saved_widths)

        # Add column sorting for history
        add_sorting_to_treeview(
            self._history_tree,
            list(self._history_columns),
            column_types={
                "id": "int",
                "apertura": "str",
                "cierre": "str",
                "inicial": "int",
                "final": "int",
                "diferencia": "int",
                "estado": "str",
            }
        )

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

        self._history_tree.grid(row=1, column=0, sticky="nsew")
        self._history_scroll.grid(row=1, column=1, sticky="ns")
        self._history_hscroll.grid(row=2, column=0, sticky="ew")

        # Bind selection event to show movements preview
        self._history_tree.bind("<<TreeviewSelect>>", self._handle_history_select)

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
            self._balance_labels["inflows"].configure(
                text=f"${bal.get('inflows', 0):,}"
            )
            self._balance_labels["outflows"].configure(
                text=f"${bal.get('outflows', 0):,}"
            )
            self._balance_labels["expected"].configure(
                text=f"${bal.get('expected', 0):,}"
            )
            diff = bal.get("difference", 0)
            self._balance_labels["difference"].configure(
                text=f"${diff:,}" if diff is not None else "—"
            )

    def update_history(self, registers: list[dict[str, Any]]) -> None:
        """Refresh the history treeview with *registers*.

        Each dict expects keys: ``id``, ``opening_amount``,
        ``opening_time``, ``closing_amount``, ``closing_time``,
        ``difference``, ``status``.
        """
        for child in self._history_tree.get_children():
            self._history_tree.delete(child)

        for r in registers:
            status_icon = "●" if r.get("status") == "open" else "○"
            self._history_tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["id"],
                    _truncate_time(r.get("opening_time", "—")),
                    _truncate_time(r.get("closing_time", "—")),
                    f"${r.get('opening_amount', 0):,}",
                    f"${r.get('closing_amount', '—'):,}"
                    if r.get("closing_amount") is not None
                    else "—",
                    f"${r.get('difference', 0):,}"
                    if r.get("difference") is not None
                    else "—",
                    status_icon,
                ),
            )

    def clear_outflow_form(self) -> None:
        """Reset the outflow form fields."""
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
            messagebox.showinfo("Caja", "Caja abierta correctamente")
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_close(self, amount: int, notes: str) -> None:
        """Close the cash register via controller."""
        result = self._controller.close_register(amount, notes)
        if result["success"]:
            data = result["data"]
            diff = data.get("diff", 0)
            messagebox.showinfo(
                "Caja cerrada",
                f"Caja cerrada correctamente.\nDiferencia: ${diff:,}",
            )
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"])

    def _controller_outflow(
        self, type_: str, amount: int, description: str | None
    ) -> None:
        """Register a manual outflow via controller."""
        result = self._controller.register_outflow(type_, amount, description)
        if result["success"]:
            messagebox.showinfo("Egreso", "Egreso registrado correctamente")
            self._refresh_status()
            self._refresh_history()
        else:
            messagebox.showerror("Error", result["error"])

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
            messagebox.showerror("Error", result["error"])

    def _refresh_history(self) -> None:
        """Reload register history from controller and update treeview."""
        result = self._controller.get_history()
        if result["success"]:
            self.update_history(result["data"])
            # Auto-show movements for active register if one is open
            self._auto_preview_active_register()
        else:
            messagebox.showerror("Error", result["error"])

    def _auto_preview_active_register(self) -> None:
        """Show movements for the active register in the preview panel."""
        result = self._controller.get_register_status()
        if result["success"] and result["data"]["active"]:
            register_id = result["data"]["register"]["id"]
            self._update_preview(register_id, label=f"Caja actual #{register_id}")

    def _handle_history_select(self, event: Any) -> None:
        """Handle selection in history treeview — show movements for selected register."""
        selection = self._history_tree.selection()
        if not selection:
            return
        register_id = int(selection[0])
        self._update_preview(register_id, label=f"Caja #{register_id}")

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
            "sale_transfer": "Venta (Transfer.)",
            "return": "Devolución",
            "supplier_payment": "Pago prov.",
            "expense": "Gasto",
        }
        for m in result["data"]:
            type_text = type_labels.get(m["type"], m["type"])
            time_text = _truncate_time(m.get("created_at", ""))
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

    def _configure_style(self) -> None:
        """Configure ttk styles to blend with CTk dark theme."""
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

    def _set_balance_defaults(self) -> None:
        for key in ("initial", "inflows", "outflows", "expected", "difference"):
            self._balance_labels[key].configure(text="—")

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


class _AmountDialog(ctk.CTkToplevel):
    """Prompt the user for an integer amount."""

    def __init__(
        self,
        master: tk.Widget,
        title: str = "Monto",
        prompt: str = "Monto ($):",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self._result: int | None = None

        ctk.CTkLabel(
            self, text=prompt, font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 10))

        self._entry = ctk.CTkEntry(self, width=200, placeholder_text="0")
        self._entry.pack(padx=20, pady=5)
        self._entry.bind("<Return>", lambda _e: self._confirm())
        self._entry.focus_set()

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
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

        self.geometry("320x180")
        self._center_on_master(master)

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

    def _center_on_master(self, master: tk.Widget) -> None:
        self.update_idletasks()
        mw, mh = master.winfo_width(), master.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"+{x}+{y}")


class _CloseDialog(ctk.CTkToplevel):
    """Prompt for closing amount and notes."""

    def __init__(self, master: tk.Widget, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.title("Cerrar caja")
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self._result: dict[str, Any] | None = None

        ctk.CTkLabel(
            self, text="Monto contado ($):", font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 10))
        self._amount_entry = ctk.CTkEntry(self, width=200, placeholder_text="0")
        self._amount_entry.pack(padx=20, pady=5)

        ctk.CTkLabel(
            self, text="Motivo de cierre:", font=ctk.CTkFont(size=14)
        ).pack(pady=(10, 5))
        self._notes_entry = ctk.CTkEntry(
            self, width=300, placeholder_text="Ej: Fin de turno..."
        )
        self._notes_entry.pack(padx=20, pady=5)
        self._notes_entry.bind("<Return>", lambda _e: self._confirm())

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=ctk.CTkFont(size=12)
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

        self.geometry("380x280")
        self._center_on_master(master)
        self._amount_entry.focus_set()

    @property
    def result(self) -> dict[str, Any] | None:
        return self._result

    def _confirm(self) -> None:
        raw_amount = self._amount_entry.get().strip()
        notes = self._notes_entry.get().strip()
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
        # Notes are now optional
        self._result = {"amount": amount, "notes": notes}
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()

    def _center_on_master(self, master: tk.Widget) -> None:
        self.update_idletasks()
        mw, mh = master.winfo_width(), master.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"+{x}+{y}")


# --------------------------------------------------------------- helpers ---


def _truncate_time(ts: str) -> str:
    """Truncate an ISO timestamp to a short display format."""
    if ts and len(ts) >= 16:
        return ts[:16].replace("T", " ")
    return ts or "—"
