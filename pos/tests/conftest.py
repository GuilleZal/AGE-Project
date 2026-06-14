"""Pytest fixtures — in-memory SQLite with full DDL and sample data.

All fixtures are **function-scoped** so every test starts with a fresh,
isolated database.
"""

import pytest
import sqlite3

from pos.model.database import DDL


# ------------------------------------------------------------------ DB ----
@pytest.fixture
def db() -> sqlite3.Connection:
    """In-memory SQLite connection with full schema (10 tables + indexes).

    Uses ``row_factory = sqlite3.Row`` for dict-like access. This fixture
    is function-scoped so each test starts from a clean database.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    yield conn
    conn.close()


# ------------------------------------------------------- SAMPLE CATEGORY --
@pytest.fixture
def sample_category(db: sqlite3.Connection) -> tuple[int, int]:
    """Insert two categories ('Bebidas', 'Snacks') and return their IDs."""
    cur = db.execute(
        "INSERT INTO categories (name) VALUES (?) RETURNING id", ("Bebidas",)
    )
    cat1 = cur.fetchone()["id"]
    cur = db.execute(
        "INSERT INTO categories (name) VALUES (?) RETURNING id", ("Snacks",)
    )
    cat2 = cur.fetchone()["id"]
    db.commit()
    return cat1, cat2


# ------------------------------------------------------ SAMPLE PRODUCTS ---
@pytest.fixture
def sample_products(db: sqlite3.Connection, sample_category: tuple[int, int]) -> list[int]:
    """Insert 5 test products (mix of unit/weight_kg/pack) and return their IDs.

    Products created:
        1. Coca-Cola 1.5L   → unit,     $800
        2. Fernet Branca    → unit,     $2500
        3. Queso Cremoso    → weight_kg, $9500/kg
        4. Maní             → weight_kg, $3000/kg (low stock: 0.3 kg)
        5. Six-Pack Cerveza → pack,     $2000
    """
    bebidas, snacks = sample_category

    products = [
        ("7790895000782", "Coca-Cola 1.5L",    bebidas, 800,  500,  24.0,   "unit"),
        ("7790895000997", "Fernet Branca 750ml", bebidas, 2500, 1600, 12.0,   "unit"),
        ("7791234000100", "Queso Cremoso x Kg",  snacks,  9500, 6000, 2.5,    "weight_kg"),
        ("7794321000200", "Maní Salado x Kg",    snacks,  3000, 1800, 0.3,    "weight_kg"),
        ("7795555000300", "Six-Pack Cerveza IPA", bebidas, 2000, 1200, 8.0,    "pack"),
    ]

    ids: list[int] = []
    for barcode, name, cat_id, price, cost, stock, unit_type in products:
        cur = db.execute(
            """INSERT INTO products
               (barcode, name, category_id, sale_price, cost_price, stock, unit_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               RETURNING id""",
            (barcode, name, cat_id, price, cost, stock, unit_type),
        )
        ids.append(cur.fetchone()["id"])

    db.commit()
    return ids


# ----------------------------------------------------- OPEN REGISTER -----
@pytest.fixture
def open_register(db: sqlite3.Connection) -> int:
    """Insert an open cash register and return its ID.

    Initial amount: $5000, opening time: 2026-06-13 08:00:00.
    """
    cur = db.execute(
        """INSERT INTO cash_registers (opening_amount, opening_time, status)
           VALUES (5000, '2026-06-13 08:00:00', 'open')
           RETURNING id""",
    )
    reg_id = cur.fetchone()["id"]
    db.commit()
    return reg_id
