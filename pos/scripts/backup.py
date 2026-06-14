"""Standalone backup script — zero external dependencies.

Can be scheduled via Windows Task Scheduler:

    python pos/scripts/backup.py

or run directly from any Python 3.12+ interpreter. The script imports
only stdlib (``shutil``, ``zipfile``, ``os``, ``datetime``) via the
``BackupService`` class.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `pos` is importable
# when executed as `python pos/scripts/backup.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pos.service.backup_service import BackupService


def main() -> None:
    """Run backup and cleanup, reporting results to stdout."""
    service = BackupService()

    try:
        zip_path = service.backup_db()
        print(f"Backup creado: {zip_path}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"ERROR: No se pudo crear el backup ({e})")
        sys.exit(1)

    deleted = service.cleanup_old(days=30)
    if deleted:
        print(f"{len(deleted)} backups antiguos eliminados:")
        for path in deleted:
            print(f"  - {path}")
    else:
        print("No hay backups antiguos para eliminar.")


if __name__ == "__main__":
    main()
