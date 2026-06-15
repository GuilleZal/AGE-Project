"""Treeview column sorting — add clickable headers with sort indicators.

Provides functionality to sort treeview columns by clicking on headers.
Cycles through three states: ascending (▼), descending (▲), and no sort.
Supports both numeric and alphabetic sorting.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any


# Sort state constants
SORT_NONE = 0
SORT_ASC = 1
SORT_DESC = 2

# Sort indicator symbols
INDICATOR_ASC = " ▼"   # Flecha hacia abajo (ascendente)
INDICATOR_DESC = " ▲"  # Flecha hacia arriba (descendente)


def add_sorting_to_treeview(tree: Any, columns: list[str], column_types: dict[str, str] | None = None) -> None:
    """Add sorting functionality to a treeview's columns.
    
    Args:
        tree: ttk.Treeview instance
        columns: List of column identifiers to make sortable
        column_types: Dict mapping column names to types ('int', 'float', 'str')
                     If not provided, auto-detects from data
    """
    # Store sort state for each column
    tree._sort_states = {col: SORT_NONE for col in columns}
    tree._sort_column_types = column_types or {}
    tree._original_headings = {}
    
    # Store original headings
    for col in columns:
        tree._original_headings[col] = tree.heading(col, "text")
    
    # Bind click events to each column header
    for col in columns:
        tree.heading(col, command=lambda c=col: _sort_column(tree, c, columns))


def _sort_column(tree: Any, col: str, all_columns: list[str]) -> None:
    """Handle sorting when a column header is clicked.
    
    Cycles through: no sort -> ascending -> descending -> no sort
    """
    # Get current sort state
    current_state = tree._sort_states.get(col, SORT_NONE)
    
    # Cycle to next state
    if current_state == SORT_NONE:
        new_state = SORT_ASC
    elif current_state == SORT_ASC:
        new_state = SORT_DESC
    else:  # SORT_DESC
        new_state = SORT_NONE
    
    # Update sort states (reset all others to NONE)
    for c in all_columns:
        tree._sort_states[c] = SORT_NONE
    tree._sort_states[col] = new_state
    
    # Update all headings to remove indicators
    for c in all_columns:
        tree.heading(c, text=tree._original_headings[c])
    
    # Add indicator to current column if sorting
    if new_state == SORT_ASC:
        tree.heading(col, text=tree._original_headings[col] + INDICATOR_ASC)
    elif new_state == SORT_DESC:
        tree.heading(col, text=tree._original_headings[col] + INDICATOR_DESC)
    
    # Get all items
    items = [(tree.set(k, col), k) for k in tree.get_children("")]
    
    # Sort or restore original order
    if new_state == SORT_NONE:
        # Restore original order (by item ID)
        items.sort(key=lambda t: t[1])
    else:
        # Determine column type
        col_type = tree._sort_column_types.get(col, "auto")
        
        if col_type == "auto":
            # Auto-detect: try numeric first, fall back to string
            col_type = _detect_column_type(items)
        
        # Sort based on type
        if col_type in ("int", "float"):
            # Numeric sorting
            items.sort(key=lambda t: _parse_numeric(t[0]), reverse=(new_state == SORT_DESC))
        else:
            # String sorting (case-insensitive)
            items.sort(key=lambda t: t[0].lower(), reverse=(new_state == SORT_DESC))
    
    # Rearrange items in the treeview
    for index, (val, kid) in enumerate(items):
        tree.move(kid, "", index)


def _detect_column_type(items: list[tuple[str, str]]) -> str:
    """Auto-detect column type from data.
    
    Args:
        items: List of (value, item_id) tuples
    
    Returns:
        'int', 'float', or 'str'
    """
    for val, _ in items[:10]:  # Check first 10 items
        # Try to parse as number
        cleaned = _clean_value(val)
        if cleaned:
            try:
                int(cleaned)
                return "int"
            except ValueError:
                try:
                    float(cleaned)
                    return "float"
                except ValueError:
                    pass
    
    return "str"


def _clean_value(val: str) -> str:
    """Clean a value string for numeric parsing.
    
    Removes currency symbols, commas, and whitespace.
    """
    # Remove common currency symbols and formatting
    cleaned = val.replace("$", "").replace(",", "").replace(" ", "").strip()
    # Remove percentage sign
    cleaned = cleaned.replace("%", "")
    # Remove warning symbols
    cleaned = cleaned.replace("⚠", "").strip()
    return cleaned


def _parse_numeric(val: str) -> float:
    """Parse a string value as a number.
    
    Handles currency symbols, commas, and other formatting.
    Returns 0.0 if parsing fails.
    """
    cleaned = _clean_value(val)
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
