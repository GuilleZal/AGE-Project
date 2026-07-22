"""Tests for CashRegisterController — open/close lifecycle and balance."""
import pytest
import sqlite3
from pos.controller.cash_register_controller import CashRegisterController


@pytest.fixture
def cash_ctrl(db: sqlite3.Connection) -> CashRegisterController:
    return CashRegisterController(db)


class TestOpenRegister:
    """Opening a cash register session."""

    def test_open_register(self, cash_ctrl):
        result = cash_ctrl.open_register(5000)
        assert result["success"] is True
        assert result["data"].opening_amount == 5000
        assert result["data"].status == "open"
        assert result["data"].id is not None

    def test_open_register_negative_amount_blocked(self, cash_ctrl):
        result = cash_ctrl.open_register(-100)
        assert result["success"] is False
        assert "negativo" in result["error"].lower()

    def test_second_open_blocked(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.open_register(3000)
        assert result["success"] is False
        assert "abierta" in result["error"].lower()

    def test_open_register_zero_amount(self, cash_ctrl):
        # Zero should be allowed (no initial cash)
        result = cash_ctrl.open_register(0)
        assert result["success"] is True


class TestCloseRegister:
    """Closing a cash register session."""

    def test_close_register(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(5200, "Cierre de turno")
        assert result["success"] is True
        data = result["data"]
        assert data["actual"] == 5200
        assert data["expected"] == 5000  # no movements yet
        assert data["diff"] == 200

    def test_close_no_open_register(self, cash_ctrl):
        result = cash_ctrl.close_register(5000, "test")
        assert result["success"] is False
        assert "abierta" in result["error"].lower()

    def test_close_empty_reason_allowed(self, cash_ctrl):
        """Close reason is now optional."""
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(5000, "   ")
        assert result["success"] is True

    def test_close_negative_amount_blocked(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.close_register(-100, "Cierre")
        assert result["success"] is False

    def test_close_with_movements(self, cash_ctrl, db):
        cash_ctrl.open_register(5000)

        # Simulate a sale movement
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount) VALUES (1, 'sale_cash', 3000)"
        )
        # Simulate an expense
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount) VALUES (1, 'expense', 500)"
        )
        db.commit()

        result = cash_ctrl.close_register(7500, "Turno completo")
        assert result["success"] is True
        assert result["data"]["expected"] == 7500  # 5000 + 3000 - 500
        assert result["data"]["diff"] == 0


class TestRegisterMovements:
    """Recording cash movements."""

    def test_register_sale(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.register_sale({"amount": 1500, "description": "Venta #1"})
        assert result["success"] is True
        assert result["data"].amount == 1500
        assert result["data"].type == "sale_cash"

    def test_register_sale_no_open_register(self, cash_ctrl):
        result = cash_ctrl.register_sale({"amount": 1000})
        assert result["success"] is False
        assert "caja" in result["error"].lower()

    def test_register_return(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.register_return({"amount": 500, "description": "Devolución"})
        assert result["success"] is True
        assert result["data"].type == "return"

    def test_register_outflow(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.register_outflow("expense", 200, "Compra de insumos")
        assert result["success"] is True
        assert result["data"].type == "expense"

    def test_register_outflow_no_open_register(self, cash_ctrl):
        result = cash_ctrl.register_outflow("expense", 500, "Insumos")
        assert result["success"] is False


class TestGetStatus:
    """Current register status and balance."""

    def test_status_no_open_register(self, cash_ctrl):
        result = cash_ctrl.get_register_status()
        assert result["success"] is True
        assert result["data"]["active"] is False
        assert result["data"]["register"] is None

    def test_status_with_open_register(self, cash_ctrl):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.get_register_status()
        assert result["success"] is True
        assert result["data"]["active"] is True
        assert result["data"]["register"]["opening_amount"] == 5000
        assert result["data"]["balance"]["opening"] == 5000
        assert result["data"]["balance"]["expected"] == 5000

    def test_status_after_movements(self, cash_ctrl, db):
        cash_ctrl.open_register(5000)
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount) VALUES (1, 'sale_cash', 2000)"
        )
        db.commit()

        result = cash_ctrl.get_register_status()
        assert result["data"]["balance"]["inflows"] == 2000
        assert result["data"]["balance"]["expected"] == 7000


class TestDailySummary:
    """Daily summary with movements."""

    def test_daily_summary_no_register(self, cash_ctrl):
        result = cash_ctrl.get_daily_summary()
        assert result["success"] is True
        assert result["data"]["active"] is False

    def test_daily_summary_with_movements(self, cash_ctrl, db):
        cash_ctrl.open_register(5000)
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (1, 'sale_cash', 1000, 'Venta')"
        )
        db.commit()

        result = cash_ctrl.get_daily_summary()
        assert result["success"] is True
        assert len(result["data"]["movements"]) == 1


class TestGetHistory:
    """Historical register sessions."""

    def test_get_history(self, cash_ctrl, db):
        cash_ctrl.open_register(5000)
        result = cash_ctrl.get_history()
        assert result["success"] is True
        assert len(result["data"]) == 1

    def test_get_history_empty(self, cash_ctrl):
        result = cash_ctrl.get_history()
        assert result["success"] is True
        assert len(result["data"]) == 0


class TestMovementDescriptionFormatting:
    """Session-based dynamic indexing of sales and returns, plus return quantities."""

    def test_movements_formatting_sales_and_returns(self, cash_ctrl, db):
        # 1. Setup sample products and active register
        db.execute(
            "INSERT INTO products (id, name, barcode, category_id, sale_price, cost_price, stock, unit_type) "
            "VALUES (10, 'Coca-Cola 1.5L', '123456', NULL, 200, 100, 10, 'Unidad')"
        )
        db.execute(
            "INSERT INTO products (id, name, barcode, category_id, sale_price, cost_price, stock, unit_type) "
            "VALUES (20, 'Queso Kg', '789101', NULL, 1000, 500, 10, 'Kg')"
        )
        cash_ctrl.open_register(5000)

        # 2. Insert sales movements (with global index numbers in desc)
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (1, 'sale_cash', 200, 'Venta #99')"
        )
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (1, 'sale_card', 200, 'Venta #100')"
        )

        # 3. Insert return records in returns table, and corresponding cash outflows
        db.execute(
            "INSERT INTO returns (id, product_id, quantity, refund_amount, cash_register_id, reason, created_at) "
            "VALUES (5, 10, 3.0, 600, 1, 'Vencido', '2026-07-22 18:00:00')"
        )
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (1, 'return', 600, 'Devolución #5 — Coca-Cola 1.5L')"
        )

        db.execute(
            "INSERT INTO returns (id, product_id, quantity, refund_amount, cash_register_id, reason, created_at) "
            "VALUES (6, 20, 1.5, 1500, 1, 'Mal estado', '2026-07-22 18:05:00')"
        )
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (1, 'return', 1500, 'Devolución #6 — Queso Kg')"
        )

        db.commit()

        # 4. Fetch summary & check formatted descriptions
        result = cash_ctrl.get_daily_summary()
        assert result["success"] is True
        movements = result["data"]["movements"]
        assert len(movements) == 4

        # Check Sales: should be numbered #1 and #2 (resetting index in session)
        assert movements[0]["description"] == "Venta #1"
        assert movements[1]["description"] == "Venta #2"

        # Check Returns: should be numbered #1 and #2, and display quantities
        assert movements[2]["description"] == "Devolución #1 — 3 u. Coca-Cola 1.5L"
        assert movements[3]["description"] == "Devolución #2 — 1.5 Kg Queso Kg"
