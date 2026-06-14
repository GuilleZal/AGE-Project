# Guía de Backup Automático — Windows Task Scheduler

El script `pos/scripts/backup.py` comprime la base de datos (`pos.db`) en un ZIP
con timestamp y elimina backups de más de 30 días. Se puede ejecutar manualmente
o programar con el Programador de Tareas de Windows.

---

## Backup Manual

```bash
python pos/scripts/backup.py
```

Salida esperada:

```
Backup creado: D:\...\pos\data\backups\pos_2026-06-14_2300.zip
No hay backups antiguos para eliminar.
```

Los backups se almacenan en `pos/data/backups/` con el formato:

```
pos_YYYY-MM-DD_HHMM.zip
```

---

## Programación Automática (Windows Task Scheduler)

### Abrir el Programador de Tareas

1. Presioná `Win + R`, escribí `taskschd.msc` y presioná Enter.
2. En el panel derecho, seleccioná **Crear tarea básica...**

### Configurar la tarea

#### General

- **Nombre**: `POS Database Backup`
- **Descripción**: `Backup diario de la base de datos del sistema POS`

#### Desencadenador (Trigger)

- **Frecuencia**: Diaria
- **Hora**: `23:00` (después del cierre del negocio)
- **Repetir cada**: 1 día

#### Acción

- **Acción**: Iniciar un programa
- **Programa o script**: `python`
  > Si `python` no está en el PATH del sistema, usá la ruta completa:
  > `C:\Users\<usuario>\AppData\Local\Programs\Python\Python312\python.exe`
- **Argumentos**: `pos/scripts/backup.py`
- **Iniciar en**: `C:\ruta\a\AGE-Project`
  > Reemplazá con la ruta real donde clonaste el repositorio.

#### Condiciones (opcional)

- Desmarcá **Iniciar la tarea solo si el equipo está conectado a la corriente alterna**
  si es una PC de escritorio.
- Marcá **Despertar el equipo para ejecutar esta tarea** solo si la PC suspende
  y querés que el backup se ejecute igual.

### Verificar que funciona

1. En el Programador de Tareas, buscá la tarea `POS Database Backup`.
2. Clic derecho → **Ejecutar**.
3. Verificá que aparezca un nuevo `.zip` en `pos/data/backups/`.

---

## Restaurar un Backup

1. **Detené la aplicación** (cerrá la ventana del POS).
2. Buscá el archivo ZIP en `pos/data/backups/` con la fecha deseada.
3. Extraé el contenido con cualquier herramienta (Explorador de Windows,
   7-Zip, WinRAR).
4. Reemplazá `pos/data/pos.db` con el archivo extraído:

   ```
   pos/data/pos.db  ← reemplazar con el extraído del ZIP
   ```

5. Iniciá la aplicación normalmente: `python pos/main.py`

> **Precaución**: restaurar un backup **sobrescribe** los datos actuales.
> Si necesitás conservar la base de datos actual, renombrala antes de restaurar.

---

## Rotación de Backups

El script de backup elimina automáticamente los archivos ZIP con más de 30 días
de antigüedad. No es necesario limpiar manualmente.

Si necesitás conservar backups por más tiempo:

- Copiá manualmente los ZIPs a otra carpeta o unidad externa.
- O modificá el parámetro `days=30` en `pos/scripts/backup.py` y en
  `pos/service/backup_service.py`.

---

## Solución de problemas

### "python no se reconoce como un comando"

En el Programador de Tareas, usá la ruta completa al ejecutable de Python 3.12:

```
C:\Users\<usuario>\AppData\Local\Programs\Python\Python312\python.exe
```

Para encontrar la ruta exacta:

```bash
where python
```

### El backup no se crea (tarea ejecutada pero sin ZIP)

Verificá que el campo **Iniciar en** tenga la ruta correcta al proyecto.
El script usa rutas relativas (`pos/data/`) y necesita ejecutarse desde
la raíz del repositorio.

### Permisos denegados

Si la carpeta del proyecto está en `C:\Program Files\`, Windows puede
bloquear la escritura. Mové el proyecto a una carpeta con permisos de
usuario (`C:\Users\<usuario>\Documents\` o `D:\Proyectos\`).
