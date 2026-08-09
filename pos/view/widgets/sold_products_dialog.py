"""Sold products dialog — shows products sold during a cash register session."""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import customtkinter as ctk

from pos.view.widgets.centered_dialog import CenteredDialog
from pos.view.widgets.treeview_sorting import add_sorting_to_treeview
from pos.view import theme
from pos.service.report_service import ReportService


class SoldProductsDialog(CenteredDialog):
    """Modal dialog displaying products sold during a register session with detailed transaction info.

    Parameters
    ----------
    master : tk.Widget
        Parent window.
    register_id : int
        ID of the register session.
    products : list[dict]
        List of sold products with name, quantity, unit_type, unit_price, subtotal, etc.
    **kwargs :
        Forwarded to ``CenteredDialog``.
    """

    COLUMNS = ("tipo", "hora", "metodo_pago", "producto", "cantidad", "precio_unit", "total")
    COLUMN_LABELS = {
        "tipo": "Tipo",
        "hora": "Hora",
        "metodo_pago": "Método de Pago",
        "producto": "Producto",
        "cantidad": "Cantidad",
        "precio_unit": "Precio Unit.",
        "total": "Total",
    }

    def __init__(
        self,
        master: tk.Widget,
        register_id: int,
        products: list[dict[str, Any]],
        opening_time: str = "",
        closing_time: str = "",
        role: str = "",
        controller: Any = None,
        on_update: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        h_val = 530 if role == "admin" else 500
        super().__init__(
            master,
            width=780,
            height=h_val,
            title=f"Productos Vendidos - Caja #{register_id}",
            **kwargs,
        )

        self._register_id = register_id
        self._products = products
        self._opening_time = opening_time
        self._closing_time = closing_time
        self._role = role
        self._controller = controller
        self._on_update = on_update

        # --- Header label (packed first, side top) ---
        self._title_label = ctk.CTkLabel(
            self,
            text=f"Resumen de Artículos Vendidos — Caja #{register_id}",
            font=theme.scaled_font(14, weight="bold"),
            anchor="center",
        )
        self._title_label.pack(side="top", fill="x", pady=(15, 2), padx=15)

        close_display = closing_time if closing_time else "Caja Abierta"
        self._subtitle_label = ctk.CTkLabel(
            self,
            text=f"Apertura: {opening_time}   |   Cierre: {close_display}",
            font=theme.scaled_font(12, weight="normal"),
            text_color="#888888" if theme.get_contrast_map()["text"] != "white" else "#bbbbbb",
            anchor="center",
        )
        self._subtitle_label.pack(side="top", fill="x", pady=(0, 10), padx=15)

        # --- Button action bar (packed second, side bottom) ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=(5, 15), padx=15)

        self._close_btn = ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            width=100,
            command=self.destroy,
        )
        self._close_btn.pack(side="left")

        if self._role == "admin":
            self._edit_btn = ctk.CTkButton(
                btn_frame,
                text="✏️ Editar",
                width=100,
                font=theme.scaled_font(12, weight="bold"),
                command=self._handle_edit_quantity,
            )
            self._edit_btn.pack(side="left", padx=10)
            self._edit_btn.configure(state="disabled")

        self._pdf_btn = ctk.CTkButton(
            btn_frame,
            text="📕 Exportar PDF",
            width=120,
            fg_color="#c0392b",
            hover_color="#a83226",
            font=theme.scaled_font(12, weight="bold"),
            command=self._export_pdf,
        )
        self._pdf_btn.pack(side="right", padx=5)

        self._excel_btn = ctk.CTkButton(
            btn_frame,
            text="📊 Exportar Excel",
            width=120,
            fg_color="#27ae60",
            hover_color="#219653",
            font=theme.scaled_font(12, weight="bold"),
            command=self._export_excel,
        )
        self._excel_btn.pack(side="right", padx=5)

        # --- Totals summary bar (packed third, side bottom) ---
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.pack(side="bottom", fill="x", padx=15, pady=(5, 5))

        # Left container for vertical stacking of qty and weight
        left_summary = ctk.CTkFrame(summary_frame, fg_color="transparent")
        left_summary.pack(side="left", padx=5)

        self._total_qty_label = ctk.CTkLabel(
            left_summary,
            text="",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        )
        self._total_qty_label.pack(anchor="w")

        self._total_weight_label = ctk.CTkLabel(
            left_summary,
            text="",
            font=theme.scaled_font(12, weight="bold"),
            anchor="w",
        )
        self._total_weight_label.pack(anchor="w")

        # Right side summary for Sales Totals and Net Profit
        right_summary = ctk.CTkFrame(summary_frame, fg_color="transparent")
        right_summary.pack(side="right", padx=5)

        self._total_sales_label = ctk.CTkLabel(
            right_summary,
            text="",
            font=theme.scaled_font(12, weight="bold"),
            anchor="e",
        )
        self._total_sales_label.pack(anchor="e")

        self._total_net_label = ctk.CTkLabel(
            right_summary,
            text="",
            font=theme.scaled_font(14, weight="bold"),
            text_color="#2ecc71",  # Green color for net profits
            anchor="e",
        )
        self._total_net_label.pack(anchor="e")

        # Initialize labels text values
        self._recalculate_and_update_labels()

        # --- Treeview container (packed last, side top, filling remaining space) ---
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(side="top", fill="both", expand=True, padx=15, pady=5)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        for col in self.COLUMNS:
            self._tree.heading(col, text=self.COLUMN_LABELS[col])

        self._tree.column("tipo", width=120, anchor="w", stretch=False)
        self._tree.column("hora", width=60, anchor="center", stretch=False)
        self._tree.column("metodo_pago", width=110, anchor="w", stretch=False)
        self._tree.column("producto", width=150, anchor="w", stretch=True)
        self._tree.column("cantidad", width=80, anchor="center", stretch=False)
        self._tree.column("precio_unit", width=90, anchor="e", stretch=False)
        self._tree.column("total", width=95, anchor="e", stretch=False)

        # Enable column sorting
        add_sorting_to_treeview(
            self._tree,
            list(self.COLUMNS),
            column_types={
                "tipo": "str",
                "hora": "str",
                "metodo_pago": "str",
                "producto": "str",
                "cantidad": "float",
                "precio_unit": "int",
                "total": "int",
            }
        )

        # Scrollbars
        self._scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._tree.yview
        )
        self._hscrollbar = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self._tree.xview
        )
        self._tree.configure(yscrollcommand=self._scrollbar.set, xscrollcommand=self._hscrollbar.set)
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self._tree.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._hscrollbar.grid(row=1, column=0, sticky="ew")

        # Populate treeview
        self._populate()

        theme.apply_theme_to_widget(self, theme.get_contrast_map())

    def _populate(self) -> None:
        """Populate the treeview with the sold product items."""
        for idx, item in enumerate(self._products):
            sale_num = item["sale_num"]
            created_at = item.get("created_at") or ""
            # Extract time part from timestamp
            time_str = created_at.split(" ")[1] if " " in created_at else created_at
            # Keep only hour and minutes (HH:MM)
            if ":" in time_str:
                parts = time_str.split(":")
                time_str = f"{parts[0]}:{parts[1]}"

            payment_method = _format_method(item["payment_method"])
            name = item["name"]
            qty = item["quantity"]
            unit_type = item.get("unit_type", "Unidad")
            is_kg = unit_type.lower() in ("kg", "weight_kg")

            if qty == 0:
                qty_str = "-"
                unit_price_str = "-"
            elif is_kg:
                formatted_qty = f"{float(qty):.3f}".rstrip("0").rstrip(".")
                # Check for negative weights
                if formatted_qty.startswith("-"):
                    abs_val = formatted_qty.lstrip("-")
                    formatted_qty = f"-{abs_val}"
                if not formatted_qty or formatted_qty == "-" or formatted_qty == "":
                    formatted_qty = "0"
                qty_str = f"{formatted_qty} Kg"
            else:
                qty_str = f"{int(qty)} u."

            if qty != 0:
                unit_price_str = f"${item['unit_price']:,}"
            
            subtotal = item["subtotal"]
            subtotal_str = f"-${abs(subtotal):,}" if subtotal < 0 else f"${subtotal:,}"

            self._tree.insert(
                "",
                "end",
                values=(sale_num, time_str, payment_method, name, qty_str, unit_price_str, subtotal_str),
                tags=(idx,),
            )

    def _export_excel(self) -> None:
        """Export the detailed list of sold products to Excel."""
        from tkinter import filedialog, messagebox
        filepath = filedialog.asksaveasfilename(
            title="Exportar a Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"Caja_{self._register_id}_Productos_Vendidos",
            parent=self,
        )
        if not filepath:
            return

        export_data = []
        for item in self._products:
            created_at = item.get("created_at") or ""
            time_str = created_at.split(" ")[1] if " " in created_at else created_at
            if ":" in time_str:
                parts = time_str.split(":")
                time_str = f"{parts[0]}:{parts[1]}"

            qty = item["quantity"]
            is_kg = (item.get("unit_type") or "Unidad").lower() in ("kg", "weight_kg")
            if qty == 0:
                qty_str = "-"
                unit_price_str = "-"
            elif is_kg:
                formatted_qty = f"{float(qty):.3f}".rstrip("0").rstrip(".")
                if formatted_qty.startswith("-"):
                    abs_val = formatted_qty.lstrip("-")
                    formatted_qty = f"-{abs_val}"
                if not formatted_qty or formatted_qty == "-" or formatted_qty == "":
                    formatted_qty = "0"
                qty_str = f"{formatted_qty} Kg"
                unit_price_str = f"${item['unit_price']:,}"
            else:
                qty_str = f"{int(qty)} u."
                unit_price_str = f"${item['unit_price']:,}"

            subtotal = item["subtotal"]
            subtotal_str = f"-${abs(subtotal):,}" if subtotal < 0 else f"${subtotal:,}"

            export_data.append({
                "Tipo": item["sale_num"],
                "Hora": time_str,
                "Método de Pago": _format_method(item["payment_method"]),
                "Producto": item["name"],
                "Cantidad": qty_str,
                "Precio Unitario": unit_price_str,
                "Total": subtotal_str,
            })

        # Calculate summary values
        total_qty = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() == "unidad"
        )
        total_qty_str = f"{int(total_qty)}"

        total_weight = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() in ("kg", "weight_kg")
        )
        total_weight_str = f"{total_weight:.3f}".rstrip("0").rstrip(".")
        if not total_weight_str or total_weight_str == "":
            total_weight_str = "0"

        # Ventas totales = sum of all sale items subtotals
        total_sales = sum(
            item["subtotal"]
            for item in self._products
            if "sale_id" in item
        )
        total_sales_str = f"-${abs(total_sales):,}" if total_sales < 0 else f"${total_sales:,}"

        # Ganancia Bruta = Sumatoria(Precio de Venta) - Sumatoria(Costo de Producto)
        total_cost = sum(
            item["quantity"] * (item.get("cost_price") or 0)
            for item in self._products
            if "sale_id" in item
        )
        gross_profit = total_sales - total_cost

        # Devoluciones totales
        total_returns = sum(
            abs(item["subtotal"])
            for item in self._products
            if "return_id" in item
        )

        # Ganancia neta = Ganancia Bruta - Devoluciones
        net_profit = gross_profit - total_returns
        net_profit_str = f"-${abs(net_profit):,}" if net_profit < 0 else f"${net_profit:,}"

        # Append summary attributes to export list
        export_data.append({
            "Tipo": "", "Hora": "", "Método de Pago": "", "Producto": "", "Cantidad": "", "Precio Unitario": "", "Total": ""
        })
        export_data.append({
            "Tipo": "", "Hora": "", "Método de Pago": "",
            "Producto": "Total productos vendidos (unidad)",
            "Cantidad": f"{total_qty_str} u.",
            "Precio Unitario": "", "Total": ""
        })
        export_data.append({
            "Tipo": "", "Hora": "", "Método de Pago": "",
            "Producto": "Total peso vendido (kg)",
            "Cantidad": f"{total_weight_str} Kg",
            "Precio Unitario": "", "Total": ""
        })
        export_data.append({
            "Tipo": "", "Hora": "", "Método de Pago": "",
            "Producto": "Ventas totales",
            "Cantidad": "", "Precio Unitario": "",
            "Total": total_sales_str
        })
        export_data.append({
            "Tipo": "", "Hora": "", "Método de Pago": "",
            "Producto": "Ganancia neta",
            "Cantidad": "", "Precio Unitario": "",
            "Total": net_profit_str
        })

        try:
            ReportService.export_excel(
                data=export_data,
                filepath=filepath,
                start_date=self._opening_time,
                end_date=self._closing_time if self._closing_time else "En curso",
                title=f"Detalle de Productos Vendidos - Caja #{self._register_id}",
            )
            messagebox.showinfo(
                "Exportación Exitosa",
                f"Se exportó el detalle a:\n{filepath}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Error al Exportar",
                f"No se pudo exportar a Excel:\n{e}",
                parent=self,
            )

    def _export_pdf(self) -> None:
        """Export the detailed list of sold products to PDF."""
        from tkinter import filedialog, messagebox
        filepath = filedialog.asksaveasfilename(
            title="Exportar a PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Caja_{self._register_id}_Productos_Vendidos",
            parent=self,
        )
        if not filepath:
            return

        export_data = []
        for item in self._products:
            created_at = item.get("created_at") or ""
            time_str = created_at.split(" ")[1] if " " in created_at else created_at
            if ":" in time_str:
                parts = time_str.split(":")
                time_str = f"{parts[0]}:{parts[1]}"

            qty = item["quantity"]
            is_kg = (item.get("unit_type") or "Unidad").lower() in ("kg", "weight_kg")
            if qty == 0:
                qty_str = "-"
                unit_price_str = "-"
            elif is_kg:
                formatted_qty = f"{float(qty):.3f}".rstrip("0").rstrip(".")
                if formatted_qty.startswith("-"):
                    abs_val = formatted_qty.lstrip("-")
                    formatted_qty = f"-{abs_val}"
                if not formatted_qty or formatted_qty == "-" or formatted_qty == "":
                    formatted_qty = "0"
                qty_str = f"{formatted_qty} Kg"
                unit_price_str = f"${item['unit_price']:,}"
            else:
                qty_str = f"{int(qty)} u."
                unit_price_str = f"${item['unit_price']:,}"

            subtotal = item["subtotal"]
            subtotal_str = f"-${abs(subtotal):,}" if subtotal < 0 else f"${subtotal:,}"

            export_data.append({
                "Tipo": item["sale_num"],
                "Hora": time_str,
                "Método de Pago": _format_method(item["payment_method"]),
                "Producto": item["name"],
                "Cantidad": qty_str,
                "Precio Unitario": unit_price_str,
                "Total": subtotal_str,
            })

        # Calculate summary values
        total_qty = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() == "unidad"
        )
        total_qty_str = f"{int(total_qty)}"

        total_weight = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() in ("kg", "weight_kg")
        )
        total_weight_str = f"{total_weight:.3f}".rstrip("0").rstrip(".")
        if not total_weight_str or total_weight_str == "":
            total_weight_str = "0"

        # Ventas totales = sum of all sale items subtotals
        total_sales = sum(
            item["subtotal"]
            for item in self._products
            if "sale_id" in item
        )
        total_sales_str = f"-${abs(total_sales):,}" if total_sales < 0 else f"${total_sales:,}"

        # Ganancia Bruta = Sumatoria(Precio de Venta) - Sumatoria(Costo de Producto)
        total_cost = sum(
            item["quantity"] * (item.get("cost_price") or 0)
            for item in self._products
            if "sale_id" in item
        )
        gross_profit = total_sales - total_cost

        # Devoluciones totales
        total_returns = sum(
            abs(item["subtotal"])
            for item in self._products
            if "return_id" in item
        )

        # Ganancia neta = Ganancia Bruta - Devoluciones
        net_profit = gross_profit - total_returns
        net_profit_str = f"-${abs(net_profit):,}" if net_profit < 0 else f"${net_profit:,}"

        summary_lines = [
            f"Total productos vendidos (unidad): {total_qty_str} u.",
            f"Total peso vendido (kg): {total_weight_str} Kg",
            f"Ventas totales: {total_sales_str}",
            f"Ganancia neta: {net_profit_str}"
        ]

        try:
            ReportService.export_pdf(
                data=export_data,
                filepath=filepath,
                start_date=self._opening_time,
                end_date=self._closing_time if self._closing_time else "En curso",
                title=f"Detalle de Productos Vendidos - Caja #{self._register_id}",
                summary_lines=summary_lines,
            )
            messagebox.showinfo(
                "Exportación Exitosa",
                f"Se exportó el detalle a:\n{filepath}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror(
                "Error al Exportar",
                f"No se pudo exportar a PDF:\n{e}",
                parent=self,
            )

    def _on_tree_select(self, event: Any) -> None:
        """Enable or disable the Edit button based on the selected row type."""
        if not hasattr(self, "_edit_btn"):
            return
        selected = self._tree.selection()
        if not selected:
            self._edit_btn.configure(state="disabled")
            return
        
        tags = self._tree.item(selected[0], "tags")
        if not tags:
            self._edit_btn.configure(state="disabled")
            return
        
        idx = int(tags[0])
        item = self._products[idx]
        
        if item.get("sale_num") == "Pago Proveedor":
            self._edit_btn.configure(state="disabled")
        else:
            self._edit_btn.configure(state="normal")

    def _handle_edit_quantity(self) -> None:
        """Prompt the admin to edit the quantity of the selected sold/returned product."""
        selected = self._tree.selection()
        if not selected:
            return
        
        tags = self._tree.item(selected[0], "tags")
        if not tags:
            return
            
        idx = int(tags[0])
        item = self._products[idx]
        unit_type = (item.get("unit_type") or "Unidad").lower()
        is_kg = unit_type in ("kg", "weight_kg")
        
        edit_mode = "quantity"
        if is_kg:
            # Show choice dialog
            choice_dlg = EditChoiceDialog(self)
            self.wait_window(choice_dlg)
            if choice_dlg.result is None:
                # User cancelled
                return
            edit_mode = choice_dlg.result
            
        if edit_mode == "quantity":
            title_text = "Editar Cantidad"
            prompt_text = f"Modificar cantidad para:\n{item['name']}\n\nCantidad actual: {abs(item['quantity'])}"
            if unit_type == "unidad":
                prompt_text += "\n(Debe ser un número entero)"
            else:
                prompt_text += "\n(Ingrese los Kilogramos, ej: 1.5)"
                
            dialog = ctk.CTkInputDialog(text=prompt_text, title=title_text)
            dialog.geometry(f"+{self.winfo_x() + 150}+{self.winfo_y() + 100}")
            
            input_value = dialog.get_input()
            if input_value is None:
                return
                
            try:
                new_qty = float(input_value)
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Ingrese un valor numérico válido.", parent=self)
                return
        else: # edit_mode == "amount"
            title_text = "Editar por Monto"
            current_amount = abs(item["subtotal"])
            prompt_text = f"Modificar monto total para:\n{item['name']}\n\nMonto actual: ${current_amount:,}"
            prompt_text += "\n(Ingrese el nuevo importe total en pesos, ej: 1200)"
            
            dialog = ctk.CTkInputDialog(text=prompt_text, title=title_text)
            dialog.geometry(f"+{self.winfo_x() + 150}+{self.winfo_y() + 100}")
            
            input_value = dialog.get_input()
            if input_value is None:
                return
                
            try:
                new_amount = float(input_value)
            except ValueError:
                from tkinter import messagebox
                messagebox.showerror("Error", "Ingrese un valor numérico válido.", parent=self)
                return
                
            if new_amount <= 0:
                from tkinter import messagebox
                messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self)
                return
                
            # Calculate corresponding quantity
            price = item["unit_price"]
            if price <= 0:
                from tkinter import messagebox
                messagebox.showerror("Error", "No se puede calcular cantidad para un producto con precio cero.", parent=self)
                return
                
            new_qty = new_amount / price
            
        result = self._controller.update_sold_product_quantity(self._register_id, item, new_qty)
        if result["success"]:
            from tkinter import messagebox
            messagebox.showinfo("Éxito", "Modificación realizada correctamente.", parent=self)
            
            refresh_res = self._controller.get_sold_products(self._register_id)
            self._products = refresh_res["data"]["products"]
            
            for child in self._tree.get_children():
                self._tree.delete(child)
            self._populate()
            self._recalculate_and_update_labels()
            
            if self._on_update is not None:
                self._on_update()
        else:
            from tkinter import messagebox
            messagebox.showerror("Error", result["error"], parent=self)

    def _recalculate_and_update_labels(self) -> None:
        """Recalculate quantities, total sales, and net profit, and refresh label text displays."""
        total_qty = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() == "unidad"
        )
        total_qty_str = f"{int(total_qty)}"

        total_weight = sum(
            item["quantity"]
            for item in self._products
            if (item.get("unit_type") or "Unidad").lower() in ("kg", "weight_kg")
        )
        total_weight_str = f"{total_weight:.3f}".rstrip("0").rstrip(".")
        if not total_weight_str or total_weight_str == "":
            total_weight_str = "0"

        # Ventas totales = sum of all sale items subtotals
        total_sales = sum(
            item["subtotal"]
            for item in self._products
            if "sale_id" in item
        )
        total_sales_str = f"-${abs(total_sales):,}" if total_sales < 0 else f"${total_sales:,}"

        # Ganancia Bruta = Sumatoria(Precio de Venta) - Sumatoria(Costo de Producto)
        total_cost = sum(
            item["quantity"] * (item.get("cost_price") or 0)
            for item in self._products
            if "sale_id" in item
        )
        gross_profit = total_sales - total_cost

        # Devoluciones totales
        total_returns = sum(
            abs(item["subtotal"])
            for item in self._products
            if "return_id" in item
        )

        # Ganancia neta = Ganancia Bruta - Devoluciones
        net_profit = gross_profit - total_returns
        net_profit_str = f"-${abs(net_profit):,}" if net_profit < 0 else f"${net_profit:,}"

        self._total_qty_label.configure(text=f"Total productos vendidos: {total_qty_str} u.")
        self._total_weight_label.configure(text=f"Total peso vendido: {total_weight_str} Kg")
        self._total_sales_label.configure(text=f"Ventas totales: {total_sales_str}")
        self._total_net_label.configure(
            text=f"Ganancia neta: {net_profit_str}",
            text_color="#2ecc71" if net_profit >= 0 else "#e74c3c"
        )


