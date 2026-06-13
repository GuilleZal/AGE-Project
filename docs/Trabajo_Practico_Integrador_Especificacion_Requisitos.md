# Trabajo Práctico Integrador: Especificación de Requisitos

## Sistema de Punto de Venta (POS) — AGE Project

---

## 1. Introducción

### 1.1. Propósito

El presente documento tiene como propósito formalizar la especificación de requisitos de software para el **Sistema de Punto de Venta (POS)** del proyecto AGE. Este documento constituye el artefacto de referencia que define, de manera estructurada y verificable, las necesidades funcionales y no funcionales del sistema en su versión MVP (Producto Mínimo Viable).

### 1.2. Ámbito del sistema

**Nombre del sistema**: Sistema de Punto de Venta (POS) — AGE Project

**Función principal**: Gestionar las operaciones de venta de productos (bebidas, alimentos y artículos generales) en un comercio minorista local, abarcando desde el cobro en mostrador hasta el control de stock, la administración de caja y la generación de reportes de gestión.

**Alcance detallado del MVP**:

El sistema abarcará las siguientes funcionalidades dentro del alcance del MVP:

- **Gestión de ventas en mostrador**: cobro de ventas con soporte para múltiples métodos de pago (efectivo, tarjeta, transferencia bancaria y pago mixto), cálculo automático de vuelto, y registro de cada transacción.
- **Control automático de stock**: deducción de inventario al confirmar cada venta, restauración de stock en caso de devoluciones, y seguimiento de entradas (compras a proveedores) y salidas (ventas/devoluciones).
- **Administración de productos y categorías (ABM)**: alta, baja y modificación de productos con validación de unicidad de código de barras, y gestión de categorías con validación de asociaciones.
- **Tipos de unidad**: soporte para tres tipos de unidad de venta — unidad (discreta), peso en kilogramos (weight_kg) y pack (multipack).
- **Control de caja**: apertura y cierre de caja con conteo de efectivo, registro de movimientos de caja (ventas en efectivo, devoluciones, pagos a proveedores, gastos), y cálculo automático de diferencias entre monto esperado y contado.
- **Importación masiva de productos desde Excel**: carga de productos mediante archivos .xlsx con validación estricta de plantilla, detección de duplicados, lógica de upsert (crear/actualizar) y reporte de errores por fila.
- **Reportes básicos de gestión**: reportes de ventas por período (hoy, semana, mes, meses personalizados, años personalizados, rango personalizado), reporte de ganancias (ingresos, costos, margen), top 10 de productos más vendidos, y exportación a CSV.
- **Impresión de comprobantes no fiscales**: impresión automática de recibos de venta en impresora térmica mediante protocolo ESC/POS.
- **Sistema de respaldo diario**: backup automático de la base de datos SQLite con compresión ZIP, retención de 30 días y ejecución programada mediante el Programador de tareas de Windows.

**Exclusiones del MVP (fuera de alcance)**:

Las siguientes funcionalidades quedan expresamente excluidas del alcance del MVP por decisión de negocio y priorización:

- **Módulo fiscal (integración ARCA/AFIP)**: no se implementará facturación electrónica ni emisión de comprobantes con validez fiscal. El sistema emitirá únicamente comprobantes internos no fiscales. Esta exclusión responde a la complejidad regulatoria, la necesidad de certificados digitales y la infraestructura de conectividad requerida, aspectos que serán abordados en una fase posterior.
- **Cuentas corrientes de clientes (fiado)**: no se gestionarán cuentas cliente ni se registrará crédito informal ("fiado"). El sistema opera exclusivamente bajo el modelo de venta al contado.
- **Generación e impresión de etiquetas de código de barras**: no se incluye la funcionalidad de generar ni imprimir etiquetas adhesivas con códigos de barras para productos.
- **Integración con balanzas seriales**: no se contempla la conexión con balanzas electrónicas mediante puerto serial para la venta por peso.
- **Ventas en red con múltiples cajas**: el sistema opera como una aplicación de escritorio autónoma, sin soporte para múltiples terminales de venta conectadas en red.

---

## 2. Descripción General

### 2.1. Perspectiva del producto

El Sistema de Punto de Venta (POS) — AGE Project es un producto de **escritorio autónomo** diseñado para ejecutarse en una estación de trabajo local dentro de un comercio minorista. El sistema no depende de servicios externos en la nube, servidores remotos ni conectividad a internet para su funcionamiento operativo, lo que garantiza disponibilidad continua incluso en ausencia de conexión a la red.

La persistencia de datos se gestiona mediante una base de datos local **SQLite**, que opera como un archivo único dentro del sistema de archivos local, eliminando la necesidad de configurar, administrar o mantener un servidor de base de datos independiente. Esta decisión arquitectónica reduce significativamente la complejidad de despliegue y mantenimiento.

La interfaz de usuario se construye sobre **CustomTkinter**, una biblioteca de interfaz gráfica moderna basada en Tkinter, que proporciona una apariencia contemporánea (esquinas redondeadas, soporte de tema oscuro/claro) sin introducir dependencias de frameworks pesados o licencias restrictivas.

La comunicación con hardware periférico (impresora térmica, escáner de código de barras) se realiza mediante bibliotecas Python estándar del ecosistema: `python-escpos` para la impresora térmica (protocolo ESC/POS vía USB, serial o red) y el modelo de teclado HID (keyboard wedge) para el escáner de código de barras, que no requiere bibliotecas adicionales.

La arquitectura del sistema sigue el patrón **MVC (Modelo-Vista-Controlador)** extendido con capas de **Repositorio** (acceso a datos) y **Servicio** (lógica de negocio), lo que garantiza una separación clara de responsabilidades, facilitando el mantenimiento, la evolución y las pruebas automatizadas.

