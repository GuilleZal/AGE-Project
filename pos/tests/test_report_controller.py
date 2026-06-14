"""Tests for ReportController — report generation and CSV export."""
import pytest
import sqlite3
from pos.controller.report_controller import ReportController


@pytest.fixture
def report_ctrl(db: sqlite3.Connection) -> ReportController:
    return ReportController(db)


@pytest.fixture
def db_with_sales(db: sqlite3.Connection, sample_products: list[int]) -> sqlite3.Connection:
    """Database with sales data for report testing."""
    # Create a cash register and sales
    db.execute("INSERT INTO cash_registers (opening_amount, opening_time, status) VALUES (5000, '2026-06-13 08:00:00', 'open')")

    # Sale 1: Coca-Cola (800) + Fernet (2500)
    db.execute("INSERT INTO sales (id, total, payment_method, cash_register_id, created_at) VALUES (1, 3300, 'cash', 1, '2026-06-13 10:00:00')")
    db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (1, ?, 1, 800, 800)", (sample_products[0],))
    db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (1, ?, 1, 2500, 2500)", (sample_products[1],))

    # Sale 2: Coca-Cola x2 (1600)
    db.execute("INSERT INTO sales (id, total, payment_method, cash_register_id, created_at) VALUES (2, 1600, 'card', 1, '2026-06-13 11:00:00')")
    db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (2, ?, 2, 800, 1600)", (sample_products[0],))

    # Sale 3: Six-Pack (2000) — outside range
    db.execute("INSERT INTO sales (id, total, payment_method, cash_register_id, created_at) VALUES (3, 2000, 'transfer', 1, '2026-06-14 12:00:00')")
    db.execute("INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (3, ?, 1, 2000, 2000)", (sample_products[4],))

    db.commit()
    return db


class TestSalesReport:
    """Sales report generation."""

    def test_sales_report_with_data(self, report_ctrl, db_with_sales):
        result = report_ctrl.generate_sales_report("2026-06-13", "2026-06-13 23:59:59")
        assert result["success"] is True
        assert result["data"]["sales"]["count"] == 2
        assert result["data"]["sales"]["total"] == 4900  # 3300 + 1600

    def test_sales_report_no_data(self, report_ctrl, db_with_sales):
        result = report_ctrl.generate_sales_report("2025-01-01", "2025-01-02")
        assert result["success"] is True
        assert result["data"]["sales"]["count"] == 0
        assert result["data"]["sales"]["total"] == 0

    def test_sales_report_invalid_dates(self, report_ctrl):
        result = report_ctrl.generate_sales_report("2026-06-14", "2026-06-13")
        assert result["success"] is False
        assert "desde" in result["error"].lower()

    def test_sales_report_top_products(self, report_ctrl, db_with_sales):
        result = report_ctrl.generate_sales_report("2026-06-13", "2026-06-13 23:59:59")
        top = result["data"]["top_products"]
        # Coca-Cola should be top (3 units sold across 2 sales)
        assert len(top) > 0
        assert top[0]["name"] == "Coca-Cola 1.5L" or top[0]["total_quantity"] >= 3.0


class TestProfitReport:
    """Profit report generation."""

    def test_profit_report(self, report_ctrl, db_with_sales):
        result = report_ctrl.generate_profit_report("2026-06-13", "2026-06-13 23:59:59")
        assert result["success"] is True
        assert result["data"]["revenue"] >= 4900
        assert result["data"]["profit"] > 0  # Should have profit

    def test_profit_report_no_sales(self, report_ctrl):
        result = report_ctrl.generate_profit_report("2025-01-01", "2025-01-02")
        assert result["success"] is True
        assert result["data"]["revenue"] == 0
        assert result["data"]["profit"] == 0
        assert result["data"]["margin_pct"] == 0.0


class TestTopProducts:
    """Top products query."""

    def test_top_products(self, report_ctrl, db_with_sales):
        result = report_ctrl.get_top_products("2026-06-13", "2026-06-14")
        assert result["success"] is True
        assert len(result["data"]) <= 10

    def test_top_products_with_limit(self, report_ctrl, db_with_sales):
        result = report_ctrl.get_top_products("2026-06-13", "2026-06-14", limit=1)
        assert len(result["data"]) == 1

    def test_top_products_no_sales(self, report_ctrl):
        result = report_ctrl.get_top_products("2025-01-01", "2025-01-02")
        assert result["success"] is True
        assert len(result["data"]) == 0


class TestCsvExport:
    """CSV export functionality."""

    def test_export_csv(self, report_ctrl, tmp_path):
        data = [
            {"name": "Coca", "sales": 10, "revenue": 8000},
            {"name": "Fanta", "sales": 5, "revenue": 3000},
        ]
        path = tmp_path / "report.csv"
        result = report_ctrl.export_to_csv(data, str(path))
        assert result["success"] is True

        # Read back and verify
        content = path.read_text(encoding="utf-8-sig")
        assert "name;sales;revenue" in content
        assert "Coca;10;8000" in content

    def test_export_csv_empty(self, report_ctrl, tmp_path):
        path = tmp_path / "empty.csv"
        result = report_ctrl.export_to_csv([], str(path))
        assert result["success"] is True
        assert path.exists()

    def test_export_csv_creates_dirs(self, report_ctrl, tmp_path):
        path = tmp_path / "subdir" / "nested" / "report.csv"
        result = report_ctrl.export_to_csv([{"a": 1}], str(path))
        assert result["success"] is True
        assert path.exists()