class EditChoiceDialog(ctk.CTkToplevel):
    """Small modal dialog asking the user to choose between editing by Quantity or by Amount."""
    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master)
        self.title("Seleccionar Modo")
        self.geometry("320x150")
        self.resizable(False, False)
        
        # Center window relative to master
        self.geometry(f"+{master.winfo_x() + 200}+{master.winfo_y() + 150}")
        
        self.result = None
        
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1), weight=1)
        
        lbl = ctk.CTkLabel(
            self,
            text="¿Desea editar por Cantidad (Kg) o por Monto ($)?",
            font=theme.scaled_font(12, weight="bold"),
            wraplength=280,
        )
        lbl.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10))
        
        btn_qty = ctk.CTkButton(
            self,
            text="Cantidad (Kg)",
            command=self._on_qty,
        )
        btn_qty.grid(row=1, column=0, padx=(15, 5), pady=10, sticky="ew")
        
        btn_amt = ctk.CTkButton(
            self,
            text="Monto ($)",
            command=self._on_amt,
        )
        btn_amt.grid(row=1, column=1, padx=(5, 15), pady=10, sticky="ew")
        
        # Make modal
        self.grab_set()
        
    def _on_qty(self) -> None:
        self.result = "quantity"
        self.destroy()
        
    def _on_amt(self) -> None:
        self.result = "amount"
        self.destroy()


def _format_method(method: str) -> str:
    """Translate internal payment method code to display label."""
    labels = {
        "cash": "Efectivo",
        "card": "Tarjeta",
        "transfer": "Transferencia",
        "qr": "Qr",
        "debit_card": "Tarjeta de Débito",
        "credit_card": "Tarjeta de Crédito",
    }
    return labels.get(method, method)