### 2.2. Funciones del producto

Las funciones principales del sistema se resumen en los siguientes flujos operativos:

1. **Ventas en mostrador**: flujo principal del sistema. El cajero escanea o ingresa manualmente el código de barras del producto, el sistema lo agrega al carrito, calcula subtotales y total en tiempo real, y al confirmar la venta descuenta stock, registra la transacción y emite comprobante. Soporta pago en efectivo (con cálculo de vuelto), tarjeta, transferencia y pago mixto. Si el código de barras no existe en el sistema, se activa un flujo de creación rápida que reutiliza el código escaneado y solicita únicamente nombre y precio de venta.

2. **Devoluciones directas atómicas**: flujo independiente de la venta original. El cajero escanea el código de barras del producto a devolver, ingresa la cantidad y el motivo (opcional), y el sistema calcula el reembolso al precio actual, restaura el stock y registra el movimiento en caja. No requiere vinculación con el ticket de venta original, lo cual se ajusta a la realidad operativa de comercios tipo despensa/kiosco donde los clientes raramente conservan el comprobante.

3. **Control de caja**: apertura de caja con monto inicial, registro de movimientos (entradas por ventas en efectivo, salidas por devoluciones, pagos a proveedores y gastos), y cierre de caja con conteo físico de efectivo, cálculo automático de diferencia (esperado vs. contado) y motivo de cierre. Solo puede existir una caja abierta a la vez.

4. **Importación de productos desde Excel**: carga masiva de productos desde archivos .xlsx con una plantilla estricta. El sistema valida que los encabezados coincidan exactamente con la plantilla esperada (rechazo total del archivo si no coinciden), valida fila por fila los tipos de datos y campos obligatorios, presenta una vista previa de las primeras 10 filas, y ejecuta lógica de upsert (crear productos nuevos o actualizar existentes según código de barras).

5. **Reportes de gestión**: generación de reportes de ventas y ganancias con selección de períodos predefinidos (hoy, semana actual, mes actual) y personalizados (meses específicos, años específicos, rango manual de fechas). Incluye métricas de total vendido, cantidad de ventas, ticket promedio, top 10 de productos más vendidos, ingresos, costos, ganancia bruta y margen de ganancia. Los reportes son exportables a formato CSV.

### 2.3. Características de los usuarios

El sistema contempla tres perfiles de usuario diferenciados:

#### Perfil 1: Cajero/a — Secretaria

- **Rol operativo**: es el usuario principal durante la jornada de atención al público. Opera exclusivamente desde la terminal de punto de venta.
- **Responsabilidades**: procesar ventas, registrar devoluciones, abrir y cerrar caja, registrar movimientos de caja.
- **Nivel técnico**: bajo. No requiere conocimientos técnicos. Debe poder operar el sistema de forma fluida e intuitiva, con interacciones mínimas (escaneo de código de barras, ingreso de cantidades, confirmación de pago).
- **Interacción principal**: vista de ventas (pantalla principal), vista de devoluciones, vista de caja.
- **Principio rector de su experiencia**: durante la venta, máxima fluidez. Ninguna alerta de stock debe interrumpir al cajero. La gestión de stock se realiza en reportes y administración, no durante la venta.

#### Perfil 2: Encargado/a — Gerente

- **Rol de gestión**: supervisa la operación del comercio, gestiona el catálogo de productos, genera reportes y controla los cierres de caja.
- **Responsabilidades**: administración de productos y categorías (ABM), importación masiva de productos desde Excel, generación de reportes de ventas y ganancias, revisión de diferencias de caja.
- **Nivel técnico**: medio-bajo. Requiere familiarity con operaciones de gestión pero no con aspectos técnicos del sistema.
- **Interacción principal**: vista de productos, vista de reportes, vista de caja (revisión).

#### Perfil 3: Administrador / Propietario

- **Rol estratégico**: tiene acceso total al sistema, incluyendo todas las funciones operativas y de gestión, más la configuración general del sistema, la administración de proveedores, el registro de compras y la gestión de respaldos.
- **Responsabilidades**: todas las anteriores, más gestión de proveedores, registro de compras a proveedores, configuración de parámetros del sistema (umbral de stock bajo, configuración de impresora), y supervisión general del negocio.
- **Nivel técnico**: variable. Puede requerir asistencia para la configuración inicial de hardware (impresora, escáner) y del sistema de respaldos.
- **Interacción principal**: todas las vistas del sistema, incluyendo proveedores, compras y configuración.

### 2.4. Restricciones

El sistema está sujeto a las siguientes restricciones técnicas y de diseño:

1. **Base de datos local SQLite**: la persistencia se implementa exclusivamente mediante SQLite, almacenada como un archivo local (`data/pos.db`). No se utilizarán motores de base de datos externos ni servicios de base de datos en red. La configuración incluye journal mode WAL (Write-Ahead Logging) para mejor rendimiento y foreign keys habilitadas para integridad referencial.

2. **Interfaz de usuario CustomTkinter**: la interfaz gráfica se construye sobre CustomTkinter (biblioteca MIT sobre Tkinter). Para las tablas de datos (carrito de compras, listado de productos), se utilizará `tkinter.ttk.Treeview` estilizado para coincidir con el tema de CustomTkinter, dado que CustomTkinter no provee un widget de tabla nativo.

3. **Validaciones estrictas de importación Excel**: la importación de productos desde archivos .xlsx sigue un modelo de validación estricta en dos niveles: (a) validación de encabezados — si los encabezados del archivo no coinciden exactamente con la plantilla esperada, el archivo completo es rechazado; (b) validación fila por fila — tipos de datos numéricos, campos obligatorios no nulos, valores de unit_type dentro del conjunto permitido.

