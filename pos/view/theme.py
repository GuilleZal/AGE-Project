"""Central font scaling module for the POS application."""
import customtkinter as ctk
from tkinter import ttk
from pos.repository.settings_repo import SettingsRepo

SCALE_LEVELS = [0, 2, 4, 6]
SETTING_KEY = "font_scale_level"
BG_COLOR_KEY = "bg_color"
_current_level: int = 0
_current_bg_color: str = "#2b2b2b"  # Default dark gray
_on_change_callback = None

# Background color presets
BG_COLORS = {
    "Azul": "#1e3a5f",
    "Gris": "#4a4a4a",
    "Crema": "#f5f5dc",
    "Marrón": "#8b6914",
}

# Contrast mapping: defines text and panel colors for each background
CONTRAST_MAP = {
    "#2b2b2b": {  # Default dark gray
        "text": "#F5F5F5",
        "panel": "#222222",
        "treeview_bg": "#222222",
        "treeview_fg": "#F5F5F5",
        "treeview_header": "#1a1a1a",
        "entry_bg": "#1e1e1e",
        "entry_border": "#3a3a3a",
        "search_bg": "#1a1a1a",
        "search_border": "#4a4a4a",
    },
    "#1e3a5f": {  # Azul (dark)
        "text": "#F5F5F5",
        "panel": "#162d4a",  # Darker variant for depth
        "treeview_bg": "#162d4a",
        "treeview_fg": "#F5F5F5",
        "treeview_header": "#0f1f33",
        "entry_bg": "#0f2238",
        "entry_border": "#1e3a5f",
        "search_bg": "#0a1a2e",
        "search_border": "#2a4a70",
    },
    "#4a4a4a": {  # Gris (dark)
        "text": "#F5F5F5",
        "panel": "#3a3a3a",  # Darker variant for depth
        "treeview_bg": "#3a3a3a",
        "treeview_fg": "#F5F5F5",
        "treeview_header": "#2a2a2a",
        "entry_bg": "#2e2e2e",
        "entry_border": "#555555",
        "search_bg": "#252525",
        "search_border": "#606060",
    },
    "#f5f5dc": {  # Crema (light)
        "text": "#111111",
        "panel": "#e8e8d0",  # Slightly darker variant
        "treeview_bg": "#ffffff",  # Pure white for contrast
        "treeview_fg": "#111111",
        "treeview_header": "#d0d0b8",
        "entry_bg": "#dddcc8",
        "entry_border": "#c0bfa8",
        "search_bg": "#d0cfb8",
        "search_border": "#b0af98",
    },
    "#8b6914": {  # Marrón (dark)
        "text": "#F5F5F5",
        "panel": "#6d5210",  # Darker variant for depth
        "treeview_bg": "#6d5210",
        "treeview_fg": "#F5F5F5",
        "treeview_header": "#4f3b0c",
        "entry_bg": "#5a440d",
        "entry_border": "#8b6914",
        "search_bg": "#4a380a",
        "search_border": "#9a7920",
    },
}

def get_offset() -> int:
    return SCALE_LEVELS[_current_level]

def scaled_font(size: int, weight: str | None = None) -> ctk.CTkFont:
    return ctk.CTkFont(size=size + get_offset(), weight=weight)

def small_font(weight=None): return scaled_font(11, weight)
def body_font(weight=None): return scaled_font(14, weight)
def header_font(weight=None): return scaled_font(16, weight)
def title_font(weight=None): return scaled_font(18, weight)
def display_font(weight=None): return scaled_font(22, weight)

def scaled_treeview_font(weight=None) -> tuple:
    return ("Segoe UI", 10 + get_offset(), weight or "normal")

def get_font_scale_level() -> int:
    return _current_level

def get_bg_color() -> str:
    return _current_bg_color

def get_contrast_map() -> dict:
    """Get the contrast mapping for the current background color."""
    return CONTRAST_MAP.get(_current_bg_color, CONTRAST_MAP["#2b2b2b"])

def set_on_change_callback(callback) -> None:
    """Set callback to invoke when font scale changes (for live refresh)."""
    global _on_change_callback
    _on_change_callback = callback

def set_font_scale_level(level: int, db=None) -> None:
    global _current_level
    if level < 0 or level >= len(SCALE_LEVELS):
        return
    _current_level = level
    if db is not None:
        repo = SettingsRepo(db)
        repo.set(SETTING_KEY, str(level))
    if _on_change_callback:
        _on_change_callback()

def set_bg_color(color_name: str, db=None) -> None:
    """Set background color by preset name."""
    global _current_bg_color
    if color_name in BG_COLORS:
        _current_bg_color = BG_COLORS[color_name]
        if db is not None:
            repo = SettingsRepo(db)
            repo.set(BG_COLOR_KEY, color_name)
        if _on_change_callback:
            _on_change_callback()

def load_font_scale(db) -> None:
    global _current_level, _current_bg_color
    repo = SettingsRepo(db)
    val = repo.get(SETTING_KEY)
    if val is not None:
        try:
            lvl = int(val)
            if 0 <= lvl < len(SCALE_LEVELS):
                _current_level = lvl
        except (ValueError, TypeError):
            pass
    
    bg_val = repo.get(BG_COLOR_KEY)
    if bg_val is not None and bg_val in BG_COLORS:
        _current_bg_color = BG_COLORS[bg_val]

def apply_theme_to_widget(widget, contrast: dict) -> None:
    """Recursively apply theme colors to a widget and all its children.
    
    Args:
        widget: The root widget to start from
        contrast: Dictionary with keys: text, panel, treeview_bg, treeview_fg, treeview_header, entry_bg, entry_border
    """
    # Apply to current widget based on type
    widget_type = type(widget).__name__
    
    if widget_type == "CTkFrame":
        # Check if frame is transparent before applying
        try:
            current_fg = widget.cget("fg_color")
            if current_fg != "transparent":
                widget.configure(fg_color=contrast["panel"])
        except:
            pass
    
    elif widget_type in ("CTkLabel", "CTkRadioButton"):
        try:
            widget.configure(text_color=contrast["text"])
        except:
            pass
    
    elif isinstance(widget, ctk.CTkEntry):
        # Use isinstance to cover subclasses like BarcodeEntry
        try:
            widget.configure(
                fg_color=contrast["entry_bg"],
                text_color=contrast["text"],
                border_color=contrast["entry_border"],
            )
        except:
            pass
    
    # CRITICAL: Do NOT modify CTkButton - their colors are functional
    
    # Update ttk.Treeview styles if this is a Treeview widget
    if widget_type == "Treeview":
        try:
            style = ttk.Style(widget)
            style.configure(
                "Treeview",
                background=contrast["treeview_bg"],
                foreground=contrast["treeview_fg"],
                fieldbackground=contrast["treeview_bg"],
            )
            style.configure(
                "Treeview.Heading",
                background=contrast["treeview_header"],
                foreground=contrast["treeview_fg"],
            )
        except:
            pass
    
    # Recursively process children
    try:
        for child in widget.winfo_children():
            apply_theme_to_widget(child, contrast)
    except:
        pass  # Some widgets don't support winfo_children()
