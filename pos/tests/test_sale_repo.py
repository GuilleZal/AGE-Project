"""Tests for SaleRepo + SaleItemRepo — creation, aggregation, and batch operations."""

import pytest

from pos.model.sale import Sale, SaleItem
from pos.model.enums import PaymentMethod
from pos.repository.sale_repo import SaleRepo
from pos.repository.sale_item_repo import SaleItemRepo


# ----------------------------------------------------------------- helpers

def _create_sample_sale(db, register_id: int, sample_products: list[int]) -> tuple[int, list[int]]:
    """Create a sale with 2 items and return (sale_id, [item_ids])."""
    sale_repo = SaleRepo(db)
    item_repo = SaleItemRepo(db)

    sale = Sale(total=3300, payment_method=PaymentMethod.CASH, cash_register_id=register_id)
    sale_repo.create(sale)

    items = [
        SaleItem(product_id=sample_products[0], quantity=1, unit_price=800, subtotal=800),
        SaleItem(product_id=sample_products[1], quantity=1, unit_price=2500, subtotal=2500),
    ]
    item_repo.create_batch(sale.id, items)
    db.commit()
    return sale.id, [it.id for it in items]


# ============================================================================
# SaleRepo tests
# ============================================================================

class TestCreateSale:
    def test_success(self, db, open_register):
        repo = SaleRepo(db)
        sale = Sale(total=1500, payment_method=PaymentMethod.CASH, cash_register_id=open_register)
        created = repo.create(sale)
        assert created.id is not None
        assert created.created_at is not None
        assert created.total == 1500

        row = db.execute("SELECT * FROM sales WHERE id = ?", (created.id,)).fetchone()
        assert row["payment_method"] == "cash"

    def test_with_discount(self, db, open_register):
        repo = SaleRepo(db)
        sale = Sale(total=1000, discount=100, payment_method="card", cash_register_id=open_register)
        created = repo.create(sale)
        assert created.discount == 100

    def test_find_by_id(self, db, open_register):
        repo = SaleRepo(db)
        sale = repo.create(Sale(total=500, payment_method="transfer", cash_register_id=open_register))
        found = repo.find_by_id(sale.id)
        assert found is not None
        assert found.total == 500

    def test_find_by_id_not_found(self, db):
        repo = SaleRepo(db)
        assert repo.find_by_id(99999) is None


class TestAggregateByPeriod:
    def test_daily_grouping(self, db, open_register, sample_products):
        """Create two sales on the same day, verify daily aggregation."""
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        s1 = sale_repo.create(Sale(total=1000, payment_method="cash", cash_register_id=open_register))
        item_repo.create_batch(s1.id, [
            SaleItem(product_id=sample_products[0], quantity=1, unit_price=1000, subtotal=1000)
        ])

        s2 = sale_repo.create(Sale(total=500, payment_method="card", cash_register_id=open_register))
        item_repo.create_batch(s2.id, [
            SaleItem(product_id=sample_products[1], quantity=1, unit_price=500, subtotal=500)
        ])
        db.commit()

        # Use a wide date range covering today
        result = sale_repo.aggregate_by_period("2020-01-01", "2030-12-31", "day")
        assert len(result) >= 1
        today_total = sum(r["total_revenue"] for r in result)
        assert today_total == 1500

    def test_monthly_grouping(self, db, open_register):
        sale_repo = SaleRepo(db)
        sale_repo.create(Sale(total=300, payment_method="cash", cash_register_id=open_register))
        db.commit()

        result = sale_repo.aggregate_by_period("2020-01-01", "2030-12-31", "month")
        assert len(result) >= 1

    def test_empty_range(self, db):
        repo = SaleRepo(db)
        result = repo.aggregate_by_period("2010-01-01", "2010-01-02", "day")
        assert result == []


