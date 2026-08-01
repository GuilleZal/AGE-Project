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

    # Migration 3: Add is_active column to products for soft delete
    row = conn.execute("PRAGMA table_info(products)").fetchall()
    columns = [col["name"] for col in row]
    if "is_active" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

    # Migration 4: DEPRECATED - We now support unit_type (Unidad/Kg).
    # This migration previously dropped unit_type. Disabled to prevent data loss.
    pass
    # (Migration 4 remainder removed to prevent data loss)

    # Migration 6: Add surcharge column to sales table
    row = conn.execute("PRAGMA table_info(sales)").fetchall()
    columns = [col["name"] for col in row]
    if "surcharge" not in columns:
        try:
            conn.execute("ALTER TABLE sales ADD COLUMN surcharge INTEGER NOT NULL DEFAULT 0")
            conn.commit()
        except Exception:
            pass

    # Migration 5: DEPRECATED - We now support REAL stock for Kg.
    # This migration previously forced stock to INTEGER. Disabled.
    pass

    # Migration 7: Add users and sessions tables for login system
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if row is None:
        conn.executescript("""
            CREATE TABLE users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT NOT NULL UNIQUE,
                password    TEXT NOT NULL,
                role        TEXT NOT NULL CHECK(role IN ('admin', 'gerente', 'cajero', 'inventario')),
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX idx_users_username ON users(username);
            CREATE INDEX idx_users_role ON users(role);

            CREATE TABLE sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                login_time      TEXT NOT NULL DEFAULT (datetime('now')),
                logout_time     TEXT
            );
            CREATE INDEX idx_sessions_user ON sessions(user_id);
            CREATE INDEX idx_sessions_active ON sessions(logout_time);
        """)

    # Migration 8: Add debit_card and credit_card to sales and cash_movements
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='sales'"
    ).fetchone()
    if row and "debit_card" not in row["sql"]:
        # Clean up any orphan temp tables from a previous failed run
        conn.execute("DROP TABLE IF EXISTS sales_new")
        conn.execute("DROP TABLE IF EXISTS cash_movements_new")
        conn.commit()

        conn.executescript("""
            PRAGMA foreign_keys=OFF;

            CREATE TABLE sales_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                total           INTEGER NOT NULL,
                discount        INTEGER NOT NULL DEFAULT 0,
                surcharge       INTEGER NOT NULL DEFAULT 0,
                payment_method  TEXT NOT NULL CHECK(payment_method IN ('cash','card','debit_card','credit_card','transfer')),
                cash_register_id INTEGER REFERENCES cash_registers(id),
                created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            INSERT INTO sales_new (id, total, discount, surcharge, payment_method, cash_register_id, created_at)
                SELECT id, total,
                    COALESCE(discount, 0),
                    COALESCE(surcharge, 0),
                    payment_method,
                    cash_register_id,
                    created_at
                FROM sales;
            DROP TABLE sales;
            ALTER TABLE sales_new RENAME TO sales;
            CREATE INDEX IF NOT EXISTS idx_sales_date    ON sales(created_at);
            CREATE INDEX IF NOT EXISTS idx_sales_payment ON sales(payment_method);

            CREATE TABLE cash_movements_new (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
                type            TEXT NOT NULL CHECK(type IN ('sale_cash','sale_card','sale_debit_card','sale_credit_card','sale_transfer','return','supplier_payment','expense')),
                amount          INTEGER NOT NULL,
                description     TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            INSERT INTO cash_movements_new SELECT * FROM cash_movements;
            DROP TABLE cash_movements;
            ALTER TABLE cash_movements_new RENAME TO cash_movements;
            CREATE INDEX IF NOT EXISTS idx_cash_movements_register ON cash_movements(cash_register_id);
            CREATE INDEX IF NOT EXISTS idx_cash_movements_type     ON cash_movements(type);
            CREATE INDEX IF NOT EXISTS idx_cash_movements_date     ON cash_movements(created_at);

            PRAGMA foreign_keys=ON;
        """)

    # Migration 9: Add unit_type to products for supporting Kg
    row = conn.execute("PRAGMA table_info(products)").fetchall()
    columns = [col["name"] for col in row]
    if "unit_type" not in columns:
        conn.execute("ALTER TABLE products ADD COLUMN unit_type TEXT NOT NULL DEFAULT 'Unidad' CHECK(unit_type IN ('Unidad', 'Kg'))")

    # Migration 10: Add user_id column to cash_registers table
    row = conn.execute("PRAGMA table_info(cash_registers)").fetchall()
    columns = [col["name"] for col in row]
    if "user_id" not in columns:
        try:
            conn.execute("ALTER TABLE cash_registers ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()
        except Exception:
            pass

    # Migration 11: Add closed_by_user_id column to cash_registers table
    if "closed_by_user_id" not in columns:
        try:
            conn.execute("ALTER TABLE cash_registers ADD COLUMN closed_by_user_id INTEGER REFERENCES users(id)")
            conn.commit()
        except Exception:
            pass

    # Migration 12: Add qr and sale_qr to sales and cash_movements check constraints
    row_sales = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='sales'"
    ).fetchone()
    if row_sales and "qr" not in row_sales["sql"]:
        try:
            conn.execute("DROP TABLE IF EXISTS sales_new")
            conn.execute("DROP TABLE IF EXISTS cash_movements_new")
            conn.commit()

            conn.executescript("""
                PRAGMA foreign_keys=OFF;

                CREATE TABLE sales_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    total           INTEGER NOT NULL,
                    discount        INTEGER NOT NULL DEFAULT 0,
                    surcharge       INTEGER NOT NULL DEFAULT 0,
                    payment_method  TEXT NOT NULL CHECK(payment_method IN ('cash','card','debit_card','credit_card','transfer','qr')),
                    cash_register_id INTEGER REFERENCES cash_registers(id),
                    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO sales_new (id, total, discount, surcharge, payment_method, cash_register_id, created_at)
                    SELECT id, total, discount, surcharge, payment_method, cash_register_id, created_at FROM sales;
                DROP TABLE sales;
                ALTER TABLE sales_new RENAME TO sales;
                CREATE INDEX IF NOT EXISTS idx_sales_date    ON sales(created_at);
                CREATE INDEX IF NOT EXISTS idx_sales_payment ON sales(payment_method);

                CREATE TABLE cash_movements_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
                    type            TEXT NOT NULL CHECK(type IN ('sale_cash','sale_card','sale_debit_card','sale_credit_card','sale_transfer','sale_qr','return','supplier_payment','expense')),
                    amount          INTEGER NOT NULL,
                    description     TEXT,
                    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO cash_movements_new SELECT * FROM cash_movements;
                DROP TABLE cash_movements;
                ALTER TABLE cash_movements_new RENAME TO cash_movements;
                CREATE INDEX IF NOT EXISTS idx_cash_movements_register ON cash_movements(cash_register_id);
                CREATE INDEX IF NOT EXISTS idx_cash_movements_type     ON cash_movements(type);
                CREATE INDEX IF NOT EXISTS idx_cash_movements_date     ON cash_movements(created_at);

                PRAGMA foreign_keys=ON;
            """)
            conn.commit()
        except Exception:
            pass



