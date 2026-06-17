"""Tests for StockService — deduct, restore, and low-stock queries."""

import sqlite3

import pytest

from pos.model.sale import SaleItem
from pos.model.exceptions import DataError
from pos.repository.product_repo import ProductRepo
from pos.service.stock_service import StockService


class TestDeduct:
    """Stock deduction via StockService.deduct()."""

    def test_reduces_stock(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        pid = sample_products[0]  # Coca-Cola, stock=24.0

        items = [SaleItem(product_id=pid, quantity=3, unit_price=800, subtotal=2400)]
        svc.deduct(items)

        repo = ProductRepo(db)
        product = repo.find_by_id(pid)
        assert product is not None
        assert product.stock == 21.0

    def test_allows_negative_stock(self, db: sqlite3.Connection, sample_products: list[int]):
        """Stock goes negative — service NEVER blocks a sale."""
        svc = StockService(db)
        pid = sample_products[0]  # stock=24.0

        items = [SaleItem(product_id=pid, quantity=100, unit_price=800, subtotal=80000)]
        svc.deduct(items)  # should NOT raise

        repo = ProductRepo(db)
        product = repo.find_by_id(pid)
        assert product is not None
        assert product.stock < 0

    def test_multiple_products_in_batch(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        p1, p2 = sample_products[0], sample_products[1]

        items = [
            SaleItem(product_id=p1, quantity=2, unit_price=800, subtotal=1600),
            SaleItem(product_id=p2, quantity=1, unit_price=2500, subtotal=2500),
        ]
        svc.deduct(items)

        repo = ProductRepo(db)
        assert repo.find_by_id(p1).stock == 22.0  # type: ignore[union-attr]
        assert repo.find_by_id(p2).stock == 11.0  # type: ignore[union-attr]

    def test_non_existent_product_rolls_back(self, db: sqlite3.Connection, sample_products: list[int]):
        """If one product doesn't exist, the entire batch rolls back."""
        svc = StockService(db)
        p1 = sample_products[0]

        items = [
            SaleItem(product_id=p1, quantity=2, unit_price=800, subtotal=1600),
            SaleItem(product_id=9999, quantity=1, unit_price=100, subtotal=100),
        ]
        with pytest.raises(DataError, match="no encontrado"):
            svc.deduct(items)

        # Verify rollback: p1 stock unchanged
        repo = ProductRepo(db)
        product = repo.find_by_id(p1)
        assert product is not None
        assert product.stock == 24.0

    def test_empty_batch_noop(self, db: sqlite3.Connection):
        svc = StockService(db)
        svc.deduct([])  # should not raise

    def test_float_quantity(self, db: sqlite3.Connection, sample_products: list[int]):
        """Weight products use float quantities."""
        svc = StockService(db)
        pid = sample_products[2]  # Queso Cremoso, stock=2.5

        items = [SaleItem(product_id=pid, quantity=0.750, unit_price=9500, subtotal=7125)]
        svc.deduct(items)

        repo = ProductRepo(db)
        product = repo.find_by_id(pid)
        assert product is not None
        assert product.stock == pytest.approx(1.75)


class TestRestore:
    """Stock restoration via StockService.restore()."""

    def test_increases_stock(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        pid = sample_products[0]

        svc.restore(pid, 5)

        repo = ProductRepo(db)
        product = repo.find_by_id(pid)
        assert product is not None
        assert product.stock == 29.0

    def test_float_quantity(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        pid = sample_products[2]  # 2.5 kg

        svc.restore(pid, 0.500)

        repo = ProductRepo(db)
        product = repo.find_by_id(pid)
        assert product is not None
        assert product.stock == pytest.approx(3.0)

    def test_non_existent_product(self, db: sqlite3.Connection):
        svc = StockService(db)
        with pytest.raises(ValueError, match="no encontrado"):
            svc.restore(9999, 1)

    def test_negative_quantity(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        with pytest.raises(ValueError, match="mayor a 0"):
            svc.restore(sample_products[0], -1)

    def test_zero_quantity(self, db: sqlite3.Connection, sample_products: list[int]):
        svc = StockService(db)
        with pytest.raises(ValueError, match="mayor a 0"):
            svc.restore(sample_products[0], 0)


class TestLowStockProducts:
    """Low-stock queries via StockService.low_stock_products()."""

    def test_uses_per_product_threshold(self, db: sqlite3.Connection, sample_products: list[int]):
        """Products below their own low_stock_threshold (default 5)."""
        svc = StockService(db)
        # Maní has stock=0.3 (< 5), Queso has stock=2.5 (< 5)
        result = svc.low_stock_products()
        ids = [p.id for p in result]
        # Maní (id 4) and Queso (id 3) should be in results
        assert sample_products[3] in ids  # Maní
        assert sample_products[2] in ids  # Queso
        # Products with stock >= 5 should NOT be included
        assert sample_products[0] not in ids  # Coca 24.0
        assert sample_products[1] not in ids  # Fernet 12.0

    def test_custom_threshold(self, db: sqlite3.Connection, sample_products: list[int]):
        """Use an explicit threshold instead of per-product setting."""
        svc = StockService(db)
        result = svc.low_stock_products(threshold=10)
        ids = [p.id for p in result]
        # All with stock <= 10
        assert sample_products[2] in ids  # Queso 2.5
        assert sample_products[3] in ids  # Maní 0.3
        assert sample_products[4] in ids  # Six-Pack 8.0
        assert sample_products[0] not in ids  # Coca 24.0
        assert sample_products[1] not in ids  # Fernet 12.0

    def test_none_below_threshold(self, db: sqlite3.Connection):
        """No products below threshold returns empty list."""
        # First add a product with high stock
        db.execute(
            """INSERT INTO products (name, sale_price, cost_price, stock)
               VALUES ('Test High', 100, 50, 100)"""
        )
        db.commit()

        svc = StockService(db)
        result = svc.low_stock_products(threshold=5)
        assert result == []

    def test_ordered_by_stock_ascending(self, db: sqlite3.Connection, sample_products: list[int]):
        """Low-stock products should be ordered by stock ASC."""
        svc = StockService(db)
        result = svc.low_stock_products(threshold=10)
        stocks = [p.stock for p in result]
        assert stocks == sorted(stocks)

    def test_empty_db(self, db: sqlite3.Connection):
        svc = StockService(db)
        result = svc.low_stock_products()
        assert result == []
