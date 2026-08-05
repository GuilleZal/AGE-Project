"""Tests for SaleView UI and dialog flows."""

import tkinter as tk
import customtkinter as ctk
import pytest
from pos.view.sale_view import SaleView, SaleErrorDialog


def test_sale_view_initialization(session_root):
    view = SaleView(session_root)
    session_root.update()

    assert view._total == 0
    assert view._selected_payment_method == "cash"
    view.destroy()


def test_sale_error_dialog(session_root):
    dialog = SaleErrorDialog(session_root, "Test error message")
    session_root.update()

    # Verify message is displayed
    label_found = False
    for child in dialog.winfo_children():
        if isinstance(child, ctk.CTkLabel) and child.cget("text") == "Test error message":
            label_found = True
            break
    assert label_found is True

    dialog.destroy()


def test_receipt_preview_quantity_formatting(session_root):
    from pos.view.widgets.receipt_preview import ReceiptPreview

    sale_data = {
        "sale": {
            "id": 123,
            "total": 1500,
            "discount": 0,
            "surcharge": 0,
            "payment_method": "cash",
            "created_at": "2026-07-22 18:00:00"
        },
        "items": [
            {
                "product_id": 1,
                "name": "Sprite 2.25L",
                "quantity": 2.0,
                "unit_price": 500,
                "subtotal": 1000,
                "unit_type": "Unidad"
            },
            {
                "product_id": 2,
                "name": "Queso Cremoso",
                "quantity": 0.5,
                "unit_price": 1000,
                "subtotal": 500,
                "unit_type": "Kg"
            }
        ],
        "change": 0
    }

    dialog = ReceiptPreview(session_root, sale_data)
    session_root.update()

    def get_labels(widget):
        labels = []
        if isinstance(widget, ctk.CTkLabel):
            labels.append(widget)
        try:
            for child in widget.winfo_children():
                labels.extend(get_labels(child))
        except:
            pass
        return labels

    all_labels = get_labels(dialog)
    label_texts = [lbl.cget("text") for lbl in all_labels]

    # Verify unit product shows quantity, unit price, and subtotal
    assert "2 u." in label_texts
    assert "x $500" in label_texts
    assert "$1,000" in label_texts

    # Verify kg product shows quantity, unit price, and subtotal
    assert "0.5 Kg" in label_texts
    assert "x $1,000" in label_texts
    assert "$500" in label_texts

    dialog.destroy()


def test_preferences_persistence(session_root):
    from pos.view import theme
    from pos.repository.settings_repo import SettingsRepo
    from pos.model.database import get_connection

    # Setup database connection
    conn = get_connection()
    repo = SettingsRepo(conn)

    # Change settings using theme functions (with db)
    theme.set_font_scale_level(2, db=conn)
    theme.set_bg_color("Crema", db=conn)
    theme.set_resolution("Estándar", db=conn)

    # Read database directly to check persistence
    assert repo.get("font_scale_level") == "2"
    assert repo.get("bg_color") == "Crema"
    assert repo.get("window_resolution") == "Estándar"

    # Reset theme values in DB to avoid affecting other tests or sessions
    repo.set("font_scale_level", "0")
    repo.set("bg_color", "Gris")
    repo.set("window_resolution", "Moderno")
    conn.commit()
    conn.close()


def test_payment_method_resets_to_cash_after_sale_completion(session_root):
    from pos.view.sale_view import SaleView

    view = SaleView(session_root)
    session_root.update()

    # Mock the controller with necessary methods
    class DummyController:
        def __init__(self):
            self.surcharge_pct = 0.0

        def clear_cart(self):
            self.surcharge_pct = 0.0
            return {"success": True}

        def get_cart(self):
            return {"success": True, "data": {"items": [], "total": 0}}

        def apply_surcharge(self, pct):
            self.surcharge_pct = pct
            return {"success": True, "data": {"surcharge_pct": pct, "surcharge_amount": 0}}

        def get_payment_surcharge_pct(self, method):
            if method == "credit_card":
                return {"success": True, "data": 10.0}
            return {"success": True, "data": 0.0}

        def search_products(self, query):
            return {"success": True, "data": []}

    ctrl = DummyController()
    view.set_controller(ctrl)

    # 1. Select credit_card (applies 10% surcharge)
    view._select_payment_method("credit_card")
    assert view._surcharge_pct == 10.0
    assert ctrl.surcharge_pct == 10.0

    # 2. Simulate sale completion, which calls _clear_cart
    view._clear_cart()

    # 3. Verify that the payment method has reset to "cash"
    assert view._selected_payment_method == "cash"
    assert view._payment_method_var.get() == "cash"
    assert view._surcharge_pct == 0.0
    assert ctrl.surcharge_pct == 0.0

    view.destroy()


