"""Tests for CashRegisterRepo + CashMovementRepo — lifecycle and balance."""

import pytest

from pos.model.cash_register import CashMovement
from pos.model.enums import MovementType
from pos.model.exceptions import DataError
from pos.repository.cash_register_repo import CashRegisterRepo
from pos.repository.cash_movement_repo import CashMovementRepo


# ============================================================================
# CashRegisterRepo tests
# ============================================================================

class TestOpenRegister:
    def test_success(self, db):
        repo = CashRegisterRepo(db)
        reg = repo.open_register(10000)
        assert reg.id is not None
        assert reg.opening_amount == 10000
        assert reg.status == "open"
        assert reg.opening_time is not None

        # Verify in DB
        row = db.execute("SELECT * FROM cash_registers WHERE id = ?", (reg.id,)).fetchone()
        assert row["status"] == "open"
        assert row["opening_amount"] == 10000

    def test_multiple_opens_allowed_at_repo_level(self, db):
        """Repo does NOT enforce single-active — that's the service layer's job."""
        repo = CashRegisterRepo(db)
        r1 = repo.open_register(5000)
        r2 = repo.open_register(3000)
        assert r1.id != r2.id
        assert r1.status == "open"
        assert r2.status == "open"


class TestFindActive:
    def test_returns_open(self, db):
        repo = CashRegisterRepo(db)
        reg = repo.open_register(5000)
        active = repo.find_active()
        assert active is not None
        assert active.id == reg.id
        assert active.status == "open"

    def test_returns_none_when_none_open(self, db):
        repo = CashRegisterRepo(db)
        # Open then close
        reg = repo.open_register(5000)
        repo.close_register(reg.id, closing_amount=5000, difference=0, reason="Cierre normal")
        db.commit()

        assert repo.find_active() is None

    def test_returns_latest_when_multiple_open(self, db):
        """If multiple open registers exist (shouldn't happen, but...), return latest."""
        repo = CashRegisterRepo(db)
        repo.open_register(1000)
        later = repo.open_register(2000)
        active = repo.find_active()
        assert active is not None
        assert active.id == later.id


class TestCloseRegister:
    def test_success(self, db):
        repo = CashRegisterRepo(db)
        reg = repo.open_register(10000)
        closed = repo.close_register(
            reg.id, closing_amount=15000, difference=500, reason="Sobrante"
        )
        assert closed.status == "closed"
        assert closed.closing_amount == 15000
        assert closed.difference == 500
        assert closed.close_reason == "Sobrante"
        assert closed.closing_time is not None
        assert closed.expected_amount == 14500  # 15000 - 500

    def test_not_found(self, db):
        repo = CashRegisterRepo(db)
        with pytest.raises(DataError, match="no encontrada"):
            repo.close_register(99999, 1000, 0, "Test")

    def test_negative_difference(self, db):
        """Difference can be negative (missing cash)."""
        repo = CashRegisterRepo(db)
        reg = repo.open_register(10000)
        closed = repo.close_register(
            reg.id, closing_amount=9000, difference=-1000, reason="Faltante"
        )
        assert closed.difference == -1000
        assert closed.expected_amount == 10000  # 9000 - (-1000) = 10000

    def test_close_by_different_user(self, db):
        repo = CashRegisterRepo(db)
        
        # Seed two users
        db.execute("INSERT INTO users (id, username, password, role) VALUES (10, 'cajero_a', 'pass', 'cajero')")
        db.execute("INSERT INTO users (id, username, password, role) VALUES (11, 'cajero_b', 'pass', 'cajero')")
        db.commit()

        reg = repo.open_register(10000, user_id=10)
        closed = repo.close_register(
            reg.id, closing_amount=15000, difference=500, reason="Sobrante", closed_by_user_id=11
        )
        assert closed.status == "closed"
        assert closed.user_id == 10
        assert closed.closed_by_user_id == 11
        assert closed.username == "cajero_a"
        assert closed.closed_by_username == "cajero_b"


