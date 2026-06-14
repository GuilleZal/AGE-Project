"""Smoke tests for Batch 1 fixtures — verifies conftest works end-to-end."""


def test_db_tables_exist(db):
    """All 10 tables should be present in the in-memory database."""
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {t["name"] for t in tables}
    expected = {
        "categories", "products", "sales", "sale_items",
        "cash_registers", "cash_movements", "returns",
        "suppliers", "purchases", "purchase_items",
    }
    assert expected.issubset(names), f"Missing tables: {expected - names}"


def test_sample_products_count(sample_products, db):
    """sample_products fixture inserts exactly 5 products."""
    assert len(sample_products) == 5
    count = db.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()["cnt"]
    assert count == 5


def test_sample_products_unit_types(db, sample_products):
    """Products include a mix of unit, weight_kg, and pack types."""
    rows = db.execute("SELECT DISTINCT unit_type FROM products").fetchall()
    types = {r["unit_type"] for r in rows}
    assert types == {"unit", "weight_kg", "pack"}


def test_sample_category_count(sample_category, db):
    """sample_category fixture inserts exactly 2 categories."""
    cat1, cat2 = sample_category
    assert cat1 != cat2
    count = db.execute("SELECT COUNT(*) AS cnt FROM categories").fetchone()["cnt"]
    assert count == 2


def test_open_register_status(open_register, db):
    """open_register fixture is indeed open with correct data."""
    reg = db.execute(
        "SELECT * FROM cash_registers WHERE id = ?", (open_register,)
    ).fetchone()
    assert reg is not None
    assert reg["status"] == "open"
    assert reg["opening_amount"] == 5000


def test_fixture_isolation_1(db, sample_products):
    """Each test should start with exactly 5 products (no leftovers)."""
    count = db.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()["cnt"]
    assert count == 5


def test_fixture_isolation_2(db):
    """This test has no sample_products — DB should be empty."""
    count = db.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()["cnt"]
    assert count == 0