def test_keyboard_shortcuts(session_root):
    from pos.view.main_window import MainWindow
    from pos.model.user import User, PermissionContext
    from pos.model.enums import UserRole
    
    # Create permission context for cashier
    user = User(id=1, username="cajero1", password="", role=UserRole.CAJERO)
    permissions = PermissionContext(
        user=user,
        allowed_tabs=["Ventas", "Devoluciones", "Caja"],
        cash_register_mode="restricted"
    )
    
    # Instantiate MainWindow with permissions
    app = MainWindow(permissions=permissions)
    session_root.update()
    
    # Verify cashier shortcuts help bar exists
    assert hasattr(app, "_shortcuts_frame")
    assert app._shortcuts_frame.winfo_exists()
    
    # Trigger key handlers directly and verify no crashes
    app._on_f1_pressed()
    app._on_f2_pressed()
    app._on_f3_pressed()
    app._on_f4_pressed()
    
    app.destroy()


def test_sale_view_inactive_product_dialogs(session_root):
    from pos.view.sale_view import SaleConfirmDialog, SaleInfoDialog
    
    confirm = SaleConfirmDialog(session_root, "Test Confirm", "Test Confirm Msg")
    session_root.update()
    assert confirm.result is False
    confirm._yes()
    
    info = SaleInfoDialog(session_root, "Test Info", "Test Info Msg")
    session_root.update()
    info.destroy()


def test_sale_view_quantity_shortcuts(session_root):
    view = SaleView(session_root, role="cajero")
    session_root.update()

    # Mock controller with a cart containing items
    class DummyController:
        def __init__(self):
            # We have one barcoded item (Coca Cola), one barcodeless unit item (Alfajor), and one Kg item (Queso)
            self._cart = [
                {
                    "product_id": 1,
                    "barcode": "7790000000001",
                    "name": "Coca Cola",
                    "quantity": 2.0,
                    "unit_price": 500,
                    "subtotal": 1000,
                    "unit_type": "Unidad"
                },
                {
                    "product_id": 2,
                    "barcode": "",
                    "name": "Alfajor",
                    "quantity": 1.0,
                    "unit_price": 400,
                    "subtotal": 400,
                    "unit_type": "Unidad"
                },
                {
                    "product_id": 3,
                    "barcode": "",
                    "name": "Queso Cremoso",
                    "quantity": 0.5,
                    "unit_price": 1000,
                    "subtotal": 500,
                    "unit_type": "Kg"
                }
            ]
        def get_cart(self):
            return {"success": True, "data": {"items": self._cart, "total": 1900}}

    ctrl = DummyController()
    view.set_controller(ctrl)
    session_root.update()

    # Wire up the update_qty callback to directly modify self._cart
    updated_qty = None
    def mock_update_qty(prod_id, qty):
        nonlocal updated_qty
        updated_qty = (prod_id, qty)
        for item in ctrl._cart:
            if item["product_id"] == prod_id:
                item["quantity"] = qty

    view.set_on_update_qty(mock_update_qty)

    # 1. No item selected -> F5/F6 should do nothing
    view._handle_f5()
    assert updated_qty is None

    # 2. Select the barcoded item (id 1)
    view._cart_tree._tree.selection_set("1")
    session_root.update()

    # 3. Press F6 (increase quantity) -> should increase to 3.0
    view._handle_f6()
    assert updated_qty == (1, 3.0)

    # 4. Press F5 (decrease quantity) -> should decrease to 2.0
    view._handle_f5()
    assert updated_qty == (1, 2.0)

    # 5. Select the barcodeless unit item (id 2)
    view._cart_tree._tree.selection_set("2")
    session_root.update()
    updated_qty = None

    # 6. Press F6 -> should increase to 2.0
    view._handle_f6()
    assert updated_qty == (2, 2.0)

    # 7. Press F5 -> decreases to 1.0
    view._handle_f5()
    assert updated_qty == (2, 1.0)

    # 8. Press F5 again -> should remain at 1.0 (limit 1)
    updated_qty = None
    view._handle_f5()
    assert updated_qty == (2, 1.0)

    # 9. Select Kg item (id 3) -> F5/F6 should do nothing because it is a Kg product
    view._cart_tree._tree.selection_set("3")
    session_root.update()
    updated_qty = None
    view._handle_f6()
    assert updated_qty is None

    view.destroy()

