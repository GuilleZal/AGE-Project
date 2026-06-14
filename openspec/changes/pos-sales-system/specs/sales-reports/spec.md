# sales-reports Specification

## Purpose

Sales and profit reports by date range. Predefined periods, top products, CSV export. Filter by payment method and category. Performance: 1 year of data under 3 seconds.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| SR-01 | Sales Report by Period | MUST | Predefined periods: Today, This week, This month, Custom months, Custom years, Custom date range (from/to) |
| SR-02 | Sales Metrics | MUST | Total sold (by payment method), number of sales, average ticket, top 10 products by quantity and by amount |
| SR-03 | Profit Report | MUST | Same periods as SR-01; metrics: total revenue, total cost, gross profit, profit margin % |
| SR-04 | Profit Breakdown | SHOULD | Breakdown by product or by category |
| SR-05 | Filter Options | MUST | Filter by payment method (cash, card, transfer), filter by product category |
| SR-06 | CSV Export | MUST | Export report data as .csv (comma-separated, UTF-8 BOM for Excel compatibility) |
| SR-07 | Performance | MUST | Report generation for 1 year, 10k sales completes in < 3 seconds |
| SR-08 | Empty Result Handling | MUST | Show "Sin resultados para el período seleccionado" when no sales exist |

## Scenarios

### SR-01: Sales Report by Period

- **Today**: GIVEN today has 5 sales, WHEN "Today" selected, THEN report shows those 5 sales only.
- **This month**: GIVEN month has sales on days 1-15, WHEN "This month" selected, THEN report spans day 1 to today.
- **Custom range**: GIVEN from=2026-01-01, to=2026-01-31, WHEN generated, THEN report includes all sales in January 2026.
- **Invalid range**: GIVEN from=2026-06-01, to=2026-05-01, WHEN generated, THEN reject "La fecha 'desde' debe ser anterior a 'hasta'".
- **Future date**: GIVEN from=today, to=today+30, WHEN generated, THEN allowed (no upper bound restriction).

### SR-02: Sales Metrics

- **Payment breakdown**: GIVEN 3 cash sales (total=15000) and 2 card sales (total=8000), THEN report shows cash=15000, card=8000, total=23000.
- **Average ticket**: GIVEN 5 sales totaling 25000, THEN average_ticket=5000.
- **Top 10 by quantity**: GIVEN product A sold 50 units, product B sold 30, THEN A ranks first.

### SR-03: Profit Report

- **Profit calc**: GIVEN revenue=100000, cost=60000, THEN gross_profit=40000, margin=40.0%.
- **Zero sales**: GIVEN period has no sales, THEN revenue=0, cost=0, profit=0, margin=N/A.
- **Profit breakdown**: GIVEN "by category" selected, THEN profit grouped by product category.

### SR-05: Filter Options

- **Payment filter**: GIVEN filter payment=cash, WHEN report generated, THEN only cash sales included.
- **Category filter**: GIVEN filter category="Bebidas", WHEN report generated, THEN only products in "Bebidas" included in totals.
- **Combined filters**: GIVEN payment=card AND category="Bebidas", WHEN report generated, THEN only card sales of beverage products included.

### SR-06: CSV Export

- **Export structure**: GIVEN report generated, WHEN "Exportar CSV" clicked, THEN .csv file saved with headers matching report columns, UTF-8 BOM.
- **Empty export**: GIVEN report has no data ("Sin resultados"), WHEN export attempted, THEN .csv with headers only.
