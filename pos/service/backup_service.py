"""Backup service — zip database and enforce 30-day retention policy.

The backup logic is deliberately simple and uses only stdlib so the
standalone ``scripts/backup.py`` can import it with zero external deps.
"""

import os
import shutil
import zipfile
from datetime import datetime, timedelta


#: Default location for the live database (relative to project root).
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "pos.db"
)

#: Default backup output directory.
DEFAULT_BACKUP_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "backups"
)


class BackupService:
    """Zip-based database backup with optional old-file cleanup."""

    def __init__(
        self,
        db_path: str | None = None,
        backup_dir: str | None = None,
    ) -> None:
        self._db_path = os.path.abspath(db_path or DEFAULT_DB_PATH)
        self._backup_dir = os.path.abspath(backup_dir or DEFAULT_BACKUP_DIR)

    # ---------------------------------------------------------------- backup

    def backup_db(self) -> str:
        """Copy ``pos.db`` into a timestamped .zip file.

        The zip contains a single file named ``pos.db`` so it can be
        extracted anywhere without clashing.

        Returns:
            Absolute path of the created zip file.

        Raises:
            FileNotFoundError: If ``pos.db`` does not exist.
            OSError: If the backup directory cannot be created or written.
        """
        if not os.path.isfile(self._db_path):
            raise FileNotFoundError(
                f"Base de datos no encontrada: {self._db_path}"
            )

        os.makedirs(self._backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        zip_name = f"pos_{timestamp}.zip"
        zip_path = os.path.join(self._backup_dir, zip_name)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(self._db_path, arcname="pos.db")

        return zip_path

    # ------------------------------------------------------------ cleanup

    def cleanup_old(self, days: int = 30) -> list[str]:
        """Delete backup zip files older than *days*.

        Args:
            days: Retention period in days (default 30).

        Returns:
            List of absolute paths that were deleted (empty if nothing
            matched).
        """
        if not os.path.isdir(self._backup_dir):
            return []

        cutoff = datetime.now() - timedelta(days=days)
        deleted: list[str] = []

        for entry in os.scandir(self._backup_dir):
            if not entry.is_file():
                continue
            if not entry.name.startswith("pos_") or not entry.name.endswith(".zip"):
                continue

            mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            if mtime < cutoff:
                os.remove(entry.path)
                deleted.append(entry.path)

        return deleted