4. **Principio de UX — Máxima fluidez en el cobro sin alertas de stock**: durante el flujo de venta, el sistema NO debe interrumpir al cajero con alertas, advertencias o bloqueos relacionados con el nivel de stock. Las ventas se procesan exitosamente independientemente del stock disponible (incluso con stock = 0). La gestión de stock (alertas de stock bajo, reportes de inventario) se realiza exclusivamente en las vistas de administración y reportes, nunca durante la operación de cobro.

5. **Arquitectura MVC + Repositorio + Servicio**: el sistema sigue estrictamente el patrón Modelo-Vista-Controlador extendido con capas de Repositorio (encapsulamiento de consultas SQL) y Servicio (lógica de negocio pura, sin dependencia de UI). Los modelos son dataclasses planos, sin ORM.

6. **Stack tecnológico fijo**: Python 3.12 (estabilidad con hardware), CustomTkinter (interfaz moderna), SQLite (persistencia local), python-escpos (impresora térmica). Las dependencias externas se limitan a 5 paquetes: `customtkinter`, `python-escpos`, `python-barcode`, `Pillow`, `pyserial`.

7. **Plataforma**: el sistema opera exclusivamente en sistema operativo Windows, utilizando el Programador de tareas de Windows para la automatización del respaldo diario.

---

## 3. Requisitos específicos

### 3.1. Funciones

Los requisitos funcionales se presentan organizados por prioridad (P1: crítico para la operación, P2: necesario para la gestión, P3: opcional/deseable) y se expresan en el formato estándar de ingeniería de requisitos.

---

#### 3.1.1 Módulo de Ventas (P1 — Crítico para la operación)

**REQ-V001**: El sistema debe permitir agregar ítems al carrito de compras mediante escáner de código de barras (keyboard wedge USB) o entrada manual del código.

- **Criterios de aceptación**:
  - CA-V001-01: El campo de entrada de código de barras captura automáticamente la lectura del escáner USB mediante binding al evento Enter (keyboard wedge).
  - CA-V001-02: El cajero puede ingresar manualmente el código de barras en el campo de entrada cuando el escáner no está disponible.
  - CA-V001-03: Al presionar Enter tras el escaneo o ingreso manual, el sistema busca el producto por código de barras y lo agrega al carrito si es encontrado.
  - CA-V001-04: El campo de código de barras se limpia automáticamente tras cada escaneo exitoso para permitir el siguiente escaneo inmediato.

**REQ-V002**: El sistema debe activar un flujo de creación rápida de producto cuando el código de barras escaneado no corresponde a ningún producto existente en la base de datos.

- **Criterios de aceptación**:
  - CA-V002-01: Al escanear un código de barras no registrado, el sistema presenta automáticamente un formulario de creación rápida sin navegar fuera de la vista de ventas.
  - CA-V002-02: El campo de código de barras del formulario de creación rápida se completa automáticamente con el código escaneado y no es editable durante la creación.
  - CA-V002-03: El formulario de creación rápida solicita únicamente: nombre del producto (obligatorio) y precio de venta (obligatorio, valor predeterminado = 0).
  - CA-V002-04: Ningún otro campo (categoría, precio de costo, stock, tipo de unidad, umbral de stock bajo) es requerido durante la creación rápida; todos utilizan valores predeterminados.
  - CA-V002-05: Tras confirmar la creación, el producto se crea en la base de datos y se agrega automáticamente al carrito de compras actual sin requerir re-escaneo.
  - CA-V002-06: Los campos no completados durante la creación rápida pueden ser editados posteriormente desde la vista de administración de productos (ABM).

**REQ-V003**: El sistema debe permitir ajustar la cantidad de cada ítem en el carrito y mostrar el subtotal por ítem y el total general en tiempo real.

- **Criterios de aceptación**:
  - CA-V003-01: El carrito muestra para cada ítem: nombre del producto, cantidad, precio unitario y subtotal.
  - CA-V003-02: El total general se recalcula automáticamente al agregar, modificar cantidad o eliminar ítems del carrito.
  - CA-V003-03: El cajero puede modificar la cantidad de un ítem ya agregado al carrito (valor por defecto: 1).
  - CA-V003-04: El cajero puede eliminar un ítem del carrito antes de confirmar la venta.

**REQ-V004**: El sistema debe procesar ventas independientemente del nivel de stock disponible, sin bloqueos ni alertas durante el flujo de cobro.

- **Criterios de aceptación**:
  - CA-V004-01: La venta se completa exitosamente incluso si el stock del producto es 0 o insuficiente.
  - CA-V004-02: El sistema NO muestra alertas, advertencias ni diálogos de confirmación relacionados con el nivel de stock durante el flujo de venta.
  - CA-V004-03: El descuento de stock se realiza automáticamente al confirmar la venta, independientemente del valor resultante (puede quedar negativo).
  - CA-V004-04: Las alertas de stock bajo se muestran exclusivamente en la vista de reportes/administración, nunca durante la venta.

**REQ-V005**: El sistema debe soportar múltiples métodos de pago: efectivo, tarjeta, transferencia bancaria y pago mixto, con cálculo automático de vuelto para pagos en efectivo.

