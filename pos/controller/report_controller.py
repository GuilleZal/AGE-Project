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
        self, start_date: str, end_date: str, top_limit: int = 10
    ) -> dict:
        """Generate a comprehensive sales report for a date range.

        Args:
            start_date: ISO-like datetime string (inclusive).
            end_date:   ISO-like datetime string (inclusive).
            top_limit:  Number of top products to return (default 10).

        Returns:
            ``{"success": True, "data": {sales, profit, top_products, low_stock, payment_methods, expenses}, "error": None}``.
        """
        try:
            _validate_dates(start_date, end_date)

            sales = self._report_service.sales_summary(start_date, end_date)
            profit = self._report_service.profit_summary(start_date, end_date)
            top = self._report_service.top_products(start_date, end_date, top_limit)
            low_stock = self._report_service.low_stock_products()
            payment_methods = self._report_service.payment_methods_summary(start_date, end_date)
            sales_by_category = self._report_service.sales_by_category(start_date, end_date)
            returns_history = self._report_service.returns_history(start_date, end_date)
            expenses = self._report_service.expenses_summary(start_date, end_date)

            # Calculate net profit
            net_profit = (
                profit["profit"]
                - expenses["purchases"]
                - expenses["shrinkage"]
                - expenses["operating_expenses"]
            )
            expenses["net_profit"] = net_profit

            return {
                "success": True,
                "data": {
                    "period": {"start": start_date, "end": end_date},
                    "sales": sales,
                    "profit": profit,
                    "top_products": top,
                    "low_stock": low_stock,
                    "payment_methods": payment_methods,
                    "sales_by_category": sales_by_category,
                    "returns_history": returns_history,
                    "expenses": expenses,
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

    def get_low_stock(self) -> dict:
        """Return all products whose current stock is at or below threshold.

        Returns ``{"success": True, "data": list[dict], "error": None}``.
        """
        try:
            low_stock = self._report_service.low_stock_products()
            return {"success": True, "data": low_stock, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ------------------------------------------------------------------ CSV ----

    def export_to_csv(self, data: list[dict], file_path: str, start_date: str = "", end_date: str = "") -> dict:
        """Export *data* (list of dicts) to a semicolon-delimited CSV with BOM.

        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            result_path = self._report_service.export_csv(data, file_path, start_date, end_date)
            return {"success": True, "data": result_path, "error": None}
        except (OSError, IOError) as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error al escribir CSV: {e}. Verifique permisos de escritura.",
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def export_to_excel(self, data: list[dict], file_path: str, start_date: str = "", end_date: str = "") -> dict:
        """Export *data* (list of dicts) to an Excel (.xlsx) file using openpyxl.

        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            result_path = self._report_service.export_excel(data, file_path, start_date, end_date)
            return {"success": True, "data": result_path, "error": None}
        except (OSError, IOError) as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error al escribir Excel: {e}. Verifique permisos de escritura.",
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
