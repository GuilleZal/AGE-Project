# product-return Specification

## Purpose

Direct atomic return: barcode product lookup, quantity selection, refund calculation at current price, stock restoration, and cash movement registration. No original sale linkage required. Linked to current cash register session.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| PR-01 | Product Lookup for Return | MUST | Barcode scan or name search to find product; show name + current sale_price |
| PR-02 | Direct Atomic Return | MUST | No original sale ID required; return linked to current cash_register_id only |
| PR-03 | Refund Calculation | MUST | Refund = current sale_price × quantity (uses current price, not historical) |
| PR-04 | Quantity Input | MUST | Default qty=1; cashier may adjust; must be > 0 and ≤ a reasonable max |
| PR-05 | Stock Restoration | MUST | On confirmation, increment product stock by return quantity |
| PR-06 | Cash Movement Registration | MUST | Register cash_movement type=return (cash outflow from register) |
| PR-07 | Reason Field | MAY | Optional free-text reason for return |
| PR-08 | Return Receipt | MAY | Optional printable return receipt with product, qty, refund, timestamp |

## Scenarios

### PR-01: Product Lookup for Return

- **Barcode scan**: GIVEN barcode `7791234567890` exists, WHEN scanned in return view, THEN product name + current sale_price displayed.
- **Unknown barcode**: GIVEN barcode not found, WHEN scanned in return view, THEN show "Producto no encontrado" (no quick creation in return flow).
- **Name search**: GIVEN cashier types "Coca", WHEN search executed, THEN matching products listed for selection.

### PR-03: Refund Calculation

- **Single item**: GIVEN product price=2000, qty=1, THEN refund=2000.
- **Multiple items**: GIVEN product price=2000, qty=3, THEN refund=6000.
- **Weight product**: GIVEN weight-enabled product price=1000/kg, qty=1.5, THEN refund=1500.

### PR-04: Quantity Input

- **Default**: GIVEN product selected, THEN qty field pre-filled with 1.
- **Zero quantity**: GIVEN qty=0, WHEN confirmed, THEN reject "La cantidad debe ser mayor a 0".
- **Negative quantity**: GIVEN qty=-1, WHEN confirmed, THEN reject "La cantidad debe ser mayor a 0".

### PR-05: Stock Restoration

- **Stock increment**: GIVEN product stock=5, qty returned=3, WHEN return confirmed, THEN stock=8.
- **No stock cap**: GIVEN product stock=100, qty returned=50, WHEN confirmed, THEN stock=150 (no upper limit enforced on return).

### PR-06: Cash Movement Registration

- **Return movement**: GIVEN open cash register, WHEN return of $6000 confirmed, THEN cash_movement created (type=return, amount=-6000), expected register balance decreases by 6000.
- **No open register**: GIVEN no open cash register, WHEN return attempted, THEN reject "Abra la caja primero".