- **Criterios de aceptación**:
  - CA-V005-01: El cajero puede seleccionar el método de pago entre: efectivo, tarjeta, transferencia bancaria y mixto.
  - CA-V005-02: Para pago en efectivo, el sistema presenta un campo "Monto recibido" y calcula automáticamente el vuelto (vuelto = monto recibido - total).
  - CA-V005-03: Para pago con tarjeta o transferencia, el sistema registra el método de pago sin cálculo de vuelto.
  - CA-V005-04: Para pago mixto, el sistema permite combinar múltiples métodos de pago hasta cubrir el total.
  - CA-V005-05: Al confirmar la venta, el sistema registra la venta en la tabla `sales`, los ítems en `sale_items`, y el movimiento de caja correspondiente (si aplica pago en efectivo).
  - CA-V005-06: Tras la confirmación exitosa de la venta, el carrito se limpia automáticamente para la siguiente venta.
  - CA-V005-07: El sistema imprime automáticamente el comprobante en impresora térmica (función opcional, puede deshabilitarse).

---

#### 3.1.2 Módulo de Devoluciones Directas (P1 — Crítico para la operación)

**REQ-V006**: El sistema debe permitir procesar devoluciones de productos de forma directa y atómica, sin vinculación con la venta original, utilizando únicamente la sesión de caja activa como referencia.

- **Criterios de aceptación**:
  - CA-V006-01: El cajero puede buscar el producto a devolver mediante escaneo de código de barras (mismo flujo que en ventas) o búsqueda por nombre como alternativa.
  - CA-V006-02: El sistema muestra el nombre del producto y el precio actual de venta.
  - CA-V006-03: El campo de cantidad tiene un valor por defecto de 1 y es editable.
  - CA-V006-04: El sistema calcula el monto de reembolso como: precio_de_venta_actual × cantidad.
  - CA-V006-05: El campo de motivo es opcional (texto libre).
  - CA-V006-06: Al confirmar la devolución, el sistema restaura el stock del producto (incrementa la cantidad).
  - CA-V006-07: Al confirmar la devolución, el sistema registra la devolución en la tabla `returns` vinculada al `cash_register_id` de la sesión activa.
  - CA-V006-08: Al confirmar la devolución, el sistema registra un movimiento de caja de tipo "return" (salida de efectivo).
  - CA-V006-09: La devolución NO requiere el ID de la venta original (flujo atómico).
  - CA-V006-10: El comprobante de devolución es opcional (imprimible bajo demanda).

---

#### 3.1.3 Módulo de Control de Caja (P1 — Crítico para la operación)

**REQ-V007**: El sistema debe permitir la apertura de caja registrando el monto inicial en efectivo y la marca de tiempo de apertura, con validación de caja única.

- **Criterios de aceptación**:
  - CA-V007-01: El campo "Monto inicial" es obligatorio y debe ser mayor o igual a 0.
  - CA-V007-02: Al confirmar la apertura, el sistema registra la marca de tiempo de apertura y establece el estado en "open".
  - CA-V007-03: Solo puede existir una caja abierta a la vez. Si se intenta abrir una segunda caja, el sistema muestra la alerta: "Ya existe una caja abierta".
  - CA-V007-04: Tras la apertura, la vista de caja muestra los movimientos en tiempo real.

**REQ-V008**: El sistema debe permitir registrar salidas de efectivo de la caja (pagos a proveedores, gastos) durante una sesión de caja abierta.

- **Criterios de aceptación**:
  - CA-V008-01: Con una caja abierta, el cajero puede registrar un movimiento de salida seleccionando el tipo: `supplier_payment` o `expense`.
  - CA-V008-02: El cajero ingresa el monto y una descripción del movimiento.
  - CA-V008-03: Al confirmar, el sistema registra el movimiento en la tabla `cash_movements` y actualiza el saldo esperado de la caja.

**REQ-V009**: El sistema debe permitir el cierre de caja con conteo de efectivo físico, cálculo automático de diferencia y registro de motivo de cierre.

- **Criterios de aceptación**:
  - CA-V009-01: La vista de cierre muestra: monto inicial, ventas en efectivo, devoluciones, salidas y saldo esperado.
  - CA-V009-02: El campo "Monto contado" (efectivo físico real en caja) es obligatorio.
  - CA-V009-03: El sistema calcula automáticamente la diferencia: diferencia = monto_contado - saldo_esperado.
  - CA-V009-04: El campo "Motivo de cierre" es obligatorio.
  - CA-V009-05: Al confirmar el cierre, el sistema actualiza el estado a "closed", registra la marca de tiempo de cierre, el monto contado, la diferencia y el motivo.
  - CA-V009-06: Con la caja cerrada, el sistema bloquea el registro de nuevas ventas y movimientos hasta la próxima apertura.
  - CA-V009-07: El historial de cajas anteriores es accesible en modo solo lectura.

---

#### 3.1.4 Módulo de Productos y Categorías (P2 — Necesario para la gestión)

**REQ-V010**: El sistema debe permitir la creación de productos con validación de unicidad de código de barras y campos obligatorios definidos.

- **Criterios de aceptación**:
  - CA-V010-01: Los campos obligatorios para crear un producto son: nombre, precio de venta, precio de costo y tipo de unidad.
  - CA-V010-02: El código de barras debe ser único; el sistema valida que no exista un producto con el mismo código antes de crear.
  - CA-V010-03: La categoría es seleccionable desde un desplegable (con opción de crear nueva categoría inline).
  - CA-V010-04: El stock inicial tiene un valor predeterminado de 0 si no se especifica.
  - CA-V010-05: El umbral de stock bajo tiene un valor predeterminado de 5 si no se especifica.

**REQ-V011**: El sistema debe permitir la edición de productos existentes, actualizando automáticamente la marca de tiempo de modificación.

