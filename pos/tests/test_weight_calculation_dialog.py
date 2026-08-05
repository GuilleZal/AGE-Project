"""Tests for WeightCalculationDialog and barcode-less product handling."""

import sqlite3
import pytest
from pos.model.product import Product
from pos.controller.sale_controller import SaleController
from pos.view.widgets.weight_calculation_dialog import WeightCalculationDialog
from pos.view.widgets.product_search_dialog import ProductSearchDialog


def test_weight_calculation_dialog_initialization(session_root):
    dialog = WeightCalculationDialog(
        session_root,
        product_name="Pan frances",
        sale_price=2100,
        initial_weight=0.5,
    )
    session_root.update()

    assert dialog._peso_entry.get() == "0.5"
    assert dialog._monto_entry.get() == "$1,050"
    assert "Pan frances" in dialog._title_label.cget("text")
    assert "$2,100 / Kg" in dialog._price_label.cget("text")
    dialog.destroy()


def test_weight_calculation_dialog_peso_to_monto(session_root):
    dialog = WeightCalculationDialog(
        session_root,
        product_name="Queso Tybo",
        sale_price=4000,
        initial_weight=0.0,
    )
    session_root.update()

    dialog._peso_entry.delete(0, "end")
    dialog._peso_entry.insert(0, "0.75")
    dialog._on_peso_changed()
    session_root.update()

    assert dialog._monto_entry.get() == "$3,000"

    # Confirm
    dialog._confirm()
    assert dialog.result == 0.75


def test_weight_calculation_dialog_monto_to_peso(session_root):
    dialog = WeightCalculationDialog(
        session_root,
        product_name="Carne Picada",
        sale_price=5000,
        initial_weight=0.0,
    )
    session_root.update()

    dialog._monto_entry.delete(0, "end")
    dialog._monto_entry.insert(0, "$2500")
    dialog._on_monto_changed()
    session_root.update()

    assert dialog._peso_entry.get() == "0.5"

    dialog._confirm()
    assert dialog.result == 0.5


def test_weight_calculation_dialog_validation_and_cancel(session_root):
    dialog = WeightCalculationDialog(
        session_root,
        product_name="Pan frances",
        sale_price=2100,
        initial_weight=0.0,
    )
    session_root.update()

    # Invalid zero weight
    dialog._peso_entry.delete(0, "end")
    dialog._peso_entry.insert(0, "0")
    dialog._confirm()
    assert dialog.result is None
    assert "mayor a 0" in dialog._error_label.cget("text")

    # Cancel
    dialog._cancel()
    assert dialog.result is None


def test_sale_controller_add_by_product_id(db: sqlite3.Connection):
    controller = SaleController(db)

    # Insert a product without barcode
    p = Product(
        barcode=None,
        name="Pan Frances Kg",
        sale_price=2100,
        cost_price=1000,
        stock=50.0,
    )
    created = controller._product_repo.create(p)

    result = controller.add_by_product_id(created.id, quantity=0.5)
    assert result["success"] is True
    assert result["data"]["product_id"] == created.id
    assert result["data"]["quantity"] == 0.5
    assert result["data"]["subtotal"] == 1050

    cart = controller.get_cart()["data"]
    assert len(cart["items"]) == 1
    assert cart["total"] == 1050


def test_product_search_dialog_barcodeless_product_opens_calc(session_root, monkeypatch):
    p_barcodeless = Product(
        id=10,
        barcode=None,
        name="Pan Frances",
        sale_price=2100,
        cost_price=1000,
        stock=100.0,
        unit_type="Kg",
    )


    # Mock WeightCalculationDialog to simulate user confirming 0.75 Kg
    class MockCalcDialog:
        def __init__(self, master, product_name, sale_price, *args, **kwargs):
            self.result = 0.75

    monkeypatch.setattr(
        "pos.view.widgets.weight_calculation_dialog.WeightCalculationDialog",
        MockCalcDialog,
    )
    monkeypatch.setattr("pos.view.widgets.product_search_dialog.CenteredDialog.wait_window", lambda self, win: None)

    dialog = ProductSearchDialog(session_root, products=[p_barcodeless])

    # Select the first item in the treeview
    items = dialog._tree.get_children()
    assert len(items) == 1
    dialog._tree.selection_set(items[0])

    dialog._on_select()

    assert dialog.result == p_barcodeless
    assert dialog.selected_quantity == 0.75


def test_product_search_dialog_barcodeless_unit_product_does_not_open_calc(session_root, monkeypatch):
    p_unit = Product(
        id=11,
        barcode=None,
        name="Alfajor sin barra",
        sale_price=800,
        cost_price=400,
        stock=10.0,
        unit_type="Unidad",
    )

    called_calc = False
    class MockCalcDialog:
        def __init__(self, *args, **kwargs):
            nonlocal called_calc
            called_calc = True
            self.result = 1.0

    monkeypatch.setattr(
        "pos.view.widgets.weight_calculation_dialog.WeightCalculationDialog",
        MockCalcDialog,
    )
    monkeypatch.setattr("pos.view.widgets.product_search_dialog.CenteredDialog.wait_window", lambda self, win: None)

    dialog = ProductSearchDialog(session_root, products=[p_unit])

    items = dialog._tree.get_children()
    assert len(items) == 1
    dialog._tree.selection_set(items[0])

    dialog._on_select()

    assert called_calc is False
    assert dialog.result == p_unit
    assert dialog.selected_quantity == 1.0


def test_weight_calculation_dialog_cajero_initialization(session_root):
    dialog = WeightCalculationDialog(
        session_root,
        product_name="Queso Cremoso",
        sale_price=9500,
        initial_weight=0.5,
        role="cajero"
    )
    session_root.update()

    # Verify fields are empty
    assert dialog._peso_entry.get() == ""
    assert dialog._monto_entry.get() == ""

    # Verify height is at least 340
    assert dialog._height >= 340

    dialog.destroy()
