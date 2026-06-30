"""Tests for SaleService — atomic sale completion (all-or-nothing).

Verifies that ``SaleService.complete_sale()``:
- Persists sale + items + stock deduction + cash movement in one transaction.
- Rolls back ALL changes when any step fails.
- Handles empty item lists gracefully.
"""

import sqlite3

import pytest

from pos.model.cash_register import CashMovement
from pos.model.enums import PaymentMethod, MovementType
from pos.model.exceptions import POSException
from pos.model.sale import Sale, SaleItem
from pos.repository.product_repo import ProductRepo
from pos.service.sale_service import SaleService


@pytest.fixture
def sale_svc(db: sqlite3.Connection) -> SaleService:
    """Return a SaleService backed by the in-memory database."""
    return SaleService(db)


@pytest.fixture
def db_with_register(db: sqlite3.Connection, sample_products: list[int]) -> sqlite3.Connection:
    """Database with sample products and an open cash register."""
    db.execute(
        "INSERT INTO cash_registers (opening_amount, opening_time, status) "
        "VALUES (5000, '2026-06-13 08:00:00', 'open')"
    )
    db.commit()
    return db


# ------------------------------------------------------------------ helpers


def _build_sale(total: int = 800, payment_method: str = "cash", register_id: int = 1) -> Sale:
    return Sale(
        total=total,
        discount=0,
        payment_method=payment_method,
        cash_register_id=register_id,
    )


def _build_items(*product_ids: int) -> list[SaleItem]:
    items: list[SaleItem] = []
    for pid in product_ids:
        items.append(SaleItem(
            product_id=pid,
            quantity=1.0,
            unit_price=800,
            subtotal=800,
        ))
    return items


# ---------------------------------------------------------- happy path -----


class TestCompleteSaleHappyPath:
    """All operations succeed → everything persisted."""

    def test_persists_sale_and_items(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=800, payment_method="card")
        items = _build_items(sample_products[0])

        result = sale_svc.complete_sale(sale, items, "card", 1)

        # Sale ID populated
        assert result.id is not None
        assert result.total == 800

        # Verify sale in DB
        row = db_with_register.execute(
            "SELECT * FROM sales WHERE id = ?", (result.id,)
        ).fetchone()
        assert row is not None
        assert row["total"] == 800

        # Verify items in DB
        item_rows = db_with_register.execute(
            "SELECT * FROM sale_items WHERE sale_id = ?", (result.id,)
        ).fetchall()
        assert len(item_rows) == 1
        assert item_rows[0]["product_id"] == sample_products[0]

    def test_deducts_stock(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=1600, payment_method="card")
        items = _build_items(sample_products[0], sample_products[1])

        sale_svc.complete_sale(sale, items, "card", 1)

        repo = ProductRepo(db_with_register)
        p1 = repo.find_by_id(sample_products[0])
        p2 = repo.find_by_id(sample_products[1])
        assert p1 is not None and p1.stock == 23.0  # 24 - 1
        assert p2 is not None and p2.stock == 11.0  # 12 - 1

    def test_allows_negative_stock(self, sale_svc, db_with_register, sample_products):
        """Stock goes negative — sale NEVER blocked."""
        sale = _build_sale(total=800, payment_method="card")
        items = [SaleItem(
            product_id=sample_products[3],  # Maní, stock=3
            quantity=10.0,
            unit_price=3000,
            subtotal=30000,
        )]

        result = sale_svc.complete_sale(sale, items, "card", 1)
        assert result.id is not None

        repo = ProductRepo(db_with_register)
        p = repo.find_by_id(sample_products[3])
        assert p is not None and p.stock == -7  # 3 - 10

    def test_registers_cash_movement_for_cash_payment(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=800, payment_method="cash")
        items = _build_items(sample_products[0])

        result = sale_svc.complete_sale(sale, items, "cash", 1)

        row = db_with_register.execute(
            "SELECT * FROM cash_movements WHERE type = 'sale_cash' AND amount = 800"
        ).fetchone()
        assert row is not None
        assert row["cash_register_id"] == 1
        assert f"Venta #{result.id}" in row["description"]

    def test_cash_movement_for_card_payment(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=800, payment_method="card")
        items = _build_items(sample_products[0])

        result = sale_svc.complete_sale(sale, items, "card", 1)

        row = db_with_register.execute(
            "SELECT * FROM cash_movements WHERE cash_register_id = 1"
        ).fetchone()
        assert row is not None
        assert row["type"] == "sale_card"
        assert row["amount"] == 800
        assert f"Venta #{result.id}" in row["description"]

    def test_cash_movement_for_transfer_payment(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=1200, payment_method="transfer")
        items = _build_items(sample_products[0])

        result = sale_svc.complete_sale(sale, items, "transfer", 1)

        row = db_with_register.execute(
            "SELECT * FROM cash_movements WHERE cash_register_id = 1"
        ).fetchone()
        assert row is not None
        assert row["type"] == "sale_transfer"
        assert row["amount"] == 1200
        assert f"Venta #{result.id}" in row["description"]

    def test_multiple_items(self, sale_svc, db_with_register, sample_products):
        sale = _build_sale(total=4100, payment_method="cash")
        items = [
            SaleItem(product_id=sample_products[0], quantity=2.0, unit_price=800, subtotal=1600),
            SaleItem(product_id=sample_products[1], quantity=1.0, unit_price=2500, subtotal=2500),
        ]

        result = sale_svc.complete_sale(sale, items, "cash", 1)

        item_rows = db_with_register.execute(
            "SELECT * FROM sale_items WHERE sale_id = ?", (result.id,)
        ).fetchall()
        assert len(item_rows) == 2

    def test_empty_items_list(self, sale_svc, db_with_register):
        """Empty items list should NOT crash — handled gracefully."""
        sale = _build_sale(total=0, payment_method="card")
        result = sale_svc.complete_sale(sale, [], "card", 1)

        assert result.id is not None
        # Sale exists, no items
        items = db_with_register.execute(
            "SELECT COUNT(*) AS cnt FROM sale_items WHERE sale_id = ?", (result.id,)
        ).fetchone()
        assert items["cnt"] == 0