- **Criterios de aceptación**:
  - CA-V011-01: La edición permite modificar todos los campos del producto, excepto el código de barras si el nuevo valor ya existe en otro producto.
  - CA-V011-02: Al confirmar la edición, el sistema actualiza automáticamente el campo `updated_at` con la marca de tiempo actual.

**REQ-V012**: El sistema debe permitir la eliminación de productos con validación de historial transaccional.

- **Criterios de aceptación**:
  - CA-V012-01: Si el producto tiene ventas o compras registradas, el sistema bloquea la eliminación y muestra el mensaje: "El producto tiene historial transaccional y no puede ser eliminado. Establezca el stock en 0 en su lugar."
  - CA-V012-02: Si el producto no tiene historial transaccional, el sistema procede con la eliminación física del registro.

**REQ-V013**: El sistema debe permitir la búsqueda y listado de productos con filtros y ordenamiento.

- **Criterios de aceptación**:
  - CA-V013-01: El listado de productos permite buscar por código de barras, nombre o categoría.
  - CA-V013-02: El listado permite ordenar por columnas.
  - CA-V013-03: Si el listado supera los 50 productos, se implementa paginación.

**REQ-V014**: El sistema debe permitir la administración completa (ABM) de categorías con validación de asociaciones a productos.

- **Criterios de aceptación**:
  - CA-V014-01: La creación de categoría requiere un nombre único (validación de duplicados).
  - CA-V014-02: La edición permite modificar el nombre de la categoría.
  - CA-V014-03: Si la categoría tiene productos asociados, el sistema bloquea la eliminación y muestra el mensaje: "La categoría tiene productos asociados y no puede ser eliminada."
  - CA-V014-04: El listado de categorías muestra la cantidad de productos asociados a cada una.

---

#### 3.1.5 Módulo de Importación desde Excel (P2 — Necesario para la gestión)

**REQ-V015**: El sistema debe permitir la descarga de una plantilla Excel (.xlsx) con la estructura exacta de columnas requerida para la importación masiva de productos.

- **Criterios de aceptación**:
  - CA-V015-01: El sistema genera un archivo .xlsx con las columnas exactas: `barcode`, `name`, `sale_price`, `cost_price`, `stock`, `unit_type`.

**REQ-V016**: El sistema debe validar estrictamente el archivo Excel cargado, rechazando archivos con formato de plantilla incorrecto y validando cada fila individualmente.

- **Criterios de aceptación**:
  - CA-V016-01: Si los encabezados del archivo cargado no coinciden exactamente con la plantilla esperada, el sistema rechaza el archivo completo con el error: "Formato de plantilla inválido".
  - CA-V016-02: Si los encabezados son correctos, el sistema valida fila por fila: `sale_price`, `cost_price` y `stock` deben ser numéricos (>= 0).
  - CA-V016-03: Los campos obligatorios (`barcode`, `name`, `sale_price`, `cost_price`, `stock`, `unit_type`) no pueden ser nulos.
  - CA-V016-04: El campo `unit_type` debe ser uno de los valores permitidos: `unit`, `weight_kg`, `pack`.
  - CA-V016-05: El sistema muestra una vista previa de las primeras 10 filas antes de confirmar la importación.
  - CA-V016-06: Si existen errores de validación, el sistema muestra un listado de las filas problemáticas con detalle del error.

**REQ-V017**: El sistema debe ejecutar la importación con lógica de upsert (crear o actualizar) y presentar un resumen de resultados.

- **Criterios de aceptación**:
  - CA-V017-01: Si el código de barras no existe en la base de datos, el sistema crea un nuevo producto.
  - CA-V017-02: Si el código de barras ya existe, el sistema actualiza los campos: `sale_price`, `cost_price`, `stock`, `unit_type`.
  - CA-V017-03: La importación se ejecuta como transacción (todo o nada para las filas válidas).
  - CA-V017-04: Tras la importación, el sistema muestra un resumen: "X productos creados, Y actualizados, Errores en filas: Z, W".

---

#### 3.1.6 Módulo de Reportes (P2 — Necesario para la gestión)

**REQ-V018**: El sistema debe generar reportes de ventas por período con métricas de resumen y filtros opcionales.

- **Criterios de aceptación**:
  - CA-V018-01: El sistema ofrece selección de período predefinido: Hoy, Esta semana, Este mes.
  - CA-V018-02: El sistema ofrece selección de meses personalizados (permitiendo seleccionar meses específicos).
  - CA-V018-03: El sistema ofrece selección de años personalizados (permitiendo seleccionar años específicos).
  - CA-V018-04: El sistema ofrece un rango de fechas personalizado (desde/hasta) como opción de respaldo manual.
  - CA-V018-05: El reporte incluye filtro opcional por método de pago.
  - CA-V018-06: El reporte incluye filtro opcional por categoría de producto.
  - CA-V018-07: Las métricas del reporte incluyen: total vendido (desglose por método de pago), cantidad de ventas, ticket promedio.
  - CA-V018-08: El reporte incluye el top 10 de productos más vendidos (por cantidad y por monto).

**REQ-V019**: El sistema debe generar reportes de ganancias con desglose por producto o categoría.

- **Criterios de aceptación**:
  - CA-V019-01: El reporte de ganancias ofrece las mismas opciones de período que el reporte de ventas (predefinido, meses personalizados, años personalizados, rango manual).
  - CA-V019-02: Las métricas del reporte incluyen: ingresos totales, costos totales, ganancia bruta (ingresos - costos), margen de ganancia (porcentaje).
  - CA-V019-03: El reporte muestra desglose de ganancias por producto o por categoría.
  - CA-V019-04: El reporte es exportable a formato CSV (compatible con Excel).

**REQ-V020**: Los reportes deben cumplir con requisitos de rendimiento mínimo.