# ------------------------------------------------------------------ DDL ----
# NOTE: Currency fields (prices, amounts, totals) use INTEGER to represent
# whole ARS pesos — there are no cents in this domain. Stock uses INTEGER
# (all products operate by unit). Quantity fields in sale_items use REAL to
# support weight_kg fractional values.

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
    stock               REAL NOT NULL DEFAULT 0.0,
    unit_type           TEXT NOT NULL DEFAULT 'Unidad' CHECK(unit_type IN ('Unidad', 'Kg')),
    description         TEXT,
    low_stock_threshold INTEGER DEFAULT 5,
    is_active           INTEGER NOT NULL DEFAULT 1,
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
    surcharge       INTEGER NOT NULL DEFAULT 0,
    payment_method  TEXT NOT NULL CHECK(payment_method IN ('cash','card','debit_card','credit_card','transfer','qr')),
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
    status          TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
    user_id         INTEGER REFERENCES users(id),
    closed_by_user_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_cash_registers_status ON cash_registers(status);
CREATE INDEX IF NOT EXISTS idx_cash_registers_time   ON cash_registers(opening_time);

-- ================================================== CASH MOVEMENTS
CREATE TABLE IF NOT EXISTS cash_movements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    type            TEXT NOT NULL CHECK(type IN ('sale_cash','sale_card','sale_debit_card','sale_credit_card','sale_transfer','sale_qr','return','supplier_payment','expense')),
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

-- ============================================================ USERS
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('admin', 'gerente', 'cajero', 'inventario')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ========================================================== SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    login_time      TEXT NOT NULL DEFAULT (datetime('now')),
    logout_time     TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(logout_time);
"""
