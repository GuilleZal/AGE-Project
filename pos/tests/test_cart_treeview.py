"""Tests for CartTreeview widget."""

import tkinter as tk
import customtkinter as ctk
import pytest
from pos.view.widgets.cart_treeview import CartTreeview


def test_cart_treeview_responsive_resize(session_root):
    cart = CartTreeview(session_root)
    cart.pack(fill="both", expand=True)
    session_root.update()

    # Simulate a resize event (Configure event) with width 600
    event = tk.Event()
    event.width = 600
    cart._on_resize(event)

    # Net width is 600 - 20 = 580
    # producto (48%) -> 278
    # cantidad (14%) -> 81
    # precio_unit (17%) -> 98
    # subtotal (21%) -> 121
    assert cart._tree.column("producto", "width") == int(580 * 0.48)
    assert cart._tree.column("cantidad", "width") == int(580 * 0.14)
    assert cart._tree.column("precio_unit", "width") == int(580 * 0.17)
    assert cart._tree.column("subtotal", "width") == int(580 * 0.21)


def test_cart_treeview_quantity_formatting_cajero(session_root):
    cart = CartTreeview(session_root, role="cajero")
    cart.pack(fill="both", expand=True)
    session_root.update()

    # Create dummy cart items
    items = [
        {
            "product_id": 1,
            "name": "Queso Cremoso x Kg",
            "quantity": 1.5,
            "unit_price": 9500,
            "subtotal": 14250,
            "unit_type": "Kg",
        },
        {
            "product_id": 2,
            "name": "Coca Cola 1.5L",
            "quantity": 2.0,
            "unit_price": 1500,
            "subtotal": 3000,
            "unit_type": "Unidad",
        }
    ]

    cart.update_cart(items)
    session_root.update()

    # Verify formatting in the treeview values
    children = cart._tree.get_children()
    assert len(children) == 2

    # Item 1: Queso Cremoso (index 0)
    vals1 = cart._tree.item(children[0], "values")
    assert vals1[0] == "Queso Cremoso x Kg"
    assert vals1[1] == "1.5 Kg"

    # Item 2: Coca Cola (index 1)
    vals2 = cart._tree.item(children[1], "values")
    assert vals2[0] == "Coca Cola 1.5L"
    assert vals2[1] == "2 u."

    # Test get_selected_item safe parsing
    # Select first item
    cart._tree.selection_set(children[0])
    selected1 = cart.get_selected_item()
    assert selected1 is not None
    assert selected1["product_id"] == 1
    assert selected1["quantity"] == 1.5

    # Select second item
    cart._tree.selection_set(children[1])
    selected2 = cart.get_selected_item()
    assert selected2 is not None
    assert selected2["product_id"] == 2
    assert selected2["quantity"] == 2.0


def test_cart_treeview_quantity_formatting_default(session_root):
    cart = CartTreeview(session_root, role="admin")
    cart.pack(fill="both", expand=True)
    session_root.update()

    items = [
        {
            "product_id": 1,
            "name": "Queso Cremoso x Kg",
            "quantity": 1.5,
            "unit_price": 9500,
            "subtotal": 14250,
            "unit_type": "Kg",
        }
    ]

    cart.update_cart(items)
    session_root.update()

    children = cart._tree.get_children()
    vals = cart._tree.item(children[0], "values")
    # For default roles it should convert quantity to int (original behavior)
    assert int(vals[1]) == 1

    cart._tree.selection_set(children[0])
    selected = cart.get_selected_item()
    assert selected is not None
    assert selected["quantity"] == 1.0
