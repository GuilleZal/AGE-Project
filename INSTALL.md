# Guía de Instalación — Sistema POS

## Requisitos

- **Python 3.12** (NO 3.13 ni superior — requisito de compatibilidad de hardware)
- **Windows 10 o 11**
- ~100 MB de espacio en disco

> **Nota**: Python 3.12 es obligatorio. Versiones 3.13+ introducen cambios
> (PEP 695, modificaciones en `tkinter`) que no son compatibles con este proyecto.
> Si tenés otra versión instalada, usá `py -3.12` en lugar de `python`.

---

## Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/GuilleZal/AGE-Project.git
cd AGE-Project
```

---

## Paso 2 — Crear entorno virtual

```bash
python -m venv venv
```

Si `python` apunta a otra versión, usá la ruta explícita:

```bash
py -3.12 -m venv venv
```

---

## Paso 3 — Activar el entorno

**PowerShell / CMD:**

```bash
venv\Scripts\activate
```

**Git Bash:**

```bash
source venv/Scripts/activate
```

Cuando el entorno está activo, el prompt muestra `(venv)` al inicio.

---

## Paso 4 — Instalar dependencias

```bash
pip install -r requirements.txt
```

Dependencias incluidas:

| Paquete | Versión | Uso |
|---------|---------|-----|
| `customtkinter` | ≥ 5.2.0 | Interfaz gráfica |
| `openpyxl` | ≥ 3.1.0 | Importación desde Excel |
| `pytest` | ≥ 8.0.0 | Tests automatizados |
| `pytest-mock` | ≥ 3.12.0 | Mocks para tests |

---

## Paso 5 — Inicializar la base de datos

Al ejecutar la aplicación por primera vez, la base de datos se crea automáticamente:

```bash
python pos/main.py
```

Esto crea:

```
pos/data/pos.db        ← Base SQLite (WAL mode, 10 tablas)
pos/data/pos.db-wal    ← Write-Ahead Log
pos/data/pos.db-shm    ← Shared Memory
```

---

## Paso 6 — Ejecutar la aplicación

```bash
python pos/main.py
```

La ventana principal (1200×800, tema oscuro) abre con 5 pestañas:
**Ventas**, **Productos**, **Devoluciones**, **Caja**, **Reportes**.

---

## Paso 7 — Verificar instalación (tests)

```bash
pytest pos/tests/ -v
```

Si todos los tests pasan, la instalación es correcta.

---

## Backup

El backup se ejecuta manualmente con:

```bash
python pos/scripts/backup.py
```

Para programarlo diariamente, ver [docs/backup_scheduling.md](docs/backup_scheduling.md).

---

## Solución de problemas

### `ModuleNotFoundError: No module named 'customtkinter'`

El entorno virtual no está activado. Activá con `venv\Scripts\activate`.

### `ImportError: ... Python 3.13`

Estás usando Python 3.13+. Instalá Python 3.12 desde
[python.org](https://www.python.org/downloads/release/python-3120/)
y usá `py -3.12` para ejecutar.

### `sqlite3.OperationalError: no such table`

La base de datos no se inicializó. Borrá `pos/data/pos.db` y ejecutá
`python pos/main.py` de nuevo.

### La ventana no abre (error de DLL)

Instalá Visual C++ Redistributable desde
[Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe).