- **Criterios de aceptación**:
  - CA-V020-01: Un reporte de 1 año con 10.000 ventas se genera en menos de 3 segundos.

---

#### 3.1.7 Módulo de Proveedores y Compras (P3 — Opcional/Deseable)

**REQ-V021**: El sistema debe permitir la administración completa (ABM) de proveedores.

- **Criterios de aceptación**:
  - CA-V021-01: La creación de proveedor requiere el nombre como campo obligatorio; CUIT, teléfono, dirección y email son opcionales.
  - CA-V021-02: La edición permite modificar todos los campos del proveedor.
  - CA-V021-03: Si el proveedor tiene compras registradas, el sistema bloquea la eliminación con alerta: "El proveedor tiene historial transaccional".
  - CA-V021-04: El listado de proveedores permite buscar por nombre o CUIT.

**REQ-V022**: El sistema debe permitir registrar compras a proveedores con actualización automática de stock.

- **Criterios de aceptación**:
  - CA-V022-01: El registro de compra requiere selección de proveedor desde un desplegable y fecha de compra (valor por defecto: fecha actual).
  - CA-V022-02: El usuario puede agregar ítems a la compra: producto + cantidad + costo unitario.
  - CA-V022-03: El sistema calcula automáticamente el subtotal por ítem y el total general.
  - CA-V022-04: El campo "Notas" es opcional (texto libre).
  - CA-V022-05: Al confirmar la compra, el sistema crea el registro en las tablas `purchases` y `purchase_items`.
  - CA-V022-06: Al confirmar la compra, el sistema agrega stock a los productos correspondientes.
  - CA-V022-07: Al confirmar la compra, el sistema ofrece la opción de registrar un movimiento de caja si el pago es inmediato.
  - CA-V022-08: El listado de compras permite filtrar por proveedor y rango de fechas.

**REQ-V023**: El sistema debe permitir registrar pagos a proveedores como movimientos de caja.

- **Criterios de aceptación**:
  - CA-V023-01: Con una caja abierta, el usuario puede seleccionar una compra pendiente y registrar un pago.
  - CA-V023-02: El sistema registra el movimiento en la tabla `cash_movements` con tipo `supplier_payment`.

---

#### 3.1.8 Requisito No Funcional — Sistema de Respaldos

**REQ-R001**: El sistema debe incluir un mecanismo de respaldo diario automático de la base de datos SQLite.

- **Criterios de aceptación**:
  - CA-R001-01: El respaldo se ejecuta diariamente mediante un script Python independiente, programado con el Programador de tareas de Windows.
  - CA-R001-02: El archivo de base de datos se comprime en formato ZIP con marca de tiempo en el nombre: `pos_YYYY-MM-DD_HHMM.zip`.
  - CA-R001-03: El sistema elimina automáticamente los respaldos con antigüedad mayor a 30 días (política de retención configurable).
  - CA-R001-04: Los respaldos se almacenan en el directorio local `data/backups/`.
  - CA-R001-05: El procedimiento de restauración es manual: copiar el archivo `.db` desde el ZIP de respaldo a `data/pos.db`.
  - CA-R001-06: El sistema de respaldos no requiere interfaz de usuario en el MVP — se ejecuta de forma desatendida (headless).

---

## 4. Apéndices

### 4.1. Plan Global de entrevistas

**Objetivo**: Recopilar información directa del propietario del negocio para validar los requisitos funcionales y no funcionales del sistema, comprender el contexto operativo del comercio y fundamentar las decisiones de diseño y alcance del MVP.

**Entrevistado**: Propietario del comercio (Administrador/Dueño)

**Entrevistador**: Analista de requisitos / Equipo de desarrollo

| N.º | Tema | Objetivos | Duración estimada |
|-----|------|-----------|-------------------|
| 1 | Contexto del negocio y operación diaria | Comprender la naturaleza del comercio, volumen de ventas diario, tipos de productos, horarios de atención y flujo de clientes. | 15 min |
| 2 | Proceso actual de venta en mostrador | Identificar el flujo actual de cobro, métodos de pago aceptados, uso de escáner de código de barras, emisión de comprobantes y manejo de efectivo. | 20 min |
| 3 | Gestión de stock e inventario | Comprender cómo se controla actualmente el inventario: reposición, conteo, alertas de faltante, y cómo se manejan las devoluciones. | 15 min |
| 4 | Control de caja y arqueo | Indagar sobre el proceso de apertura/cierre de caja, conteo de efectivo, registro de movimientos y manejo de diferencias. | 10 min |
| 5 | Necesidades de reportes y gestión | Identificar qué información necesita el propietario para tomar decisiones: ventas del día, ganancias, productos más vendidos, períodos de análisis. | 15 min |
| 6 | Obligaciones fiscales y regulatorias | Consultar sobre la situación actual respecto a facturación electrónica (ARCA/AFIP), si emite facturas, con qué sistema, y si es una necesidad inmediata. | 10 min |
| 7 | Importación y carga inicial de productos | Comprender el volumen del catálogo actual, si existe un listado en Excel, cómo se cargan los productos y si se necesita migración de datos. | 10 min |
| 8 | Hardware disponible y restricciones técnicas | Verificar qué hardware posee (computadora, impresora térmica, escáner de código de barras), sistema operativo, y restricciones de conectividad. | 10 min |
| 9 | Expectativas, prioridades y cronograma | Validar prioridades del MVP, expectativas de tiempo, disposición para un proceso iterativo, y funcionalidades post-MVP deseadas. | 15 min |

**Duración total estimada**: ~120 minutos (2 horas)

**Lugar**: En el local comercial (para observar el contexto operativo real)

