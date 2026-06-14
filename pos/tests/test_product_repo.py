"""Tests for ProductRepo — CRUD, search, upsert, and delete-protection."""

import pytest

from pos.model.product import Product
from pos.model.enums import UnitType
from pos.model.exceptions import DataError
from pos.repository.product_repo import ProductRepo


# ------------------------------------------------------------------ helpers

def _make_product(**overrides) -> Product:
    defaults = {
        "name": "Test Product",
        "sale_price": 1000,
        "cost_price": 600,
        "unit_type": UnitType.UNIT,
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

    def test_create_with_enum_unit_type(self, db):
        """Creating with UnitType enum should store the string value."""
        repo = ProductRepo(db)
        prod = _make_product(unit_type=UnitType.WEIGHT_KG, barcode="WT001")
        created = repo.create(prod)
        row = db.execute("SELECT unit_type FROM products WHERE id = ?", (created.id,)).fetchone()
        assert row["unit_type"] == "weight_kg"


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
        ghost = Product(id=99999, name="Ghost", sale_price=100, cost_price=50,
                        unit_type="unit")
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

    def test_unit_type_persists_as_string(self, db):
        repo = ProductRepo(db)
        prod = repo.create(_make_product(barcode="UT001", unit_type="unit"))
        prod.unit_type = UnitType.PACK
        repo.update(prod)
        row = db.execute("SELECT unit_type FROM products WHERE id = ?", (prod.id,)).fetchone()
        assert row["unit_type"] == "pack"


# ---------------------------------------------------------------- delete --

class TestDelete:
    def test_success(self, db):
        repo = ProductRepo(db)
        prod = repo.create(_make_product(barcode="DEL001"))
        repo.delete(prod.id)
        assert repo.find_by_barcode("DEL001") is None

    def test_with_sales_blocks(self, db, sample_products, open_register):
        repo = ProductRepo(db)
        # Create a sale that references a sample product
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

        with pytest.raises(DataError, match="historial"):
            repo.delete(product_id)

    def test_with_purchases_blocks(self, db, sample_products):
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

        with pytest.raises(DataError, match="historial"):
            repo.delete(product_id)

    def test_no_transactions_allows_delete(self, db, sample_products):
        repo = ProductRepo(db)
        # Product index 4 (Six-Pack) has no sales or purchases
        product_id = sample_products[4]
        repo.delete(product_id)
        assert db.execute("SELECT COUNT(*) AS cnt FROM products WHERE id = ?",
                          (product_id,)).fetchone()["cnt"] == 0


# --------------------------------------------------------------- upsert ---

class TestUpsertFromImport:
    def test_creates_new(self, db):
        repo = ProductRepo(db)
        prod = _make_product(barcode="IMP001", name="Imported Beer")
        result, action = repo.upsert_from_import(prod)
        assert action == "created"
        assert result.id is not None
        assert result.name == "Imported Beer"

    def test_updates_existing_preserves_name(self, db):
        repo = ProductRepo(db)
        # First, create with a specific name
        original = repo.create(_make_product(barcode="IMP002", name="Original Name",
                                             sale_price=500, cost_price=300,
                                             stock=5.0))
        # Now upsert with a different name — name should NOT change
        import_prod = _make_product(barcode="IMP002", name="Should Not Overwrite",
                                    sale_price=800, cost_price=500, stock=10.0, unit_type="weight_kg")
        result, action = repo.upsert_from_import(import_prod)
        assert action == "updated"
        assert result.id == original.id

        # Verify DB: name unchanged, other fields updated
        row = db.execute("SELECT * FROM products WHERE id = ?", (original.id,)).fetchone()
        assert row["name"] == "Original Name"   # preserved
        assert row["sale_price"] == 800          # updated
        assert row["cost_price"] == 500          # updated
        assert row["stock"] == 10.0              # updated
        assert row["unit_type"] == "weight_kg"   # updated

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
