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

    def open_register(self, opening_amount: int, user_id: int | None = None) -> CashRegister:
        """Create a new cash register with ``status='open'``.

        ``opening_time`` is set to the current moment.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self._db.execute(
            """INSERT INTO cash_registers (opening_amount, opening_time, status, user_id)
               VALUES (?, ?, 'open', ?)
               RETURNING id""",
            (opening_amount, now, user_id),
        )
        reg_id = cur.fetchone()["id"]
        return CashRegister(
            id=reg_id,
            opening_amount=opening_amount,
            opening_time=now,
            status="open",
            user_id=user_id,
        )

    # ------------------------------------------------------------- active --

    def find_active(self) -> CashRegister | None:
        """Return the currently open register, or ``None``."""
        row = self._db.execute(
            """SELECT cr.*, u.username, u2.username as closed_by_username 
               FROM cash_registers cr 
               LEFT JOIN users u ON cr.user_id = u.id 
               LEFT JOIN users u2 ON cr.closed_by_user_id = u2.id 
               WHERE cr.status = 'open' 
               ORDER BY cr.id DESC LIMIT 1"""
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
        closed_by_user_id: int | None = None,
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
                   close_reason = ?, status = 'closed', expected_amount = ?,
                   closed_by_user_id = ?
               WHERE id = ?""",
            (closing_amount, now, difference, reason, expected_amount, closed_by_user_id, register_id),
        )
        if cur.rowcount == 0:
            raise DataError(f"Caja registradora id={register_id} no encontrada")
        row = self._db.execute(
            """SELECT cr.*, u.username, u2.username as closed_by_username
               FROM cash_registers cr
               LEFT JOIN users u ON cr.user_id = u.id
               LEFT JOIN users u2 ON cr.closed_by_user_id = u2.id
               WHERE cr.id = ?""",
            (register_id,),
        )
        return self._from_row(row.fetchone())

    # -------------------------------------------------------------- balance

    def get_balance(self, register_id: int) -> dict:
        """Compute the live balance for a register.

        Returns a dict with keys:
            ``opening``, ``inflows``, ``outflows``, ``expected``, and detailed breakdowns.
        """
        register = self._db.execute(
            "SELECT * FROM cash_registers WHERE id = ?", (register_id,)
        ).fetchone()
        if register is None:
            raise DataError(f"Caja registradora id={register_id} no encontrada")

        # Inflows breakdowns
        inflow_cash = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type = 'sale_cash'",
            (register_id,),
        ).fetchone()[0]

        inflow_transfer = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type = 'sale_transfer'",
            (register_id,),
        ).fetchone()[0]

        inflow_qr = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type = 'sale_qr'",
            (register_id,),
        ).fetchone()[0]

        inflow_debit = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type = 'sale_debit_card'",
            (register_id,),
        ).fetchone()[0]

        inflow_credit = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type IN ('sale_credit_card', 'sale_card')",
            (register_id,),
        ).fetchone()[0]

        # Outflows breakdowns
        outflow_supplier = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type = 'supplier_payment'",
            (register_id,),
        ).fetchone()[0]

        outflow_expense = self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_movements WHERE cash_register_id = ? AND type IN ('expense', 'return')",
            (register_id,),
        ).fetchone()[0]

        opening = register["opening_amount"]
        inflows = inflow_cash + inflow_transfer + inflow_qr + inflow_debit + inflow_credit
        outflows = outflow_supplier + outflow_expense
        expected = opening + inflows - outflows
        expected_cash = opening + inflow_cash - outflows

        return {
            "opening": opening,
            "inflows": inflows,
            "outflows": outflows,
            "expected": expected,
            "inflow_cash": inflow_cash,
            "inflow_transfer": inflow_transfer,
            "inflow_qr": inflow_qr,
            "inflow_debit": inflow_debit,
            "inflow_credit": inflow_credit,
            "outflow_supplier": outflow_supplier,
            "outflow_expense": outflow_expense,
            "outflow_total": outflows,
            "expected_cash": expected_cash,
        }

    # -------------------------------------------------------------- history

    def get_history(self, start_date: str | None = None, end_date: str | None = None) -> list[CashRegister]:
        """Return registers filtered by date range, most-recent first.
        
        Args:
            start_date: Optional start date in 'YYYY-MM-DD' format (inclusive).
            end_date: Optional end date in 'YYYY-MM-DD' format (inclusive).
        
        Returns:
            List of CashRegister objects matching the date range.
        """
        query = """SELECT cr.*, u.username, u2.username as closed_by_username 
                   FROM cash_registers cr 
                   LEFT JOIN users u ON cr.user_id = u.id 
                   LEFT JOIN users u2 ON cr.closed_by_user_id = u2.id"""
        params: list = []
        
        if start_date or end_date:
            query += " WHERE "
            conditions = []
            if start_date:
                conditions.append("cr.opening_time >= ?")
                params.append(f"{start_date} 00:00:00")
            if end_date:
                conditions.append("cr.opening_time <= ?")
                params.append(f"{end_date} 23:59:59")
            query += " AND ".join(conditions)
        
        query += " ORDER BY cr.opening_time DESC"
        
        rows = self._db.execute(query, params).fetchall()
        return [self._from_row(r) for r in rows]

    def get_sold_products(self, register_id: int) -> dict:
        """Return a detailed list of all items sold in a specific cash register session along with opening and closing times."""
        # Query session metadata
        meta_query = "SELECT opening_time, closing_time FROM cash_registers WHERE id = ?"
        meta_row = self._db.execute(meta_query, (register_id,)).fetchone()
        opening_time = meta_row["opening_time"] if meta_row else ""
        closing_time = meta_row["closing_time"] if (meta_row and meta_row["closing_time"]) else ""

        # Fetch sales items
        query = """
            SELECT 
                s.id as sale_id,
                p.id as product_id,
                s.created_at,
                s.payment_method,
                p.name as product_name,
                p.unit_type,
                p.cost_price as cost_price,
                si.quantity,
                si.unit_price,
                si.subtotal
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE s.cash_register_id = ?
            ORDER BY s.created_at ASC, s.id ASC, si.id ASC
        """
        rows = self._db.execute(query, (register_id,)).fetchall()
        
        # Map sale_id to sequential sale number (Venta #1, Venta #2, etc.)
        sale_id_to_num = {}
        next_num = 1
        
        results = []
        for row in rows:
            sid = row["sale_id"]
            if sid not in sale_id_to_num:
                sale_id_to_num[sid] = f"Venta #{next_num}"
                next_num += 1
                
            results.append({
                "sale_id": row["sale_id"],
                "product_id": row["product_id"],
                "sale_num": sale_id_to_num[sid],
                "created_at": row["created_at"],
                "payment_method": row["payment_method"],
                "name": row["product_name"],
                "unit_type": row["unit_type"],
                "cost_price": row["cost_price"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "subtotal": row["subtotal"]
            })

        # Fetch returns
        ret_query = """
            SELECT 
                r.id as return_id,
                p.id as product_id,
                r.created_at,
                p.name as product_name,
                p.unit_type,
                p.cost_price as cost_price,
                r.quantity,
                r.refund_amount,
                p.sale_price
            FROM returns r
            JOIN products p ON r.product_id = p.id
            WHERE r.cash_register_id = ?
            ORDER BY r.created_at ASC
        """
        ret_rows = self._db.execute(ret_query, (register_id,)).fetchall()
        
        for row in ret_rows:
            qty = row["quantity"]
            refund = row["refund_amount"]
            
            results.append({
                "return_id": row["return_id"],
                "product_id": row["product_id"],
                "sale_num": "Devolución",
                "created_at": row["created_at"],
                "payment_method": "-",
                "name": row["product_name"],
                "unit_type": row["unit_type"],
                "cost_price": row["cost_price"],
                "quantity": -qty,
                "unit_price": row["sale_price"],
                "subtotal": -refund
            })

        # Fetch purchases (supplier payments) from cash_movements
        pur_query = """
            SELECT 
                cm.id as movement_id,
                cm.created_at,
                cm.amount,
                cm.description
            FROM cash_movements cm
            WHERE cm.cash_register_id = ? AND cm.type = 'supplier_payment'
            ORDER BY cm.created_at ASC
        """
        pur_rows = self._db.execute(pur_query, (register_id,)).fetchall()
        
        for row in pur_rows:
            desc = row["description"] if row["description"] else "Pago Proveedor"
            results.append({
                "movement_id": row["movement_id"],
                "sale_num": "Pago Proveedor",
                "created_at": row["created_at"],
                "payment_method": "cash",
                "name": desc,
                "unit_type": "Unidad",
                "cost_price": 0,
                "quantity": 0.0,
                "unit_price": 0,
                "subtotal": -row["amount"]
            })

        # Sort combined results chronologically
        results.sort(key=lambda x: x["created_at"])
        
        return {
            "products": results,
            "opening_time": opening_time,
            "closing_time": closing_time
        }

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
            user_id=row["user_id"] if "user_id" in row.keys() else None,
            username=row["username"] if "username" in row.keys() else None,
            closed_by_user_id=row["closed_by_user_id"] if "closed_by_user_id" in row.keys() else None,
            closed_by_username=row["closed_by_username"] if "closed_by_username" in row.keys() else None,
        )
