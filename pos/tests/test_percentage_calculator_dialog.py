"""Tests for PercentageCalculatorDialog."""

import pytest
from pos.view.widgets.percentage_calculator_dialog import PercentageCalculatorDialog


def test_percentage_calculator_dialog_calculation(session_root):
    dialog = PercentageCalculatorDialog(session_root)
    session_root.update()

    # Enter amount and percentage
    dialog._amount_entry.delete(0, "end")
    dialog._amount_entry.insert(0, "1000")
    dialog._pct_entry.delete(0, "end")
    dialog._pct_entry.insert(0, "25")

    # Trigger update
    dialog._update_preview()
    session_root.update()

    # Assert preview text contains expected values (1000 / 0.75 = 1333.33)
    preview_text = dialog._preview_label.cget("text")
    assert "Ganancia: $333.33" in preview_text
    assert "Total con ganancia: $1,333.33" in preview_text
    assert dialog._error_label.cget("text") == ""

    # Test invalid percentage (>= 100)
    dialog._pct_entry.delete(0, "end")
    dialog._pct_entry.insert(0, "100")
    dialog._update_preview()
    session_root.update()
    assert dialog._preview_label.cget("text") == ""
    assert "El porcentaje debe ser menor a 100%" in dialog._error_label.cget("text")

    # Test negative percentage
    dialog._pct_entry.delete(0, "end")
    dialog._pct_entry.insert(0, "-5")
    dialog._update_preview()
    session_root.update()
    assert dialog._preview_label.cget("text") == ""
    assert "El porcentaje no puede ser negativo" in dialog._error_label.cget("text")

    dialog.destroy()
