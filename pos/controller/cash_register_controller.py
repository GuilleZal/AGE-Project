"""Cash register controller — open/close lifecycle, balance, and outflow registration.

Enforces the single-active-register rule and computes live expected balance
from opening amount + inflows − outflows.
"""

import sqlite3
from datetime import datetime

from pos.model.enums import MovementType
from pos.model.exceptions import POSException
from pos.repository.cash_register_repo import CashRegisterRepo
from pos.repository.cash_movement_repo import CashMovementRepo


class CashRegisterController:
    """Orchestrates cash register sessions: open, close, outflow registration."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._register_repo = CashRegisterRepo(db)
        self._movement_repo = CashMovementRepo(db)

    # ------------------------------------------------------------------ open ---

    def open_register(self, initial_amount: int) -> dict:
        """Open a new cash register session.

        Args:
            initial_amount: Opening cash amount in whole ARS (must be ≥ 0).

        Returns:
            ``{"success": True, "data": CashRegister, "error": None}``
            or ``{"success": False, "data": None, "error": message}``.
        """
        if initial_amount < 0:
            return {
                "success": False,
                "data": None,
                "error": "El monto inicial no puede ser negativo",
            }

        try:
            # Enforce single-active rule
            active = self._register_repo.find_active()
            if active is not None:
                return {
                    "success": False,
                    "data": None,
                    "error": "Ya existe una caja abierta. Ciérrela antes de abrir una nueva.",
                }

            # Find active user_id from session
            user_row = self._db.execute(
                "SELECT user_id FROM sessions WHERE logout_time IS NULL ORDER BY login_time DESC LIMIT 1"
            ).fetchone()
            user_id = user_row["user_id"] if user_row else None

            register = self._register_repo.open_register(initial_amount, user_id)
            self._db.commit()
            return {"success": True, "data": register, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ----------------------------------------------------------------- close ---

    def close_register(self, final_amount: int, notes: str) -> dict:
        """Close the active cash register session.

        The expected amount is computed as:
            opening + Σsale_cash − Σreturns − Σoutflows.

        The difference is ``actual − expected``.

        Args:
            final_amount: Physically counted cash amount (int, ≥ 0).
            notes:        Close reason (mandatory).

        Returns:
            ``{"success": True, "data": {"register": ..., "diff": int}, "error": None}``
            or an error dict.
        """
        if final_amount < 0:
            return {
                "success": False,
                "data": None,
                "error": "El monto contado no puede ser negativo",
            }
        # Notes are now optional

        try:
            active = self._register_repo.find_active()
            if active is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "No hay caja abierta para cerrar",
                }

            balance = self._register_repo.get_balance(active.id)
            expected = balance["expected"]
            diff = final_amount - expected

            closed = self._register_repo.close_register(
                register_id=active.id,
                closing_amount=final_amount,
                difference=diff,
                reason=notes.strip(),
            )
            self._db.commit()
            return {
                "success": True,
                "data": {
                    "register": {
                        "id": closed.id,
                        "opening_amount": closed.opening_amount,
                        "closing_amount": closed.closing_amount,
                        "expected_amount": closed.expected_amount,
                        "difference": closed.difference,
                        "close_reason": closed.close_reason,
                        "status": closed.status,
                        "opening_time": closed.opening_time,
                        "closing_time": closed.closing_time,
                    },
                    "expected": expected,
                    "actual": final_amount,
                    "diff": diff,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ----------------------------------------------------- register movement ---

    def register_sale(self, sale_data: dict) -> dict:
        """Record a sale cash movement in the active register.

        This is normally called by ``SaleController.complete_sale``,
        but exposed here for programmatic registration.

        Args:
            sale_data: Dict with ``amount`` (int) and optional ``description``.

        Returns:
            ``{"success": True, "data": CashMovement, "error": None}``.
        """
        try:
            active = self._register_repo.find_active()
            if active is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "No hay caja abierta",
                }

            movement = self._movement_repo.create(
                register_id=active.id,
                type_=MovementType.SALE_CASH,
                amount=int(sale_data["amount"]),
                description=sale_data.get("description"),
            )
            self._db.commit()
            return {"success": True, "data": movement, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def register_return(self, return_data: dict) -> dict:
        """Record a return cash outflow in the active register.

        Args:
            return_data: Dict with ``amount`` (int) and optional ``description``.

        Returns:
            ``{"success": True, "data": CashMovement, "error": None}``.
        """
        try:
            active = self._register_repo.find_active()
            if active is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "No hay caja abierta",
                }

            movement = self._movement_repo.create(
                register_id=active.id,
                type_=MovementType.RETURN,
                amount=int(return_data["amount"]),
                description=return_data.get("description"),
            )
            self._db.commit()
            return {"success": True, "data": movement, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def register_outflow(
        self, type_: str, amount: int, description: str | None = None
    ) -> dict:
        """Register a manual outflow (supplier_payment or expense).

        Args:
            type_:       ``"supplier_payment"`` or ``"expense"``.
            amount:      Whole ARS pesos.
            description: Optional note.

        Returns:
            ``{"success": True, "data": CashMovement, "error": None}``.
        """
        try:
            active = self._register_repo.find_active()
            if active is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "No hay caja abierta",
                }

            movement = self._movement_repo.create(
                register_id=active.id,
                type_=type_,
                amount=amount,
                description=description,
            )
            self._db.commit()
            return {"success": True, "data": movement, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ----------------------------------------------------------------- status --

    def get_register_status(self) -> dict:
        """Return the current status of the cash register.

        If a register is open, includes live balance (opening, inflows,
        outflows, expected). If none is open, returns ``active: False``.
        """
        try:
            active = self._register_repo.find_active()
            if active is None:
                return {
                    "success": True,
                    "data": {
                        "active": False,
                        "register": None,
                        "balance": None,
                    },
                    "error": None,
                }

            balance = self._register_repo.get_balance(active.id)
            balance["difference"] = balance["expected"] - balance["opening"]
            balance["closing"] = None
            balance["diff_cash"] = None
            return {
                "success": True,
                "data": {
                    "active": True,
                    "register": {
                        "id": active.id,
                        "opening_amount": active.opening_amount,
                        "opening_time": active.opening_time,
                        "status": active.status,
                    },
                    "balance": balance,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_daily_summary(self) -> dict:
        """Return a summary of today's registers and movements.

        Returns a dict with the current register status and a list of
        all movements for the active register.
        """
        try:
            status = self.get_register_status()
            if not status["success"] or not status["data"]["active"]:
                return status

            active = status["data"]["register"]
            movements = self._movement_repo.get_by_register(active["id"])
            return {
                "success": True,
                "data": {
                    "register": active,
                    "balance": status["data"]["balance"],
                    "movements": self._format_movements_for_display(movements),
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_history(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        """Return cash register sessions filtered by date range, most-recent first.
        
        Args:
            start_date: Optional start date in 'YYYY-MM-DD' format (inclusive).
            end_date: Optional end date in 'YYYY-MM-DD' format (inclusive).
        """
        try:
            registers = self._register_repo.get_history(start_date, end_date)
            return {
                "success": True,
                "data": [
                    {
                        "id": r.id,
                        "opening_amount": r.opening_amount,
                        "opening_time": r.opening_time,
                        "closing_amount": r.closing_amount,
                        "closing_time": r.closing_time,
                        "expected_amount": r.expected_amount,
                        "difference": r.difference,
                        "close_reason": r.close_reason,
                        "status": r.status,
                        "username": r.username,
                    }
                    for r in registers
                ],
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_register_balance(self, register_id: int) -> dict:
        """Return the balance of a specific register session, using its status to calculate the correct difference."""
        try:
            # Get database row for register to check status and stored difference
            row = self._db.execute(
                "SELECT * FROM cash_registers WHERE id = ?", (register_id,)
            ).fetchone()
            if row is None:
                return {"success": False, "data": None, "error": f"Caja #{register_id} no encontrada"}
            
            balance = self._register_repo.get_balance(register_id)
            if row["status"] == "closed":
                # For closed registers, use the physically stored difference (closing_amount - expected_amount)
                balance["difference"] = row["difference"]
                balance["diff_cash"] = row["closing_amount"] - balance["expected_cash"]
            else:
                # For open/active registers, use net flow (expected - opening)
                balance["difference"] = balance["expected"] - balance["opening"]
                balance["diff_cash"] = None
                
            balance["closing"] = row["closing_amount"]
            return {"success": True, "data": balance, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_movements(self, register_id: int) -> dict:
        """Return all cash movements for a specific register session."""
        try:
            movements = self._movement_repo.get_by_register(register_id)
            return {
                "success": True,
                "data": self._format_movements_for_display(movements),
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def _format_movements_for_display(self, movements: list) -> list[dict]:
        """Format movements for display in the cash register view, dynamically numbering sales and returns per session."""
        formatted = []
        sale_idx = 0
        return_idx = 0

        for m in movements:
            desc = m.description or ""
            if m.type in ("sale_cash", "sale_card", "sale_debit_card", "sale_credit_card", "sale_transfer"):
                sale_idx += 1
                if "Venta #" in desc:
                    parts = desc.split("Venta #", 1)
                    number_str = ""
                    suffix = ""
                    for char in parts[1]:
                        if char.isdigit():
                            number_str += char
                        else:
                            suffix = parts[1][len(number_str):]
                            break
                    desc = f"{parts[0]}Venta #{sale_idx}{suffix}"
                else:
                    desc = f"Venta #{sale_idx}"
            
            elif m.type == "return":
                return_idx += 1
                return_id = None
                if "Devolución #" in desc:
                    parts = desc.split("Devolución #", 1)
                    number_str = ""
                    for char in parts[1]:
                        if char.isdigit():
                            number_str += char
                        else:
                            break
                    if number_str:
                        return_id = int(number_str)
                
                qty_str = ""
                if return_id is not None:
                    row = self._db.execute(
                        """SELECT r.quantity, p.unit_type, p.name 
                           FROM returns r
                           JOIN products p ON r.product_id = p.id
                           WHERE r.id = ?""",
                        (return_id,)
                    ).fetchone()
                    if row:
                        qty = row["quantity"]
                        unit_type = row["unit_type"] or "Unidad"
                        product_name = row["name"]
                        is_kg = unit_type.lower() in ("kg", "weight_kg")
                        if is_kg:
                            qty_str = f"{float(qty)} Kg "
                        else:
                            qty_str = f"{int(qty)} u. "
                        desc = f"Devolución #{return_idx} — {qty_str}{product_name}"
                    else:
                        if " — " in desc:
                            pname = desc.split(" — ", 1)[1]
                            desc = f"Devolución #{return_idx} — {pname}"
                        else:
                            desc = f"Devolución #{return_idx}"
                else:
                    if " — " in desc:
                        pname = desc.split(" — ", 1)[1]
                        desc = f"Devolución #{return_idx} — {pname}"
                    else:
                        desc = f"Devolución #{return_idx}"

            formatted.append({
                "id": m.id,
                "type": m.type,
                "amount": m.amount,
                "description": desc,
                "created_at": m.created_at,
            })
        
        return formatted
