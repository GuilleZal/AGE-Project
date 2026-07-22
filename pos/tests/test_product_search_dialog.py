"""Tests for ProductSearchDialog search filtering."""

import tkinter as tk
import customtkinter as ctk
import pytest
from pos.model.product import Product
from pos.view.widgets.product_search_dialog import ProductSearchDialog


def test_product_search_dialog_filtering(session_root):
    # Setup dummy data
    p1 = Product(
        id=1,
        barcode="111",
        name="Coca-Cola 1.5L",
        category_id=1,
        sale_price=150,
        cost_price=100,
        stock=10.0,
        description="",
        low_stock_threshold=5,
        is_active=True,
        created_at="2026-07-17T00:00:00",
        updated_at="2026-07-17T00:00:00",
    )
    p2 = Product(
        id=2,
        barcode="222",
        name="Pepsi 1.5L",
        category_id=1,
        sale_price=140,
        cost_price=90,
        stock=12.0,
        description="",
        low_stock_threshold=5,
        is_active=True,
        created_at="2026-07-17T00:00:00",
        updated_at="2026-07-17T00:00:00",
    )
    p3 = Product(
        id=3,
        barcode="333",
        name="Jabón Sussex",
        category_id=2,
        sale_price=80,
        cost_price=50,
        stock=15.0,
        description="",
        low_stock_threshold=5,
        is_active=True,
        created_at="2026-07-17T00:00:00",
        updated_at="2026-07-17T00:00:00",
    )

    categories = [
        {"id": 1, "name": "Bebidas"},
        {"id": 2, "name": "Limpieza"},
    ]

    dialog = ProductSearchDialog(session_root, products=[p1, p2, p3], categories=categories)

    # Initial state - all 3 products populated
    assert len(dialog._tree.get_children()) == 3

    # Type "pepsi" in search entry
    dialog._search_entry.delete(0, "end")
    dialog._search_entry.insert(0, "pepsi")
    dialog._on_search_changed()
    session_root.update()

    # Should filter to 1 item (Pepsi 1.5L)
    children = dialog._tree.get_children()
    assert len(children) == 1
    assert dialog._tree.item(children[0], "values")[1] == "Pepsi 1.5L"

    # Type "Bebidas" in search entry to search by category
    dialog._search_entry.delete(0, "end")
    dialog._search_entry.insert(0, "Bebidas")
    dialog._on_search_changed()
    session_root.update()

    # Should filter to 2 items (Coca-Cola and Pepsi)
    assert len(dialog._tree.get_children()) == 2

    dialog.destroy()


def test_product_search_dialog_cajero_category_filtering(session_root):
    # Setup dummy data
    p1 = Product(
        id=1,
        barcode="111",
        name="Coca-Cola 1.5L",
        category_id=1,
        sale_price=150,
        cost_price=100,
        stock=10.0,
    )
    p2 = Product(
        id=2,
        barcode="222",
        name="Pepsi 1.5L",
        category_id=1,
        sale_price=140,
        cost_price=90,
        stock=12.0,
    )
    p3 = Product(
        id=3,
        barcode="333",
        name="Jabón Sussex",
        category_id=2,
        sale_price=80,
        cost_price=50,
        stock=15.0,
    )

    categories = [
        {"id": 1, "name": "Bebidas"},
        {"id": 2, "name": "Limpieza"},
    ]

    dialog = ProductSearchDialog(session_root, products=[p1, p2, p3], categories=categories, role="cajero")
    session_root.update()

    # Verify dialog width and category variable/menu exists
    assert dialog._width == 750
    assert hasattr(dialog, "_category_menu")
    assert dialog._category_var.get() == "Todas"

    # Initial state - all 3 products populated
    assert len(dialog._tree.get_children()) == 3

    # Select "Bebidas" from category menu
    dialog._category_var.set("Bebidas")
    dialog._on_category_changed("Bebidas")
    session_root.update()

    # Should filter to 2 items (Coca-Cola and Pepsi)
    assert len(dialog._tree.get_children()) == 2

    # Type "Pepsi" in search entry while category is "Bebidas"
    dialog._search_entry.delete(0, "end")
    dialog._search_entry.insert(0, "Pepsi")
    dialog._on_search_changed()
    session_root.update()

    # Should filter to 1 item (Pepsi 1.5L)
    children = dialog._tree.get_children()
    assert len(children) == 1
    assert dialog._tree.item(children[0], "values")[1] == "Pepsi 1.5L"

    # Type "Sussex" in search entry while category is "Bebidas"
    dialog._search_entry.delete(0, "end")
    dialog._search_entry.insert(0, "Sussex")
    dialog._on_search_changed()
    session_root.update()

    # Should filter to 0 items (Sussex is in Limpieza, not Bebidas)
    assert len(dialog._tree.get_children()) == 0

    dialog.destroy()


def test_product_search_dialog_return_mode_skips_weight_dialog(session_root):
    # Setup dummy data
    p_barcodeless = Product(
        id=1,
        barcode=None,
        name="Queso Cremoso",
        category_id=1,
        sale_price=950,
        cost_price=700,
        stock=100.0,
        unit_type="Kg",
    )

    dialog = ProductSearchDialog(session_root, products=[p_barcodeless], is_return=True)
    session_root.update()

    items = dialog._tree.get_children()
    assert len(items) == 1
    dialog._tree.selection_set(items[0])

    # In returns mode, selecting a barcodeless product should bypass the weight dialog
    # and return the product with 1.0 quantity immediately.
    dialog._on_select()

    assert dialog.result == p_barcodeless
    assert dialog.selected_quantity == 1.0

    dialog.destroy()
