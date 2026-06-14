# sale-management Specification

## Purpose

POS terminal flow: barcode-driven product lookup, cart management, multi-method payment, inline product creation for unknown barcodes, and manual product entry. Sales never blocked by stock level.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| SM-01 | Barcode Product Lookup | MUST | Accept barcode via keyboard wedge (Enter) or serial scanner; find product; add to cart with qty=1 |
| SM-02 | Manual Product Entry | MUST | Search by name; select from results; add to cart |
| SM-03 | Quick Product Creation | MUST | Unknown barcode → prompt name + sale_price only; create product; auto-add to cart |
| SM-04 | Cart Management | MUST | Display items (product, qty, unit_price, subtotal); real-time total; modify qty; remove items |
| SM-05 | Weight-Based Products | MUST | For unit_type=weight_kg: enter weight (kg, up to 2 decimals); auto-calc subtotal = weight × price |
| SM-06 | Sale Completion | MUST | Payment methods: cash, card, transfer, mixed; cash → enter received → calc change; confirm → deduct stock, create sale+sale_items, register cash movement, clear cart |
| SM-07 | Stock Non-Blocking | SHALL | Sales succeed regardless of stock level; stock may go negative |
| SM-08 | Receipt Preview | SHOULD | Show on-screen receipt preview before printing; "Don't print" default |
| SM-09 | Quick-Access Buttons | MAY | Configurable buttons for frequent products (no barcode needed) |

## Scenarios

### SM-01: Barcode Product Lookup

- **Happy path**: GIVEN barcode `7791234567890` exists, WHEN scanned, THEN product appears in cart with qty=1 and subtotal=sale_price.
- **Unknown barcode**: GIVEN barcode not found, WHEN scanned, THEN trigger SM-03 quick creation flow.
- **Empty/whitespace input**: GIVEN empty entry, WHEN Enter pressed, THEN ignored.
- **Duplicate scan**: GIVEN same product already in cart, WHEN scanned again, THEN increment qty by 1.

### SM-03: Quick Product Creation

- **Minimal fields**: GIVEN unknown barcode `999`, WHEN cashier enters name "Coca-Cola" and price 2000, THEN product created with defaults (unit_type=unit, cost_price=0, stock=0, stock_threshold=5) AND added to cart.
- **Missing name**: GIVEN unknown barcode, WHEN name is empty, THEN reject with "El nombre es obligatorio".
- **Negative price**: GIVEN sale_price entered as -100, THEN reject with "El precio debe ser ≥ 0".

### SM-06: Sale Completion

- **Cash with change**: GIVEN total=5000 and received=10000, WHEN confirmed, THEN show "Cambio: $5000", create sale, deduct stock, clear cart.
- **Insufficient cash**: GIVEN total=5000 and received=3000, WHEN confirmed, THEN reject "Monto insuficiente".
- **Zero received**: GIVEN cash payment and received=0, WHEN confirmed, THEN reject "Ingrese el monto recibido".
- **Card payment**: GIVEN payment=card, WHEN confirmed, THEN sale completes (no change calc).
- **Mixed payment**: GIVEN total=5000, cash=3000 + card=2000, WHEN confirmed, THEN sale completes, change calculated on cash portion only.
- **No items**: GIVEN cart is empty, WHEN "Pay" clicked, THEN reject "Agregue productos al carrito".
- **Negative stock**: GIVEN product stock=2 and qty=5, WHEN confirmed, THEN sale succeeds, stock=-3.

### SM-05: Weight-Based Products

- **Weight entry**: GIVEN product with unit_type=weight_kg and price=1000/kg, WHEN cashier enters weight=1.5, THEN subtotal=1500.
- **Zero weight**: GIVEN weight=0, WHEN entered, THEN reject "El peso debe ser mayor a 0".
