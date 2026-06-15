"""SQLite connection manager with WAL journal mode and foreign-key enforcement.

Provides `get_connection()` (file-based for production) and `init_db(conn)`
to create the full 10-table schema plus strategic indexes.
"""

import os
import sqlite3

#: Path relative to the project root (pos/ is one level inside the repo).
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "pos.db")


def get_connection(*, db_path: str | None = None) -> sqlite3.Connection:
    """Return a file-based SQLite connection with WAL + FK pragmas.

    Args:
        db_path: Override path (used by tests for :memory: or temp files).

    Returns:
        A ``sqlite3.Connection`` ready for queries.
    """
    target = db_path if db_path is not None else DB_PATH

    os.makedirs(os.path.dirname(target), exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Execute full DDL (all 10 tables + indexes) inside *conn*.

    Idempotent — uses ``IF NOT EXISTS`` so it is safe to call on every
    application start.  Also runs any pending migrations for existing
    databases created with older schemas.
    """
    conn.executescript(DDL)
    _run_migrations(conn)


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for existing databases.

    Each migration checks if it's already been applied before making changes.
    Safe to call on every application start.
    """
    # Migration 1: Add sale_card and sale_transfer to cash_movements type constraint
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='cash_movements'"
    ).fetchone()
    if row and "sale_card" not in row["sql"]:
        conn.executescript("""
            CREATE TABLE cash_movements_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
                type            TEXT NOT NULL CHECK(type IN ('sale_cash','sale_card','sale_transfer','return','supplier_payment','expense')),
                amount          INTEGER NOT NULL,
                description     TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            INSERT INTO cash_movements_new SELECT * FROM cash_movements;

            DROP TABLE cash_movements;

            ALTER TABLE cash_movements_new RENAME TO cash_movements;

            CREATE INDEX idx_cash_movements_register ON cash_movements(cash_register_id);
            CREATE INDEX idx_cash_movements_type ON cash_movements(type);
            CREATE INDEX idx_cash_movements_date ON cash_movements(created_at);
        """)

    # Migration 2: Add settings table
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
    ).fetchone()
    if row is None:
        conn.executescript("""
            CREATE TABLE settings (
                key         TEXT PRIMARY KEY,
                value       TEXT NOT NULL,
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)


# ------------------------------------------------------------------ DDL ----
# NOTE: Currency fields (prices, amounts, totals) use INTEGER to represent
# whole ARS pesos — there are no cents in this domain. Stock and quantity
# fields use REAL to support weight_kg fractional values.

DDL = """
-- ============================================================ CATEGORIES
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================= PRODUCTS
CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode             TEXT UNIQUE,
    name                TEXT NOT NULL,
    category_id         INTEGER REFERENCES categories(id),
    sale_price          INTEGER NOT NULL,
    cost_price          INTEGER NOT NULL,
    stock               REAL NOT NULL DEFAULT 0,
    unit_type           TEXT NOT NULL CHECK(unit_type IN ('unit','weight_kg','pack')),
    description         TEXT,
    low_stock_threshold REAL DEFAULT 5,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_products_barcode  ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_name     ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);

-- ================================================================ SALES
CREATE TABLE IF NOT EXISTS sales (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    total           INTEGER NOT NULL,
    discount        INTEGER NOT NULL DEFAULT 0,
    payment_method  TEXT NOT NULL CHECK(payment_method IN ('cash','card','transfer')),
    cash_register_id INTEGER REFERENCES cash_registers(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sales_date    ON sales(created_at);
CREATE INDEX IF NOT EXISTS idx_sales_payment ON sales(payment_method);

-- ========================================================== SALE ITEMS
CREATE TABLE IF NOT EXISTS sale_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id     INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    REAL NOT NULL,
    unit_price  INTEGER NOT NULL,
    subtotal    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale    ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);

-- ========================================================= SUPPLIERS
CREATE TABLE IF NOT EXISTS suppliers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    cuit        TEXT,
    phone       TEXT,
    address     TEXT,
    email       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ========================================================= PURCHASES
CREATE TABLE IF NOT EXISTS purchases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id     INTEGER REFERENCES suppliers(id),
    total           INTEGER NOT NULL,
    purchase_date   TEXT NOT NULL,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_purchases_date     ON purchases(purchase_date);
CREATE INDEX IF NOT EXISTS idx_purchases_supplier ON purchases(supplier_id);

-- ==================================================== PURCHASE ITEMS
CREATE TABLE IF NOT EXISTS purchase_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id     INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    quantity        REAL NOT NULL,
    unit_cost       INTEGER NOT NULL,
    subtotal        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_purchase_items_purchase ON purchase_items(purchase_id);

-- ==================================================== CASH REGISTERS
CREATE TABLE IF NOT EXISTS cash_registers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_amount  INTEGER NOT NULL,
    opening_time    TEXT NOT NULL,
    closing_amount  INTEGER,
    closing_time    TEXT,
    expected_amount INTEGER,
    difference      INTEGER,
    close_reason    TEXT,
    status          TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed'))
);
CREATE INDEX IF NOT EXISTS idx_cash_registers_status ON cash_registers(status);
CREATE INDEX IF NOT EXISTS idx_cash_registers_time   ON cash_registers(opening_time);

-- ================================================== CASH MOVEMENTS
CREATE TABLE IF NOT EXISTS cash_movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    type            TEXT NOT NULL CHECK(type IN ('sale_cash','sale_card','sale_transfer','return','supplier_payment','expense')),
    amount          INTEGER NOT NULL,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cash_movements_register ON cash_movements(cash_register_id);
CREATE INDEX IF NOT EXISTS idx_cash_movements_type     ON cash_movements(type);
CREATE INDEX IF NOT EXISTS idx_cash_movements_date     ON cash_movements(created_at);

-- ========================================================== RETURNS
CREATE TABLE IF NOT EXISTS returns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id),
    quantity        REAL NOT NULL,
    refund_amount   INTEGER NOT NULL,
    reason          TEXT,
    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_returns_product      ON returns(product_id);
CREATE INDEX IF NOT EXISTS idx_returns_date         ON returns(created_at);
CREATE INDEX IF NOT EXISTS idx_returns_cash_register ON returns(cash_register_id);

-- ========================================================== SETTINGS
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
