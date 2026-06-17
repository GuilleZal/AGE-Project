"""Tests for ProductRepo — CRUD, search, upsert, and delete-protection."""

import pytest

from pos.model.product import Product
from pos.model.exceptions import DataError
from pos.repository.product_repo import ProductRepo


# ------------------------------------------------------------------ helpers

def _make_product(**overrides) -> Product:
    defaults = {
        "name": "Test Product",
        "sale_price": 1000,
        "cost_price": 600,
        "barcode": "1234567890",
        "stock": 10.0,
    }
    defaults.update(overrides)
    return Product(**defaults)


# ---------------------------------------------------------------- find ----

class TestFindByBarcode:
    def test_found(self, db, sample_products):
        repo = ProductRepo(db)
        # Coca-Cola barcode from conftest: 7790895000782
        product = repo.find_by_barcode("7790895000782")
        assert product is not None
        assert product.name == "Coca-Cola 1.5L"
        assert product.sale_price == 800

    def test_not_found(self, db):
        repo = ProductRepo(db)
        assert repo.find_by_barcode("9999999999999") is None

    def test_none_barcode_product(self, db):
        """Product without barcode should still be findable by id but not by barcode."""
        repo = ProductRepo(db)
        prod = _make_product(barcode=None)
        repo.create(prod)
        assert repo.find_by_barcode("") is None  # empty string is not NULL


# ---------------------------------------------------------------- search --

class TestSearch:
    def test_partial_match(self, db, sample_products):
        repo = ProductRepo(db)
        results = repo.search("Coca")
        assert len(results) >= 1
        names = {r.name for r in results}
        assert "Coca-Cola 1.5L" in names

    def test_no_match(self, db):
        repo = ProductRepo(db)
        results = repo.search("zzz_nonexistent")
        assert results == []

    def test_case_sensitive_like(self, db, sample_products):
        """SQLite LIKE is case-insensitive for ASCII by default."""
        repo = ProductRepo(db)
        results = repo.search("coca")
        assert len(results) >= 1


# ---------------------------------------------------------------- create --

class TestCreate:
    def test_success(self, db):
        repo = ProductRepo(db)
        prod = _make_product()
        created = repo.create(prod)
        assert created.id is not None
        assert created.created_at is not None
        assert created.updated_at is not None

        # Verify in DB
        row = db.execute("SELECT * FROM products WHERE id = ?", (created.id,)).fetchone()
        assert row["name"] == "Test Product"
        assert row["sale_price"] == 1000

    def test_duplicate_barcode(self, db):
        repo = ProductRepo(db)
        repo.create(_make_product(barcode="UNIQUE123"))
        with pytest.raises(DataError, match="ya existe"):
            repo.create(_make_product(barcode="UNIQUE123"))

    def test_null_barcode_twice(self, db):
        """Two products without barcode should be allowed (barcode is UNIQUE but NULL != NULL)."""
        repo = ProductRepo(db)
        a = repo.create(_make_product(barcode=None, name="A"))
        b = repo.create(_make_product(barcode=None, name="B"))
        assert a.id != b.id


# ---------------------------------------------------------------- update --

class TestUpdate:
    def test_success(self, db):
        repo = ProductRepo(db)
        prod = repo.create(_make_product(barcode="UPD001"))
        prod.name = "Updated Name"
        prod.sale_price = 1500
        updated = repo.update(prod)
        assert updated.name == "Updated Name"

        row = db.execute("SELECT * FROM products WHERE id = ?", (prod.id,)).fetchone()
        assert row["name"] == "Updated Name"
        assert row["sale_price"] == 1500

    def test_not_found(self, db):
        repo = ProductRepo(db)
        ghost = Product(id=99999, name="Ghost", sale_price=100, cost_price=50)
        with pytest.raises(DataError, match="no encontrado"):
            repo.update(ghost)

    def test_update_duplicate_barcode(self, db):
        repo = ProductRepo(db)
        repo.create(_make_product(barcode="DUP001", name="First"))
        second = repo.create(_make_product(barcode="DUP002", name="Second"))
        # Try to change second's barcode to the first's
        second.barcode = "DUP001"
        with pytest.raises(DataError, match="ya existe"):
            repo.update(second)


