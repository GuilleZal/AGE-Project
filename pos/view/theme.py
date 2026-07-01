"""Central font scaling module for the POS application."""
import customtkinter as ctk
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