class TestTopProducts:
    def test_returns_top_products(self, db, open_register, sample_products):
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        # Sale 1: product 0 (3 units), product 1 (1 unit)
        s1 = sale_repo.create(Sale(total=4900, payment_method="cash", cash_register_id=open_register))
        item_repo.create_batch(s1.id, [
            SaleItem(product_id=sample_products[0], quantity=3, unit_price=800, subtotal=2400),
            SaleItem(product_id=sample_products[1], quantity=1, unit_price=2500, subtotal=2500),
        ])

        # Sale 2: product 0 (1 unit)
        s2 = sale_repo.create(Sale(total=800, payment_method="card", cash_register_id=open_register))
        item_repo.create_batch(s2.id, [
            SaleItem(product_id=sample_products[0], quantity=1, unit_price=800, subtotal=800),
        ])
        db.commit()

        result = sale_repo.top_products("2020-01-01", "2030-12-31", limit=3)
        assert len(result) >= 1
        # Product 0 (Coca-Cola) should be #1 with total_quantity=4
        top = result[0]
        assert top["total_quantity"] == 4
        assert top["total_amount"] == 3200  # 2400 + 800


class TestTotalByPaymentMethod:
    def test_breakdown(self, db, open_register, sample_products):
        sale_repo = SaleRepo(db)

        sale_repo.create(Sale(total=1000, payment_method="cash", cash_register_id=open_register))
        sale_repo.create(Sale(total=2000, payment_method="cash", cash_register_id=open_register))
        sale_repo.create(Sale(total=500, payment_method="card", cash_register_id=open_register))
        db.commit()

        result = sale_repo.total_by_payment_method("2020-01-01", "2030-12-31")
        methods = {r["payment_method"]: r for r in result}
        assert methods["cash"]["total_amount"] == 3000
        assert methods["cash"]["sale_count"] == 2
        assert methods["card"]["total_amount"] == 500
        assert methods["card"]["sale_count"] == 1

    def test_empty_range(self, db):
        repo = SaleRepo(db)
        result = repo.total_by_payment_method("2010-01-01", "2010-01-02")
        assert result == []


# ============================================================================
# SaleItemRepo tests
# ============================================================================

class TestCreateBatch:
    def test_success(self, db, open_register, sample_products):
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        sale = sale_repo.create(Sale(total=3300, payment_method="cash", cash_register_id=open_register))
        items = [
            SaleItem(product_id=sample_products[0], quantity=2, unit_price=800, subtotal=1600),
            SaleItem(product_id=sample_products[1], quantity=1, unit_price=2500, subtotal=2500),
        ]
        result = item_repo.create_batch(sale.id, items)
        db.commit()

        assert len(result) == 2
        assert all(it.id is not None for it in result)
        assert all(it.sale_id == sale.id for it in result)

        # Verify in DB
        rows = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale.id,)).fetchall()
        assert len(rows) == 2

    def test_empty_batch(self, db, open_register):
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        sale = sale_repo.create(Sale(total=0, payment_method="cash", cash_register_id=open_register))
        result = item_repo.create_batch(sale.id, [])
        assert result == []

    def test_float_quantities(self, db, open_register, sample_products):
        """Weight products may have fractional quantities."""
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        sale = sale_repo.create(Sale(total=2375, payment_method="cash", cash_register_id=open_register))
        items = [
            SaleItem(product_id=sample_products[2], quantity=0.25, unit_price=9500, subtotal=2375),
        ]
        item_repo.create_batch(sale.id, items)
        db.commit()

        row = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale.id,)).fetchone()
        assert row["quantity"] == 0.25


class TestGetBySale:
    def test_returns_items(self, db, open_register, sample_products):
        sale_id, item_ids = _create_sample_sale(db, open_register, sample_products)

        item_repo = SaleItemRepo(db)
        items = item_repo.get_by_sale(sale_id)
        assert len(items) == 2
        # Order is by id
        assert items[0].product_id in {sample_products[0], sample_products[1]}

    def test_no_items(self, db, open_register):
        sale_repo = SaleRepo(db)
        item_repo = SaleItemRepo(db)

        sale = sale_repo.create(Sale(total=100, payment_method="cash", cash_register_id=open_register))
        db.commit()
        assert item_repo.get_by_sale(sale.id) == []


class TestCascadeDelete:
    def test_sale_items_cascade_on_sale_delete(self, db, open_register, sample_products):
        sale_id, item_ids = _create_sample_sale(db, open_register, sample_products)

        # Delete the sale — items should cascade
        db.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        db.commit()

        item_rows = db.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)).fetchall()
        assert len(item_rows) == 0
