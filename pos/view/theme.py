"""Central font scaling module for the POS application."""
import customtkinter as ctk
from pos.repository.settings_repo import SettingsRepo

SCALE_LEVELS = [0, 2, 4, 6]
SETTING_KEY = "font_scale_level"
_current_level: int = 0
_on_change_callback = None

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

def load_font_scale(db) -> None:
    global _current_level
    repo = SettingsRepo(db)
    val = repo.get(SETTING_KEY)
    if val is not None:
        try:
            lvl = int(val)
            if 0 <= lvl < len(SCALE_LEVELS):
                _current_level = lvl
        except (ValueError, TypeError):
            pass
