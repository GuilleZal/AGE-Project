"""End-to-end smoke tests for P1 critical flows.

Verifies the 5 P1 acceptance scenarios using the controller layer
with in-memory SQLite fixtures (conftest.py).  No Tkinter dependency —
pure logic verification.

Flows covered:
    Flow 1.1  — Complete sale (scan → cart → pay → receipt)
    Flow 1.1b — Weight-based products (kg input → price calc)
    Flow 1.1c — Quick product creation (unknown barcode → create → add)
    Flow 1.2  — Product return (lookup → qty → confirm → stock restored)
    Flow 1.3–5 — Cash register lifecycle (open → movements → close)
"""

import pytest
import sqlite3

from pos.controller.sale_controller import SaleController
from pos.controller.return_controller import ReturnController
from pos.controller.cash_register_controller import CashRegisterController


# ── Controller fixtures ───────────────────────────────────────────────

@pytest.fixture
def sale_ctrl(db: sqlite3.Connection) -> SaleController:
    return SaleController(db)


@pytest.fixture
def return_ctrl(db: sqlite3.Connection) -> ReturnController:
    return ReturnController(db)


@pytest.fixture
def cash_ctrl(db: sqlite3.Connection) -> CashRegisterController:
    return CashRegisterController(db)


@pytest.fixture
def db_open(db: sqlite3.Connection, sample_products: list[int]) -> sqlite3.Connection:
    """Database with sample products and an open cash register (initial=5000)."""
    db.execute(
        "INSERT INTO cash_registers (opening_amount, opening_time, status) "
        "VALUES (5000, '2026-06-13 08:00:00', 'open')"
    )
    db.commit()
    return db


# ═══════════════════════════════════════════════════════════════════════
# Flow 1.1 — Complete Sale
# ═══════════════════════════════════════════════════════════════════════

