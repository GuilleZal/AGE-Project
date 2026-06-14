# Proposal: Desktop POS Sales System (MVP)

## Intent

Build a desktop POS for a small beverage/product shop in Argentina. The owner needs: barcode-driven sales with instant checkout, simple returns, cash register control, product management, and basic reports. Current state: no system exists — everything is manual. MVP must be usable from day one, even without a barcode scanner or thermal printer.

## Scope

### In Scope (MVP)
- **Sales**: barcode scan (keyboard wedge), manual entry, cart with real-time total, cash/card/transfer/mixed payments, change calculation, no stock blocking during sale
- **Quick product creation**: unknown barcode → create product inline (name + price) without leaving sale view
- **Cash register**: open/close with initial amount, cash counting (actual vs expected), expense/supplier-payment outflows, single active register
- **Direct returns**: atomic return (no original sale linkage), barcode lookup, restores stock, registers cash outflow
- **Product catalog**: CRUD with uniqueness validation, categories, transaction-history delete protection
- **Excel import**: batch product import/update via .xlsx with row-by-row validation and upsert logic
- **Reports**: sales and profit reports by period (today/week/month/custom range), top products, CSV export
- **Products without barcode**: name search, weight-in-kg with auto-calculated price, quick-access buttons for frequent items
- **Backup**: automated daily SQLite backup, 30-day retention, no UI needed

### Out of Scope
- Thermal printer (on-screen receipt preview only; "Don't print" by default)
- Fiscal module (ARCA/AFIP)
- Customer accounts / credit ("fiado")
- Barcode label generation/printing
- Serial scale integration
- Multi-register network sales
- Crash recovery (cart lost on crash; cashier starts fresh)
- Suppliers & purchases (P3 — deferred to v1.1)

## Domain Constraints

- **Currency**: ARS ($), whole prices only, no decimals
- **Locale**: Argentina, UI language Spanish
- **Stock policy**: Sales never blocked by stock level; stock is for admin visibility only
- **Return policy**: Direct Atomic Return — cash register session linkage only, no original sale tracking

## Capabilities

### New Capabilities
- `sale-management`: POS terminal flow, barcode scanning, cart, payment, quick product creation
- `cash-register`: Open/close lifecycle, cash counting, outflow registration, single-active enforcement
- `product-return`: Direct atomic return, stock restoration, cash movement tracking
- `product-catalog`: Product and category CRUD with integrity validations
- `excel-import`: Batch product import from .xlsx with upsert logic
- `sales-reports`: Sales and profit reports by date range, CSV export

### Modified Capabilities
None — greenfield project.

## Approach

**Architecture**: MVC + Repository + Service. Models are plain dataclasses. Repositories encapsulate SQLite. Services hold pure business logic (stock, reports, discount). Views use CustomTkinter. Controllers orchestrate without UI dependency.

**Stack**: Python 3.12, CustomTkinter (UI), SQLite (DB, WAL mode, foreign keys ON). Dependencies: `customtkinter`, `openpyxl`, `pyserial` (optional serial scanner). No `python-escpos` (printer out of MVP).

**Barcode**: Keyboard wedge via `<Return>` binding on focused Entry widget. Optional serial scanner via `pyserial`.

**Tables**: Data tables use `ttk.Treeview` styled to match CustomTkinter theme.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pos/` | New | Full MVC project from scratch |
| `pos/model/` | New | Dataclasses + DB schema (8 tables) |
| `pos/repository/` | New | SQLite data access layer |
| `pos/service/` | New | Business logic (stock, reports, discount) |
| `pos/controller/` | New | Orchestration layer |
| `pos/view/` | New | CustomTkinter UI with ttk.Treeview tables |
| `pos/tests/` | New | pytest with in-memory SQLite fixtures |
| `requirements.txt` | New | Python dependencies |
| `data/` | New | SQLite DB + automated backups |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CustomTkinter lacks Treeview — must mix ttk widgets | Medium | Style ttk.Treeview to match; documented in design |
| Keyboard wedge scanner variability (extra chars, duplicate Enter) | Medium | Input sanitization: strip whitespace, validate numeric-only, debounce rapid scans |
| No crash recovery — cart lost on unexpected close | Low (accepted) | Explicit UX: "start fresh" is simpler; P3 could add draft persistence |
| SQLite single-writer limitation if multi-user ever needed | Low | Acceptable for single-PC POS; migration path to PostgreSQL documented |
| Whole-peso-only prices may lose precision on bulk operations | Low | Use `int` (cent-less ARS); if decimals ever needed, migrate prices × 100 internally |

## Rollback Plan

Since this is a greenfield project, "rollback" means:
1. SQLite daily backups provide point-in-time restore (`data/backups/`)
2. If a feature deployment breaks core sales flow: revert to previous commit, restore DB from most recent backup
3. DB schema uses WAL mode — no corruption on unexpected shutdown
4. `git revert` of any single feature commit is safe (no shared state in greenfield code)

## Dependencies

- Python 3.12 installed on target machine
- `pip install customtkinter openpyxl pyserial`
- Windows OS (primary target; CustomTkinter + pyserial work cross-platform)

## Success Criteria

- [ ] Cashier can complete a sale (scan → cart → pay → receipt preview) in under 10 seconds
- [ ] Unknown barcode triggers inline product creation without leaving sale view
- [ ] Cash register open/close with cash counting works end-to-end (difference detection)
- [ ] Product CRUD + Excel import/update works with integrity validations
- [ ] Reports generate accurate sales/profit data for 1 year of transactions in < 3 seconds
- [ ] All P1 flows pass manual QA; all P2 repository/service layers have ≥ 80% test coverage
- [ ] Daily backup script produces valid, restorable `.zip` files
