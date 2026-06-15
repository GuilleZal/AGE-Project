"""Column width persistence — save and restore treeview column widths.

Stores column widths in a JSON file so they persist between sessions.
"""

import json
import os
from pathlib import Path
from typing import Any


# Path to store column widths configuration
_CONFIG_DIR = Path(__file__).parent.parent / "data"
_CONFIG_FILE = _CONFIG_DIR / "column_widths.json"


def load_column_widths(view_name: str) -> dict[str, int] | None:
    """Load saved column widths for a specific view.
    
    Args:
        view_name: Identifier for the view (e.g., "product_view", "cash_register_movements")
    
    Returns:
        Dict mapping column names to widths, or None if no saved config exists.
    """
    if not _CONFIG_FILE.exists():
        return None
    
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(view_name)
    except (json.JSONDecodeError, OSError):
        return None


def save_column_widths(view_name: str, widths: dict[str, int]) -> None:
    """Save column widths for a specific view.
    
    Args:
        view_name: Identifier for the view
        widths: Dict mapping column names to widths
    """
    # Ensure config directory exists
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing config
    data = {}
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}
    
    # Update with new widths
    data[view_name] = widths
    
    # Save back
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # Silently fail if we can't write


def get_treeview_widths(tree: Any) -> dict[str, int]:
    """Extract current column widths from a treeview.
    
    Args:
        tree: ttk.Treeview instance
    
    Returns:
        Dict mapping column names to widths
    """
    widths = {}
    for col in tree["columns"]:
        widths[col] = tree.column(col, "width")
    return widths


def apply_treeview_widths(tree: Any, widths: dict[str, int] | None) -> None:
    """Apply saved column widths to a treeview.
    
    Args:
        tree: ttk.Treeview instance
        widths: Dict mapping column names to widths, or None
    """
    if widths is None:
        return
    
    for col, width in widths.items():
        try:
            tree.column(col, width=width)
        except (KeyError, ValueError):
            pass  # Column doesn't exist or invalid width
