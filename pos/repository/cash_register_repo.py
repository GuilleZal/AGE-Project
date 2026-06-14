"""Cash-register repository — open, close, find-active, and balance queries.

Only ONE register can be open at a time (enforced in the service layer, not here).
"""

import sqlite3
from datetime import datetime

from pos.model.cash_register import CashRegister
from pos.model.exceptions import DataError


class CashRegisterRepo:
    """Data-access for the ``cash_registers`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ------------------------------------------------------------------ open

    def open_register(self, opening_amount: int) -> CashRegister:
        """Create a new cash register with ``status='open'``.

        ``opening_time`` is set to the current moment.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self._db.execute(
            """INSERT INTO cash_registers (opening_amount, opening_time, status)
               VALUES (?, ?, 'open')
               RETURNING id""",
            (opening_amount, now),
        )
        reg_id = cur.fetchone()["id"]
        return CashRegister(
            id=reg_id,
            opening_amount=opening_amount,
            opening_time=now,
            status="open",
        )

    # ------------------------------------------------------------- active --

    def find_active(self) -> CashRegister | None:
        """Return the currently open register, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM cash_registers WHERE status = 'open' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    # ----------------------------------------------------------------- close

    def close_register(
        self,
        register_id: int,
        closing_amount: int,
        difference: int,
        reason: str,
    ) -> CashRegister:
        """Close a register: set ``closing_amount``, ``difference``,
        ``close_reason``, ``status='closed'``, and store ``expected_amount``.

        Raises:
            DataError: If the register is not found.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expected_amount = closing_amount - difference
        cur = self._db.execute(
            """UPDATE cash_registers
               SET closing_amount = ?, closing_time = ?, difference = ?,
                   close_reason = ?, status = 'closed', expected_amount = ?
               WHERE id = ?
               RETURNING *""",
            (closing_amount, now, difference, reason, expected_amount, register_id),
        )
        row = cur.fetchone()
        if row is None:
            raise DataError(f"Caja registradora id={register_id} no encontrada")
        return self._from_row(row)

    # -------------------------------------------------------------- balance

    def get_balance(self, register_id: int) -> dict:
        """Compute the live balance for a register.

        Returns a dict with keys:
            ``opening``, ``inflows``, ``outflows``, ``expected``.
        """
        register = self._db.execute(
            "SELECT * FROM cash_registers WHERE id = ?", (register_id,)
        ).fetchone()
        if register is None:
            raise DataError(f"Caja registradora id={register_id} no encontrada")

        inflows = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM cash_movements
               WHERE cash_register_id = ? AND type = 'sale_cash'""",
            (register_id,),
        ).fetchone()[0]

        outflows = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM cash_movements
               WHERE cash_register_id = ?
                 AND type IN ('return', 'supplier_payment', 'expense')""",
            (register_id,),
        ).fetchone()[0]

        opening = register["opening_amount"]
        expected = opening + inflows - outflows

        return {
            "opening": opening,
            "inflows": inflows,
            "outflows": outflows,
            "expected": expected,
        }

    # -------------------------------------------------------------- history

    def get_history(self) -> list[CashRegister]:
        """Return all registers, most-recent first."""
        rows = self._db.execute(
            "SELECT * FROM cash_registers ORDER BY opening_time DESC"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    # ----------------------------------------------------------- helpers ---

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CashRegister:
        return CashRegister(
            id=row["id"],
            opening_amount=row["opening_amount"],
            opening_time=row["opening_time"],
            closing_amount=row["closing_amount"],
            closing_time=row["closing_time"],
            expected_amount=row["expected_amount"],
            difference=row["difference"],
            close_reason=row["close_reason"],
            status=row["status"],
        )
