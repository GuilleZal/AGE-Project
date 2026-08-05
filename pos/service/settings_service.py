"""Settings service — manage global preferences and apply bulk updates."""

import sqlite3

from pos.repository.settings_repo import SettingsRepo
from pos.repository.product_repo import ProductRepo


# Setting keys
LOW_STOCK_THRESHOLD = "low_stock_threshold"
PROFIT_MARGIN_PCT = "profit_margin_pct"
QR_SURCHARGE_PCT = "qr_surcharge_pct"
DEBIT_SURCHARGE_PCT = "debit_surcharge_pct"
CREDIT_SURCHARGE_PCT = "credit_surcharge_pct"

# Defaults
DEFAULT_LOW_STOCK_THRESHOLD = 5
DEFAULT_PROFIT_MARGIN_PCT = 30.0
DEFAULT_QR_SURCHARGE_PCT = 0.0
DEFAULT_DEBIT_SURCHARGE_PCT = 0.0
DEFAULT_CREDIT_SURCHARGE_PCT = 0.0


class SettingsService:
    """Business logic for global settings.

    Provides methods to get/set preferences and apply bulk updates
    to all products (e.g., recalculate prices based on margin).
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._settings_repo = SettingsRepo(db)
        self._product_repo = ProductRepo(db)

    # -------------------------------------------------------- getters

    def get_low_stock_threshold(self) -> int:
        """Return the global low-stock threshold."""
        return self._settings_repo.get_int(
            LOW_STOCK_THRESHOLD, DEFAULT_LOW_STOCK_THRESHOLD
        )

    def get_profit_margin_pct(self) -> float:
        """Return the global profit margin percentage."""
        return self._settings_repo.get_float(
            PROFIT_MARGIN_PCT, DEFAULT_PROFIT_MARGIN_PCT
        )

    def get_qr_surcharge_pct(self) -> float:
        """Return the global Qr surcharge percentage."""
        return self._settings_repo.get_float(
            QR_SURCHARGE_PCT, DEFAULT_QR_SURCHARGE_PCT
        )

    def get_debit_surcharge_pct(self) -> float:
        """Return the global debit card surcharge percentage."""
        return self._settings_repo.get_float(
            DEBIT_SURCHARGE_PCT, DEFAULT_DEBIT_SURCHARGE_PCT
        )

    def get_credit_surcharge_pct(self) -> float:
        """Return the global credit card surcharge percentage."""
        return self._settings_repo.get_float(
            CREDIT_SURCHARGE_PCT, DEFAULT_CREDIT_SURCHARGE_PCT
        )

    def get_all(self) -> dict[str, int | float]:
        """Return all settings as a dict."""
        return {
            LOW_STOCK_THRESHOLD: self.get_low_stock_threshold(),
            PROFIT_MARGIN_PCT: self.get_profit_margin_pct(),
            QR_SURCHARGE_PCT: self.get_qr_surcharge_pct(),
            DEBIT_SURCHARGE_PCT: self.get_debit_surcharge_pct(),
            CREDIT_SURCHARGE_PCT: self.get_credit_surcharge_pct(),
        }

    def get_font_scale_level(self) -> int:
        val = self._settings_repo.get("font_scale_level")
        return int(val) if val else 0

    def set_font_scale_level(self, level: int) -> None:
        self._settings_repo.set("font_scale_level", str(level))

    # -------------------------------------------------------- setters

    def set_low_stock_threshold(self, value: int) -> None:
        """Set the global low-stock threshold."""
        self._settings_repo.set(LOW_STOCK_THRESHOLD, str(value))

    def set_profit_margin_pct(self, value: float) -> None:
        """Set the global profit margin percentage."""
        self._settings_repo.set(PROFIT_MARGIN_PCT, str(value))

    def set_qr_surcharge_pct(self, value: float) -> None:
        """Set the global Qr surcharge percentage."""
        self._settings_repo.set(QR_SURCHARGE_PCT, str(value))

    def set_debit_surcharge_pct(self, value: float) -> None:
        """Set the global debit card surcharge percentage."""
        self._settings_repo.set(DEBIT_SURCHARGE_PCT, str(value))

    def set_credit_surcharge_pct(self, value: float) -> None:
        """Set the global credit card surcharge percentage."""
        self._settings_repo.set(CREDIT_SURCHARGE_PCT, str(value))

    # -------------------------------------------------------- bulk operations

    def apply_low_stock_threshold(self, threshold: int, category_id: int | None = None) -> int:
        """Update products' low_stock_threshold to *threshold*.

        Args:
            threshold: New threshold value.
            category_id: If provided, only update products in this category.
                        If None, update all products.

        Returns the number of products updated.
        """
        if category_id is None:
            self._db.execute(
                "UPDATE products SET low_stock_threshold = ?", (threshold,)
            )
        else:
            self._db.execute(
                "UPDATE products SET low_stock_threshold = ? WHERE category_id = ?",
                (threshold, category_id),
            )
        return self._db.execute("SELECT changes()").fetchone()[0]

    def apply_profit_margin(self, margin_pct: float, category_id: int | None = None) -> int:
        """Recalculate products' sale_price based on cost_price and margin.

        Formula: sale_price = cost_price / (1 - margin_pct / 100)

        Args:
            margin_pct: New profit margin percentage.
            category_id: If provided, only update products in this category.
                        If None, update all products.

        Returns the number of products updated.
        """
        if margin_pct >= 100 or margin_pct < 0:
            raise ValueError("El porcentaje de ganancia debe estar entre 0 y 99.9%")

        divisor = 1 - (margin_pct / 100)
        if category_id is None:
            self._db.execute(
                """UPDATE products
                   SET sale_price = CAST(ROUND(cost_price / ?) AS INTEGER)""",
                (divisor,),
            )
        else:
            self._db.execute(
                """UPDATE products
                   SET sale_price = CAST(ROUND(cost_price / ?) AS INTEGER)
                   WHERE category_id = ?""",
                (divisor, category_id),
            )
        return self._db.execute("SELECT changes()").fetchone()[0]