**Metodología**: Entrevista semi-estructurada con guía de temas. Se允许 profundizar en temas específicos según las respuestas del entrevistado. Se tomarán notas y se grabará la sesión (con consentimiento) para posterior transcripción y análisis.

---

### 4.2. Informe de entrevistas

**Fecha de la entrevista**: 15 de marzo de 2026

**Lugar**: Local comercial del propietario, ubicado en la ciudad de Buenos Aires

**Entrevistado**: Sr. [Propietario del comercio] — Dueño y administrador del negocio

**Entrevistador**: Equipo de desarrollo del proyecto AGE

---

#### Resumen narrativo de la entrevista

La entrevista se realizó en el local comercial durante una jornada de baja afluencia de clientes, lo que permitió al propietario dedicar tiempo a responder con detalle cada sección. A continuación, se presentan los hallazgos más relevantes organizados por temática.

---

**Sobre el contexto del negocio y la operación diaria:**

El propietario describió un comercio de tipo despensa/kiosco especializado en bebidas (vinos, cervezas, gaseosas) y productos generales. La operación diaria comprende entre 40 y 80 ventas por jornada, con picos los fines de semana. El horario de atención es de lunes a sábados de 9:00 a 20:00. Actualmente, llevan un registro manual de las ventas en una libreta y el control de stock se hace "de memoria" o contando físicamente cuando sospechan que algo se está por agotar. El propietario afirmó: *"No tengo tiempo de contar botellas durante el día, cuando hay clientes no puedo parar a mirar el inventario"*.

---

**Sobre el proceso de venta en mostrador y la fluidez operativa:**

Este fue uno de los puntos más enfáticos de la entrevista. El propietario relató que en momentos de alta demanda (fines de semana, fiestas, cumpleaños), la velocidad de cobro es crítica. *"Si me tardo mucho con un cliente, se me hace fila y se enojan. Necesito que pasar el producto por el escáner y cobrar sea lo más rápido posible, como en un supermercado"*.

Cuando se le consultó sobre las alertas de stock durante la venta, el propietario fue contundente: *"No me avises durante la venta que queda poco stock. Eso me desconcentra y me hace perder tiempo. Yo prefiero ver al final del día o en un reporte qué productos están bajos. Cuando estoy cobrando, lo único que importa es cobrar rápido"*.

Esta respuesta fundamenta directamente el **principio de UX de máxima fluidez en el cobro sin alertas de stock**: el sistema debe permitir vender siempre, incluso cuando el stock sea 0, porque en la práctica del comercio, la venta es prioritaria sobre el control de inventario en el momento del cobro. El control de stock se gestiona en los reportes y la administración, no en la terminal de venta.

---

**Sobre la exclusión del módulo fiscal (ARCA/AFIP):**

Al consultar sobre las obligaciones de facturación electrónica, el propietario explicó su situación actual: *"Honestamente, todavía no estoy inscripto para emitir facturas electrónicas. Tengo monotributo y por ahora manejo todo con recibos internos. Sé que en algún momento voy a tener que tener algo fiscal, pero ahora no es mi prioridad ni estoy preparado para eso"*.

Agregó que ha consultado con su contador, quien le indicó que la integración con ARCA/AFIP requiere certificados digitales, un entorno de facturación electrónica y, en muchos casos, un software certificado o un webservice propio. *"Mi contador me dijo que eso es un proyecto aparte, que necesita su tiempo y su inversión. Prefiero tener primero un sistema que me resuelva el día a día del cobro y el stock, y después vemos lo fiscal"*.

Esta respuesta fundamenta la **decisión de excluir el módulo fiscal del MVP**. La integración con ARCA/AFIP es una funcionalidad compleja que requiere: (a) certificado digital emitido por AFIP, (b) implementación del webservice WSFE (Web Service de Facturación Electrónica), (c) manejo de puntos de venta autorizados, (d) conectividad constante con los servidores de AFIP, y (e) validaciones y contingencias específicas. Incorporar esta funcionalidad al MVP habría incrementado significativamente el alcance, el tiempo de desarrollo y la complejidad técnica, sin aportar valor operativo inmediato al propietario.

Se prevé que el módulo fiscal sea incorporado en una fase posterior (post-MVP), cuando el propietario complete los trámites regulatorios necesarios y el sistema base esté estable.

---

**Sobre el control de caja y el arqueo:**

El propietario describió su proceso actual de cierre de caja: *"Al final del día, cuento la plata que tengo en la caja, le resto lo que puse a la mañana, y veo si coincide con lo que debería tener. A veces falta, a veces sobra, pero necesito saber cuánto"*.

Se le consultó sobre la importancia de registrar movimientos como pagos a proveedores o gastos del local desde la caja. Respondió: *"Sí, a veces pago al delivery de la cerveza en la misma caja, o compro hielo con la plata de la caja. Eso necesito anotarlo, sino nunca me cierran los números"*.

Estas respuestas fundamentan el **módulo de control de caja con apertura, cierre con conteo, cálculo de diferencias y registro de movimientos**. La funcionalidad de conteo de efectivo con comparación esperado vs. contado responde directamente a la necesidad expresada por el propietario de "saber si coincide" al final de cada jornada.

---

**Sobre la importación de productos desde Excel:**

Al consultar sobre el catálogo de productos y cómo se gestionan actualmente, el propietario indicó que tiene un listado en Excel con aproximadamente 300 productos que le pasó un proveedor. *"Tengo una planilla con el código, el nombre y el precio. Pero la actualizo a mano, y cuando cargo un producto nuevo lo anoto en la libreta y después lo paso a la planilla cuando tengo tiempo"*.