# ------------------------------------------------------- rollback tests ----


class TestCompleteSaleRollback:
    """Any failure → ALL changes rolled back."""

    def test_sale_item_fk_failure_rolls_back_sale(self, sale_svc, db_with_register, sample_products):
        """Non-existent product in items → FK violation → sale NOT persisted.

        The FK on ``sale_items.product_id REFERENCES products(id)`` fires
        before stock deduction is reached.  Regardless of which step fails,
        the entire transaction must roll back.
        """
        sale = _build_sale(total=800, payment_method="card")
        items = [
            SaleItem(product_id=sample_products[0], quantity=1.0, unit_price=800, subtotal=800),
            SaleItem(product_id=99999, quantity=1.0, unit_price=100, subtotal=100),  # invalid FK
        ]

        with pytest.raises(POSException):
            sale_svc.complete_sale(sale, items, "card", 1)

        # Verify sale was NOT persisted (rollback)
        row = db_with_register.execute(
            "SELECT COUNT(*) AS cnt FROM sales"
        ).fetchone()
        assert row["cnt"] == 0

        # Verify stock was NOT deducted for the valid product
        repo = ProductRepo(db_with_register)
        p = repo.find_by_id(sample_products[0])
        assert p is not None and p.stock == 24.0  # unchanged

    def test_cash_movement_failure_rolls_back_everything(self, sale_svc, db_with_register, sample_products):
        """Invalid cash_register_id → FK violation → all rolled back."""
        sale = _build_sale(total=800, payment_method="cash", register_id=99999)
        items = _build_items(sample_products[0])

        with pytest.raises(POSException):
            sale_svc.complete_sale(sale, items, "cash", 99999)

        # Verify nothing persisted
        row = db_with_register.execute(
            "SELECT COUNT(*) AS cnt FROM sales"
        ).fetchone()
        assert row["cnt"] == 0

        # Stock unchanged
        repo = ProductRepo(db_with_register)
        p = repo.find_by_id(sample_products[0])
        assert p is not None and p.stock == 24.0
