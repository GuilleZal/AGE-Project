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


def test_return_quantity_dialog(session_root):
    from pos.view.return_view import ReturnQuantityDialog
    
    # Test case 1: Unit product (should only allow integers)
    dialog_unit = ReturnQuantityDialog(session_root, "Coca-Cola", is_kg=False, current_qty="1")
    session_root.update()
    
    # Enter an invalid non-numeric string
    dialog_unit._qty_entry.delete(0, tk.END)
    dialog_unit._qty_entry.insert(0, "abc")
    dialog_unit._confirm()
    assert dialog_unit.result is None
    assert dialog_unit._error_label.cget("text") == "Ingrese una cantidad válida"
    
    # Enter a float for unit product
    dialog_unit._qty_entry.delete(0, tk.END)
    dialog_unit._qty_entry.insert(0, "2.5")
    dialog_unit._confirm()
    assert dialog_unit.result is None
    assert dialog_unit._error_label.cget("text") == "Ingrese un número entero"
    
    # Enter a valid integer
    dialog_unit._qty_entry.delete(0, tk.END)
    dialog_unit._qty_entry.insert(0, "3")
    dialog_unit._confirm()
    assert dialog_unit.result == 3.0
    
    # Test case 2: Weight product (should allow float)
    dialog_weight = ReturnQuantityDialog(session_root, "Queso Cremoso", is_kg=True, current_qty="1")
    session_root.update()
    
    # Enter a float
    dialog_weight._qty_entry.delete(0, tk.END)
    dialog_weight._qty_entry.insert(0, "1.75")
    dialog_weight._confirm()
    assert dialog_weight.result == 1.75


def test_return_view_no_barcode(session_root):
    """Verify that when a product has no barcode (None, empty, or 'None'), the Código label shows '—'."""
    view = ReturnView(session_root)
    session_root.update()

    # Case 1: missing barcode
    view.show_product({
        "id": 1,
        "name": "Pan Frances Kg",
        "sale_price": 2100,
        "unit_type": "Kg"
    })
    session_root.update()
    assert view._barcode_val_lbl.cget("text") == "—"

    # Case 2: None barcode
    view.show_product({
        "id": 1,
        "name": "Pan Frances Kg",
        "barcode": None,
        "sale_price": 2100,
        "unit_type": "Kg"
    })
    session_root.update()
    assert view._barcode_val_lbl.cget("text") == "—"

    # Case 3: 'None' string barcode
    view.show_product({
        "id": 1,
        "name": "Pan Frances Kg",
        "barcode": "None",
        "sale_price": 2100,
        "unit_type": "Kg"
    })
    session_root.update()
    assert view._barcode_val_lbl.cget("text") == "—"

    # Case 4: actual barcode
    view.show_product({
        "id": 1,
        "name": "Pan Frances Kg",
        "barcode": "123456",
        "sale_price": 2100,
        "unit_type": "Kg"
    })
    session_root.update()
    assert view._barcode_val_lbl.cget("text") == "123456"

    view.destroy()


def test_return_view_clears_error_on_show_product(session_root):
    """Verify that showing a product automatically clears any previous error message."""
    view = ReturnView(session_root)
    session_root.update()

    # Simulate an error
    view.show_error("Producto no encontrado")
    assert view._error_label.cget("text") == "Producto no encontrado"

    # Show a product (this should clear the error)
    view.show_product({
        "id": 1,
        "name": "Coca-Cola 1.5L",
        "sale_price": 150,
        "unit_type": "Unidad"
    })
    session_root.update()

    # Error must be empty now
    assert view._error_label.cget("text") == ""

    view.destroy()

