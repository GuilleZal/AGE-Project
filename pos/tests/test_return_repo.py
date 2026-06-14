"""Tests for ReturnRepo — atomic returns with date-range queries."""

from pos.model.return_ import Return
from pos.repository.return_repo import ReturnRepo


class TestCreate:
    def test_success(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        ret = Return(
            product_id=sample_products[0],
            quantity=1,
            refund_amount=800,
            cash_register_id=open_register,
            reason="Producto vencido",
        )
        created = repo.create(ret)
        assert created.id is not None
        assert created.created_at is not None
        assert created.refund_amount == 800
        assert created.reason == "Producto vencido"

        # Verify in DB
        row = db.execute("SELECT * FROM returns WHERE id = ?", (created.id,)).fetchone()
        assert row["product_id"] == sample_products[0]
        assert row["quantity"] == 1
        assert row["cash_register_id"] == open_register

    def test_no_reason(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        ret = Return(
            product_id=sample_products[1],
            quantity=2,
            refund_amount=5000,
            cash_register_id=open_register,
            reason=None,
        )
        created = repo.create(ret)
        assert created.reason is None

    def test_no_fk_to_sales(self, db, sample_products, open_register):
        """Return does NOT require a sale to exist (atomic model)."""
        repo = ReturnRepo(db)
        # Create a return referencing a product that has no sales
        ret = Return(
            product_id=sample_products[3],  # Maní — no sale in fixture
            quantity=1,
            refund_amount=3000,
            cash_register_id=open_register,
        )
        created = repo.create(ret)
        assert created.id is not None

    def test_float_quantity(self, db, sample_products, open_register):
        """Weight products may have fractional returns."""
        repo = ReturnRepo(db)
        ret = Return(
            product_id=sample_products[2],  # Queso Cremoso (weight_kg)
            quantity=0.5,
            refund_amount=4750,
            cash_register_id=open_register,
        )
        created = repo.create(ret)
        row = db.execute("SELECT quantity FROM returns WHERE id = ?", (created.id,)).fetchone()
        assert row["quantity"] == 0.5


class TestGetByDate:
    def test_returns_matching(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        ret = repo.create(Return(
            product_id=sample_products[0], quantity=1, refund_amount=800,
            cash_register_id=open_register,
        ))
        db.commit()

        results = repo.get_by_date("2020-01-01", "2030-12-31")
        assert len(results) == 1
        assert results[0].id == ret.id

    def test_none_in_range(self, db):
        repo = ReturnRepo(db)
        results = repo.get_by_date("2010-01-01", "2010-01-02")
        assert results == []

    def test_out_of_range_excluded(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        repo.create(Return(
            product_id=sample_products[0], quantity=1, refund_amount=800,
            cash_register_id=open_register,
        ))
        db.commit()

        # Query a range in the past
        results = repo.get_by_date("2010-01-01", "2010-12-31")
        assert results == []

    def test_most_recent_first(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        r1 = repo.create(Return(product_id=sample_products[0], quantity=1,
                                refund_amount=800, cash_register_id=open_register))
        r2 = repo.create(Return(product_id=sample_products[1], quantity=1,
                                refund_amount=2500, cash_register_id=open_register))
        db.commit()

        results = repo.get_by_date("2020-01-01", "2030-12-31")
        assert len(results) == 2
        # Most recent first
        assert results[0].id == r2.id
        assert results[1].id == r1.id


class TestGetAll:
    def test_returns_all(self, db, sample_products, open_register):
        repo = ReturnRepo(db)
        repo.create(Return(product_id=sample_products[0], quantity=1,
                           refund_amount=800, cash_register_id=open_register))
        repo.create(Return(product_id=sample_products[1], quantity=2,
                           refund_amount=5000, cash_register_id=open_register))
        db.commit()

        all_returns = repo.get_all()
        assert len(all_returns) == 2

    def test_empty(self, db):
        repo = ReturnRepo(db)
        assert repo.get_all() == []
