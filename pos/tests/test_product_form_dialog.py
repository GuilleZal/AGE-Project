"""Tests for ProductFormDialog bidirectional calculations."""

import tkinter as tk
import customtkinter as ctk
import pytest
from pos.view.widgets.product_form_dialog import ProductFormDialog


def test_initial_margin_populate(session_root):
    # If cost and sale are present, margin % should be calculated and pre-populated
    product = {
        "cost_price": 100,
        "sale_price": 150,
        "barcode": "123",
        "name": "Test Product",
        "category_id": None,
        "stock": 10.0,
        "low_stock_threshold": 5,
        "description": ""
    }
    dialog = ProductFormDialog(session_root, product=product, categories=[])
    
    assert dialog._cost_price_entry.get() == "100"
    assert dialog._sale_price_entry.get() == "150"
    assert dialog._margin_entry.get() == "50"


def test_change_cost_updates_sale_with_margin(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter margin and cost
    dialog._margin_entry.insert(0, "50")
    dialog._cost_price_entry.insert(0, "200")
    
    # Trigger cost change handler
    dialog._on_cost_changed()
    
    # Cost = 200, Margin = 50% -> Sale = 300
    assert dialog._sale_price_entry.get() == "300"


def test_change_cost_updates_margin_with_sale(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter sale and cost
    dialog._sale_price_entry.insert(0, "150")
    dialog._cost_price_entry.insert(0, "100")
    
    # Trigger cost change handler
    dialog._on_cost_changed()
    
    # Cost = 100, Sale = 150 -> Margin = 50%
    assert dialog._margin_entry.get() == "50"


def test_change_margin_updates_sale_with_cost(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter cost and margin
    dialog._cost_price_entry.insert(0, "100")
    dialog._margin_entry.insert(0, "25")
    
    # Trigger margin change handler
    dialog._on_margin_changed()
    
    # Cost = 100, Margin = 25% -> Sale = 125
    assert dialog._sale_price_entry.get() == "125"


def test_change_margin_updates_cost_with_sale(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter sale and margin
    dialog._sale_price_entry.insert(0, "150")
    dialog._margin_entry.insert(0, "50")
    
    # Trigger margin change handler
    dialog._on_margin_changed()
    
    # Sale = 150, Margin = 50% -> Cost = 100
    assert dialog._cost_price_entry.get() == "100"


def test_change_sale_updates_margin_with_cost(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter cost and sale
    dialog._cost_price_entry.insert(0, "80")
    dialog._sale_price_entry.insert(0, "100")
    
    # Trigger sale change handler
    dialog._on_sale_changed()
    
    # Cost = 80, Sale = 100 -> Margin = 25%
    assert dialog._margin_entry.get() == "25"


def test_change_sale_updates_cost_with_margin(session_root):
    dialog = ProductFormDialog(session_root, product=None, categories=[])
    
    # Enter margin and sale
    dialog._margin_entry.insert(0, "100")
    dialog._sale_price_entry.insert(0, "200")
    
    # Trigger sale change handler
    dialog._on_sale_changed()
    
    # Sale = 200, Margin = 100% -> Cost = 100
    assert dialog._cost_price_entry.get() == "100"
