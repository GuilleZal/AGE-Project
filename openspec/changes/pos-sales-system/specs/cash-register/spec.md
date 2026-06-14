# cash-register Specification

## Purpose

Cash register lifecycle: open with initial amount, track all cash movements during session, close with physical cash counting (actual vs expected), and enforce single-active-register constraint.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| CR-01 | Open Register | MUST | Enter initial amount (≥0); record opening_time; set status=open; timestamp |
| CR-02 | Single Active Enforcement | MUST | Only one register open at a time; if open exists, block opening with alert |
| CR-03 | Cash Movement Registration | MUST | Record movements: sale_cash (auto on cash sale), return (auto on return), supplier_payment, expense (manual) |
| CR-04 | Close Register | MUST | Enter actual counted amount; system computes expected = initial + sum(inflows) − sum(outflows) and difference = actual − expected; enter reason; set status=closed, closing_time |
| CR-05 | Sales Block on Closed Register | MUST | With no open register, block new sales; show "Abra la caja primero" |
| CR-06 | Register History | SHOULD | View past closed registers (read-only) with amounts, times, differences |
| CR-07 | In-Session Balance Display | MUST | Show real-time: initial amount, cash sales total, returns total, outflows total, expected balance |

## Scenarios

### CR-01: Open Register

- **Happy path**: GIVEN no open register, WHEN cashier enters initial=5000 and confirms, THEN register opens with status=open, opening_time=now.
- **Zero initial**: GIVEN initial amount=0, WHEN confirmed, THEN allowed (register with no starting cash).
- **Negative initial**: GIVEN initial amount=-100, WHEN confirmed, THEN reject "El monto inicial debe ser ≥ 0".

### CR-02: Single Active Enforcement

- **Already open**: GIVEN a register with status=open exists, WHEN cashier tries to open another, THEN reject "Ya hay una caja abierta".
- **Close then reopen**: GIVEN register is closed, WHEN cashier opens new register, THEN allowed (new session).

### CR-03: Cash Movement Registration

- **Sale cash (auto)**: GIVEN open register, WHEN cash sale completes, THEN system creates cash_movement (type=sale_cash, amount=sale_total) linked to current register.
- **Return (auto)**: GIVEN open register, WHEN return completes, THEN system creates cash_movement (type=return, amount=refund) linked to current register.
- **Manual outflow**: GIVEN open register, WHEN cashier registers type=expense amount=500 description="Luz", THEN movement recorded, expected balance updated.

### CR-04: Close Register

- **Happy path**: GIVEN open register (initial=5000, sales=15000, returns=2000, outflows=1000 → expected=17000), WHEN cashier counts actual=16900 and enters reason="Cierre de turno", THEN system records difference=-100, closing_time=now, status=closed.
- **Exact match**: GIVEN expected=17000, WHEN actual=17000, THEN difference=0.
- **Missing reason**: GIVEN actual amount entered, WHEN reason is empty, THEN reject "La razón de cierre es obligatoria".
- **No movements**: GIVEN open register with zero transactions, WHEN cashier closes with actual=initial, THEN expected=initial, difference=0.

### CR-05: Sales Block on Closed Register

- **No open register**: GIVEN all registers are closed, WHEN cashier attempts sale, THEN reject "Abra la caja primero".
- **After close**: GIVEN register just closed, WHEN cashier tries new sale, THEN blocked until new register opened.
