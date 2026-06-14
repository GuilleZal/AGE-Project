# POS Sales System — Specifications

## Overview

Desktop POS for a beverage shop in Argentina. ARS ($), whole prices. MVC + Repository + Service. Python 3.12 + CustomTkinter + SQLite (WAL). Direct atomic return policy. Greenfield project — no existing specs.

---

## 1. Sale Management

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| SM-01 | Barcode input via keyboard wedge (Enter-terminated), sanitize whitespace | MUST |
| SM-02 | Product lookup → add to cart qty=1, display name + price, recalc total | MUST |
| SM-03 | Unknown barcode → inline creation: pre-fill barcode, ask name + sale_price only; auto-add to cart | MUST |
| SM-04 | Cart: modify qty, remove items, real-time total, weight products (price × kg) | MUST |
| SM-05 | Payment: cash (change calc), card, transfer, mixed; confirm → deduct stock, persist sale + items, register cash movement, clear cart | MUST |
| SM-06 | Sales NEVER blocked by stock (stock may go negative) | MUST |
| SM-07 | On-screen receipt preview; print optional | SHOULD |

### Data Model

`sales(id, total, discount, payment_method, cash_register_id FK, created_at)` →
`sale_items(id, sale_id FK CASCADE, product_id FK, quantity, unit_price, subtotal)`

### Business Rules

- Stock deduction on sale confirmation; no validation before
- Duplicate scan increment qty; empty barcode ignored; rapid scans (<300ms) debounced
- Cash change = received − total; insufficient → blocked
- Quick-create defaults: cost=0, stock=0, unit_type=unit, threshold=5

### User Interactions

1. Scan/add items → cart populates → adjust qty/remove as needed
2. Select payment method → if cash: enter received → change shown
3. Confirm → receipt preview → cart clears for next sale

### Error Handling

| Condition | Behavior |
|-----------|----------|
| Empty barcode / only whitespace | Ignore |
| Non-numeric barcode chars | Strip; if invalid → "Código no válido" |
| Quick-create: name empty | Block; highlight field |
| Quick-create: price negative | Block; "El precio no puede ser negativo" |
| Cash: received < total | Block; "Monto insuficiente" |

---

## 2. Cash Register

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| CR-01 | Open: mandatory initial amount (≥0), record opening_time, status=open | MUST |
| CR-02 | Single-active enforcement: block second open with alert | MUST |
| CR-03 | Track movements: sale_cash (auto), return (auto), supplier_payment, expense (manual) | MUST |
| CR-04 | Close: mandatory actual counted amount; diff = actual − expected; mandatory reason; status=closed, block new sales | MUST |
| CR-05 | View closed register history (read-only) | SHOULD |

### Data Model

`cash_registers(id, opening_amount, opening_time, closing_amount, closing_time, expected_amount, difference, close_reason, status)` →
`cash_movements(id, cash_register_id FK, type, amount, description, created_at)`

### Business Rules

- Expected = initial + Σcash_sales − Σreturns − Σoutflows
- Sale blocked when no register open; "Abra la caja primero"
- All sales/returns reference active cash_register_id

### User Interactions

1. Open register → enter initial cash → confirm
2. During session: view real-time balance (initial, inflows, outflows, expected)
3. Register manual outflows (expense/supplier)
4. Close: count physical cash → enter actual → see difference → enter reason → confirm

### Error Handling

| Condition | Behavior |
|-----------|----------|
| initial_amount < 0 | Block; "El monto inicial no puede ser negativo" |
| Second open attempt | Block; "Ya existe una caja abierta" |
| Close: actual_amount empty | Block; "Debe ingresar el monto contado" |
| Close: reason empty | Block; "Debe ingresar un motivo de cierre" |

---

## 3. Product Return

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| PR-01 | Product lookup by barcode or name search | MUST |
| PR-02 | Default qty=1; refund = current sale_price × qty | MUST |
| PR-03 | On confirm: restore stock (+qty), record return, register cash_movement (type=return) | MUST |
| PR-04 | No original sale linkage (atomic); references active cash_register_id | MUST |
| PR-05 | Optional reason field | SHOULD |

### Data Model

`returns(id, product_id FK, quantity, refund_amount, reason, cash_register_id FK, created_at)`

### Business Rules

- Refund uses CURRENT price, not historical
- No upper stock cap on restoration
- No quick-create in return flow (unlike sales)

### User Interactions

1. Open Returns tab → scan barcode or search product
2. System shows name + current price → enter qty → optional reason
3. Confirm → stock restored → cash movement recorded → receipt preview

### Error Handling

| Condition | Behavior |
|-----------|----------|
| Product not found | "Producto no encontrado"; offer name search |
| qty ≤ 0 | Block; "La cantidad debe ser mayor a 0" |
| No active register | Block; "No hay caja abierta" |

---