# ---------------------------------------------------------------- delete --

class TestDelete:
    def test_success(self, db):
        repo = ProductRepo(db)
        prod = repo.create(_make_product(barcode="DEL001"))
        repo.delete(prod.id)
        # Product should not be found (is_active = 0)
        assert repo.find_by_barcode("DEL001") is None
        # But it should still exist in DB with is_active = 0
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (prod.id,)).fetchone()
        assert row["is_active"] == 0

    def test_with_sales_soft_deletes(self, db, sample_products, open_register):
        """Products with sales history can be soft deleted."""
        repo = ProductRepo(db)
        product_id = sample_products[0]
        db.execute(
            "INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', ?)",
            (open_register,),
        )
        sale_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 1, 800, 800)",
            (sale_id, product_id),
        )
        db.commit()

        # Should succeed (soft delete)
        repo.delete(product_id)
        # Product should not be found in active products
        assert repo.find_by_id(product_id) is None
        # But should exist in DB with is_active = 0
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 0

    def test_with_purchases_soft_deletes(self, db, sample_products):
        """Products with purchase history can be soft deleted."""
        repo = ProductRepo(db)
        product_id = sample_products[0]
        db.execute(
            "INSERT INTO suppliers (name) VALUES ('Test Supplier')"
        )
        supplier_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO purchases (supplier_id, total, purchase_date) VALUES (?, 500, '2026-01-01')",
            (supplier_id,),
        )
        purchase_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO purchase_items (purchase_id, product_id, quantity, unit_cost, subtotal) VALUES (?, ?, 1, 500, 500)",
            (purchase_id, product_id),
        )
        db.commit()

        # Should succeed (soft delete)
        repo.delete(product_id)
        # Product should not be found in active products
        assert repo.find_by_id(product_id) is None
        # But should exist in DB with is_active = 0
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 0

    def test_no_transactions_allows_delete(self, db, sample_products):
        repo = ProductRepo(db)
        # Product index 4 (Six-Pack) has no sales or purchases
        product_id = sample_products[4]
        repo.delete(product_id)
        # Product should still exist in DB but with is_active = 0
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 0

    def test_reactivate(self, db, sample_products):
        repo = ProductRepo(db)
        product_id = sample_products[0]
        # First deactivate
        repo.delete(product_id)
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 0
        # Now reactivate
        repo.reactivate(product_id)
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 1
        # Product should be found again
        product = repo.find_by_id(product_id)
        assert product is not None

    def test_reactivate_already_active(self, db, sample_products):
        repo = ProductRepo(db)
        product_id = sample_products[0]
        # Try to reactivate an already active product
        with pytest.raises(DataError, match="no encontrado o ya está activo"):
            repo.reactivate(product_id)

    def test_hard_delete_no_transactions(self, db, sample_products):
        repo = ProductRepo(db)
        # Product index 4 (Six-Pack) has no sales or purchases
        product_id = sample_products[4]
        repo.hard_delete(product_id)
        # Product should be completely removed from DB
        row = db.execute("SELECT COUNT(*) AS cnt FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["cnt"] == 0

    def test_hard_delete_with_sales_blocked(self, db, sample_products, open_register):
        repo = ProductRepo(db)
        product_id = sample_products[0]
        # Create a sale referencing this product
        db.execute(
            "INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', ?)",
            (open_register,),
        )
        sale_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 1, 800, 800)",
            (sale_id, product_id),
        )
        db.commit()

        # Should fail with transaction history error
        with pytest.raises(DataError, match="historial de transacciones"):
            repo.hard_delete(product_id)
        
        # Product should still exist
        row = db.execute("SELECT COUNT(*) AS cnt FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["cnt"] == 1

    def test_smart_delete_no_history(self, db, sample_products):
        """Test smart delete performs hard delete when no transaction history."""
        repo = ProductRepo(db)
        # Product index 4 (Six-Pack) has no sales or purchases
        product_id = sample_products[4]
        action = repo.smart_delete(product_id)
        assert action == "hard_deleted"
        # Product should be completely removed from DB
        row = db.execute("SELECT COUNT(*) AS cnt FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["cnt"] == 0

    def test_smart_delete_with_history(self, db, sample_products, open_register):
        """Test smart delete performs soft delete when transaction history exists."""
        repo = ProductRepo(db)
        product_id = sample_products[0]
        # Create a sale referencing this product
        db.execute(
            "INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', ?)",
            (open_register,),
        )
        sale_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 1, 800, 800)",
            (sale_id, product_id),
        )
        db.commit()

        action = repo.smart_delete(product_id)
        assert action == "soft_deleted"
        # Product should still exist but with is_active = 0
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,)).fetchone()
        assert row["is_active"] == 0

    def test_smart_delete_batch(self, db, sample_products, open_register):
        """Test smart delete batch processes multiple products correctly."""
        repo = ProductRepo(db)
        
        # Product 4 has no history -> should be hard deleted
        product_no_history = sample_products[4]
        
        # Product 0 has history -> should be soft deleted
        product_with_history = sample_products[0]
        db.execute(
            "INSERT INTO sales (total, payment_method, cash_register_id) VALUES (800, 'cash', ?)",
            (open_register,),
        )
        sale_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 1, 800, 800)",
            (sale_id, product_with_history),
        )
        db.commit()

        result = repo.smart_delete_batch([product_no_history, product_with_history])
        
        assert result["hard_deleted"] == 1
        assert result["soft_deleted"] == 1
        assert len(result["errors"]) == 0
        
        # Verify product_no_history is completely gone
        row = db.execute("SELECT COUNT(*) AS cnt FROM products WHERE id = ?", (product_no_history,)).fetchone()
        assert row["cnt"] == 0
        
        # Verify product_with_history is deactivated
        row = db.execute("SELECT is_active FROM products WHERE id = ?", (product_with_history,)).fetchone()
        assert row["is_active"] == 0


