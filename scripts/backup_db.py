import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta

# Configuración de Rutas Relativas
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "pos", "data", "pos.db")
BACKUPS_DIR = os.path.join(PROJECT_ROOT, "backups")

def run_backup():
    print("Iniciando backup exclusivo de la base de datos POS...")
    
    # 1. Asegurar la existencia del directorio de backups
    if not os.path.exists(BACKUPS_DIR):
        os.makedirs(BACKUPS_DIR)
        print(f"Creado directorio de backups en: {BACKUPS_DIR}")

    # Verificar que la base de datos de origen existe
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontró la base de datos en {DB_PATH}")
        return

    # 2. Generar nombre de archivos con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    temp_backup_db = os.path.join(BACKUPS_DIR, f"pos_temp_{timestamp}.db")
    zip_filename = f"backup_pos_{timestamp}.zip"
    zip_filepath = os.path.join(BACKUPS_DIR, zip_filename)

    try:
        # 3. Copia atómica y segura de la base de datos activa usando sqlite3.backup()
        # Esto previene corrupciones si el sistema POS está ejecutándose al mismo tiempo.
        print("Realizando copia atómica de SQLite...")
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(temp_backup_db)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        # 4. Comprimir la copia temporal de la BD en un archivo ZIP
        print(f"Comprimiendo copia en formato ZIP: {zip_filename}")
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Almacena el archivo en el ZIP con el nombre 'pos.db'
            zipf.write(temp_backup_db, arcname="pos.db")

        print(f"Backup creado exitosamente: {zip_filepath}")

    except Exception as e:
        print(f"Error durante el proceso de backup: {e}")
        if os.path.exists(zip_filepath):
            os.remove(zip_filepath)
    finally:
        # Eliminar el archivo temporal de base de datos descomprimido
        if os.path.exists(temp_backup_db):
            os.remove(temp_backup_db)

    # 5. Lógica de limpieza y retención (Eliminar archivos de más de 7 días)
    cleanup_old_backups()

def cleanup_old_backups():
    print("Iniciando escaneo de retención (limpieza de backups antiguos)...")
    limite_retencion = datetime.now() - timedelta(days=7)
    
    try:
        for file in os.listdir(BACKUPS_DIR):
            if file.startswith("backup_pos_") and file.endswith(".zip"):
                filepath = os.path.join(BACKUPS_DIR, file)
                
                # Obtener la fecha de modificación del archivo
                mtime = os.path.getmtime(filepath)
                file_date = datetime.fromtimestamp(mtime)
                
                if file_date < limite_retencion:
                    os.remove(filepath)
                    print(f"Eliminado backup antiguo (más de 7 días): {file}")
        print("Limpieza de retención completada.")
    except Exception as e:
        print(f"Error durante la limpieza de backups antiguos: {e}")

if __name__ == "__main__":
    run_backup()
