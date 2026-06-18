"""Tests for discount functionality in SaleController."""

import pytest
import sqlite3

from pos.controller.sale_controller import SaleController
from pos.model.product import Product
from pos.repository.product_repo import ProductRepo


@pytest.fixture
def sale_ctrl(db: sqlite3.Connection) -> SaleController:
    return SaleController(db)


@pytest.fixture
def sample_product(db: sqlite3.Connection) -> Product:
    """Create a sample product for testing."""
    repo = ProductRepo(db)
    product = Product(
        barcode="7790000000001",
        name="Producto Test",
        sale_price=1000,
        cost_price=600,
        stock=100.0,
    )
    return repo.create(product)


class TestApplyDiscount:
    """Test discount application functionality."""

    def test_apply_valid_discount(self, sale_ctrl, sample_product, db):
        """Test applying a valid discount percentage."""
        # Add product to cart
        sale_ctrl.add_by_barcode("7790000000001")
        
        # Apply 10% discount
        result = sale_ctrl.apply_discount(10.0)
        
        assert result["success"] is True
        assert result["data"]["discount_pct"] == 10.0
        assert result["data"]["discount_amount"] == 100  # 10% of 1000
        assert result["data"]["final_total"] == 900

    def test_apply_zero_discount(self, sale_ctrl, sample_product, db):
        """Test applying 0% discount (no discount)."""
        sale_ctrl.add_by_barcode("7790000000001")
        
        result = sale_ctrl.apply_discount(0.0)
        
        assert result["success"] is True
        assert result["data"]["discount_amount"] == 0
        assert result["data"]["final_total"] == 1000

    def test_apply_100_percent_discount(self, sale_ctrl, sample_product, db):
        """Test applying 100% discount (free sale)."""
        sale_ctrl.add_by_barcode("7790000000001")
        
        result = sale_ctrl.apply_discount(100.0)
        
        assert result["success"] is True
        assert result["data"]["discount_amount"] == 1000
        assert result["data"]["final_total"] == 0

    def test_apply_invalid_negative_discount(self, sale_ctrl, sample_product, db):
        """Test applying negative discount (should fail)."""
        sale_ctrl.add_by_barcode("7790000000001")
        
        result = sale_ctrl.apply_discount(-10.0)
        
        assert result["success"] is False
        assert "entre 0 y 100" in result["error"]

    def test_apply_invalid_over_100_discount(self, sale_ctrl, sample_product, db):
        """Test applying discount over 100% (should fail)."""
        sale_ctrl.add_by_barcode("7790000000001")
        
        result = sale_ctrl.apply_discount(150.0)
        
        assert result["success"] is False
        assert "entre 0 y 100" in result["error"]

    def test_discount_with_multiple_items(self, sale_ctrl, db):
        """Test discount with multiple products in cart."""
        # Create two products
        repo = ProductRepo(db)
        product1 = repo.create(Product(
            barcode="7790000000001",
            name="Producto 1",
            sale_price=500,
            cost_price=300,
            stock=100.0,
        ))
        product2 = repo.create(Product(
            barcode="7790000000002",
            name="Producto 2",
            sale_price=500,
            cost_price=300,
            stock=100.0,
        ))
        
        # Add both to cart
        sale_ctrl.add_by_barcode("7790000000001")
        sale_ctrl.add_by_barcode("7790000000002")
        
        # Apply 20% discount
        result = sale_ctrl.apply_discount(20.0)
        
        assert result["success"] is True
        assert result["data"]["discount_amount"] == 200  # 20% of 1000
        assert result["data"]["final_total"] == 800

    def test_clear_cart_resets_discount(self, sale_ctrl, sample_product, db):
        """Test that clearing cart resets discount."""
        sale_ctrl.add_by_barcode("7790000000001")
        sale_ctrl.apply_discount(10.0)
        
        sale_ctrl.clear_cart()
        
        discount_info = sale_ctrl.get_discount_info()
        assert discount_info["data"]["discount_pct"] == 0.0
        assert discount_info["data"]["discount_amount"] == 0

    def test_get_discount_info(self, sale_ctrl, sample_product, db):
        """Test getting current discount information."""
        sale_ctrl.add_by_barcode("7790000000001")
        sale_ctrl.apply_discount(15.0)
        
        result = sale_ctrl.get_discount_info()
        
        assert result["success"] is True
        assert result["data"]["discount_pct"] == 15.0
        assert result["data"]["discount_amount"] == 150  # 15% of 1000