Se le preguntó si le resultaría útil poder cargar los productos de forma masiva desde un Excel. Su respuesta fue entusiasta: *"Sí, eso me serviría mucho. El problema es que yo no sé de computadoras, así que necesito que sea fácil. Si me das una plantilla con las columnas que tengo que llenar y me decís qué va en cada una, yo la lleno y la cargo"*.

Cuando se le consultó sobre qué debería pasar si el archivo no está bien formateado, respondió: *"Si me equivoco, decime en qué me equivoqué, pero no me cargues cualquier cosa. Prefiero que me rechace el archivo y me diga qué está mal, a que me cargue datos que después no sé de dónde salieron"*.

Estas respuestas fundamentan el **sistema de importación Excel con validación estricta de plantilla**: (a) descarga de plantilla con columnas predefinidas para guiar al usuario, (b) validación de encabezados con rechazo total del archivo si no coinciden (porque *"no me cargues cualquier cosa"*), (c) validación fila por fila con reporte detallado de errores, y (d) lógica de upsert para permitir actualizaciones masivas de precios sin duplicar productos.

---

**Sobre las devoluciones:**

Al consultar sobre cómo maneja actualmente las devoluciones, el propietario explicó: *"A veces viene un cliente con una botella que no le gustó o que estaba cortada. Le doy el dinero de vuelta ahí mismo, pero no anoto nada. A veces me acuerdo y a veces no"*.

Se le preguntó si sería útil vincular la devolución con la venta original. Respondió: *"La mayoría no trae el ticket. Yo les creo, les tomo el producto y les devuelvo la plata. No necesito buscar en qué venta fue"*.

Esta respuesta fundamenta el **modelo de devolución directa atómica sin vinculación con la venta original**. En la práctica operativa del comercio, los clientes raramente conservan el comprobante, y el propietario no requiere trazabilidad de la venta original para procesar una devolución. La vinculación con la sesión de caja activa (`cash_register_id`) proporciona el nivel de auditoría adecuado para este contexto.

---

**Sobre los reportes y la gestión:**

El propietario expresó interés particular en los reportes: *"Lo que más necesito es saber cuánto vendí en el día, en la semana y en el mes. Y saber cuánto gané, porque a veces vendo mucho pero no sé si estoy ganando o perdiendo"*.

También mencionó: *"Me gustaría ver cuáles son los productos que más se venden, para saber qué no me tiene que faltar"*.

Cuando se le consultó sobre períodos de análisis más complejos, dijo: *"Con hoy, esta semana y este mes me alcanza para el día a día. Pero capaz que a fin de año quiero ver cuánto vendí en todo el año, o comparar diciembre con enero"*.

Estas respuestas fundamentan el **sistema de reportes con períodos predefinidos (hoy, semana, mes) y personalizados (meses específicos, años específicos, rango manual)**, así como las métricas de total vendido, ticket promedio, top 10 de productos y reporte de ganancias con margen.

---

**Sobre el hardware y las restricciones técnicas:**

El propietario confirmó que cuenta con: una computadora con Windows 10, una impresora térmica genérica USB (modelo Epson-compatible) y un escáner de código de barras USB. *"Todo lo compré en una casa de computación, son genéricos pero funcionan bien"*. No tiene conexión a internet estable en el local: *"A veces tenemos WiFi, a veces no. Por eso necesito que el sistema funcione sin internet"*.

Estas respuestas fundamentan las **restricciones de plataforma (Windows), la elección de SQLite como base de datos local sin dependencia de red, y el soporte para hardware genérico** (escáner keyboard wedge USB e impresora térmica ESC/POS compatible).

---

**Sobre las expectativas y prioridades:**

El propietario cerró la entrevista expresando: *"Lo que necesito es algo que me resuelva el cobro rápido, que me controle el stock sin que yo tenga que estar encima, y que me diga cuánto vendí y gané. Si eso funciona, ya estoy contento. Lo demás lo vamos agregando de a poco"*.

Esta declaración confirma la priorización del MVP: (P1) ventas, devoluciones y caja como funciones críticas para la operación diaria; (P2) productos, categorías, importación Excel y reportes como funciones necesarias para la gestión; y (P3) proveedores y compras como funciones opcionales que pueden incorporarse progresivamente.

---

#### Conclusiones del informe de entrevista

La entrevista con el propietario permitió validar las siguientes decisiones de diseño y alcance del MVP:

1. **Exclusión del módulo fiscal**: el propietario no requiere facturación electrónica en esta etapa. La complejidad de integración con ARCA/AFIP justifica postergar esta funcionalidad a una fase posterior.

2. **Máxima fluidez en el cobro sin alertas de stock**: el propietario prioriza la velocidad de cobro por sobre cualquier control de inventario durante la venta. Las alertas de stock deben confinarse a reportes y administración.

3. **Importación Excel con validación estricta**: el propietario necesita una herramienta guiada (plantilla) con validaciones robustas (rechazo de archivos inválidos, reporte de errores por fila) porque no tiene experiencia técnica y necesita confiar en que los datos se cargan correctamente.

4. **Devoluciones atómicas sin vinculación a venta original**: la práctica real del comercio confirma que los clientes no conservan tickets y el propietario no requiere trazabilidad de la venta original para procesar devoluciones.

5. **Operación offline**: la inestabilidad de la conexión a internet del local refuerza la decisión de un sistema 100% local con SQLite y sin dependencias de servicios en la nube.

6. **Hardware genérico**: el sistema debe ser compatible con hardware estándar de mercado (escáneres USB keyboard wedge, impresoras térmicas ESC/POS genéricas) sin requerir configuraciones complejas.

---

*Fin del documento.*
