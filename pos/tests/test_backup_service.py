"""Tests for BackupService — zip creation and retention cleanup.

All tests use temporary directories to avoid touching the real database.
"""

import os
import tempfile
import time
import zipfile
from datetime import datetime

import pytest

from pos.service.backup_service import BackupService


@pytest.fixture
def temp_db() -> str:
    """Create a dummy pos.db file in a temporary directory."""
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "pos.db")
    with open(db_path, "wb") as f:
        f.write(b"dummy database content")
    return db_path


@pytest.fixture
def temp_backup_dir() -> str:
    """Create a temporary backup directory."""
    backup_dir = tempfile.mkdtemp()
    return backup_dir


# ---------------------------------------------------------------- backup ---

class TestBackup:
    def test_creates_zip(self, temp_db: str, temp_backup_dir: str):
        svc = BackupService(db_path=temp_db, backup_dir=temp_backup_dir)
        zip_path = svc.backup_db()

        assert os.path.isfile(zip_path)
        assert zip_path.startswith(temp_backup_dir)
        assert zip_path.endswith(".zip")
        assert "pos_" in os.path.basename(zip_path)

        # Verify zip contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "pos.db" in names
            with zf.open("pos.db") as f:
                assert f.read() == b"dummy database content"

    def test_timestamp_format(self, temp_db: str, temp_backup_dir: str):
        svc = BackupService(db_path=temp_db, backup_dir=temp_backup_dir)
        zip_path = svc.backup_db()

        # Expected format: pos_YYYY-MM-DD_HHMM.zip
        basename = os.path.basename(zip_path)
        assert basename.startswith("pos_")
        assert basename.endswith(".zip")
        # Strip prefix/suffix to get the timestamp part
        ts_part = basename[4:-4]  # remove "pos_" and ".zip"
        # Should be parseable
        dt = datetime.strptime(ts_part, "%Y-%m-%d_%H%M")
        assert dt is not None

    def test_creates_backup_dir_if_missing(self, temp_db: str):
        tmpdir = tempfile.mkdtemp()
        backups = os.path.join(tmpdir, "non_existent_backups")
        assert not os.path.exists(backups)

        svc = BackupService(db_path=temp_db, backup_dir=backups)
        zip_path = svc.backup_db()
        assert os.path.isdir(backups)
        assert os.path.isfile(zip_path)

    def test_non_existent_db_raises(self, temp_backup_dir: str):
        svc = BackupService(
            db_path="/nonexistent/path/pos.db",
            backup_dir=temp_backup_dir,
        )
        with pytest.raises(FileNotFoundError, match="no encontrada"):
            svc.backup_db()


# --------------------------------------------------------------- cleanup ---

class TestCleanup:
    def test_deletes_old_backups(self, temp_backup_dir: str):
        # Create fake backup files with old modification times
        old_file = os.path.join(temp_backup_dir, "pos_2020-01-01_1200.zip")
        with open(old_file, "w") as f:
            f.write("old")
        # Set mtime to 2 years ago
        old_time = time.time() - (365 * 2 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        svc = BackupService(backup_dir=temp_backup_dir)
        deleted = svc.cleanup_old(days=30)

        assert old_file in deleted
        assert not os.path.isfile(old_file)

    def test_keeps_recent_backups(self, temp_backup_dir: str):
        recent_file = os.path.join(temp_backup_dir, "pos_2026-06-12_1200.zip")
        with open(recent_file, "w") as f:
            f.write("recent")
        # mtime = now (recent)
        # No need to modify — it's already recent

        svc = BackupService(backup_dir=temp_backup_dir)
        deleted = svc.cleanup_old(days=30)

        assert deleted == []
        assert os.path.isfile(recent_file)

    def test_ignores_non_backup_files(self, temp_backup_dir: str):
        # Create a file that doesn't match the backup pattern
        other = os.path.join(temp_backup_dir, "not_a_backup.txt")
        with open(other, "w") as f:
            f.write("other")
        old_time = time.time() - (365 * 2 * 24 * 3600)
        os.utime(other, (old_time, old_time))

        svc = BackupService(backup_dir=temp_backup_dir)
        deleted = svc.cleanup_old(days=30)

        assert deleted == []
        assert os.path.isfile(other)

    def test_missing_backup_dir(self):
        svc = BackupService(backup_dir="/nonexistent/backups")
        deleted = svc.cleanup_old(days=30)
        assert deleted == []

    def test_multiple_files_mixed_ages(self, temp_backup_dir: str):
        # One old (2 years), one recent (today)
        old_file = os.path.join(temp_backup_dir, "pos_2020-06-01_0800.zip")
        recent_file = os.path.join(temp_backup_dir, "pos_2026-06-12_1200.zip")

        with open(old_file, "w") as f:
            f.write("old")
        with open(recent_file, "w") as f:
            f.write("recent")

        old_time = time.time() - (365 * 2 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        svc = BackupService(backup_dir=temp_backup_dir)
        deleted = svc.cleanup_old(days=30)

        assert old_file in deleted
        assert recent_file not in deleted
        assert not os.path.isfile(old_file)
        assert os.path.isfile(recent_file)
