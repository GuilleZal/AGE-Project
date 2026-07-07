"""User management view — admin-only user list and create/edit form."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk
from pos.view import theme


class UserManagementView(ctk.CTkFrame):
    """Admin interface for user CRUD.

    Layout:
        ┌──────────────────────────────────────────┐
        │  [Crear usuario]                          │
        │                                           │
        │  ┌─────────────────────────────────────┐  │
        │  │ Username  │ Role      │ Estado      │  │
        │  │ admin     │ Admin     │ Activo      │  │
        │  │ gerente1  │ Gerente   │ Activo      │  │
        │  │ cajero1   │ Cajero    │ Inactivo    │  │
        │  └─────────────────────────────────────┘  │
        │                                           │
        │  [Editar] [Desactivar]                    │
        └──────────────────────────────────────────┘
    """

    COLUMNS = ("username", "role", "status")
    ROLE_DISPLAY = {
        "admin": "Administrador",
        "gerente": "Gerente",
        "cajero": "Cajero",
        "inventario": "Inventario",
    }

    def __init__(self, master, **kwargs) -> None:
        border_color = theme.get_contrast_map()["search_border"]
        super().__init__(master, fg_color="transparent", border_width=2, border_color=border_color, **kwargs)
        self._controller = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top bar: create button ---
        self._top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        self._create_btn = ctk.CTkButton(
            self._top_frame,
            text="+ Crear usuario",
            width=150,
            height=36,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#28a745",
            command=self._on_create_clicked,
        )
        self._create_btn.pack(side="left")

        # --- User list treeview ---
        self._tree_frame = ctk.CTkFrame(self)
        self._tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self._tree_frame.grid_rowconfigure(0, weight=1)
        self._tree_frame.grid_columnconfigure(0, weight=1)

        self._style = ttk.Style(self._tree_frame)
        self._configure_style()

        self._tree = ttk.Treeview(
            self._tree_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("username", text="Usuario")
        self._tree.heading("role", text="Rol")
        self._tree.heading("status", text="Estado")

        self._tree.column("username", width=200, minwidth=150, anchor="w")
        self._tree.column("role", width=150, minwidth=120, anchor="center")
        self._tree.column("status", width=120, minwidth=100, anchor="center")

        self._tree.grid(row=0, column=0, sticky="nsew")

        self._vscroll = ttk.Scrollbar(
            self._tree_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=self._vscroll.set)
        self._vscroll.grid(row=0, column=1, sticky="ns")

        # --- Action buttons ---
        self._action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._action_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))

        self._edit_btn = ctk.CTkButton(
            self._action_frame,
            text="Editar",
            width=120,
            height=36,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#1f538d",
            command=self._on_edit_clicked,
        )
        self._edit_btn.pack(side="left", padx=5)

        self._toggle_btn = ctk.CTkButton(
            self._action_frame,
            text="Desactivar",
            width=120,
            height=36,
            font=theme.scaled_font(13, weight="bold"),
            fg_color="#8b1a1a",
            command=self._on_deactivate_clicked,
        )
        self._toggle_btn.pack(side="left", padx=5)

    def set_controller(self, controller) -> None:
        """Store reference to UserManagementController."""
        self._controller = controller
        self.refresh_users()

    def refresh_users(self) -> None:
        """Reload user list from controller."""
        if self._controller is None:
            return
        result = self._controller.list_users()
        if not result["success"]:
            return

        for child in self._tree.get_children():
            self._tree.delete(child)

        for u in result["data"]:
            role_display = self.ROLE_DISPLAY.get(u["role"], u["role"])
            status = "Activo" if u["is_active"] else "Inactivo"
            self._tree.insert(
                "",
                "end",
                iid=str(u["id"]),
                values=(u["username"], role_display, status),
            )

    def _on_create_clicked(self) -> None:
        """Show create form."""
        dialog = _UserFormDialog(self, title="Crear usuario")
        self.wait_window(dialog)
        if dialog.result and self._controller:
            data = dialog.result
            result = self._controller.create_user(
                data["username"], data["password"], data["role"]
            )
            if result["success"]:
                self.refresh_users()
            else:
                messagebox.showerror("Error", result["error"])

    def _on_edit_clicked(self) -> None:
        """Show edit form for selected user. Disabled for admin bootstrap."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Seleccionar", "Seleccione un usuario para editar")
            return
        user_id = int(sel[0])
        if self._controller and self._controller.is_admin_protected(user_id):
            messagebox.showwarning("Protegido", "No se puede editar el usuario admin")
            return

        username = self._tree.item(sel[0], "values")[0]
        dialog = _UserFormDialog(
            self, title="Editar usuario", username=username, edit_mode=True
        )
        self.wait_window(dialog)
        if dialog.result and self._controller:
            data = dialog.result
            result = self._controller.update_user(
                user_id,
                password=data.get("password"),
                role=data.get("role"),
            )
            if result["success"]:
                self.refresh_users()
            else:
                messagebox.showerror("Error", result["error"])

    def _on_deactivate_clicked(self) -> None:
        """Toggle active status. Disabled for admin bootstrap."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Seleccionar", "Seleccione un usuario")
            return
        user_id = int(sel[0])
        if self._controller and self._controller.is_admin_protected(user_id):
            messagebox.showwarning("Protegido", "No se puede desactivar el usuario admin")
            return

        values = self._tree.item(sel[0], "values")
        current_status = values[2]
        if current_status == "Activo":
            result = self._controller.deactivate_user(user_id)
        else:
            result = self._controller.activate_user(user_id)

        if result["success"]:
            self.refresh_users()
        else:
            messagebox.showerror("Error", result["error"])

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


class _UserFormDialog(ctk.CTkToplevel):
    """Dialog for creating or editing a user."""

    def __init__(
        self,
        master,
        title: str = "Crear usuario",
        username: str = "",
        edit_mode: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self._result: dict[str, Any] | None = None
        self._edit_mode = edit_mode

        ctk.CTkLabel(
            self, text="Usuario:", font=theme.scaled_font(14)
        ).pack(pady=(20, 5))

        self._username_entry = ctk.CTkEntry(self, width=250, height=36)
        self._username_entry.pack(padx=20, pady=5)
        if username:
            self._username_entry.insert(0, username)
            self._username_entry.configure(state="disabled")

        ctk.CTkLabel(
            self,
            text="Contrasena:" + ("" if edit_mode else " (obligatoria)"),
            font=theme.scaled_font(14),
        ).pack(pady=(10, 5))

        self._password_entry = ctk.CTkEntry(
            self, width=250, height=36, show="*"
        )
        self._password_entry.pack(padx=20, pady=5)

        ctk.CTkLabel(
            self, text="Rol:", font=theme.scaled_font(14)
        ).pack(pady=(10, 5))

        self._role_var = ctk.StringVar(value="cajero")
        self._role_menu = ctk.CTkOptionMenu(
            self,
            values=["gerente", "cajero", "inventario"],
            variable=self._role_var,
            width=250,
        )
        self._role_menu.pack(padx=20, pady=5)

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="red", font=theme.scaled_font(12)
        )
        self._error_label.pack()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 20))
        ctk.CTkButton(
            btn_frame, text="Cancelar", width=100, fg_color="gray",
            command=self._cancel,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame, text="Guardar", width=100, command=self._confirm,
        ).pack(side="left", padx=5)

        self.geometry("350x420")
        self._center_on_master(master)
        if not edit_mode:
            self._username_entry.focus_set()
        else:
            self._password_entry.focus_set()

        contrast = theme.get_contrast_map()
        self.configure(fg_color=contrast.get("panel", "#2b2b2b"))
        theme.apply_theme_to_widget(self, contrast)

    @property
    def result(self) -> dict[str, Any] | None:
        return self._result

    def _confirm(self) -> None:
        username = self._username_entry.get().strip()
        password = self._password_entry.get().strip()
        role = self._role_var.get()

        if not self._edit_mode:
            if not username or not password:
                self._error_label.configure(text="Complete todos los campos")
                return
            self._result = {"username": username, "password": password, "role": role}
        else:
            if not password:
                self._result = {"role": role}
            else:
                self._result = {"password": password, "role": role}
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()

    def _center_on_master(self, master) -> None:
        self.update_idletasks()
        mw, mh = master.winfo_width(), master.winfo_height()
        mx, my = master.winfo_rootx(), master.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        self.geometry(f"+{x}+{y}")