# --------------------------------------------------------------- upsert ---

class TestUpsertFromImport:
    def test_creates_new(self, db):
        repo = ProductRepo(db)
        prod = _make_product(barcode="IMP001", name="Imported Beer")
        result, action = repo.upsert_from_import(prod)
        assert action == "created"
        assert result.id is not None
        assert result.name == "Imported Beer"

    def test_updates_existing_updates_name(self, db):
        repo = ProductRepo(db)
        # First, create with a specific name
        original = repo.create(_make_product(barcode="IMP002", name="Original Name",
                                             sale_price=500, cost_price=300,
                                             stock=5.0))
        # Now upsert with a different name — name SHOULD change
        import_prod = _make_product(barcode="IMP002", name="Updated Name",
                                    sale_price=800, cost_price=500, stock=10.0)
        result, action = repo.upsert_from_import(import_prod)
        assert action == "updated"
        assert result.id == original.id

        # Verify DB: name updated, other fields updated
        row = db.execute("SELECT * FROM products WHERE id = ?", (original.id,)).fetchone()
        assert row["name"] == "Updated Name"     # updated
        assert row["sale_price"] == 800          # updated
        assert row["cost_price"] == 500          # updated
        assert row["stock"] == 10.0              # updated
        assert row["is_active"] == 1             # reactivated

    def test_null_barcode_creates(self, db):
        """Products without barcode are always created (no match on NULL)."""
        repo = ProductRepo(db)
        repo.create(_make_product(barcode=None, name="NoBarcode1"))
        prod2 = _make_product(barcode=None, name="NoBarcode2", sale_price=999)
        result, action = repo.upsert_from_import(prod2)
        assert action == "created"
        # Should have 2 products without barcode
        count = db.execute("SELECT COUNT(*) AS cnt FROM products WHERE barcode IS NULL").fetchone()["cnt"]
        assert count == 2


# ------------------------------------------------------------- get-all ----

class TestGetAll:
    def test_returns_all_ordered(self, db, sample_products):
        repo = ProductRepo(db)
        all_products = repo.get_all()
        assert len(all_products) == 5
        names = [p.name for p in all_products]
        assert names == sorted(names)
