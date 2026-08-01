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
    """Insert 5 test products and return their IDs.

    Products created:
        1. Coca-Cola 1.5L   → $800
        2. Fernet Branca    → $2500
        3. Queso Cremoso    → $9500/kg
        4. Maní             → $3000/kg (low stock: 3)
        5. Six-Pack Cerveza → $2000
    """
    bebidas, snacks = sample_category

    products = [
        ("7790895000782", "Coca-Cola 1.5L",    bebidas, 800,  500,  24),
        ("7790895000997", "Fernet Branca 750ml", bebidas, 2500, 1600, 12),
        ("7791234000100", "Queso Cremoso x Kg",  snacks,  9500, 6000, 5),
        ("7794321000200", "Maní Salado x Kg",    snacks,  3000, 1800, 3),
        ("7795555000300", "Six-Pack Cerveza IPA", bebidas, 2000, 1200, 8),
    ]

    ids: list[int] = []
    for barcode, name, cat_id, price, cost, stock in products:
        cur = db.execute(
            """INSERT INTO products
               (barcode, name, category_id, sale_price, cost_price, stock)
               VALUES (?, ?, ?, ?, ?, ?)
               RETURNING id""",
            (barcode, name, cat_id, price, cost, stock),
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


# ----------------------------------------------------- CLOSED REGISTER -----
@pytest.fixture
def closed_register(db: sqlite3.Connection) -> int:
    """Insert a closed cash register and return its ID.

    Initial amount: $5000, opening time: 2026-06-13 08:00:00, closing time: 2026-06-13 20:00:00.
    """
    cur = db.execute(
        """INSERT INTO cash_registers (opening_amount, opening_time, closing_amount, closing_time, status)
           VALUES (5000, '2026-06-13 08:00:00', 6000, '2026-06-13 20:00:00', 'closed')
           RETURNING id""",
    )
    reg_id = cur.fetchone()["id"]
    db.commit()
    return reg_id


# ------------------------------------------------------------- TKINTER ROOT ---
@pytest.fixture(scope="session")
def session_root():
    """Shared CTk root window for the entire test session.

    This prevents Tcl/Tk re-initialization resource errors on Windows.
    """
    import customtkinter as ctk
    r = ctk.CTk()
    r.withdraw()
    yield r
    r.destroy()
