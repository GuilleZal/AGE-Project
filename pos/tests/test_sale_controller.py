"""Tests for SaleController — cart management and sale completion."""
import pytest
import sqlite3
from pos.model.database import DDL
from pos.controller.sale_controller import SaleController


@pytest.fixture
def sale_ctrl(db: sqlite3.Connection) -> SaleController:
    """Return a SaleController backed by the in-memory database."""
    return SaleController(db)


@pytest.fixture
def db_with_products(db: sqlite3.Connection, sample_products: list[int]) -> sqlite3.Connection:
    """Database with sample products and an open register."""
    db.execute(
        "INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, '2026-06-13 08:00:00', 'open')"
    )
    db.commit()
    return db


class TestAddByBarcode:
    """Barcode scanning and cart addition."""

    def test_add_existing_product(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7790895000782")
        assert result["success"] is True
        assert result["data"]["name"] == "Coca-Cola 1.5L"
        assert result["data"]["quantity"] == 1.0
        assert result["data"]["unit_price"] == 800
        assert result["data"]["subtotal"] == 800

    def test_add_duplicate_increments_qty(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")
        result = sale_ctrl.add_by_barcode("7790895000782")
        assert result["success"] is True
        assert result["data"]["quantity"] == 2.0
        assert result["data"]["subtotal"] == 1600

    def test_add_unknown_barcode_returns_false(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("9999999999999")
        assert result["success"] is False
        assert result["error"] is None  # not an error — quick-create flow
        assert result["data"]["barcode"] == "9999999999999"

    def test_add_weight_product(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7791234000100", quantity=0.750)
        assert result["success"] is True
        assert result["data"]["name"] == "Queso Cremoso x Kg"
        assert result["data"]["quantity"] == 0.750
        assert result["data"]["subtotal"] == 7125  # 9500 * 0.75 = 7125

    def test_add_inactive_product_returns_inactive_flag(self, sale_ctrl, db_with_products):
        """When scanning an inactive product, should return inactive flag."""
        # First, deactivate a product
        from pos.repository.product_repo import ProductRepo
        repo = ProductRepo(db_with_products)
        product = repo.find_by_barcode("7790895000782")
        repo.delete(product.id)
        
        # Now try to scan it
        result = sale_ctrl.add_by_barcode("7790895000782")
        assert result["success"] is False
        assert result["error"] is None
        assert result["data"]["barcode"] == "7790895000782"
        assert result["data"]["inactive"] is True
        assert result["data"]["product"] is not None
        assert result["data"]["product"].name == "Coca-Cola 1.5L"

    def test_reactivate_and_add(self, sale_ctrl, db_with_products):
        """Test reactivating an inactive product and adding to cart."""
        # First, deactivate a product
        from pos.repository.product_repo import ProductRepo
        repo = ProductRepo(db_with_products)
        product = repo.find_by_barcode("7790895000782")
        product_id = product.id
        repo.delete(product_id)
        
        # Now reactivate and add
        result = sale_ctrl.reactivate_and_add(product_id, 1.0)
        assert result["success"] is True
        assert result["data"]["name"] == "Coca-Cola 1.5L"
        assert result["data"]["quantity"] == 1.0
        
        # Verify product is now active
        product = repo.find_by_id(product_id)
        assert product is not None
        assert product.is_active is True


class TestQuickCreateProduct:
    """Quick product creation for unknown barcodes."""

    def test_create_quick_product(self, sale_ctrl, db_with_products):
        result = sale_ctrl.create_quick_product("9999999999999", "Producto Rápido", 500)
        assert result["success"] is True
        assert result["data"]["name"] == "Producto Rápido"
        assert result["data"]["unit_price"] == 500
        assert result["data"]["quantity"] == 1.0

    def test_create_quick_product_then_scan_adds_to_cart(self, sale_ctrl, db_with_products):
        sale_ctrl.create_quick_product("9999999999999", "Producto Rápido", 500)
        # Now scanning the same barcode should find it
        result = sale_ctrl.add_by_barcode("9999999999999")
        assert result["success"] is True
        # Already in cart, so quantity should be 2
        assert result["data"]["quantity"] == 2.0

    def test_create_quick_negative_price_blocked(self, sale_ctrl, db_with_products):
        result = sale_ctrl.create_quick_product("9999999999999", "Malo", -100)
        assert result["success"] is False
        assert "negativo" in result["error"].lower()

    def test_create_quick_empty_name_blocked(self, sale_ctrl, db_with_products):
        result = sale_ctrl.create_quick_product("9999999999999", "   ", 500)
        assert result["success"] is False
        assert "nombre" in result["error"].lower()


class TestCartManipulation:
    """Modifying quantities and removing items."""

    def test_update_quantity(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7790895000782")
        product_id = result["data"]["product_id"]

        result = sale_ctrl.update_item_quantity(product_id, 3)
        assert result["success"] is True
        assert result["data"]["quantity"] == 3.0
        assert result["data"]["subtotal"] == 2400  # 800 * 3

    def test_update_quantity_zero_removes(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7790895000782")
        product_id = result["data"]["product_id"]

        result = sale_ctrl.update_item_quantity(product_id, 0)
        assert result["success"] is True
        cart = sale_ctrl.get_cart()
        assert len(cart["data"]["items"]) == 0

    def test_update_quantity_negative_removes(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7790895000782")
        product_id = result["data"]["product_id"]

        result = sale_ctrl.update_item_quantity(product_id, -1)
        assert result["success"] is True

    def test_remove_item(self, sale_ctrl, db_with_products):
        result = sale_ctrl.add_by_barcode("7790895000782")
        product_id = result["data"]["product_id"]

        result = sale_ctrl.remove_item(product_id)
        assert result["success"] is True
        cart = sale_ctrl.get_cart()
        assert len(cart["data"]["items"]) == 0

    def test_remove_nonexistent_item(self, sale_ctrl):
        result = sale_ctrl.remove_item(99999)
        assert result["success"] is False

    def test_get_cart_empty(self, sale_ctrl):
        cart = sale_ctrl.get_cart()
        assert cart["success"] is True
        assert cart["data"]["items"] == []
        assert cart["data"]["total"] == 0


class TestCalculateTotal:
    """Cart total calculation."""

    def test_empty_cart_total_zero(self, sale_ctrl):
        result = sale_ctrl.calculate_total()
        assert result["data"]["total"] == 0

    def test_total_with_items(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        sale_ctrl.add_by_barcode("7790895000997")  # 2500
        result = sale_ctrl.calculate_total()
        assert result["data"]["total"] == 3300

    def test_total_with_weight_items(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7791234000100", quantity=0.5)  # 9500 * 0.5 = 4750
        result = sale_ctrl.calculate_total()
        assert result["data"]["total"] == 4750


class TestClearCart:
    """Clearing the cart after sale."""

    def test_clear_cart(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")
        sale_ctrl.add_by_barcode("7790895000997")
        result = sale_ctrl.clear_cart()
        assert result["success"] is True
        cart = sale_ctrl.get_cart()
        assert len(cart["data"]["items"]) == 0


class TestCompleteSale:
    """Payment processing and sale persistence."""

    def test_complete_cash_sale(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=1000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 800
        assert result["data"]["change"] == 200
        assert result["data"]["sale"]["payment_method"] == "cash"

        # Cart should be empty after sale
        cart = sale_ctrl.get_cart()
        assert len(cart["data"]["items"]) == 0

    def test_complete_sale_empty_cart_blocked(self, sale_ctrl, db_with_products):
        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=100)
        assert result["success"] is False
        assert "vacío" in result["error"].lower()

    def test_complete_sale_insufficient_cash_blocked(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=500)
        assert result["success"] is False
        assert "insuficiente" in result["error"].lower()

    def test_complete_sale_no_register_blocked(self, sale_ctrl, db):
        """DB has no open register — sale should be blocked."""
        # Need to add a product first (use a direct product insert)
        db.execute(
            "INSERT INTO products (barcode, name, sale_price, cost_price, stock) VALUES ('111', 'Test', 100, 50, 10)"
        )
        db.commit()
        sale_ctrl.add_by_barcode("111")
        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=200)
        assert result["success"] is False
        assert "caja" in result["error"].lower()

    def test_complete_sale_card_payment(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        result = sale_ctrl.complete_sale(payment_method="card", amount_received=0)
        assert result["success"] is True
        assert result["data"]["sale"]["payment_method"] == "card"
        assert result["data"]["change"] == 0

    def test_complete_sale_transfer_payment(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000997")  # 2500
        result = sale_ctrl.complete_sale(payment_method="transfer", amount_received=0)
        assert result["success"] is True
        assert result["data"]["sale"]["payment_method"] == "transfer"

    def test_complete_sale_deducts_stock(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # Coca-Cola, stock=24
        sale_ctrl.complete_sale(payment_method="cash", amount_received=1000)

        # Verify stock was deducted
        import sqlite3
        row = db_with_products.execute("SELECT stock FROM products WHERE barcode = '7790895000782'").fetchone()
        assert row["stock"] == 23.0  # 24 - 1

    def test_complete_sale_allows_negative_stock(self, sale_ctrl, db_with_products):
        # Maní has 0.3 stock
        sale_ctrl.add_by_barcode("7794321000200", quantity=5.0)  # Maní, stock=0.3
        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=20000)
        assert result["success"] is True

        # Stock should go negative
        import sqlite3
        row = db_with_products.execute("SELECT stock FROM products WHERE barcode = '7794321000200'").fetchone()
        assert row["stock"] == -4.7  # 0.3 - 5.0

    def test_complete_sale_invalid_payment_method(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")
        result = sale_ctrl.complete_sale(payment_method="bitcoin", amount_received=1000)
        assert result["success"] is False
        assert "no válido" in result["error"].lower()

    def test_complete_sale_registers_cash_movement(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        sale_ctrl.complete_sale(payment_method="cash", amount_received=1000)

        # Check cash movement was created
        row = db_with_products.execute(
            "SELECT COUNT(*) as cnt FROM cash_movements WHERE type = 'sale_cash' AND amount = 800"
        ).fetchone()
        assert row["cnt"] == 1

    def test_complete_sale_multiple_items(self, sale_ctrl, db_with_products):
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        sale_ctrl.add_by_barcode("7790895000997")  # 2500
        sale_ctrl.add_by_barcode("7795555000300", quantity=2)  # 2000 * 2 = 4000

        result = sale_ctrl.complete_sale(payment_method="cash", amount_received=10000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 7300  # 800 + 2500 + 4000
        assert result["data"]["change"] == 2700
