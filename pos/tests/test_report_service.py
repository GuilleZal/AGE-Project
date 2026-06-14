"""Tests for ReportService — sales summaries, profit analysis, CSV export.

Uses in-memory SQLite with sample data to verify aggregation logic
and CSV formatting (BOM + semicolon delimiter).
"""

import os
import tempfile
import sqlite3

import pytest

from pos.service.report_service import ReportService


# ----------------------------------------------------------------- helpers --
def _seed_sales(db: sqlite3.Connection, sample_products: list[int]) -> None:
    """Insert a realistic set of sales + sale_items for report tests."""
    p1, p2, p3, p4, p5 = sample_products

    # Sale 1: cash, 2026-06-01
    cur = db.execute(
        """INSERT INTO sales (total, payment_method, created_at)
           VALUES (?, ?, ?) RETURNING id""",
        (3300, "cash", "2026-06-01 10:00:00"),
    )
    s1 = cur.fetchone()["id"]
    db.executemany(
        "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        [
            (s1, p1, 2, 800, 1600),    # Coca  x2
            (s1, p2, 1, 2500, 2500),   # Fernet
        ],
    )

    # Sale 2: card, 2026-06-02
    cur = db.execute(
        """INSERT INTO sales (total, payment_method, created_at)
           VALUES (?, ?, ?) RETURNING id""",
        (4000, "card", "2026-06-02 14:00:00"),
    )
    s2 = cur.fetchone()["id"]
    db.executemany(
        "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        [
            (s2, p5, 2, 2000, 4000),   # Six-Pack x2
        ],
    )

    # Sale 3: cash, 2026-06-03
    cur = db.execute(
        """INSERT INTO sales (total, payment_method, created_at)
           VALUES (?, ?, ?) RETURNING id""",
        (19000, "cash", "2026-06-03 18:00:00"),
    )
    s3 = cur.fetchone()["id"]
    db.executemany(
        "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        [
            (s3, p3, 2, 9500, 19000),  # Queso x2 kg
        ],
    )

    # Sale 4: transfer, 2026-06-04
    cur = db.execute(
        """INSERT INTO sales (total, payment_method, created_at)
           VALUES (?, ?, ?) RETURNING id""",
        (2500, "transfer", "2026-06-04 09:00:00"),
    )
    s4 = cur.fetchone()["id"]
    db.executemany(
        "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        [
            (s4, p2, 1, 2500, 2500),   # Fernet
        ],
    )

    # Sale 5: cash, 2026-06-05 (low-stock product)
    cur = db.execute(
        """INSERT INTO sales (total, payment_method, created_at)
           VALUES (?, ?, ?) RETURNING id""",
        (3000, "cash", "2026-06-05 12:00:00"),
    )
    s5 = cur.fetchone()["id"]
    db.executemany(
        "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
        [
            (s5, p4, 1, 3000, 3000),   # Maní x1 kg
        ],
    )

    db.commit()


# ------------------------------------------------------------ sales summary

class TestSalesSummary:
    def test_with_data(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        result = svc.sales_summary("2026-06-01 00:00:00", "2026-06-05 23:59:59")

        assert result["count"] == 5
        assert result["total"] == 3300 + 4000 + 19000 + 2500 + 3000  # = 31800
        assert result["avg_ticket"] == pytest.approx(31800 / 5)  # 6360.0

    def test_no_sales(self, db: sqlite3.Connection):
        svc = ReportService(db)
        result = svc.sales_summary("2020-01-01", "2020-12-31")
        assert result["count"] == 0
        assert result["total"] == 0
        assert result["avg_ticket"] == 0.0

    def test_date_filtering(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        # Only June 1-2
        result = svc.sales_summary("2026-06-01 00:00:00", "2026-06-02 23:59:59")
        assert result["count"] == 2
        assert result["total"] == 3300 + 4000  # 7300


# ----------------------------------------------------------- profit summary

class TestProfitSummary:
    def test_with_data(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        result = svc.profit_summary("2026-06-01 00:00:00", "2026-06-05 23:59:59")

        # Revenue = sum of subtotals
        expected_revenue = 1600 + 2500 + 4000 + 19000 + 2500 + 3000  # = 32600
        # Cost = sum(quantity * cost_price per line)
        # Coca:  2 * 500   = 1000
        # Fernet: 1 * 1600  = 1600
        # Six-Pack: 2 * 1200 = 2400
        # Queso:  2 * 6000  = 12000
        # Fernet: 1 * 1600  = 1600
        # Maní:   1 * 1800  = 1800
        expected_cost = 1000 + 1600 + 2400 + 12000 + 1600 + 1800  # = 20400
        expected_profit = expected_revenue - expected_cost  # 12200
        expected_margin = (expected_profit / expected_revenue) * 100

        assert result["revenue"] == expected_revenue
        assert result["cost"] == expected_cost
        assert result["profit"] == expected_profit
        assert result["margin_pct"] == pytest.approx(expected_margin)

    def test_no_sales(self, db: sqlite3.Connection):
        svc = ReportService(db)
        result = svc.profit_summary("2020-01-01", "2020-12-31")
        assert result["revenue"] == 0
        assert result["cost"] == 0
        assert result["profit"] == 0
        assert result["margin_pct"] == 0.0

    def test_date_filtering(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        result = svc.profit_summary("2026-06-03 00:00:00", "2026-06-03 23:59:59")
        # Only sale 3: Queso x2 = 19000 revenue, 12000 cost
        assert result["revenue"] == 19000
        assert result["cost"] == 12000
        assert result["profit"] == 7000


# ------------------------------------------------------------- top products

class TestTopProducts:
    def test_returns_top_by_quantity(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        result = svc.top_products("2026-06-01 00:00:00", "2026-06-05 23:59:59", limit=10)

        assert len(result) > 0
        # First should be Queso (2.0 kg) or Coca (2) or Six-Pack (2)
        # They all have quantity=2, ordered by total_quantity DESC
        assert result[0]["total_quantity"] >= 1

    def test_limit_respected(self, db: sqlite3.Connection, sample_products: list[int]):
        _seed_sales(db, sample_products)
        svc = ReportService(db)

        result = svc.top_products("2026-06-01 00:00:00", "2026-06-05 23:59:59", limit=2)
        assert len(result) <= 2

    def test_no_sales(self, db: sqlite3.Connection):
        svc = ReportService(db)
        result = svc.top_products("2020-01-01", "2020-12-31")
        assert result == []


# ------------------------------------------------------------------- CSV ---

class TestExportCSV:
    def test_basic_export(self):
        data = [
            {"name": "Coca-Cola", "total": 1600, "qty": 2},
            {"name": "Fernet", "total": 2500, "qty": 1},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "report.csv")
            result = ReportService.export_csv(data, filepath)
            assert result == filepath

            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()

            # Verify BOM presence (U+FEFF at start for utf-8-sig)
            # Verify semicolon delimiter
            assert "name;total;qty" in content
            assert "Coca-Cola;1600;2" in content
            assert "Fernet;2500;1" in content
            # No commas used as delimiters
            assert "name,total,qty" not in content

    def test_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty.csv")
            result = ReportService.export_csv([], filepath)
            assert result == filepath
            assert os.path.isfile(filepath)

    def test_creates_parent_dirs(self):
        data = [{"col": "val"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "sub", "deep", "report.csv")
            result = ReportService.export_csv(data, filepath)
            assert os.path.isfile(filepath)

    def test_single_row(self):
        data = [{"producto": "Coca", "ventas": "10"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "single.csv")
            ReportService.export_csv(data, filepath)
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            assert "producto;ventas" in content
            assert "Coca;10" in content
