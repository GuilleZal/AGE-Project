"""Report service — sales summaries, profit analysis, and CSV export.

Performance target: <3s for 10k sales (verified via date indexes on
``sales.created_at`` and ``sale_items`` join columns).
"""

import csv
import os
import sqlite3

from pos.repository.product_repo import ProductRepo
from pos.repository.sale_repo import SaleRepo


class ReportService:
    """Aggregation logic for sales and profit reports.

    Wraps ``SaleRepo`` for data access. All summary methods return dicts
    with type-hinted keys for easy consumption by controllers and views.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._sale_repo = SaleRepo(db)
        self._product_repo = ProductRepo(db)

    # -------------------------------------------------------- sales summary

    def sales_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, int | float]:
        """Return total revenue, sale count and average ticket.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            Dict with keys ``total`` (int), ``count`` (int), ``avg_ticket`` (float).
            Division-by-zero safe: ``avg_ticket`` is 0.0 when ``count`` is 0.
        """
        row = self._db.execute(
            """SELECT COALESCE(SUM(total), 0) AS total,
                       COUNT(*)              AS count
               FROM sales
               WHERE created_at >= ? AND created_at <= ?""",
            (start_date, end_date),
        ).fetchone()

        total = row["total"] or 0
        count = row["count"] or 0
        avg_ticket = (total / count) if count > 0 else 0.0
        return {"total": total, "count": count, "avg_ticket": avg_ticket}

    # ------------------------------------------------------- profit summary

    def profit_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, int | float]:
        """Return revenue, cost, profit and margin percentage.

        Revenue = sum(sale_items.subtotal)
        Cost    = sum(sale_items.quantity × product.cost_price)
        Profit  = revenue − cost
        Margin% = (profit / revenue) × 100 (0 when revenue ≤ 0)

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            Dict with keys ``revenue``, ``cost``, ``profit``, ``margin_pct``.
        """
        row = self._db.execute(
            """SELECT COALESCE(SUM(si.subtotal), 0)       AS revenue,
                      COALESCE(SUM(si.quantity * p.cost_price), 0) AS cost
               FROM sale_items si
               JOIN products p ON p.id = si.product_id
               JOIN sales    s ON s.id = si.sale_id
                WHERE s.created_at >= ? AND s.created_at <= ?""",
            (start_date, end_date),
        ).fetchone()

        revenue = row["revenue"] or 0
        cost = row["cost"] or 0
        profit = revenue - cost
        margin_pct = (profit / revenue * 100) if revenue > 0 else 0.0
        return {
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "margin_pct": margin_pct,
        }

    # --------------------------------------------------------- top products

    def top_products(
        self, start_date: str, end_date: str, limit: int = 10
    ) -> list[dict]:
        """Return the top *N* products sold in the period.

        Delegates to ``SaleRepo.top_products`` which provides
        ``product_id``, ``name``, ``barcode``, ``total_quantity``,
        ``total_amount``.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).
            limit:      Max number of products to return (default 10).

        Returns:
            List of product summary dicts sorted by total_quantity DESC.
        """
        return self._sale_repo.top_products(start_date, end_date, limit)

    # ------------------------------------------------------- low stock ----

    def low_stock_products(self) -> list[dict]:
        """Return all products whose current stock is at or below their
        ``low_stock_threshold``.

        Delegates to ``ProductRepo.low_stock_products``.

        Returns:
            List of dicts with product fields, ordered by stock ascending.
        """
        return self._product_repo.low_stock_products()

    # ---------------------------------------------- payment methods summary

    _PAYMENT_METHOD_LABELS: dict[str, str] = {
        "cash": "Efectivo",
        "card": "Tarjeta",
        "debit_card": "Tarjeta de Débito",
        "credit_card": "Tarjeta de Crédito",
        "transfer": "Transferencia",
    }

    def payment_methods_summary(
        self, start_date: str, end_date: str
    ) -> list[dict]:
        """Return revenue breakdown by payment method for the given period.

        Each entry includes the absolute total, operations count and its percentage
        of total revenue.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            List of dicts with keys ``payment_method`` (str),
            ``sale_count`` (int), ``total_amount`` (int), ``percentage`` (float).
            Sorted by ``total_amount`` DESC.
        """
        raw = self._sale_repo.total_by_payment_method(start_date, end_date)
        grand_total = sum(item["total_amount"] for item in raw)

        result: list[dict] = []
        for item in raw:
            method = item["payment_method"]
            total_amount = item["total_amount"]
            sale_count = item.get("sale_count", 0)
            percentage = (
                round((total_amount / grand_total) * 100, 1)
                if grand_total > 0
                else 0.0
            )
            result.append(
                {
                    "payment_method": self._PAYMENT_METHOD_LABELS.get(
                        method, method
                    ),
                    "sale_count": sale_count,
                    "total_amount": total_amount,
                    "percentage": percentage,
                }
            )

        result.sort(key=lambda x: x["total_amount"], reverse=True)
        return result

    # ---------------------------------------------------- sales by category

    def sales_by_category(
        self, start_date: str, end_date: str
    ) -> list[dict]:
        """Return sales aggregate by product category for the given period.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            List of dicts with keys: ``category_name``, ``qty_kg``, ``qty_unit``,
            ``total_amount``.
        """
        rows = self._db.execute(
            """SELECT COALESCE(c.name, 'Sin categoría') AS category_name,
                       SUM(CASE WHEN p.unit_type = 'Kg' THEN si.quantity ELSE 0 END) AS qty_kg,
                       SUM(CASE WHEN p.unit_type = 'Unidad' THEN si.quantity ELSE 0 END) AS qty_unit,
                       SUM(si.subtotal) AS total_amount
                FROM sale_items si
                JOIN products p ON p.id = si.product_id
                LEFT JOIN categories c ON c.id = p.category_id
                JOIN sales s ON s.id = si.sale_id
                WHERE s.created_at >= ? AND s.created_at <= ?
                GROUP BY p.category_id
                ORDER BY total_amount DESC""",
            (start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------ returns history

    def returns_history(
        self, start_date: str, end_date: str
    ) -> list[dict]:
        """Return returns history for the given period with product details.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            List of dicts with keys: ``created_at``, ``product_name``,
            ``quantity``, ``refund_amount``, ``reason``.
        """
        rows = self._db.execute(
            """SELECT r.created_at,
                       p.name AS product_name,
                       r.quantity,
                       r.refund_amount,
                       r.reason
                FROM returns r
                JOIN products p ON p.id = r.product_id
                WHERE r.created_at >= ? AND r.created_at <= ?
                ORDER BY r.created_at DESC""",
            (start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------- purchases summary ----

    def purchases_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, int]:
        """Return total purchase spend for the given period.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            Dict with key ``total`` (int).
        """
        row = self._db.execute(
            """SELECT COALESCE(SUM(total), 0) AS total
               FROM purchases
               WHERE purchase_date >= ? AND purchase_date <= ?""",
            (start_date, end_date),
        ).fetchone()
        return {"total": row["total"] or 0}

    # ------------------------------------------------- expenses summary ---

    def expenses_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, int]:
        """Return expense components for the given period.

        Components (from cash_movements table):
            * purchases — total of 'supplier_payment' movements (Pago a Proveedor).
            * shrinkage — kept for compatibility (always 0, no source yet).
            * operating_expenses — total of 'expense' movements (Gastos).

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).

        Returns:
            Dict with keys ``purchases``, ``shrinkage``,
            ``operating_expenses`` (all int).
        """
        # Compras a Proveedores = supplier_payment from cash_movements
        purchases = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total
               FROM cash_movements
               WHERE type = 'supplier_payment'
                 AND created_at >= ? AND created_at <= ?""",
            (start_date, end_date),
        ).fetchone()

        # Gastos Operativos = expense from cash_movements
        operating = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total
               FROM cash_movements
               WHERE type = 'expense'
                 AND created_at >= ? AND created_at <= ?""",
            (start_date, end_date),
        ).fetchone()

        # Pérdidas (shrinkage) = returns with reasons other than "Producto en buenas condiciones"
        shrinkage = self._db.execute(
            """SELECT COALESCE(SUM(refund_amount), 0) AS total
               FROM returns
               WHERE (reason IS NULL OR reason != 'Producto en buenas condiciones')
                 AND created_at >= ? AND created_at <= ?""",
            (start_date, end_date),
        ).fetchone()

        return {
            "purchases": purchases["total"] or 0,
            "shrinkage": shrinkage["total"] or 0,
            "operating_expenses": operating["total"] or 0,
        }

    # -------------------------------------------------------------- CSV ----

    @staticmethod
    def export_csv(data: list[dict], filepath: str) -> str:
        """Write *data* (list of dicts) to a semicolon-delimited CSV with BOM.

        The UTF-8 BOM ensures Excel (Spanish locale) opens the file correctly.
        Semicolons are used instead of commas per Argentine Excel convention.

        Args:
            data:     List of homogeneous dicts (all same keys).
            filepath: Destination path for the CSV file.

        Returns:
            The *filepath* on success.

        Raises:
            OSError: If the file cannot be written.
        """
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            if not data:
                # Write BOM only (empty file with BOM header)
                return filepath

            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=";",
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            writer.writerows(data)

        return filepath
