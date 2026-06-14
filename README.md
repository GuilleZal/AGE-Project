# Sistema POS — Tienda de Bebidas

Sistema de punto de venta para tienda de bebidas y productos relacionados.
Diseñado para Argentina — precios en ARS ($), pesos enteros, facturación simple.

## Características

- **Ventas**: escaneo de código de barras (teclado/serial), carrito editable,
  múltiples métodos de pago (efectivo, tarjeta, transferencia, mixto),
  cálculo automático de vuelto, comprobante en pantalla.
- **Devoluciones**: devolución atómica directa sin vínculo a venta original.
  Restauración automática de stock, registro en caja, motivo opcional.
- **Caja diaria**: apertura con monto inicial, único registro activo,
  registro de movimientos (ventas, devoluciones, gastos, pagos a proveedores),
  cierre con arqueo físico y diferencia. Balance en tiempo real.
- **Productos**: CRUD completo, importación desde Excel con validación y
  vista previa, búsqueda por código/nombre/categoría, soporte para
  productos por unidad, peso (kg) y pack. Creación rápida desde venta.
- **Reportes**: ventas, ganancias brutas, top 10 productos, exportación CSV
  (UTF-8 + BOM, separador punto y coma — convención Excel Argentina).
- **Backup**: script independiente con compresión ZIP y rotación de 30 días.
  Programable desde Windows Task Scheduler.

## Arquitectura

MVC + Repository + Service sobre Python 3.12, CustomTkinter y SQLite (WAL mode).

```
pos/
├── model/          # Dataclasses + enumeraciones + conexión DB
├── repository/     # Consultas SQL parametrizadas
├── service/        # Lógica de negocio pura
├── controller/     # Orquestación (capa de aplicación)
├── view/           # UI — CustomTkinter (CTk)
│   └── widgets/    # Componentes reutilizables
├── tests/          # pytest (base de datos en memoria)
├── scripts/        # backup.py independiente
└── data/           # pos.db + backups/ (runtime)
```

### Principios de diseño

- **Stock no bloqueante**: las ventas nunca se frenan por falta de stock.
  El inventario es visibilidad administrativa, no un freno operativo.
- **Devolución atómica**: sin FK a la venta original. La trazabilidad se
  mantiene vía `cash_register_id`.
- **Transacciones atómicas**: toda venta o devolución se persiste en una
  única transacción SQLite (WAL mode).
- **Separación estricta**: UI no toca la base de datos. Los repositorios
  no conocen la UI. Los servicios no importan CustomTkinter.

## Stack

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12 (no compatible con 3.13+) |
| UI | CustomTkinter ≥ 5.2 |
| Base de datos | SQLite (WAL mode, foreign keys ON) |
| Excel | openpyxl ≥ 3.1 |
| Testing | pytest ≥ 8.0 + pytest-mock |
| Entorno | Windows 10/11 |

## Instalación

Ver [INSTALL.md](INSTALL.md) para la guía paso a paso.

## Tests

```bash
pytest pos/tests/ -v
```

Pruebas unitarias, de integración y end-to-end con base de datos SQLite en memoria.
Sin dependencia de UI para los tests automatizados.

## Backup

```bash
python pos/scripts/backup.py
```

Crea `pos/data/backups/pos_YYYY-MM-DD_HHMM.zip` y elimina backups de más de 30 días.
Ver [docs/backup_scheduling.md](docs/backup_scheduling.md) para programación automática.

## Licencia

Proyecto académico — Universidad Nacional de General Sarmiento (UNGS).