class TestGetBalance:
    def test_opening_only(self, db):
        repo = CashRegisterRepo(db)
        reg = repo.open_register(5000)
        balance = repo.get_balance(reg.id)
        assert balance["opening"] == 5000
        assert balance["inflows"] == 0
        assert balance["outflows"] == 0
        assert balance["expected"] == 5000

    def test_with_movements(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(10000)
        # Inflow: sale_cash, sale_debit_card, sale_credit_card, sale_qr
        mov_repo.create(reg.id, MovementType.SALE_CASH, 3000, "Venta")
        mov_repo.create(reg.id, MovementType.SALE_DEBIT_CARD, 2000, "Venta tarjeta debito")
        mov_repo.create(reg.id, MovementType.SALE_CREDIT_CARD, 1000, "Venta tarjeta credito")
        mov_repo.create(reg.id, MovementType.SALE_QR, 1500, "Venta qr")
        # Outflow: return
        mov_repo.create(reg.id, MovementType.RETURN, 500, "Devolución")
        # Outflow: expense
        mov_repo.create(reg.id, MovementType.EXPENSE, 200, "Gasto")
        db.commit()

        balance = reg_repo.get_balance(reg.id)
        assert balance["opening"] == 10000
        assert balance["inflows"] == 7500    # 3000 + 2000 + 1000 + 1500
        assert balance["outflows"] == 700    # 500 + 200
        assert balance["expected"] == 16800  # 10000 + 7500 - 700
        
        # New breakdown assertions
        assert balance["inflow_cash"] == 3000
        assert balance["inflow_transfer"] == 0
        assert balance["inflow_qr"] == 1500
        assert balance["inflow_debit"] == 2000
        assert balance["inflow_credit"] == 1000
        assert balance["outflow_supplier"] == 0
        assert balance["outflow_expense"] == 700
        assert balance["outflow_total"] == 700
        assert balance["expected_cash"] == 12300  # 10000 + 3000 - 700

    def test_not_found(self, db):
        repo = CashRegisterRepo(db)
        with pytest.raises(DataError, match="no encontrada"):
            repo.get_balance(99999)


class TestGetHistory:
    def test_returns_all(self, db):
        repo = CashRegisterRepo(db)
        r1 = repo.open_register(1000)
        repo.close_register(r1.id, 1000, 0, "ok")
        r2 = repo.open_register(2000)
        db.commit()

        history = repo.get_history()
        assert len(history) == 2
        # Most recent first
        assert history[0].id == r2.id


# ============================================================================
# CashMovementRepo tests
# ============================================================================

class TestCreateMovement:
    def test_success(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        mov = mov_repo.create(reg.id, "sale_cash", 1500, "Venta efectivo")
        assert mov.id is not None
        assert mov.amount == 1500
        assert mov.type == "sale_cash"
        assert mov.created_at is not None

        row = db.execute("SELECT * FROM cash_movements WHERE id = ?", (mov.id,)).fetchone()
        assert row["description"] == "Venta efectivo"

    def test_with_enum_type(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        mov = mov_repo.create(reg.id, MovementType.EXPENSE, 300, "Limpieza")
        assert mov.type == "expense"

    def test_no_description(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        mov = mov_repo.create(reg.id, "sale_cash", 1000)
        assert mov.description is None


class TestSumByType:
    def test_sums_correctly(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        mov_repo.create(reg.id, "sale_cash", 1000)
        mov_repo.create(reg.id, "sale_cash", 2000)
        mov_repo.create(reg.id, "sale_cash", 500)
        mov_repo.create(reg.id, "expense", 100)
        db.commit()

        assert mov_repo.sum_by_type(reg.id, "sale_cash") == 3500
        assert mov_repo.sum_by_type(reg.id, "expense") == 100
        assert mov_repo.sum_by_type(reg.id, "return") == 0

    def test_no_movements(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        assert mov_repo.sum_by_type(reg.id, "sale_cash") == 0


class TestGetByRegister:
    def test_returns_ordered(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        m1 = mov_repo.create(reg.id, "sale_cash", 1000)
        m2 = mov_repo.create(reg.id, "expense", 200)
        m3 = mov_repo.create(reg.id, "sale_cash", 3000)
        db.commit()

        movements = mov_repo.get_by_register(reg.id)
        assert len(movements) == 3
        assert [m.id for m in movements] == [m1.id, m2.id, m3.id]

    def test_empty(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)

        reg = reg_repo.open_register(5000)
        assert mov_repo.get_by_register(reg.id) == []


class TestMovementTypes:
    def test_all_types_accepted(self, db):
        reg_repo = CashRegisterRepo(db)
        mov_repo = CashMovementRepo(db)
        reg = reg_repo.open_register(5000)

        for mt in ("sale_cash", "return", "supplier_payment", "expense"):
            mov = mov_repo.create(reg.id, mt, 100)
            assert mov.type == mt

    def test_invalid_type_rejected_by_db(self, db):
        import sqlite3
        reg_repo = CashRegisterRepo(db)
        reg = reg_repo.open_register(5000)

        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO cash_movements (cash_register_id, type, amount) VALUES (?, 'invalid_type', 100)",
                (reg.id,),
            )


class TestGetSoldProducts:
    def test_returns_correct_products(self, db, open_register):
        repo = CashRegisterRepo(db)
        
        # Insert products
        db.execute("INSERT INTO products (id, name, sale_price, cost_price, stock, unit_type) VALUES (101, 'Prod A', 100, 50, 10, 'Unidad')")
        db.execute("INSERT INTO products (id, name, sale_price, cost_price, stock, unit_type) VALUES (102, 'Prod B', 200, 100, 15, 'Kg')")
        
        # Insert sales and items associated with this register
        db.execute("INSERT INTO sales (id, total, payment_method, cash_register_id) VALUES (201, 500, 'cash', ?)", (open_register,))
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (201, 101, 3, 100, 300)")
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (201, 102, 1.0, 200, 200)")
        
        db.execute("INSERT INTO sales (id, total, payment_method, cash_register_id) VALUES (202, 300, 'card', ?)", (open_register,))
        db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (202, 101, 3, 100, 300)")
        
        # Insert a return associated with this register
        db.execute("INSERT INTO returns (product_id, quantity, refund_amount, reason, cash_register_id) VALUES (101, 1, 100, 'vencido', ?)", (open_register,))
        
        # Insert a supplier payment cash movement
        db.execute(
            "INSERT INTO cash_movements (cash_register_id, type, amount, description) VALUES (?, 'supplier_payment', 150, 'Pago a Supplier X')",
            (open_register,)
        )
        db.commit()
        
        res = repo.get_sold_products(open_register)
        assert res["opening_time"] != ""
        products = res["products"]
        assert len(products) == 5
        
        assert products[0]["sale_num"] == "Venta #1"
        assert products[0]["name"] == "Prod A"
        assert products[0]["quantity"] == 3
        assert products[0]["unit_price"] == 100
        assert products[0]["subtotal"] == 300
        assert products[0]["payment_method"] == "cash"
        assert products[0]["cost_price"] == 50
        
        assert products[1]["sale_num"] == "Venta #1"
        assert products[1]["name"] == "Prod B"
        assert products[1]["quantity"] == 1.0
        assert products[1]["unit_price"] == 200
        assert products[1]["subtotal"] == 200
        assert products[1]["cost_price"] == 100
        
        assert products[2]["sale_num"] == "Venta #2"
        assert products[2]["name"] == "Prod A"
        assert products[2]["quantity"] == 3
        assert products[2]["unit_price"] == 100
        assert products[2]["subtotal"] == 300
        assert products[2]["payment_method"] == "card"
        assert products[2]["cost_price"] == 50

        # The return is sorted chronologically
        assert products[3]["sale_num"] == "Devolución"
        assert products[3]["name"] == "Prod A"
        assert products[3]["quantity"] == -1
        assert products[3]["subtotal"] == -100
        assert products[3]["payment_method"] == "-"
        assert products[3]["cost_price"] == 50

        # The supplier payment is sorted chronologically at the end
        assert products[4]["sale_num"] == "Pago Proveedor"
        assert products[4]["name"] == "Pago a Supplier X"
        assert products[4]["quantity"] == 0.0
        assert products[4]["unit_price"] == 0
        assert products[4]["subtotal"] == -150
        assert products[4]["payment_method"] == "cash"
        assert products[4]["cost_price"] == 0