class TestE2ESaleFlow:
    """Flow 1.1: Scan → cart → pay → receipt (end-to-end)."""

    def test_sale_existing_product(self, sale_ctrl, db_open):
        """Scan a known barcode, complete cash sale, verify receipt data."""
        # Scan
        result = sale_ctrl.add_by_barcode("7790895000782")  # Coca-Cola 1.5L
        assert result["success"] is True
        assert result["data"]["name"] == "Coca-Cola 1.5L"
        assert result["data"]["quantity"] == 1.0
        assert result["data"]["unit_price"] == 800
        assert result["data"]["subtotal"] == 800

        # Complete sale — cash payment
        result = sale_ctrl.complete_sale("cash", 1000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 800
        assert result["data"]["sale"]["payment_method"] == "cash"
        assert result["data"]["change"] == 200

        # Cart must be empty after sale
        cart = sale_ctrl.get_cart()
        assert cart["data"]["items"] == []
        assert cart["data"]["total"] == 0

    def test_sale_multiple_items(self, sale_ctrl, db_open):
        """Scan 3 products, verify total calculation and change."""
        sale_ctrl.add_by_barcode("7790895000782")            # Coca-Cola          800
        sale_ctrl.add_by_barcode("7790895000997")            # Fernet            2500
        sale_ctrl.add_by_barcode("7795555000300", 2)         # Six-Pack × 2     4000
        #                                                        total           7300

        result = sale_ctrl.complete_sale("cash", 10000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 7300
        assert result["data"]["change"] == 2700

    def test_sale_card_payment(self, sale_ctrl, db_open):
        """Card payment — no change calculation, no received-amount validation."""
        sale_ctrl.add_by_barcode("7790895000997")  # Fernet 2500

        result = sale_ctrl.complete_sale("card", 0)
        assert result["success"] is True
        assert result["data"]["sale"]["payment_method"] == "card"
        assert result["data"]["change"] == 0

    def test_sale_transfer_payment(self, sale_ctrl, db_open):
        """Transfer payment — no change, same as card."""
        sale_ctrl.add_by_barcode("7790895000997")  # 2500
        result = sale_ctrl.complete_sale("transfer", 0)
        assert result["success"] is True
        assert result["data"]["sale"]["payment_method"] == "transfer"

    def test_sale_deducts_stock(self, sale_ctrl, db_open):
        """After sale, product stock is reduced by the sold quantity."""
        sale_ctrl.add_by_barcode("7790895000782")  # stock = 24
        sale_ctrl.complete_sale("cash", 1000)

        row = db_open.execute(
            "SELECT stock FROM products WHERE barcode = '7790895000782'"
        ).fetchone()
        assert row["stock"] == 23.0

    def test_sale_allows_negative_stock(self, sale_ctrl, db_open):
        """Stock goes negative when selling more than available (non-blocking policy)."""
        sale_ctrl.add_by_barcode("7794321000200", 5.0)  # Maní, stock = 3
        result = sale_ctrl.complete_sale("cash", 20000)
        assert result["success"] is True

        row = db_open.execute(
            "SELECT stock FROM products WHERE barcode = '7794321000200'"
        ).fetchone()
        assert row["stock"] == -2  # 3 − 5

    def test_sale_empty_cart_blocked(self, sale_ctrl, db_open):
        """Cannot complete a sale when the cart is empty."""
        result = sale_ctrl.complete_sale("cash", 100)
        assert result["success"] is False
        assert "vacío" in result["error"].lower()

    def test_sale_insufficient_cash_blocked(self, sale_ctrl, db_open):
        """Cash payment must cover the total — blocks if received < total."""
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        result = sale_ctrl.complete_sale("cash", 500)
        assert result["success"] is False
        assert "insuficiente" in result["error"].lower()

    def test_sale_no_open_register_blocked(self, sale_ctrl, db, sample_products):
        """Sale blocked when no cash register is open."""
        sale_ctrl.add_by_barcode("7790895000782")
        result = sale_ctrl.complete_sale("cash", 1000)
        assert result["success"] is False
        assert "caja" in result["error"].lower()

    def test_sale_invalid_payment_method(self, sale_ctrl, db_open):
        """Unknown payment methods are rejected."""
        sale_ctrl.add_by_barcode("7790895000782")
        result = sale_ctrl.complete_sale("bitcoin", 1000)
        assert result["success"] is False
        assert "no válido" in result["error"].lower()

    def test_sale_records_cash_movement(self, sale_ctrl, db_open):
        """Cash sale creates a 'sale_cash' movement in the active register."""
        sale_ctrl.add_by_barcode("7790895000782")  # 800
        sale_ctrl.complete_sale("cash", 1000)

        row = db_open.execute(
            "SELECT COUNT(*) as cnt FROM cash_movements "
            "WHERE type = 'sale_cash' AND amount = 800"
        ).fetchone()
        assert row["cnt"] == 1


# ═══════════════════════════════════════════════════════════════════════
# Flow 1.1b — Weight-Based Products
# ═══════════════════════════════════════════════════════════════════════

class TestE2EWeightProductFlow:
    """Flow 1.1 variant: weight_kg products (kg input → price calculation)."""

    def test_weight_product_add_by_qty(self, sale_ctrl, db_open):
        """Add weight product with explicit fractional quantity."""
        result = sale_ctrl.add_by_barcode("7791234000100", 0.750)  # Queso x Kg
        assert result["success"] is True
        assert result["data"]["name"] == "Queso Cremoso x Kg"
        assert result["data"]["quantity"] == 0.750
        assert result["data"]["subtotal"] == 7125  # 9500 × 0.75

    def test_weight_product_update_qty(self, sale_ctrl, db_open):
        """Update weight product quantity after initial add."""
        result = sale_ctrl.add_by_barcode("7791234000100")  # default qty = 1.0
        product_id = result["data"]["product_id"]

        result = sale_ctrl.update_item_quantity(product_id, 0.5)
        assert result["success"] is True
        assert result["data"]["quantity"] == 0.5
        assert result["data"]["subtotal"] == 4750  # 9500 × 0.5

    def test_weight_product_complete_sale(self, sale_ctrl, db_open):
        """Complete a sale containing a weight-based product."""
        sale_ctrl.add_by_barcode("7791234000100", 0.5)  # 9500 × 0.5 = 4750

        result = sale_ctrl.complete_sale("cash", 5000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 4750
        assert result["data"]["change"] == 250

    def test_weight_product_stock_deduction(self, sale_ctrl, db_open):
        """Weight product stock is reduced by the exact quantity sold."""
        sale_ctrl.add_by_barcode("7791234000100", 0.750)  # stock = 5 kg
        sale_ctrl.complete_sale("cash", 10000)

        row = db_open.execute(
            "SELECT stock FROM products WHERE barcode = '7791234000100'"
        ).fetchone()
        assert row["stock"] == 4  # int(5 − 0.75) = 4


# ═══════════════════════════════════════════════════════════════════════
# Flow 1.1c — Quick Product Creation
# ═══════════════════════════════════════════════════════════════════════

class TestE2EQuickCreateFlow:
    """Flow 1.1 variant: unknown barcode → create product → add to cart."""

    def test_unknown_barcode_returns_quick_create_hint(self, sale_ctrl, db_open):
        """Scanning an unknown barcode signals quick-create opportunity (not an error)."""
        result = sale_ctrl.add_by_barcode("9999999999999")
        assert result["success"] is False
        assert result["error"] is None  # not an error — quick-create flow
        assert result["data"]["barcode"] == "9999999999999"

    def test_quick_create_then_scan_adds_to_cart(self, sale_ctrl, db_open):
        """Create product for unknown barcode, then scanning it adds to cart."""
        # Unknown → quick-create
        sale_ctrl.add_by_barcode("9999999999999")
        result = sale_ctrl.create_quick_product(
            "9999999999999", "Producto Nuevo", 1200
        )
        assert result["success"] is True
        assert result["data"]["name"] == "Producto Nuevo"
        assert result["data"]["unit_price"] == 1200

        # Scan again → already in cart, qty increments
        result = sale_ctrl.add_by_barcode("9999999999999")
        assert result["success"] is True
        assert result["data"]["quantity"] == 2.0  # created (qty=1) + scanned (qty=1)

    def test_quick_create_then_complete_sale(self, sale_ctrl, db_open):
        """Quick-create a product and complete a sale with it."""
        sale_ctrl.add_by_barcode("8888888888888")
        sale_ctrl.create_quick_product("8888888888888", "Rápido", 500)
        sale_ctrl.add_by_barcode("8888888888888")  # now qty = 2

        result = sale_ctrl.complete_sale("cash", 2000)
        assert result["success"] is True
        assert result["data"]["sale"]["total"] == 1000  # 500 × 2

    def test_quick_create_negative_price_blocked(self, sale_ctrl, db_open):
        """Quick-create rejects negative prices."""
        result = sale_ctrl.create_quick_product("9999999999999", "Malo", -100)
        assert result["success"] is False
        assert "negativo" in result["error"].lower()

    def test_quick_create_empty_name_blocked(self, sale_ctrl, db_open):
        """Quick-create rejects blank names."""
        result = sale_ctrl.create_quick_product("9999999999999", "   ", 500)
        assert result["success"] is False
        assert "nombre" in result["error"].lower()

    def test_quick_create_persists_in_db(self, sale_ctrl, db_open):
        """Quick-created products are actually saved to the database."""
        sale_ctrl.create_quick_product("7777777777777", "Persistente", 999)

        row = db_open.execute(
            "SELECT * FROM products WHERE barcode = '7777777777777'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "Persistente"
        assert row["sale_price"] == 999


# ═══════════════════════════════════════════════════════════════════════
# Flow 1.2 — Product Return (Atomic)
# ═══════════════════════════════════════════════════════════════════════

class TestE2EReturnFlow:
    """Flow 1.2: Lookup → set qty → confirm → stock restored (end-to-end)."""

    def test_return_lookup_by_barcode(self, return_ctrl, sample_products):
        """Lookup product by barcode returns full product info."""
        result = return_ctrl.lookup_product("7790895000782")  # Coca-Cola
        assert result["success"] is True
        assert result["data"]["id"] == sample_products[0]
        assert result["data"]["name"] == "Coca-Cola 1.5L"
        assert result["data"]["sale_price"] == 800

    def test_return_lookup_not_found(self, return_ctrl):
        """Unknown barcode returns an error."""
        result = return_ctrl.lookup_product("9999999999999")
        assert result["success"] is False
        assert result["error"] == "Producto no encontrado"

    def test_return_process_with_reason(self, return_ctrl, db_open, sample_products):
        """Full return: lookup, process with reason, verify refund."""
        pid = sample_products[0]  # Coca-Cola, price = 800

        result = return_ctrl.process_return(pid, 2, "Producto vencido")
        assert result["success"] is True
        assert result["data"]["refund_amount"] == 1600  # 800 × 2
        assert result["data"]["return"]["reason"] == "Producto vencido"

    def test_return_restores_stock(self, return_ctrl, db_open, sample_products):
        """Returning a product increases its stock by the returned quantity."""
        pid = sample_products[0]  # stock = 24
        return_ctrl.process_return(pid, 3)

        row = db_open.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()
        assert row["stock"] == 27.0  # 24 + 3

    def test_return_weight_product(self, return_ctrl, db_open, sample_products):
        """Return a weight-based product with fractional quantity."""
        pid = sample_products[2]  # Queso Cremoso, price = 9500/kg, stock = 5

        result = return_ctrl.process_return(pid, 0.5)
        assert result["success"] is True
        assert result["data"]["refund_amount"] == 4750  # 9500 × 0.5

        row = db_open.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()
        assert row["stock"] == 5  # int(5 + 0.5) = 5

    def test_return_records_cash_movement(self, return_ctrl, db_open, sample_products):
        """Return creates a 'return' cash movement in the active register."""
        pid = sample_products[0]  # 800
        return_ctrl.process_return(pid, 1)

        row = db_open.execute(
            "SELECT COUNT(*) as cnt FROM cash_movements "
            "WHERE type = 'return' AND amount = 800"
        ).fetchone()
        assert row["cnt"] == 1

    def test_return_creates_return_record(self, return_ctrl, db_open, sample_products):
        """Return creates a row in the returns table."""
        pid = sample_products[0]
        return_ctrl.process_return(pid, 2, "Roto")

        row = db_open.execute(
            "SELECT COUNT(*) as cnt FROM returns WHERE product_id = ?", (pid,)
        ).fetchone()
        assert row["cnt"] == 1

    def test_return_no_open_register_blocked(self, return_ctrl, sample_products):
        """Return blocked when no cash register is open."""
        result = return_ctrl.process_return(sample_products[0], 1)
        assert result["success"] is False
        assert "caja" in result["error"].lower()

    def test_return_zero_quantity_blocked(self, return_ctrl, db_open, sample_products):
        """Quantity must be > 0."""
        result = return_ctrl.process_return(sample_products[0], 0)
        assert result["success"] is False
        assert "cantidad" in result["error"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Flow 1.3–1.5 — Cash Register Lifecycle
# ═══════════════════════════════════════════════════════════════════════

class TestE2ECashRegisterFlow:
    """Flow 1.3–1.5: Open → record movements → close with balance check."""

    def test_full_lifecycle(self, cash_ctrl):
        """Complete session: open, outflow, close — verify expected balance."""
        # 1.3 — Open
        result = cash_ctrl.open_register(5000)
        assert result["success"] is True
        register = result["data"]
        assert register.opening_amount == 5000
        assert register.status == "open"
        assert register.id is not None
        register_id = register.id

        # 1.4 — Register manual outflow
        result = cash_ctrl.register_outflow("expense", 500, "Compra de insumos")
        assert result["success"] is True
        assert result["data"].type == "expense"
        assert result["data"].amount == 500

        # 1.5 — Close with physical count matching expected
        result = cash_ctrl.close_register(4500, "Cierre del día")
        assert result["success"] is True
        assert result["data"]["expected"] == 4500   # 5000 − 500
        assert result["data"]["actual"] == 4500
        assert result["data"]["diff"] == 0

    def test_open_zero_amount(self, cash_ctrl):
        """Opening with zero is allowed (no initial cash)."""
        result = cash_ctrl.open_register(0)
        assert result["success"] is True
        assert result["data"].opening_amount == 0

    def test_open_negative_amount_blocked(self, cash_ctrl):
        """Negative opening amount is rejected."""
        result = cash_ctrl.open_register(-100)
        assert result["success"] is False
        assert "negativo" in result["error"].lower()

    def test_second_open_blocked(self, cash_ctrl):
        """Cannot open a second register while one is active."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.open_register(3000)
        assert result["success"] is False
        assert "abierta" in result["error"].lower()

    def test_close_with_surplus(self, cash_ctrl):
        """Close with more cash than expected (positive diff)."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(5200, "Sobrante")
        assert result["success"] is True
        assert result["data"]["expected"] == 5000
        assert result["data"]["actual"] == 5200
        assert result["data"]["diff"] == 200

    def test_close_with_deficit(self, cash_ctrl):
        """Close with less cash than expected (negative diff)."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(4800, "Faltante")
        assert result["success"] is True
        assert result["data"]["diff"] == -200

    def test_close_with_movements(self, cash_ctrl, db):
        """Expected balance accounts for sale inflows and outflows."""
        cash_ctrl.open_register(5000)

        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount) "
            "VALUES (1, 'sale_cash', 3000)"
        )
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount) "
            "VALUES (1, 'expense', 500)"
        )
        db.commit()

        result = cash_ctrl.close_register(7500, "Turno completo")
        assert result["success"] is True
        assert result["data"]["expected"] == 7500   # 5000 + 3000 − 500
        assert result["data"]["diff"] == 0

    def test_close_empty_reason_allowed(self, cash_ctrl):
        """Close reason is now optional."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(5000, "   ")
        assert result["success"] is True

    def test_close_negative_amount_blocked(self, cash_ctrl):
        """Closing with negative amount is rejected."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(-100, "Cierre inválido")
        assert result["success"] is False

    def test_close_no_open_register_blocked(self, cash_ctrl):
        """Cannot close when no register is open."""
        result = cash_ctrl.close_register(5000, "test")
        assert result["success"] is False
        assert "abierta" in result["error"].lower()

    def test_get_status_after_open(self, cash_ctrl):
        """Status reflects active register with correct opening balance."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.get_register_status()
        assert result["success"] is True
        assert result["data"]["active"] is True
        assert result["data"]["balance"]["opening"] == 5000
        assert result["data"]["balance"]["expected"] == 5000

    def test_get_history(self, cash_ctrl):
        """History lists all register sessions."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.get_history()
        assert result["success"] is True
        assert len(result["data"]) == 1


# ═══════════════════════════════════════════════════════════════════════
# Cross-Flow Integration
# ═══════════════════════════════════════════════════════════════════════

class TestE2ECrossFlow:
    """End-to-end flows that span multiple P1 capabilities."""

    def test_sale_then_return_nets_stock_to_original(
        self, sale_ctrl, return_ctrl, db_open, sample_products
    ):
        """Sell 1, return 1 → stock returns to original value."""
        pid = sample_products[0]  # Coca-Cola, stock = 24

        # Sale
        sale_ctrl.add_by_barcode("7790895000782")
        sale_ctrl.complete_sale("cash", 1000)
        row = db_open.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()
        assert row["stock"] == 23.0

        # Return
        return_ctrl.process_return(pid, 1)
        row = db_open.execute(
            "SELECT stock FROM products WHERE id = ?", (pid,)
        ).fetchone()
        assert row["stock"] == 24.0

    def test_sale_and_outflow_reflected_in_balance(
        self, sale_ctrl, cash_ctrl, db_open
    ):
        """Cash register balance reflects both sales and manual outflows."""
        # db_open already has register with opening = 5000

        # Complete a cash sale (800)
        sale_ctrl.add_by_barcode("7790895000782")
        sale_ctrl.complete_sale("cash", 1000)

        # Register a manual outflow (200)
        cash_ctrl.register_outflow("expense", 200, "Insumos")

        # Close and verify: 5000 + 800 − 200 = 5600
        result = cash_ctrl.close_register(5600, "Turno completo")
        assert result["success"] is True
        assert result["data"]["expected"] == 5600
        assert result["data"]["diff"] == 0
