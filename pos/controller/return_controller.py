"""Return controller — direct atomic product returns with stock restoration.

No original-sale linkage (atomic model); references the active cash register
for audit trail.  Stock is restored after confirmation.
"""

import sqlite3

from pos.model.enums import MovementType
from pos.model.exceptions import POSException
from pos.model.return_ import Return
from pos.repository.product_repo import ProductRepo
from pos.repository.return_repo import ReturnRepo
from pos.repository.cash_register_repo import CashRegisterRepo
from pos.repository.cash_movement_repo import CashMovementRepo
from pos.service.stock_service import StockService


class ReturnController:
    """Orchestrates the atomic return flow: lookup → validate → refund → restore."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._product_repo = ProductRepo(db)
        self._return_repo = ReturnRepo(db)
        self._cash_register_repo = CashRegisterRepo(db)
        self._cash_movement_repo = CashMovementRepo(db)
        self._stock_service = StockService(db)

    # ---------------------------------------------------------- lookup product ---

    def lookup_product(self, barcode: str) -> dict:
        """Look up a product by barcode for return processing.

        Args:
            barcode: The product barcode to search.

        Returns:
            ``{"success": True, "data": {product info}, "error": None}``
            or an error dict if not found.
        """
        try:
            product = self._product_repo.find_by_barcode(barcode)
            if product is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "Producto no encontrado",
                }
            return {
                "success": True,
                "data": {
                    "id": product.id,
                    "barcode": product.barcode,
                    "name": product.name,
                    "sale_price": product.sale_price,
                    "unit_type": product.unit_type,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ---------------------------------------------------------- process return --

    def process_return(
        self, product_id: int, quantity: float, reason: str | None = None
    ) -> dict:
        """Process an atomic product return.

        Steps:
        1. Validate product exists.
        2. Validate active cash register.
        3. Calculate refund = current sale_price × quantity.
        4. Inside a transaction: restore stock → create return record →
           register cash outflow.

        Args:
            product_id: Product to return.
            quantity:   Amount to return (must be > 0).
            reason:     Optional reason for the return.

        Returns:
            ``{"success": True, "data": {return, refund_amount}, "error": None}``
            or an error dict.
        """
        if quantity <= 0:
            return {
                "success": False,
                "data": None,
                "error": "La cantidad debe ser mayor a 0",
            }

        try:
            # Validate product exists
            product = self._product_repo.find_by_id(product_id)
            if product is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "Producto no encontrado",
                }

            # Validate active register
            active_register = self._cash_register_repo.find_active()
            if active_register is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "No hay caja abierta. Abra la caja primero.",
                }

            refund_amount = int(product.sale_price * quantity)

            # --- Transaction ---
            self._db.execute("BEGIN")

            # Restore stock
            self._stock_service.restore(product_id, quantity)

            # Record return
            return_ = Return(
                product_id=product_id,
                quantity=quantity,
                refund_amount=refund_amount,
                cash_register_id=active_register.id,
                reason=reason,
            )
            created_return = self._return_repo.create(return_)

            # Register cash outflow (return)
            self._cash_movement_repo.create(
                register_id=active_register.id,
                type_=MovementType.RETURN,
                amount=refund_amount,
                description=f"Devolución #{created_return.id} — {product.name}",
            )

            self._db.execute("COMMIT")

            return {
                "success": True,
                "data": {
                    "return": {
                        "id": created_return.id,
                        "product_id": created_return.product_id,
                        "product_name": product.name,
                        "quantity": created_return.quantity,
                        "refund_amount": created_return.refund_amount,
                        "reason": created_return.reason,
                        "created_at": created_return.created_at,
                    },
                    "refund_amount": refund_amount,
                },
                "error": None,
            }
        except POSException as e:
            self._db.execute("ROLLBACK")
            return {"success": False, "data": None, "error": str(e)}
        except Exception as e:
            self._db.execute("ROLLBACK")
            return {"success": False, "data": None, "error": f"Error al procesar devolución: {e}"}

    # --------------------------------------------------------------- validate ---

    def validate_return_eligibility(self, product_id: int) -> dict:
        """Check whether a product exists and can be returned.

        In the atomic model any product that exists is eligible.
        """
        try:
            product = self._product_repo.find_by_id(product_id)
            if product is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "Producto no encontrado",
                }
            return {
                "success": True,
                "data": {
                    "eligible": True,
                    "product_id": product.id,
                    "name": product.name,
                    "sale_price": product.sale_price,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ---------------------------------------------------------- calculate refund

    def calculate_refund(self, product_id: int, quantity: float) -> dict:
        """Calculate the refund amount for a given product and quantity.

        Uses the current sale_price (not historical).
        """
        if quantity <= 0:
            return {
                "success": False,
                "data": None,
                "error": "La cantidad debe ser mayor a 0",
            }

        try:
            product = self._product_repo.find_by_id(product_id)
            if product is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "Producto no encontrado",
                }

            refund = int(product.sale_price * quantity)
            return {
                "success": True,
                "data": {
                    "product_name": product.name,
                    "unit_price": product.sale_price,
                    "quantity": quantity,
                    "refund_amount": refund,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ---------------------------------------------------------- return history --

    def get_return_history(self, product_id: int | None = None) -> dict:
        """Return the list of all returns, optionally filtered by *product_id*.

        Returns are sorted most-recent first.
        """
        try:
            returns = self._return_repo.get_all()
            if product_id is not None:
                returns = [r for r in returns if r.product_id == product_id]

            result = []
            for r in returns:
                product = self._product_repo.find_by_id(r.product_id)
                result.append({
                    "id": r.id,
                    "product_id": r.product_id,
                    "product_name": product.name if product else f"#{r.product_id}",
                    "quantity": r.quantity,
                    "refund_amount": r.refund_amount,
                    "reason": r.reason,
                    "cash_register_id": r.cash_register_id,
                    "created_at": r.created_at,
                })

            return {"success": True, "data": result, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ---------------------------------------------------------- search products ---

    def search_products(self, query: str) -> dict:
        """Search products by barcode, name, or category name.

        If query is empty, returns all products.
        """
        try:
            query = query.strip() if query else ""
            if not query:
                products = self._product_repo.get_all()
            else:
                products = self._product_repo.search_unified(query)
            return {"success": True, "data": products, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_categories(self) -> dict:
        """Return all categories for the search dialog."""
        try:
            from pos.repository.category_repo import CategoryRepo
            category_repo = CategoryRepo(self._db)
            categories = category_repo.get_all()
            return {
                "success": True,
                "data": categories,
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
