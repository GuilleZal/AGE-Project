"""Tests for ProductController — CRUD orchestration with validation."""
import pytest
import sqlite3
from pos.controller.product_controller import ProductController


@pytest.fixture
def product_ctrl(db: sqlite3.Connection) -> ProductController:
    return ProductController(db)


class TestCreateProduct:
    """Product creation with validation."""

    def test_create_valid_product(self, product_ctrl, sample_category):
        cat1, _ = sample_category
        result = product_ctrl.create_product({
            "name": "Sprite 2L",
            "barcode": "7790000000001",
            "sale_price": 600,
            "cost_price": 350,
            "category_id": cat1,
            "stock": 20,
        })
        assert result["success"] is True
        assert result["data"].name == "Sprite 2L"
        assert result["data"].sale_price == 600
        assert result["data"].id is not None

    def test_create_duplicate_barcode_blocked(self, product_ctrl, sample_category):
        cat1, _ = sample_category
        product_ctrl.create_product({
            "name": "X", "barcode": "7790000000001",
            "sale_price": 100, "cost_price": 50,
        })
        result = product_ctrl.create_product({
            "name": "Y", "barcode": "7790000000001",
            "sale_price": 200, "cost_price": 100,
        })
        assert result["success"] is False
        assert "ya existe" in result["error"].lower()

    def test_create_empty_name_blocked(self, product_ctrl):
        result = product_ctrl.create_product({
            "name": "  ", "sale_price": 100, "cost_price": 50,
        })
        assert result["success"] is False

    def test_create_negative_price_blocked(self, product_ctrl):
        result = product_ctrl.create_product({
            "name": "Test", "sale_price": -10, "cost_price": 50,
        })
        assert result["success"] is False

    def test_create_default_values(self, product_ctrl):
        result = product_ctrl.create_product({
            "name": "Minimal", "sale_price": 100, "cost_price": 50,
        })
        assert result["success"] is True
        p = result["data"]
        assert p.stock == 0.0
        assert p.low_stock_threshold == 5.0


class TestUpdateProduct:
    """Product update with partial data."""

    def test_update_name(self, product_ctrl, sample_products):
        pid = sample_products[0]  # Coca-Cola
        result = product_ctrl.update_product(pid, {"name": "Coca-Cola 2L"})
        assert result["success"] is True
        assert result["data"].name == "Coca-Cola 2L"

    def test_update_price(self, product_ctrl, sample_products):
        pid = sample_products[0]
        result = product_ctrl.update_product(pid, {"sale_price": 900})
        assert result["success"] is True
        assert result["data"].sale_price == 900

    def test_update_nonexistent(self, product_ctrl):
        result = product_ctrl.update_product(99999, {"name": "Ghost"})
        assert result["success"] is False

    def test_update_partial_preserves_others(self, product_ctrl, sample_products):
        pid = sample_products[0]
        original = product_ctrl.get_product(pid)
        result = product_ctrl.update_product(pid, {"sale_price": 999})
        assert result["success"] is True
        assert result["data"].name == original["data"].name  # unchanged


