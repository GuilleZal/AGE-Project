"""Report controller — generate sales/profit reports and export to CSV.

Delegates to ``ReportService`` for aggregation logic and CSV writing.
Validates date ranges before calling the service.
"""

import sqlite3

from pos.model.exceptions import POSException
from pos.service.report_service import ReportService


class ReportController:
    """Orchestrates report generation and CSV export."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._report_service = ReportService(db)

    # ----------------------------------------------------------- sales report --

    def generate_sales_report(
        self, start_date: str, end_date: str, filters: dict | None = None
    ) -> dict:
        """Generate a sales summary report for a date range.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).
            filters:    Optional dict with ``payment_method`` or ``category_id``
                        for narrowing the report.

        Returns:
            ``{"success": True, "data": {sales_summary, profit_summary, top_products}, "error": None}``.
        """
        try:
            _validate_dates(start_date, end_date)

            sales = self._report_service.sales_summary(start_date, end_date)
            profit = self._report_service.profit_summary(start_date, end_date)
            top = self._report_service.top_products(start_date, end_date)

            return {
                "success": True,
                "data": {
                    "period": {"start": start_date, "end": end_date},
                    "sales": sales,
                    "profit": profit,
                    "top_products": top,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
        except ValueError as e:
            return {"success": False, "data": None, "error": str(e)}

    def generate_profit_report(self, start_date: str, end_date: str) -> dict:
        """Generate a profit-only report for a date range.

        Returns ``{"success": True, "data": {revenue, cost, profit, margin_pct}, "error": None}``.
        """
        try:
            _validate_dates(start_date, end_date)
            profit = self._report_service.profit_summary(start_date, end_date)
            return {"success": True, "data": profit, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
        except ValueError as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_top_products(
        self, start_date: str, end_date: str, limit: int = 10
    ) -> dict:
        """Return the top *N* products by quantity sold.

        Returns ``{"success": True, "data": list[dict], "error": None}``.
        """
        try:
            _validate_dates(start_date, end_date)
            top = self._report_service.top_products(start_date, end_date, limit)
            return {"success": True, "data": top, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
        except ValueError as e:
            return {"success": False, "data": None, "error": str(e)}

    # ------------------------------------------------------------------ CSV ----

    def export_to_csv(self, data: list[dict], file_path: str) -> dict:
        """Export *data* (list of dicts) to a semicolon-delimited CSV with BOM.

        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            result_path = self._report_service.export_csv(data, file_path)
            return {"success": True, "data": result_path, "error": None}
        except (OSError, IOError) as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error al escribir CSV: {e}. Verifique permisos de escritura.",
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}


# --------------------------------------------------------------- helpers ---

def _validate_dates(start_date: str, end_date: str) -> None:
    """Raise ``ValueError`` if the date range is invalid."""
    if not start_date or not end_date:
        raise ValueError("Debe especificar fecha de inicio y fin")
    if start_date > end_date:
        raise ValueError("Fecha desde > fecha hasta")
