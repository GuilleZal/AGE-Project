"""Tests for ReturnView quantity input and validation."""

import pytest
import tkinter as tk
import customtkinter as ctk
from pos.view.return_view import ReturnView


def test_return_view_quantity_validation(session_root):
    view = ReturnView(session_root)
    session_root.update()

    # Case 1: Unit product
    view.show_product({
        "id": 1,
        "name": "Coca-Cola 1.5L",
        "sale_price": 150,
        "unit_type": "Unidad"
    })
    session_root.update()

    # Enter a float value "1.5"
    view._qty_var.set("1.5")
    view._update_refund()
    session_root.update()

    # Should filter non-digits and set to "15"
    assert view._qty_var.get() == "15"
    assert view._summary_qty_lbl.cget("text") == "15 u."

    # Case 2: Weight product
    view.show_product({
        "id": 2,
        "name": "Queso Cremoso",
        "sale_price": 950,
        "unit_type": "Kg"
    })
    session_root.update()

    # Enter a float value "1.5"
    view._qty_var.set("1.5")
    view._update_refund()
    session_root.update()

    # Should allow float
    assert view._qty_var.get() == "1.5"
    assert view._summary_qty_lbl.cget("text") == "1.5 Kg"

    view.destroy()


def test_return_view_reactive_quantity_trace(session_root):
    """Verify that writing to _qty_var automatically updates the UI via StringVar trace."""
    view = ReturnView(session_root)
    session_root.update()

    # Show a unit product
    view.show_product({
        "id": 1,
        "name": "Sprite 2.25L",
        "sale_price": 200,
        "unit_type": "Unidad"
    })
    session_root.update()

    # Initial state should be 1 u.
    assert view._qty_var.get() == "1"
    assert view._summary_qty_lbl.cget("text") == "1 u."
    assert view._refund_label.cget("text") == "$200"

    # Set value programmatically, which simulates user typing.
    # The trace should run automatically without calling _update_refund.
    view._qty_var.set("5")
    session_root.update()

    assert view._qty_var.get() == "5"
    assert view._summary_qty_lbl.cget("text") == "5 u."
    assert view._refund_label.cget("text") == "$1,000"

    view.destroy()

