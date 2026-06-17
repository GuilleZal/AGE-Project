"""Tests for ReturnController — atomic return processing."""
import pytest
import sqlite3
from pos.controller.return_controller import ReturnController


@pytest.fixture
def return_ctrl(db: sqlite3.Connection) -> ReturnController:
    return ReturnController(db)


@pytest.fixture
def db_with_register(db: sqlite3.Connection, sample_products: list[int]) -> sqlite3.Connection:
    """Database with an open register."""
    db.execute(
        "INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, '2026-06-13 08:00:00', 'open')"
    )
    db.commit()
    return db


class TestProcessReturn:
    """Processing an atomic return."""

    def test_process_return(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[0]  # Coca-Cola, price=800
        result = return_ctrl.process_return(pid, 1)
        assert result["success"] is True
        assert result["data"]["refund_amount"] == 800
        assert result["data"]["return"]["product_name"] == "Coca-Cola 1.5L"

    def test_process_return_restores_stock(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[0]  # stock=24
        result = return_ctrl.process_return(pid, 2)
        assert result["success"] is True

        row = db_with_register.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()
        assert row["stock"] == 26.0  # 24 + 2

    def test_process_return_weight_product(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[2]  # Queso Cremoso, price=9500, stock=2.5
        result = return_ctrl.process_return(pid, 0.5)
        assert result["success"] is True
        assert result["data"]["refund_amount"] == 4750  # 9500 * 0.5

        row = db_with_register.execute("SELECT stock FROM products WHERE id = ?", (pid,)).fetchone()
        assert row["stock"] == 3.0  # 2.5 + 0.5

    def test_process_return_with_reason(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[0]
        result = return_ctrl.process_return(pid, 1, "Producto vencido")
        assert result["success"] is True
        assert result["data"]["return"]["reason"] == "Producto vencido"

    def test_process_return_zero_quantity_blocked(self, return_ctrl, db_with_register, sample_products):
        result = return_ctrl.process_return(sample_products[0], 0)
        assert result["success"] is False
        assert "cantidad" in result["error"].lower()

    def test_process_return_negative_quantity_blocked(self, return_ctrl, db_with_register, sample_products):
        result = return_ctrl.process_return(sample_products[0], -1)
        assert result["success"] is False

    def test_process_return_nonexistent_product(self, return_ctrl, db_with_register):
        result = return_ctrl.process_return(99999, 1)
        assert result["success"] is False
        assert "no encontrado" in result["error"].lower()

    def test_process_return_no_open_register(self, return_ctrl, sample_products):
        # No open register in the base db fixture
        result = return_ctrl.process_return(sample_products[0], 1)
        assert result["success"] is False
        assert "caja" in result["error"].lower()

    def test_process_return_records_cash_movement(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[0]
        return_ctrl.process_return(pid, 1)

        row = db_with_register.execute(
            "SELECT COUNT(*) as cnt FROM cash_movements WHERE type = 'return' AND amount = 800"
        ).fetchone()
        assert row["cnt"] == 1

    def test_process_return_creates_return_record(self, return_ctrl, db_with_register, sample_products):
        pid = sample_products[0]
        result = return_ctrl.process_return(pid, 3, "Roto")
        assert result["success"] is True

        row = db_with_register.execute(
            "SELECT COUNT(*) as cnt FROM returns WHERE product_id = ?", (pid,)
        ).fetchone()
        assert row["cnt"] == 1


class TestValidateReturnEligibility:
    """Checking if a product can be returned."""

    def test_product_exists(self, return_ctrl, sample_products):
        result = return_ctrl.validate_return_eligibility(sample_products[0])
        assert result["success"] is True
        assert result["data"]["eligible"] is True

    def test_product_not_found(self, return_ctrl):
        result = return_ctrl.validate_return_eligibility(99999)
        assert result["success"] is False


class TestCalculateRefund:
    """Refund amount calculation."""

    def test_calculate_refund_unit(self, return_ctrl, sample_products):
        pid = sample_products[0]  # 800
        result = return_ctrl.calculate_refund(pid, 3)
        assert result["success"] is True
        assert result["data"]["refund_amount"] == 2400

    def test_calculate_refund_weight(self, return_ctrl, sample_products):
        pid = sample_products[2]  # 9500/kg
        result = return_ctrl.calculate_refund(pid, 1.5)
        assert result["data"]["refund_amount"] == 14250  # 9500 * 1.5

    def test_calculate_refund_zero_blocked(self, return_ctrl, sample_products):
        result = return_ctrl.calculate_refund(sample_products[0], 0)
        assert result["success"] is False

    def test_calculate_refund_unknown_product(self, return_ctrl):
        result = return_ctrl.calculate_refund(99999, 1)
        assert result["success"] is False


class TestReturnHistory:
    """Return history retrieval."""

    def test_get_history(self, return_ctrl, db_with_register, sample_products):
        return_ctrl.process_return(sample_products[0], 1, "Test")
        result = return_ctrl.get_return_history()
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["product_name"] == "Coca-Cola 1.5L"

    def test_get_history_empty(self, return_ctrl):
        result = return_ctrl.get_return_history()
        assert result["success"] is True
        assert len(result["data"]) == 0

    def test_get_history_filtered_by_product(self, return_ctrl, db_with_register, sample_products):
        return_ctrl.process_return(sample_products[0], 1, "Test")
        return_ctrl.process_return(sample_products[1], 1, "Test2")

        result = return_ctrl.get_return_history(product_id=sample_products[0])
        assert len(result["data"]) == 1
        assert result["data"][0]["product_name"] == "Coca-Cola 1.5L"


class TestLookupProduct:
    """Lookup product by barcode for return processing."""

    def test_lookup_found(self, return_ctrl, sample_products):
        result = return_ctrl.lookup_product("7790895000782")  # Coca-Cola
        assert result["success"] is True
        assert result["data"]["id"] == sample_products[0]
        assert result["data"]["name"] == "Coca-Cola 1.5L"
        assert result["data"]["sale_price"] == 800

    def test_lookup_not_found(self, return_ctrl):
        result = return_ctrl.lookup_product("9999999999999")
        assert result["success"] is False
        assert result["error"] == "Producto no encontrado"

    def test_lookup_weight_product(self, return_ctrl, sample_products):
        result = return_ctrl.lookup_product("7791234000100")  # Queso
        assert result["success"] is True
