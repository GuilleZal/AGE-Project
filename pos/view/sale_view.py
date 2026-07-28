"""Sale view — POS terminal layout for the main sales screen.

Two-column layout matching the reference design:
- Left column: barcode search, product table, delete button
- Right column: payment sidebar with totals, payment methods, and action buttons

All business logic lives in ``SaleController`` — this view only emits callbacks.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.barcode_entry import BarcodeEntry
from pos.view.widgets.cart_treeview import CartTreeview
from pos.view import theme
from pos.view.widgets.centered_dialog import CenteredDialog

class SaleView(ctk.CTkFrame):
    """POS terminal — two-column layout with integrated payment sidebar.

    Parameters
    ----------
    master : tk.Widget
        Parent frame (typically the "Ventas" tab frame).
    callbacks : dict[str, Callable] | None
        Optional dict with keys ``on_scan``, ``on_update_qty``,
        ``on_remove_item``, ``on_payment`` receiving callbacks.
    **kwargs :
        Forwarded to ``ctk.CTkFrame``.
    """

    # Single-row methods (icon, label, value)
    SINGLE_METHODS: list[tuple[str, str, str]] = [
        ("💵", "Efectivo", "cash"),
        ("🔄", "Transferencia", "transfer"),
    ]
    # Card sub-types shown as a grouped pair
    CARD_METHODS: list[tuple[str, str, str]] = [
        ("🏦", "Débito", "debit_card"),
        ("💳", "Crédito", "credit_card"),
    ]

    def __init__(
        self,
        master: tk.Widget,
        callbacks: dict[str, Callable[..., Any]] | None = None,
        role: str = "",
        **kwargs,
    ) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        self._role = role
        callbacks = callbacks or {}

        # Callback slots — wired by main_window.py during integration
        self._on_scan: Callable[[str], None] | None = callbacks.get("on_scan")
        self._on_update_qty: Callable[[int, float], None] | None = callbacks.get(
            "on_update_qty"
        )
        self._on_remove_item: Callable[[int], None] | None = callbacks.get(
            "on_remove_item"
        )
        self._on_payment: Callable[[str, int], None] | None = callbacks.get(
            "on_payment"
        )
        self._on_sale_completed: Callable[[], None] | None = callbacks.get(
            "on_sale_completed"
        )
        self._on_discount: Callable[[float], None] | None = callbacks.get(
            "on_discount"
        )
        self._on_surcharge: Callable[[float], None] | None = None
        self._on_product_created: Callable[[], None] | None = None

        self._total: int = 0
        self._discount_pct: float = 0.0
        self._discount_amount: int = 0
        self._surcharge_pct: float = 0.0
        self._surcharge_amount: int = 0
        self._selected_payment_method: str = "cash"

        # --- main two-column layout ---
        self.grid_columnconfigure(0, weight=1)  # left column stretches
        self.grid_columnconfigure(1, weight=0)  # right column fixed width
        self.grid_rowconfigure(0, weight=1)

        # ============================================================
        # LEFT COLUMN: Sales area
        # ============================================================
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=0)
        left_frame.grid_columnconfigure(2, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)  # cart row stretches

        # --- row 0: top bar (barcode entry + settings button) ---
        self._top_frame = ctk.CTkFrame(left_frame)
        self._top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        self._top_frame.grid_columnconfigure(0, weight=1)

        # --- barcode entry (always visible, always focused) ---
        self._barcode_entry = BarcodeEntry(
            self._top_frame,
            on_scan=self._handle_scan,
            on_search=self._handle_search,
            height=45,
            font=theme.scaled_font(16),
        )
        self._barcode_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # --- search button (magnifying glass) ---
        search_contrast = theme.get_contrast_map()
        self._search_btn = ctk.CTkButton(
            self._top_frame,
            text="🔍",
            width=50,
            height=45,
            font=theme.scaled_font(18),
            fg_color=search_contrast["search_bg"],
            hover_color=search_contrast["panel"],
            border_width=2,
            border_color=search_contrast["search_border"],
            text_color=theme.get_contrast_map()["text"],
            command=self._handle_search_button,
        )
        self._search_btn.grid(row=0, column=1, sticky="e")

        # --- settings button (gear) ---
        self._settings_btn = ctk.CTkButton(
            self._top_frame,
            text="⚙️",
            width=50,
            height=45,
            font=theme.scaled_font(18),
            fg_color=search_contrast["search_bg"],
            hover_color=search_contrast["panel"],
            border_width=2,
            border_color=search_contrast["search_border"],
            text_color=theme.get_contrast_map()["text"],
            command=self._handle_settings_button,
        )
        if self._role != "cajero":
            self._settings_btn.grid(row=0, column=2, sticky="e", padx=(5, 0))

        # --- row 1: cart treeview ---
        self._cart_tree = CartTreeview(
            left_frame,
            on_delete=self._handle_remove,
            role=self._role,
        )
        self._cart_tree.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # --- row 2: delete button (bottom left) + discount button (bottom right) ---
        self._delete_btn = ctk.CTkButton(
            left_frame,
            text="Eliminar",
            width=120,
            height=40,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=theme.scaled_font(14, weight="bold"),
            command=self._handle_remove_button,
        )
        self._delete_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self._discount_btn = ctk.CTkButton(
            left_frame,
            text="Descuento",
            width=120,
            height=40,
            fg_color="#f59e0b",
            hover_color="#d97706",
            font=theme.scaled_font(14, weight="bold"),
            command=self._handle_discount_button,
        )
        self._discount_btn.grid(row=2, column=2, sticky="e", pady=(10, 0))

        self._discount_btn.grid(row=2, column=2, sticky="e", pady=(10, 0))

        # ============================================================
        # RIGHT COLUMN: Payment sidebar
        # ============================================================
        self._payment_sidebar = ctk.CTkScrollableFrame(self, width=280)
        self._payment_sidebar.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=(10, 10))
        self._payment_sidebar.grid_columnconfigure(0, weight=1)
        self._payment_sidebar.grid_rowconfigure(0, weight=0) # Totales (fijo)
        self._payment_sidebar.grid_rowconfigure(1, weight=0) # Métodos (fijo)
        self._payment_sidebar.grid_rowconfigure(2, weight=0) # Monto/Vuelto (fijo)
        self._payment_sidebar.grid_rowconfigure(3, weight=1) # ESPACIO FANTASMA (absorbe el sobrante)
        self._payment_sidebar.grid_rowconfigure(4, weight=0) # Botones (fijo)

        # --- Totals section ---
        totals_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        totals_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(2, 2))  # Margen compactado
        totals_frame.grid_columnconfigure(0, weight=1)
        totals_frame.grid_columnconfigure(1, weight=0)

        # Title
        ctk.CTkLabel(
            totals_frame,
            text="Pago",
            font=theme.scaled_font(16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))  # Margen compactado

        # Separator line
        separator = ctk.CTkFrame(totals_frame, height=2, fg_color="#c0c0c0")
        separator.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))  # Margen compactado

        # Subtotal row
        ctk.CTkLabel(
            totals_frame,
            text="Subtotal:",
            font=theme.scaled_font(14),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=1)
        self._subtotal_label = ctk.CTkLabel(
            totals_frame,
            text="$0",
            font=theme.scaled_font(14, weight="bold"),
            anchor="e",
        )
        self._subtotal_label.grid(row=2, column=1, sticky="e", pady=1, padx=(15, 0))

        # Discount row
        ctk.CTkLabel(
            totals_frame,
            text="Descuento:",
            font=theme.scaled_font(14),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=1)
        self._discount_label = ctk.CTkLabel(
            totals_frame,
            text="$0",
            font=theme.scaled_font(14, weight="bold"),
            anchor="e",
            text_color="#a0a0a0",
        )
        self._discount_label.grid(row=3, column=1, sticky="e", pady=1, padx=(15, 0))

        # Surcharge row
        ctk.CTkLabel(
            totals_frame,
            text="Recargo:",
            font=theme.scaled_font(14),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=4, column=0, sticky="w", pady=1)
        self._surcharge_label = ctk.CTkLabel(
            totals_frame,
            text="$0",
            font=theme.scaled_font(14, weight="bold"),
            anchor="e",
            text_color="#a0a0a0",
        )
        self._surcharge_label.grid(row=4, column=1, sticky="e", pady=1, padx=(15, 0))

        # Total box
        total_box = ctk.CTkFrame(totals_frame, fg_color="#2b2b2b", corner_radius=8)
        total_box._custom_theme_color = "entry_bg"
        total_box.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))  # Margen compactado
        total_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            total_box,
            text="TOTAL A PAGAR",
            font=theme.scaled_font(10),
            text_color="#a0a0a0",
        ).grid(row=0, column=0, pady=(2, 0))  # Margen compactado
        self._total_label = ctk.CTkLabel(
            total_box,
            text="$0",
            font=theme.scaled_font(24, weight="bold"),
            text_color="#ffffff",
        )
        self._total_label.grid(row=1, column=0, pady=(0, 2))  # Margen compactado

        # --- Payment method selection ---
        payment_methods_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        payment_methods_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 2))
        payment_methods_frame.grid_columnconfigure(0, weight=1)

        # Title for payment methods
        ctk.CTkLabel(
            payment_methods_frame,
            text="Método de pago",
            font=theme.scaled_font(12, weight="bold"),
            text_color="#a0a0a0",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        self._payment_method_var = tk.StringVar(value="cash")
        self._method_frames: dict[str, ctk.CTkFrame] = {}

        contrast = theme.get_contrast_map()
        selected_bg = contrast["treeview_header"]
        selected_border = "#0078d4"
        unselected_border = contrast["search_border"]

        grid_row = 1

        if self._role == "cajero":
            # --- Cajero Layout ---
            # 1. Efectivo/Transferencia (cash) & Qr (transfer) side-by-side squares
            cajero_pair_frame = ctk.CTkFrame(payment_methods_frame, fg_color="transparent")
            cajero_pair_frame.grid(row=grid_row, column=0, sticky="ew", pady=(0, 2))
            cajero_pair_frame.grid_columnconfigure(0, weight=2) # Ligeramente menos ancho
            cajero_pair_frame.grid_columnconfigure(1, weight=5) # Ligeramente más ancho
            grid_row += 1

            cajero_methods = [
                ("💵", "Efectivo/\nTransf.", "cash"),
                ("📱", "Qr", "transfer")
            ]

            for col_idx, (m_icon, m_label, m_method) in enumerate(cajero_methods):
                is_selected = (m_method == "cash")
                method_frame = ctk.CTkFrame(
                    cajero_pair_frame,
                    fg_color=selected_bg if is_selected else "transparent",
                    border_width=2,
                    border_color=selected_border if is_selected else unselected_border,
                    corner_radius=10,
                    cursor="hand2",
                )
                method_frame._custom_theme_color = "skip"
                padx_val = (0, 3) if col_idx == 0 else (3, 0)
                method_frame.grid(row=0, column=col_idx, sticky="nsew", padx=padx_val)
                method_frame.grid_columnconfigure(0, weight=1)
                method_frame.grid_rowconfigure(0, weight=1)
                self._method_frames[m_method] = method_frame

                inner = ctk.CTkFrame(method_frame, fg_color="transparent")
                inner.grid(row=0, column=0, pady=(10, 10))

                ctk.CTkLabel(
                    inner,
                    text=m_icon,
                    font=theme.scaled_font(18),
                ).pack(pady=(0, 2))
                ctk.CTkLabel(
                    inner,
                    text=m_label,
                    font=theme.scaled_font(12, weight="bold"),
                ).pack()

                method_frame.bind("<Button-1>", lambda e, m=m_method: self._select_payment_method(m))
                for child in method_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, m=m_method: self._select_payment_method(m))
                    for grandchild in child.winfo_children():
                        grandchild.bind("<Button-1>", lambda e, m=m_method: self._select_payment_method(m))

            # 2. Card header and methods below
            card_header = ctk.CTkLabel(
                payment_methods_frame,
                text="💳  Tarjeta",
                font=theme.scaled_font(11, weight="bold"),
                text_color="#a0a0a0",
                anchor="w",
            )
            card_header.grid(row=grid_row, column=0, sticky="w", padx=4, pady=(4, 1))
            grid_row += 1

            card_pair_frame = ctk.CTkFrame(payment_methods_frame, fg_color="transparent")
            card_pair_frame.grid(row=grid_row, column=0, sticky="ew", pady=(0, 2))
            card_pair_frame.grid_columnconfigure(0, weight=1)
            card_pair_frame.grid_columnconfigure(1, weight=1)
            grid_row += 1

            for col_idx, (card_icon, card_label, card_method) in enumerate(self.CARD_METHODS):
                card_frame = ctk.CTkFrame(
                    card_pair_frame,
                    fg_color="transparent",
                    border_width=2,
                    border_color=unselected_border,
                    corner_radius=10,
                    cursor="hand2",
                )
                card_frame._custom_theme_color = "skip"
                padx_val = (0, 3) if col_idx == 0 else (3, 0)
                card_frame.grid(row=0, column=col_idx, sticky="nsew", padx=padx_val)
                card_frame.grid_columnconfigure(0, weight=1)
                card_frame.grid_rowconfigure(0, weight=1)
                self._method_frames[card_method] = card_frame

                inner = ctk.CTkFrame(card_frame, fg_color="transparent")
                inner.grid(row=0, column=0, pady=(10, 10))

                ctk.CTkLabel(
                    inner,
                    text=card_icon,
                    font=theme.scaled_font(18),
                ).pack(pady=(0, 2))
                ctk.CTkLabel(
                    inner,
                    text=card_label,
                    font=theme.scaled_font(12, weight="bold"),
                ).pack()

                card_frame.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))
                for child in card_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))
                    for grandchild in child.winfo_children():
                        grandchild.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))

        else:
            # --- Non-Cajero Layout ---
            # --- Single-row methods (cash, transfer) ---
            for icon, label, method in self.SINGLE_METHODS:
                display_label = label
                is_selected = method == "cash"
                
                method_frame = ctk.CTkFrame(
                    payment_methods_frame,
                    fg_color=selected_bg if is_selected else "transparent",
                    border_width=2,
                    border_color=selected_border if is_selected else unselected_border,
                    corner_radius=10,
                    cursor="hand2",
                )
                method_frame._custom_theme_color = "skip"
                method_frame.grid(row=grid_row, column=0, sticky="ew", pady=1)
                method_frame.grid_columnconfigure(2, weight=1)
                self._method_frames[method] = method_frame

                radio_frame = ctk.CTkFrame(method_frame, fg_color="transparent", width=26)
                radio_frame.grid(row=0, column=0, padx=(8, 2))
                ctk.CTkRadioButton(
                    radio_frame,
                    text="",
                    variable=self._payment_method_var,
                    value=method,
                    command=lambda m=method: self._on_payment_method_changed(m),
                    width=18,
                    height=18,
                ).pack(pady=3)

                ctk.CTkLabel(
                    method_frame,
                    text=icon,
                    font=theme.scaled_font(14),
                    anchor="w",
                ).grid(row=0, column=1, sticky="w", padx=(2, 4), pady=2)

                ctk.CTkLabel(
                    method_frame,
                    text=display_label,
                    font=theme.scaled_font(13, weight="bold" if is_selected else "normal"),
                    anchor="w",
                ).grid(row=0, column=2, sticky="w", padx=(0, 8), pady=2)

                method_frame.bind("<Button-1>", lambda e, m=method: self._select_payment_method(m))
                for child in method_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, m=method: self._select_payment_method(m))

                grid_row += 1

                # Insert the card group after "cash" row
                if method == "cash":
                    # --- Card group header ---
                    card_header = ctk.CTkLabel(
                        payment_methods_frame,
                        text="💳  Tarjeta",
                        font=theme.scaled_font(11, weight="bold"),
                        text_color="#a0a0a0",
                        anchor="w",
                    )
                    card_header.grid(row=grid_row, column=0, sticky="w", padx=4, pady=(4, 1))
                    grid_row += 1

                    # --- Two card sub-type buttons side by side ---
                    card_pair_frame = ctk.CTkFrame(payment_methods_frame, fg_color="transparent")
                    card_pair_frame.grid(row=grid_row, column=0, sticky="ew", pady=(0, 2))
                    card_pair_frame.grid_columnconfigure(0, weight=1)
                    card_pair_frame.grid_columnconfigure(1, weight=1)
                    grid_row += 1

                    for col_idx, (card_icon, card_label, card_method) in enumerate(self.CARD_METHODS):
                        card_frame = ctk.CTkFrame(
                            card_pair_frame,
                            fg_color="transparent",
                            border_width=2,
                            border_color=unselected_border,
                            corner_radius=10,
                            cursor="hand2",
                        )
                        card_frame._custom_theme_color = "skip"
                        padx_val = (0, 3) if col_idx == 0 else (3, 0)
                        card_frame.grid(row=0, column=col_idx, sticky="ew", padx=padx_val)
                        card_frame.grid_columnconfigure(0, weight=1)
                        self._method_frames[card_method] = card_frame

                        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
                        inner.grid(row=0, column=0, pady=(6, 6))

                        ctk.CTkLabel(
                            inner,
                            text=card_icon,
                            font=theme.scaled_font(18),
                        ).pack()
                        ctk.CTkLabel(
                            inner,
                            text=card_label,
                            font=theme.scaled_font(12, weight="bold"),
                        ).pack()

                        card_frame.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))
                        for child in card_frame.winfo_children():
                            child.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))
                            for grandchild in child.winfo_children():
                                grandchild.bind("<Button-1>", lambda e, m=card_method: self._select_payment_method(m))

        # --- Amount received ---
        self._amount_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        self._amount_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 2))  # Margen compactado
        self._amount_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._amount_frame,
            text="Monto recibido ($):",
            font=theme.scaled_font(11),
            text_color="#a0a0a0",
        ).grid(row=0, column=0, pady=(0, 1))  # Margen compactado

        self._received_entry = ctk.CTkEntry(
            self._amount_frame,
            placeholder_text="Ej: 5000",
            height=32,
            font=theme.scaled_font(14),
        )
        self._received_entry.grid(row=1, column=0, sticky="ew")
        self._received_entry.bind("<KeyRelease>", self._on_received_changed)

        change_frame = ctk.CTkFrame(self._amount_frame, fg_color="transparent")
        change_frame.grid(row=2, column=0, pady=(2, 2))  # Margen compactado

        ctk.CTkLabel(
            change_frame,
            text="Vuelto:",
            font=theme.scaled_font(14),
            text_color="#a0a0a0"
        ).pack(side="left", padx=(0, 4))

        self._change_label = ctk.CTkLabel(
            change_frame,
            text="$0",
            font=theme.scaled_font(16, weight="bold")
        )
        self._change_label.pack(side="left")

        # --- Action buttons ---
        buttons_frame = ctk.CTkFrame(self._payment_sidebar, fg_color="transparent")
        buttons_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(2, 5))  # Margen compactado
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        self._cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancelar",
            height=32,
            fg_color="#52525b",
            hover_color="#71717a",
            font=theme.scaled_font(12, weight="bold"),
            command=self._handle_cancel,
        )
        self._cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._confirm_btn = ctk.CTkButton(
            buttons_frame,
            text="Confirmar",
            height=32,
            fg_color="#0078d4",
            hover_color="#106ebe",
            font=theme.scaled_font(12, weight="bold"),
            command=self._handle_confirm,
        )
        self._confirm_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # --- auto-focus barcode entry whenever the frame is mapped ---
        self.bind("<Map>", lambda _e: self._barcode_entry.focus_set())
        
    # ---------------------------------------------------------------- public ---

    def update_cart(self, items: list[dict[str, Any]]) -> None:
        """Refresh the cart treeview with the given *items*."""
        self._cart_tree.update_cart(items)

    def update_total(self, total: int) -> None:
        """Update the displayed cart total and related fields."""
        self._total = total
        self._discount_amount = int(total * self._discount_pct / 100)
        self._surcharge_amount = int(total * self._surcharge_pct / 100)
        final_total = total - self._discount_amount + self._surcharge_amount
        
        self._subtotal_label.configure(text=f"${total:,}")
        
        if self._discount_amount > 0:
            self._discount_label.configure(
                text=f"${self._discount_amount:,} ({self._discount_pct:.0f}%)",
                text_color="#2ecc71",
            )
        else:
            self._discount_label.configure(
                text="$0",
                text_color="#a0a0a0",
            )
        
        if self._surcharge_amount > 0:
            self._surcharge_label.configure(
                text=f"${self._surcharge_amount:,} ({self._surcharge_pct:.0f}%)",
                text_color="#e74c3c",
            )
        else:
            self._surcharge_label.configure(
                text="$0",
                text_color="#a0a0a0",
            )
        
        self._total_label.configure(text=f"${final_total:,}")
        self._on_received_changed()

    def focus_barcode(self) -> None:
        """Force focus onto the barcode entry widget."""
        self._barcode_entry.focus_set()

    def update_theme(self) -> None:
        """Update search button colors, border, and payment method buttons when theme changes."""
        contrast = theme.get_contrast_map()
        self._search_btn.configure(
            fg_color=contrast["search_bg"],
            hover_color=contrast["panel"],
            border_color=contrast["search_border"],
            text_color=contrast["text"],
        )
        self._settings_btn.configure(
            fg_color=contrast["search_bg"],
            hover_color=contrast["panel"],
            border_color=contrast["search_border"],
            text_color=contrast["text"],
        )
        self.configure(border_color=contrast["search_border"])
        
        # Update payment method buttons with new theme colors
        selected_bg = contrast["treeview_header"]  # Darker background for better visibility
        selected_border = "#0078d4"  # Blue border for selected state
        unselected_border = contrast["search_border"]
        
        for m, frame in self._method_frames.items():
            if m == self._selected_payment_method:
                frame.configure(
                    fg_color=selected_bg,
                    border_color=selected_border,
                )
            else:
                frame.configure(
                    fg_color="transparent",
                    border_color=unselected_border,
                )

    def show_receipt(self, sale_data: dict[str, Any]) -> None:
        """Display an on-screen receipt preview after a successful sale.

        *sale_data* is the controller response ``data`` field, expected
        to contain ``sale``, ``items``, and ``change``.
        """
        from pos.view.widgets.receipt_preview import ReceiptPreview

        ReceiptPreview(self, sale_data)

    # ----------------------------------------------------------- callbacks ----

    def set_on_scan(self, callback: Callable[[str], None]) -> None:
        """Wire the scan callback."""
        self._on_scan = callback

    def set_on_update_qty(self, callback: Callable[[int, float], None]) -> None:
        """Wire the quantity-update callback."""
        self._on_update_qty = callback

    def set_on_remove_item(self, callback: Callable[[int], None]) -> None:
        """Wire the remove-item callback."""
        self._on_remove_item = callback

    def set_on_payment(self, callback: Callable[[str, int], None]) -> None:
        """Wire the payment callback."""
        self._on_payment = callback

    def set_on_discount(self, callback: Callable[[float], None]) -> None:
        """Wire the discount callback."""
        self._on_discount = callback

    def set_on_surcharge(self, callback: Callable[[float], None]) -> None:
        """Wire the surcharge callback."""
        self._on_surcharge = callback

    # ------------------------------------------------------- controller wire ---

    def set_controller(self, controller: Any) -> None:
        """Wire a ``SaleController`` instance and set up all event handlers.

        This is a convenience method that replaces manual callback wiring.
        After calling this, all view events are automatically routed to
        the controller and the cart view is refreshed.
        """
        self._controller = controller

        self._on_scan = self._controller_scan
        self._on_update_qty = self._controller_update_qty
        self._on_remove_item = self._controller_remove_item
        self._on_payment = self._controller_payment
        self._on_discount = self._controller_discount
        self._on_surcharge = self._controller_surcharge
        self._controller_search = self._controller.search_products

        self._update_cart()

    # ---------------------------------------------------- controller handlers ---

    def _controller_scan(self, barcode: str) -> None:
        """Handle barcode scan by looking up product via controller."""
        from pos.view.widgets.quick_create_dialog import QuickCreateDialog

        result = self._controller.add_by_barcode(barcode)
        if result["success"]:
            self._update_cart()
            return

        # Check if it is the "not found" flow (not an error)
        data = result.get("data") or {}
        if data.get("barcode") == barcode and result.get("error") is None:
            # Check if product exists but is inactive
            if data.get("inactive"):
                product = data.get("product")
                product_name = product.name if product else "producto"
                confirm_dialog = SaleConfirmDialog(
                    self,
                    title="Producto desactivado",
                    message=f'El producto "{product_name}" está desactivado.\n\n¿Desea reactivarlo y agregarlo al carrito?',
                )
                self.wait_window(confirm_dialog)
                confirm = confirm_dialog.result
                if confirm:
                    reactivate_result = self._controller.reactivate_and_add(
                        product.id, 1.0
                    )
                    if reactivate_result["success"]:
                        self._update_cart()
                        info_dialog = SaleInfoDialog(
                            self,
                            title="Producto reactivado",
                            message=f'El producto "{product_name}" ha sido reactivado y agregado al carrito.',
                        )
                        self.wait_window(info_dialog)
                    else:
                        self.show_error(reactivate_result["error"])
                # Whether they confirm or not, return focus to barcode entry
                self._barcode_entry.focus_set()
                return
            
            # Product not found — open QuickCreateDialog
            dialog = QuickCreateDialog(self, barcode)
            self.wait_window(dialog)
            product_data = dialog.result
            if product_data:
                create_result = self._controller.create_quick_product(
                    barcode=barcode,
                    name=product_data["name"],
                    sale_price=product_data["sale_price"],
                )
                if create_result["success"]:
                    self._update_cart()
                    if self._on_product_created:
                        # Defer refresh to next event loop cycle so the
                        # dialog is fully destroyed and the DB commit is
                        # visible before the products treeview redraws.
                        self.after_idle(self._on_product_created)
                else:
                    self.show_error(create_result["error"])
        else:
            self.show_error(result.get("error", "Error desconocido"))

        self._barcode_entry.focus_set()

    def _controller_update_qty(self, product_id: int, quantity: float) -> None:
        """Handle quantity update via controller."""
        result = self._controller.update_item_quantity(product_id, quantity)
        if result["success"]:
            self._update_cart()
        else:
            self.show_error(result["error"])

    def _controller_remove_item(self, product_id: int) -> None:
        """Handle item removal via controller."""
        result = self._controller.remove_item(product_id)
        if result["success"]:
            self._update_cart()
        else:
            self.show_error(result["error"])

    def _controller_discount(self, discount_pct: float) -> None:
        """Handle discount application via controller."""
        result = self._controller.apply_discount(discount_pct)
        if result["success"]:
            self._discount_pct = discount_pct
            self._discount_amount = result["data"]["discount_amount"]
            self.update_total(self._total)
        else:
            self.show_error(result["error"])

    def _controller_surcharge(self, surcharge_pct: float) -> None:
        """Handle surcharge application via controller."""
        result = self._controller.apply_surcharge(surcharge_pct)
        if result["success"]:
            self._surcharge_pct = surcharge_pct
            self._surcharge_amount = result["data"]["surcharge_amount"]
            self.update_total(self._total)
        else:
            self.show_error(result["error"])

    def _controller_payment(self, method: str, received: int) -> None:
        """Process payment via controller and show receipt on success."""
        result = self._controller.complete_sale(
            payment_method=method,
            amount_received=received,
        )
        if result["success"]:
            # Show receipt preview
            self.show_receipt(result["data"])
            self._clear_cart()
            # Reset payment sidebar
            self._received_entry.delete(0, tk.END)
            self._change_label.configure(text="$0")
            # Notify other views (e.g., cash register) that a sale completed
            if self._on_sale_completed is not None:
                self._on_sale_completed()
        else:
            self.show_error(result["error"])

    def _update_cart(self) -> None:
        """Refresh cart treeview and total label from controller."""
        cart_result = self._controller.get_cart()
        if cart_result["success"]:
            items = cart_result["data"]["items"]
            total = cart_result["data"]["total"]
            self.update_cart(items)
            self.update_total(total)

    def _clear_cart(self) -> None:
        """Clear the cart via controller and reset UI."""
        self._controller.clear_cart()
        self.update_cart([])
        self._discount_pct = 0.0
        self._discount_amount = 0
        self._surcharge_pct = 0.0
        self._surcharge_amount = 0
        self.update_total(0)
        self._barcode_entry.focus_set()
        
        # Reset payment method selection to cash (default) to avoid cashier confusion
        self._selected_payment_method = "cash"
        self._payment_method_var.set("cash")
        self._on_payment_method_changed("cash")

    # --------------------------------------------------------------- private ---

    def _select_payment_method(self, method: str) -> None:
        """Select a payment method when clicking on its frame."""
        self._payment_method_var.set(method)
        self._on_payment_method_changed(method)

    def _on_payment_method_changed(self, method: str) -> None:
        """Update visual state when payment method changes."""
        self._selected_payment_method = method
        # Get theme colors for consistent styling
        contrast = theme.get_contrast_map()
        selected_bg = contrast["treeview_header"]  # Darker background for better visibility
        selected_border = "#0078d4"  # Blue border for selected state
        unselected_border = contrast["search_border"]
        
        # Update border colors and backgrounds to show selection
        for m, frame in self._method_frames.items():
            if m == method:
                frame.configure(
                    fg_color=selected_bg,
                    border_color=selected_border,
                )
            else:
                frame.configure(
                    fg_color="transparent",
                    border_color=unselected_border,
                )
        
        # Show/hide amount received field based on payment method
        if method == "cash":
            self._amount_frame.grid()
            if self._surcharge_pct > 0:
                self._surcharge_pct = 0.0
                self._surcharge_amount = 0
                self.update_total(self._total)
            if hasattr(self, '_controller') and self._controller is not None:
                self._controller.apply_surcharge(0)
        else:
            self._amount_frame.grid_remove()
            
            # Auto-apply fixed surcharge
            if hasattr(self, '_controller') and self._controller is not None:
                if hasattr(self._controller, 'get_payment_surcharge_pct'):
                    res = self._controller.get_payment_surcharge_pct(method)
                    if res["success"]:
                        self._controller_surcharge(res["data"])

    def _on_received_changed(self, event: tk.Event | None = None) -> None:
        """Recalculate change as the user types the received amount."""
        raw = self._received_entry.get().strip()
        if not raw:
            self._change_label.configure(text="$0")
            return
        try:
            received = int(raw)
        except ValueError:
            self._change_label.configure(text="$0")
            return

        # Use total after discount and surcharge
        final_total = self._total - self._discount_amount + self._surcharge_amount
        change = received - final_total
        if change >= 0:
            self._change_label.configure(text=f"${change:,}")
        else:
            self._change_label.configure(text=f"-${abs(change):,}")

    def _handle_scan(self, barcode: str) -> None:
        if self._on_scan is not None:
            self._on_scan(barcode)

    def _handle_search(self, query: str) -> None:
        if not hasattr(self, "_controller_search") or self._controller_search is None:
            return
        result = self._controller_search(query)
        if not result["success"]:
            self.show_error(result.get("error", "Error desconocido"))
            self._barcode_entry.focus_set()
            return
        products = result["data"]
        if not products:
            # If the input looks like a barcode (all digits), treat it the
            # same as a scanner hit — open QuickCreateDialog so the user
            # can register the product on the spot.
            if query.isdigit():
                self._controller_scan(query)
            else:
                messagebox.showinfo("Buscar", "No se encontraron productos")
            self._barcode_entry.focus_set()
            return
        if len(products) == 1:
            p = products[0]
            has_barcode = bool(p.barcode and p.barcode.strip() and p.barcode != "—")
            if has_barcode:
                add_result = self._controller.add_by_barcode(p.barcode)
                if add_result["success"]:
                    self._update_cart()
                else:
                    self.show_error(add_result.get("error", "Error desconocido"))
                self._barcode_entry.focus_set()
                return
        from pos.view.widgets.product_search_dialog import ProductSearchDialog
        categories = self._get_categories()
        dialog = ProductSearchDialog(self, products, categories, role=self._role)
        self.wait_window(dialog)
        selected = dialog.result
        if selected is not None:
            qty = getattr(dialog, "selected_quantity", 1.0)
            has_barcode = bool(selected.barcode and selected.barcode.strip() and selected.barcode != "—")
            if has_barcode:
                add_result = self._controller.add_by_barcode(selected.barcode, quantity=qty)
            else:
                add_result = self._controller.add_by_product_id(selected.id, quantity=qty)

            if add_result["success"]:
                self._update_cart()
            else:
                self.show_error(add_result.get("error", "Error desconocido"))
        self._barcode_entry.focus_set()

    def _handle_search_button(self) -> None:
        """Open search dialog with all products for manual browsing."""
        if not hasattr(self, "_controller_search") or self._controller_search is None:
            return
        # Search with empty query to get all products
        result = self._controller_search("")
        if not result["success"]:
            self.show_error(result.get("error", "Error desconocido"))
            return
        products = result["data"]
        if not products:
            messagebox.showinfo("Buscar", "No hay productos disponibles")
            return
        from pos.view.widgets.product_search_dialog import ProductSearchDialog
        categories = self._get_categories()
        dialog = ProductSearchDialog(self, products, categories, role=self._role)
        self.wait_window(dialog)
        selected = dialog.result
        if selected is not None:
            qty = getattr(dialog, "selected_quantity", 1.0)
            has_barcode = bool(selected.barcode and selected.barcode.strip() and selected.barcode != "—")
            if has_barcode:
                add_result = self._controller.add_by_barcode(selected.barcode, quantity=qty)
            else:
                add_result = self._controller.add_by_product_id(selected.id, quantity=qty)

            if add_result["success"]:
                self._update_cart()
            else:
                self.show_error(add_result.get("error", "Error desconocido"))
        self._barcode_entry.focus_set()

    def _get_categories(self) -> list:
        """Fetch categories from controller for the search dialog."""
        if hasattr(self, "_controller") and hasattr(self._controller, "list_categories"):
            result = self._controller.list_categories()
            if result["success"]:
                return result["data"]
        return []

    def _handle_remove(self, product_id: int) -> None:
        if self._on_remove_item is not None:
            self._on_remove_item(product_id)

    def _handle_remove_button(self) -> None:
        selected = self._cart_tree.get_selected_item()
        if selected is None:
            messagebox.showwarning("Eliminar", "Seleccione un producto del carrito")
            return
        self._handle_remove(selected["product_id"])

    def _handle_discount_button(self) -> None:
        """Open discount dialog to apply a percentage discount."""
        from pos.view.widgets.discount_dialog import DiscountDialog

        dialog = DiscountDialog(
            self,
            subtotal=self._total,
            current_discount_pct=self._discount_pct,
        )
        self.wait_window(dialog)
        result = dialog.result

        if result is not None and self._on_discount is not None:
            self._on_discount(result)

    def _handle_cancel(self) -> None:
        """Cancel the current sale and clear the cart."""
        if self._total > 0:
            confirm = messagebox.askyesno(
                "Cancelar venta",
                "¿Está seguro de cancelar la venta actual?\n\nSe perderán todos los productos del carrito.",
            )
            if not confirm:
                return
        
        self._clear_cart()
        self._received_entry.delete(0, tk.END)
        self._change_label.configure(text="$0")

    def _handle_confirm(self) -> None:
        """Process the payment with the selected method and received amount."""
        if self._total == 0:
            self.show_error("No hay productos en el carrito")
            return

        method = self._payment_method_var.get()
        
        # Calculate final total after discount and surcharge
        final_total = self._total - self._discount_amount + self._surcharge_amount
        
        if method == "cash":
            raw = self._received_entry.get().strip()
            try:
                received = int(raw)
            except ValueError:
                self.show_error("Ingrese un monto válido")
                self._received_entry.focus_set()
                return

            if received < final_total:
                self.show_error("Monto insuficiente")
                self._received_entry.focus_set()
                return
        else:
            received = 0

        if self._on_payment is not None:
            self._on_payment(method, received)

    def show_error(self, message: str) -> None:
        """Display an error message centered on the system window."""
        dialog = SaleErrorDialog(self, message)
        self.wait_window(dialog)

    def _handle_settings_button(self) -> None:
        """Open sale settings dialog."""
        if not hasattr(self, "_controller") or self._controller is None:
            return
        from pos.view.widgets.sale_settings_dialog import SaleSettingsDialog
        dialog = SaleSettingsDialog(self, self._controller)
        self.wait_window(dialog)
        
        # If settings were applied, immediately update the total based on current method
        if dialog.applied:
            self._on_payment_method_changed(self._selected_payment_method)


class SaleErrorDialog(CenteredDialog):
    """Custom error message dialog centered on the system window."""

    def __init__(self, master: tk.Widget, message: str, **kwargs) -> None:
        super().__init__(
            master,
            width=380,
            height=200,
            title="Error",
            **kwargs,
        )

        # --- Icon/Header ---
        ctk.CTkLabel(
            self,
            text="⚠️ Error",
            font=theme.scaled_font(16, weight="bold"),
            text_color="#ef4444",
        ).pack(pady=(20, 10))

        # --- Message ---
        ctk.CTkLabel(
            self,
            text=message,
            font=theme.scaled_font(13),
            justify="center",
            wraplength=320,
        ).pack(pady=(0, 20))

        # --- Close button ---
        ctk.CTkButton(
            self,
            text="Aceptar",
            width=100,
            height=32,
            font=theme.scaled_font(13, weight="bold"),
            command=self.destroy,
        ).pack(pady=(0, 15))

        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self.update_idletasks()
        self._center_on_parent(master)

        # Focus
        self.focus_set()


class SaleConfirmDialog(CenteredDialog):
    """Custom yes/no confirmation dialog centered on the system window."""
    
    def __init__(self, master: tk.Widget, title: str, message: str, **kwargs) -> None:
        super().__init__(
            master,
            width=380,
            height=200,
            title=title,
            **kwargs,
        )
        self._result = False

        # --- Icon/Header ---
        ctk.CTkLabel(
            self,
            text=f"❓ {title}",
            font=theme.scaled_font(16, weight="bold"),
            text_color="#0078d4",
        ).place(relx=0.5, y=20, anchor="n")

        # --- Message ---
        ctk.CTkLabel(
            self,
            text=message,
            font=theme.scaled_font(13),
            justify="center",
            wraplength=320,
        ).place(relx=0.5, y=60, anchor="n")

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.place(relx=0.5, y=140, anchor="n")

        ctk.CTkButton(
            btn_frame,
            text="No",
            width=100,
            height=32,
            fg_color="gray",
            hover_color="#5a6268",
            font=theme.scaled_font(13, weight="bold"),
            command=self._no,
        ).pack(side="left", padx=10)

        self._yes_btn = ctk.CTkButton(
            btn_frame,
            text="Sí",
            width=100,
            height=32,
            font=theme.scaled_font(13, weight="bold"),
            command=self._yes,
        )
        self._yes_btn.pack(side="left", padx=10)

        self.bind("<Return>", lambda _e: self._yes())
        self.bind("<Escape>", lambda _e: self._no())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self.update_idletasks()
        self._center_on_parent(master)

        self.after(100, self._yes_btn.focus_set)

    @property
    def result(self) -> bool:
        return self._result

    def _yes(self) -> None:
        self._result = True
        self.destroy()

    def _no(self) -> None:
        self._result = False
        self.destroy()


class SaleInfoDialog(CenteredDialog):
    """Custom info message dialog centered on the system window."""

    def __init__(self, master: tk.Widget, title: str, message: str, **kwargs) -> None:
        super().__init__(
            master,
            width=380,
            height=200,
            title=title,
            **kwargs,
        )

        # --- Icon/Header ---
        ctk.CTkLabel(
            self,
            text=f"ℹ️ {title}",
            font=theme.scaled_font(16, weight="bold"),
            text_color="#0078d4",
        ).place(relx=0.5, y=20, anchor="n")

        # --- Message ---
        ctk.CTkLabel(
            self,
            text=message,
            font=theme.scaled_font(13),
            justify="center",
            wraplength=320,
        ).place(relx=0.5, y=60, anchor="n")

        # --- Close button ---
        self._ok_btn = ctk.CTkButton(
            self,
            text="Aceptar",
            width=100,
            height=32,
            font=theme.scaled_font(13, weight="bold"),
            command=self.destroy,
        )
        self._ok_btn.place(relx=0.5, y=140, anchor="n")

        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())

        theme.apply_theme_to_widget(self, theme.get_contrast_map())
        self.update_idletasks()
        self._center_on_parent(master)

        self.after(100, self._ok_btn.focus_set)
