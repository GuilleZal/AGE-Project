"""Sale controller — cart management, barcode scanning, and payment completion.

Maintains an in-memory cart (list of dicts) and orchestrates the full
sale flow: product lookup → quick-create fallback → cart manipulation →
payment → atomic persistence via ``SaleService``.
"""

import sqlite3

from pos.model.enums import PaymentMethod
from pos.model.exceptions import POSException
from pos.model.product import Product
from pos.model.sale import Sale, SaleItem
from pos.repository.product_repo import ProductRepo
from pos.repository.cash_register_repo import CashRegisterRepo
from pos.service.sale_service import SaleService


class SaleController:
    """Orchestrates the complete sale lifecycle.

    The cart is an in-memory list of dicts with keys:
        ``product_id``, ``barcode``, ``name``, ``quantity``, ``unit_price``, ``subtotal``.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._product_repo = ProductRepo(db)
        self._cash_register_repo = CashRegisterRepo(db)
        self._sale_service = SaleService(db)
        self._cart: list[dict] = []

    # ---------------------------------------------------------------- cart ---

    def add_by_barcode(
        self, barcode: str, quantity: float = 1.0
    ) -> dict:
        """Look up a product by *barcode* and add it to the cart.

        Args:
            barcode: Scanned barcode (stripped, numeric).
            quantity: Quantity to add (default 1, supports float for weight_kg).

        Returns:
            ``{"success": True, "data": cart_item, "error": None}`` on success.
            ``{"success": False, "data": {"barcode": barcode}, "error": None}``
            when the product is NOT found (the view shows QuickCreateDialog).
        """
        try:
            product = self._product_repo.find_by_barcode(barcode)
        except POSException:
            product = None

        if product is None:
            return {
                "success": False,
                "data": {"barcode": barcode},
                "error": None,  # not an error — trigger quick-create flow
            }

        return self._add_product_to_cart(product, quantity)

    def create_quick_product(
        self, barcode: str, name: str, sale_price: int
    ) -> dict:
        """Create a minimal product for an unknown barcode and add it to the cart.

        Uses quick-create defaults: ``cost_price=0``, ``stock=0``,
        ``unit_type='unit'``, ``low_stock_threshold=5``.

        Args:
            barcode:    Scanned barcode.
            name:       Product name (from QuickCreateDialog).
            sale_price: Sale price in whole ARS (must be ≥ 0).

        Returns:
            ``{"success": True, "data": cart_item, "error": None}``
            or ``{"success": False, "data": None, "error": message}``.
        """
        if sale_price < 0:
            return {
                "success": False,
                "data": None,
                "error": "El precio no puede ser negativo",
            }
        if not name.strip():
            return {
                "success": False,
                "data": None,
                "error": "El nombre del producto es obligatorio",
            }

        try:
            product = Product(
                barcode=barcode,
                name=name.strip(),
                sale_price=sale_price,
                cost_price=0,
                stock=0.0,
                unit_type="unit",
                low_stock_threshold=5.0,
            )
            created = self._product_repo.create(product)
            return self._add_product_to_cart(created, 1.0)
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def update_item_quantity(self, product_id: int, quantity: float) -> dict:
        """Change the quantity of a cart item.

        If *quantity* ≤ 0 the item is removed.
        """
        if quantity <= 0:
            return self.remove_item(product_id)

        for item in self._cart:
            if item["product_id"] == product_id:
                item["quantity"] = quantity
                item["subtotal"] = int(item["unit_price"] * quantity)
                return {"success": True, "data": item, "error": None}

        return {
            "success": False,
            "data": None,
            "error": "Producto no encontrado en el carrito",
        }

    def remove_item(self, product_id: int) -> dict:
        """Remove an item from the cart by *product_id*."""
        before = len(self._cart)
        self._cart = [i for i in self._cart if i["product_id"] != product_id]
        if len(self._cart) == before:
            return {
                "success": False,
                "data": None,
                "error": "Producto no encontrado en el carrito",
            }
        return {"success": True, "data": None, "error": None}

    def get_cart(self) -> dict:
        """Return the current cart contents and total."""
        total = self._calculate_total()
        return {"success": True, "data": {"items": self._cart, "total": total}, "error": None}

    def calculate_total(self) -> dict:
        """Return the cart total."""
        total = self._calculate_total()
        return {"success": True, "data": {"total": total}, "error": None}

    def clear_cart(self) -> dict:
        """Empty the cart after a successful sale."""
        self._cart.clear()
        return {"success": True, "data": None, "error": None}

    # ------------------------------------------------------------- complete ----

    def complete_sale(
        self, payment_method: str | PaymentMethod, amount_received: int = 0
    ) -> dict:
        """Process payment and persist the complete sale.

        Flow:
        1. Validate cart is not empty.
        2. Validate active cash register exists.
        3. For cash: validate received ≥ total; calculate change.
        4. Delegate atomic persistence to ``SaleService.complete_sale()``
           (single transaction — all or nothing).

        Args:
            payment_method: ``"cash"``, ``"card"``, ``"transfer"``, or ``"mixed"``.
            amount_received: Cash amount tendered (required for cash payments).

        Returns:
            ``{"success": True, "data": {sale, items, change}, "error": None}``
            or ``{"success": False, "data": None, "error": message}``.
        """
        if not self._cart:
            return {"success": False, "data": None, "error": "El carrito está vacío"}

        # Normalize payment method
        pm = payment_method.value if isinstance(payment_method, PaymentMethod) else payment_method

        try:
            PaymentMethod(pm)  # validate
        except ValueError:
            return {
                "success": False,
                "data": None,
                "error": f"Método de pago no válido: {pm}",
            }

        # --- Active cash register ---
        active_register = self._cash_register_repo.find_active()
        if active_register is None:
            return {
                "success": False,
                "data": None,
                "error": "No hay caja abierta. Abra la caja primero.",
            }

        total = self._calculate_total()

        # Cash validation
        change = 0
        if pm == "cash":
            if amount_received < total:
                return {
                    "success": False,
                    "data": None,
                    "error": "Monto insuficiente",
                }
            change = amount_received - total

        # --- Build domain objects ---
        sale = Sale(
            total=total,
            discount=0,
            payment_method=pm,
            cash_register_id=active_register.id,
        )

        items: list[SaleItem] = []
        for ci in self._cart:
            items.append(SaleItem(
                product_id=ci["product_id"],
                quantity=ci["quantity"],
                unit_price=ci["unit_price"],
                subtotal=ci["subtotal"],
            ))

        # --- Delegate atomic persistence to SaleService ---
        cart_snapshot = list(self._cart)
        try:
            created_sale = self._sale_service.complete_sale(
                sale, items, pm, active_register.id
            )
            self.clear_cart()

            return {
                "success": True,
                "data": {
                    "sale": {
                        "id": created_sale.id,
                        "total": created_sale.total,
                        "payment_method": pm,
                        "created_at": created_sale.created_at,
                    },
                    "items": cart_snapshot,
                    "change": change,
                },
                "error": None,
            }
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}
        except Exception as e:
            return {"success": False, "data": None, "error": f"Error al procesar venta: {e}"}

    # ----------------------------------------------------------- helpers ---

    def _add_product_to_cart(self, product: Product, quantity: float) -> dict:
        """Add or increment a product in the in-memory cart."""
        for item in self._cart:
            if item["product_id"] == product.id:
                item["quantity"] += quantity
                item["subtotal"] = int(item["unit_price"] * item["quantity"])
                return {"success": True, "data": item, "error": None}

        entry = {
            "product_id": product.id,
            "barcode": product.barcode,
            "name": product.name,
            "quantity": quantity,
            "unit_price": product.sale_price,
            "subtotal": int(product.sale_price * quantity),
        }
        self._cart.append(entry)
        return {"success": True, "data": entry, "error": None}

    def _calculate_total(self) -> int:
        """Sum all cart subtotals (int, whole ARS pesos)."""
        return sum(item["subtotal"] for item in self._cart)
