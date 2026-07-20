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