## 4. Product Catalog

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| PC-01 | Create: name, sale_price (≥0), cost_price (≥0), unit_type mandatory; barcode optional but unique | MUST |
| PC-02 | Edit: all fields; barcode change blocked if duplicate; auto-update updated_at | MUST |
| PC-03 | Delete: blocked if product has sales OR purchases; else physical delete | MUST |
| PC-04 | Category CRUD: unique name; delete blocked if products associated | MUST |
| PC-05 | Search by barcode (exact), name (LIKE), category; low-stock highlight | MUST |

### Data Model

`categories(id, name UNIQUE, created_at)` ← `products(id, barcode UNIQUE, name, category_id FK, sale_price, cost_price, stock DEFAULT 0, unit_type CHECK(unit/weight_kg/pack), description, low_stock_threshold DEFAULT 5, created_at, updated_at)`

### Business Rules

- Barcode nullable (products without barcode OK)
- Delete-protection: transaction history check
- Low-stock alert when stock ≤ threshold

### User Interactions

1. Products tab → list/search → Add/Edit/Delete buttons
2. Create: fill form → validate barcode uniqueness → confirm
3. Edit: select row → modify → confirm
4. Delete: confirm dialog → history check → delete or block

### Error Handling

| Condition | Behavior |
|-----------|----------|
| Duplicate barcode | Block; "El código de barras ya existe" |
| Delete: has transactions | Block; "Tiene historial. Configure stock=0." |
| Category delete: has products | Block; "La categoría tiene productos asociados." |
| Invalid unit_type | Block; list valid values |

---

## 5. Excel Import

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| EI-01 | Template download: .xlsx with columns [barcode, name, sale_price, cost_price, stock, unit_type] | MUST |
| EI-02 | Header validation: exact match required; reject mismatch | MUST |
| EI-03 | Row validation: prices/stock numeric ≥0; no nulls; unit_type in (unit, weight_kg, pack) | MUST |
| EI-04 | Upsert: barcode not in DB → CREATE; barcode exists → UPDATE (price, cost, stock, unit_type; name NOT updated) | MUST |
| EI-05 | Duplicate barcode within file → error | MUST |
| EI-06 | Transactional: valid rows all-or-nothing | MUST |
| EI-07 | Preview first 10 rows; summary: "X creados, Y actualizados, Errores en filas: Z" | MUST |

### Business Rules

- Name is CREATE-only on upsert (not overwritten)
- File-level errors (headers) reject entire file; row errors skip that row only
- Intra-file barcode duplicates flagged

### User Interactions

1. Products tab → "Importar Excel" → download template if needed
2. Select .xlsx file → header validation → preview 10 rows
3. Review errors → confirm import → summary shown

### Error Handling

| Condition | Behavior |
|-----------|----------|
| Not .xlsx | Block; "Formato no soportado. Use .xlsx" |
| Headers mismatch | Reject file; list expected vs found |
| Row: non-numeric price | Flag row; report field + value |
| Row: invalid unit_type | Flag row; list allowed values |
| Intra-file duplicate barcode | Both rows flagged |
| DB error during upsert | Rollback all |

---

## 6. Sales Reports

### Requirements

| # | Requirement | RFC 2119 |
|---|-------------|----------|
| SR-01 | Periods: Today, This week, This month, multi-month, multi-year, custom range | MUST |
| SR-02 | Metrics: total revenue, sale count, average ticket, top 10 products (by qty & revenue) | MUST |
| SR-03 | Profit: revenue − cost, gross profit, margin %; breakdown by product/category | MUST |
| SR-04 | Filters: payment method, category (optional) | SHOULD |
| SR-05 | CSV export (semicolon delimiter, UTF-8 BOM) | MUST |
| SR-06 | Performance: 1-year / 10k sales in <3s | MUST |

### Business Rules

- Cost = sum(cost_price × quantity) per product sold
- Margin % = (profit / revenue) × 100
- Division by zero: show 0% when revenue=0
- Empty period: show "Sin ventas en el período seleccionado"

### User Interactions

1. Reports tab → select period (preset or custom)
2. Optionally filter by payment method / category
3. View metrics + top 10 + profit breakdown
4. Export to CSV

### Error Handling

| Condition | Behavior |
|-----------|----------|
| from > to | Block; "Fecha desde > fecha hasta" |
| No sales in period | Display "Sin ventas..." (not an error) |
| CSV write denied | "Verifique permisos de escritura" |
| Query >5s | Warning; suggest narrower range |

---

## Cross-Cutting Rules

| Rule | Detail |
|------|--------|
| **Currency** | ARS ($), whole numbers (INTEGER) |
| **Stock** | Never blocks sales; stock ≤ threshold → UI highlight |
| **Audit** | Every sale/return linked to cash_register_id; cash movements track all events |
| **Locale** | Spanish UI; CSV semicolons + UTF-8 BOM |
| **Concurrency** | Single-user, single-PC; SQLite WAL mode |
| **DB Protection** | FK ON, CASCADE on sale_items/purchase_items; WAL journal |