class TestDeleteProduct:
    """Product soft deletion (is_active = 0)."""

    def test_delete_product_no_history(self, product_ctrl, sample_products):
        pid = sample_products[4]  # Six-Pack — no sales
        result = product_ctrl.delete_product(pid)
        assert result["success"] is True

        # Verify gone from active products
        result = product_ctrl.get_product(pid)
        assert result["success"] is False

    def test_delete_with_sales_soft_deletes(self, product_ctrl, db, sample_products):
        """Products with sales history can be soft deleted."""
        pid = sample_products[0]
        # Create a sale referencing this product
        db.execute("INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, 'now', 'open')")
        db.execute("INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', 1)")
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (1, ?, 1, 800, 800)", (pid,))
        db.commit()

        # Should succeed (soft delete)
        result = product_ctrl.delete_product(pid)
        assert result["success"] is True

        # Product should not be found in active products
        result = product_ctrl.get_product(pid)
        assert result["success"] is False

    def test_reactivate_product(self, product_ctrl, sample_products):
        """Test reactivating a deactivated product."""
        pid = sample_products[0]
        # First deactivate
        result = product_ctrl.delete_product(pid)
        assert result["success"] is True
        # Now reactivate
        result = product_ctrl.reactivate_product(pid)
        assert result["success"] is True
        # Product should be found again
        result = product_ctrl.get_product(pid)
        assert result["success"] is True

    def test_reactivate_already_active(self, product_ctrl, sample_products):
        """Test reactivating an already active product fails."""
        pid = sample_products[0]
        result = product_ctrl.reactivate_product(pid)
        assert result["success"] is False
        assert "ya está activo" in result["error"]

    def test_hard_delete_product(self, product_ctrl, sample_products):
        """Test permanently deleting a product with no history."""
        pid = sample_products[4]  # Six-Pack has no sales
        result = product_ctrl.hard_delete_product(pid)
        assert result["success"] is True
        # Product should be completely gone
        result = product_ctrl.get_product(pid)
        assert result["success"] is False

    def test_hard_delete_with_history_blocked(self, product_ctrl, db, sample_products):
        """Test that hard delete is blocked for products with transaction history."""
        pid = sample_products[0]
        # Create a sale referencing this product
        db.execute("INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, 'now', 'open')")
        db.execute("INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', 1)")
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (1, ?, 1, 800, 800)", (pid,))
        db.commit()

        result = product_ctrl.hard_delete_product(pid)
        assert result["success"] is False
        assert "historial de transacciones" in result["error"]
        # Product should still exist (soft delete would work instead)
        result = product_ctrl.get_product(pid)
        assert result["success"] is True

    def test_smart_delete_products(self, product_ctrl, db, sample_products):
        """Test smart delete processes multiple products correctly."""
        # Product 4 has no history -> should be hard deleted
        pid_no_history = sample_products[4]
        
        # Product 0 has history -> should be soft deleted
        pid_with_history = sample_products[0]
        db.execute("INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, 'now', 'open')")
        db.execute("INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', 1)")
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (1, ?, 1, 800, 800)", (pid_with_history,))
        db.commit()

        result = product_ctrl.smart_delete_products([pid_no_history, pid_with_history])
        assert result["success"] is True
        assert result["data"]["hard_deleted"] == 1
        assert result["data"]["soft_deleted"] == 1
        assert len(result["data"]["errors"]) == 0
        
        # Verify product_no_history is completely gone
        result = product_ctrl.get_product(pid_no_history)
        assert result["success"] is False
        
        # Verify product_with_history is deactivated
        result = product_ctrl.get_product(pid_with_history)
        assert result["success"] is False  # Not found in active products


class TestGetAndListProducts:
    """Product retrieval and listing."""

    def test_get_product(self, product_ctrl, sample_products):
        pid = sample_products[0]
        result = product_ctrl.get_product(pid)
        assert result["success"] is True
        assert result["data"].name == "Coca-Cola 1.5L"

    def test_get_nonexistent(self, product_ctrl):
        result = product_ctrl.get_product(99999)
        assert result["success"] is False

    def test_list_all(self, product_ctrl, sample_products):
        result = product_ctrl.list_products()
        assert result["success"] is True
        assert len(result["data"]) == 5

    def test_list_with_search(self, product_ctrl, sample_products):
        result = product_ctrl.list_products({"search": "Coca"})
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0].name == "Coca-Cola 1.5L"

    def test_list_low_stock(self, product_ctrl, sample_products):
        result = product_ctrl.list_products({"low_stock": True})
        assert result["success"] is True
        # Maní has 3 stock, threshold 5
        names = [p.name for p in result["data"]]
        assert "Maní Salado x Kg" in names


class TestCategories:
    """Category CRUD via ProductController."""

    def test_create_category(self, product_ctrl):
        result = product_ctrl.create_category("Vinos")
        assert result["success"] is True
        assert result["data"].name == "Vinos"

    def test_create_duplicate_category_blocked(self, product_ctrl):
        product_ctrl.create_category("Vinos")
        result = product_ctrl.create_category("Vinos")
        assert result["success"] is False

    def test_list_categories(self, product_ctrl, sample_category):
        result = product_ctrl.list_categories()
        assert result["success"] is True
        assert len(result["data"]) == 2


class TestGenerateTemplate:
    """Excel template generation."""

    def test_generate_template(self, product_ctrl, tmp_path):
        path = tmp_path / "template.xlsx"
        result = product_ctrl.generate_template(str(path))
        assert result["success"] is True

        import openpyxl
        wb = openpyxl.load_workbook(str(path))
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        assert headers == ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock"]
