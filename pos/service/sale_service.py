"""Sale service — atomic sale completion.

Encapsulates the entire sale lifecycle in a single database transaction:
sale record → sale items → stock deduction → cash movement → COMMIT.
Any failure rolls back ALL changes, guaranteeing transactional atomicity.
"""

import sqlite3

from pos.model.cash_register import CashMovement
from pos.model.enums import PaymentMethod, MovementType
from pos.model.exceptions import POSException
from pos.model.sale import Sale, SaleItem
from pos.repository.cash_movement_repo import CashMovementRepo
from pos.repository.sale_item_repo import SaleItemRepo
from pos.repository.sale_repo import SaleRepo
from pos.service.stock_service import StockService


class SaleService:
    """Completes a sale atomically — all or nothing.

    Wraps ``SaleRepo``, ``SaleItemRepo``, ``CashMovementRepo``, and
    ``StockService`` so the controller delegates the full persistence
    step to a single method with a single transaction boundary.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._sale_repo = SaleRepo(db)
        self._sale_item_repo = SaleItemRepo(db)
        self._cash_movement_repo = CashMovementRepo(db)
        self._stock_service = StockService(db)

    # ---------------------------------------------------------- complete_sale

    def complete_sale(
        self,
        sale: Sale,
        items: list[SaleItem],
        payment_method: PaymentMethod | str,
        cash_register_id: int,
    ) -> Sale:
        """Persist the full sale in a single atomic transaction.

        Steps (all within one ``BEGIN … COMMIT``):
        1. Insert the sale record.
        2. Insert all sale line items.
        3. Deduct stock (never blocks, allows negative).
        4. Register a cash movement when payment is cash.
        5. COMMIT — any exception triggers ROLLBACK.

        Args:
            sale:              The ``Sale`` domain object to persist.
            items:             Line items for this sale.
            payment_method:    ``"cash"``, ``"card"``, ``"transfer"``, or ``"mixed"``
                               (string or ``PaymentMethod`` enum).
            cash_register_id:  The active cash register ID.

        Returns:
            The sale with ``id`` and ``created_at`` populated.

        Raises:
            POSException: On any persistence failure — all changes rolled back.
        """
        # Normalize payment method
        pm = (
            payment_method.value
            if isinstance(payment_method, PaymentMethod)
            else payment_method
        )

        try:
            self._db.execute("BEGIN")

            # 1. Persist sale
            sale_id = self._sale_repo.create(sale).id

            # 2. Persist line items
            self._sale_item_repo.create_batch(sale_id, items)

            # 3. Deduct stock (caller manages transaction)
            self._stock_service.deduct_without_transaction(items)

            # 4. Register cash movement for all payment methods
            if pm == PaymentMethod.CASH:
                movement_type = MovementType.SALE_CASH
            elif pm == PaymentMethod.CARD:
                movement_type = MovementType.SALE_CARD
            elif pm == PaymentMethod.TRANSFER:
                movement_type = MovementType.SALE_TRANSFER
            else:
                movement_type = None

            if movement_type:
                movement = CashMovement(
                    cash_register_id=cash_register_id,
                    type=movement_type,
                    amount=sale.total,
                    description=f"Venta #{sale_id}",
                )
                self._cash_movement_repo.create(
                    register_id=movement.cash_register_id,
                    type_=movement.type,
                    amount=movement.amount,
                    description=movement.description,
                )

            self._db.execute("COMMIT")
            return sale

        except Exception as e:
            self._db.execute("ROLLBACK")
            raise POSException(f"Error al completar venta: {e}") from e
