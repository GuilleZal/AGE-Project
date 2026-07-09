"""Login view — username/password form with error display."""

import tkinter as tk
import customtkinter as ctk
from pos.view import theme


class LoginView(ctk.CTkToplevel):
    """Standalone login window displayed before MainWindow.

    Layout (centered, 400x300):
        ┌─────────────────────────────┐
        │     Sistema POS              │
        │                              │
        │  Usuario: [___________]      │
        │  Contrasena: [___________]   │
        │  (error label, hidden)       │
        │                              │
        │  [  Iniciar sesion  ]        │
        │                              │
        └─────────────────────────────┘

    Events:
        - "Iniciar sesion" button click → calls controller
        - Enter key in either field → calls controller
        - controller is set via set_controller(login_controller)
    """

    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 380

    def __init__(self, master=None) -> None:
        super().__init__(master)
        self.title("Sistema POS - Login")
        self.resizable(False, False)
        self.minsize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self._controller = None
        self._success_callback = None

        self._center_on_screen()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- Title ---
        self._title_label = ctk.CTkLabel(
            self,
            text="Sistema POS",
            font=theme.scaled_font(22, weight="bold"),
        )
        self._title_label.pack(pady=(30, 20))

        # --- Username field ---
        self._username_label = ctk.CTkLabel(
            self,
            text="Usuario:",
            font=theme.scaled_font(14),
        )
        self._username_label.pack(pady=(0, 5))

        self._username_entry = ctk.CTkEntry(
            self,
            height=36,
            placeholder_text="Ingrese su usuario",
            font=theme.scaled_font(13),
        )
        self._username_entry.pack(fill="x", padx=40, pady=(0, 15))
        self._username_entry.bind("<Return>", lambda _e: self._on_submit())
        self._username_entry.focus_set()

        # --- Password field ---
        self._password_label = ctk.CTkLabel(
            self,
            text="Contrasena:",
            font=theme.scaled_font(14),
        )
        self._password_label.pack(pady=(0, 5))

        self._password_entry = ctk.CTkEntry(
            self,
            height=36,
            placeholder_text="Ingrese su contrasena",
            show="*",
            font=theme.scaled_font(13),
        )
        self._password_entry.pack(fill="x", padx=40, pady=(0, 10))
        self._password_entry.bind("<Return>", lambda _e: self._on_submit())

        # --- Error label (hidden by default) ---
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#e74c3c",
            font=theme.scaled_font(12, weight="bold"),
        )
        self._error_label.pack(pady=(0, 10))

        # --- Submit button ---
        self._submit_btn = ctk.CTkButton(
            self,
            text="Iniciar sesion",
            height=40,
            font=theme.scaled_font(14, weight="bold"),
            command=self._on_submit,
        )
        self._submit_btn.pack(fill="x", padx=40, pady=(0, 15))

        # Apply theme
        contrast = theme.get_contrast_map()
        self.configure(fg_color=contrast.get("panel", "#2b2b2b"))
        theme.apply_theme_to_widget(self, contrast)
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def set_controller(self, controller) -> None:
        """Store reference to LoginController."""
        self._controller = controller

    def set_success_callback(self, callback) -> None:
        """Store callback to invoke on successful login."""
        self._success_callback = callback

    def show_error(self, message: str) -> None:
        """Display error label with message, focus username field."""
        self._error_label.configure(text=message)
        # Force update to ensure the error is visible
        self.update_idletasks()
        self._username_entry.focus_set()

    def get_username(self) -> str:
        """Return stripped username from entry."""
        return self._username_entry.get().strip()

    def get_password(self) -> str:
        """Return password from entry."""
        return self._password_entry.get()

    def _on_submit(self) -> None:
        """Called on button click or Enter key. Delegates to controller."""
        if self._controller is None:
            return
        username = self.get_username()
        password = self.get_password()

        input_result = self._controller.validate_input(username, password)
        if not input_result["success"]:
            self.show_error(input_result["error"])
            return

        result = self._controller.validate(username, password)
        if result["success"]:
            self._error_label.configure(text="")
            if self._success_callback:
                # Pass user and permissions to callback
                self._success_callback(result["data"]["user"], result["data"]["permissions"])
            # Destroy the window to signal completion
            self.grab_release()
            self.destroy()
        else:
            self.show_error(result["error"])

    def _on_close(self) -> None:
        """Handle window close button - destroy the window."""
        self.grab_release()
        self.destroy()

    def _center_on_screen(self) -> None:
        """Center the login window on the screen."""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.WINDOW_WIDTH) // 2
        y = (screen_height - self.WINDOW_HEIGHT) // 2
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")