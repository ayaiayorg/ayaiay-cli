"""Tests for package management functionality."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ayaiay.installer import InstallResult
from ayaiay.models import LockFile, LockFilePackage, Pack, PackType, PackVersion
from ayaiay.package_manager import PackageManager


@pytest.fixture
def temp_lock_file(tmp_path: Path) -> Path:
    """Create a temporary lock file path."""
    return tmp_path / "ayaiay.json"


@pytest.fixture
def package_manager(temp_lock_file: Path) -> PackageManager:
    """Create a PackageManager instance with temporary lock file."""
    return PackageManager(lock_file_path=temp_lock_file)


class TestLockFile:
    """Tests for lock file operations."""

    def test_load_nonexistent_lock_file(self, package_manager: PackageManager) -> None:
        """Test loading a non-existent lock file returns empty lock file."""
        lock_file = package_manager.load_lock_file()
        assert isinstance(lock_file, LockFile)
        assert len(lock_file.packages) == 0

    def test_save_and_load_lock_file(
        self, package_manager: PackageManager, temp_lock_file: Path
    ) -> None:
        """Test saving and loading a lock file."""
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                    installed_at=datetime.now(UTC),
                    digest="sha256:abc123",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        assert temp_lock_file.exists()

        loaded = package_manager.load_lock_file()
        assert "acme/test-pack" in loaded.packages
        assert loaded.packages["acme/test-pack"].version == "1.0.0"

    def test_init_creates_lock_file(
        self, package_manager: PackageManager, temp_lock_file: Path
    ) -> None:
        """Test init creates a new lock file."""
        assert not temp_lock_file.exists()
        result = package_manager.init()
        assert result is True
        assert temp_lock_file.exists()

    def test_init_fails_if_exists(
        self, package_manager: PackageManager, temp_lock_file: Path
    ) -> None:
        """Test init fails if lock file already exists."""
        package_manager.init()
        result = package_manager.init()
        assert result is False


class TestAddPackage:
    """Tests for adding packages."""

    def test_add_package_success(self, package_manager: PackageManager) -> None:
        """Test adding a package successfully."""
        mock_pack = Pack(
            id="pack-1",
            name="test-pack",
            publisher="acme",
            pack_type=PackType.AGENT,
            latest_version="1.0.0",
        )
        mock_version = PackVersion(
            version="1.0.0",
            published_at=datetime.now(UTC),
            digest="sha256:abc123",
        )
        mock_result = InstallResult(
            success=True,
            pack=mock_pack,
            version=mock_version,
            install_path=Path("/tmp/test"),
            message="Success",
        )

        with patch.object(
            package_manager.installer, "install", return_value=mock_result
        ):
            success, message, result = package_manager.add_package("acme/test-pack")

        assert success is True
        assert result.success is True

        lock_file = package_manager.load_lock_file()
        assert "acme/test-pack" in lock_file.packages
        assert lock_file.packages["acme/test-pack"].version == "1.0.0"

    def test_add_package_invalid_reference(
        self, package_manager: PackageManager
    ) -> None:
        """Test adding a package with invalid reference."""
        success, message, result = package_manager.add_package("invalid")
        assert success is False
        assert "Invalid pack reference" in message

    def test_add_package_already_exists(self, package_manager: PackageManager) -> None:
        """Test adding a package that already exists in lock file."""
        # First add
        mock_pack = Pack(
            id="pack-1",
            name="test-pack",
            publisher="acme",
            pack_type=PackType.AGENT,
            latest_version="1.0.0",
        )
        mock_version = PackVersion(version="1.0.0")
        mock_result = InstallResult(
            success=True,
            pack=mock_pack,
            version=mock_version,
            install_path=Path("/tmp/test"),
            message="Success",
        )

        with patch.object(
            package_manager.installer, "install", return_value=mock_result
        ):
            package_manager.add_package("acme/test-pack")

        # Try to add again
        success, message, result = package_manager.add_package("acme/test-pack")
        assert success is False
        assert "already in ayaiay.json" in message.lower()


class TestRemovePackage:
    """Tests for removing packages."""

    def test_remove_package_success(self, package_manager: PackageManager) -> None:
        """Test removing a package successfully."""
        # Add package first
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        mock_result = InstallResult(
            success=True,
            pack=None,
            version=None,
            install_path=None,
            message="Uninstalled",
        )

        with patch.object(
            package_manager.installer, "uninstall", return_value=mock_result
        ):
            success, message = package_manager.remove_package("acme/test-pack")

        assert success is True

        lock_file = package_manager.load_lock_file()
        assert "acme/test-pack" not in lock_file.packages

    def test_remove_package_not_in_lock_file(
        self, package_manager: PackageManager
    ) -> None:
        """Test removing a package not in lock file."""
        success, message = package_manager.remove_package("acme/nonexistent")
        assert success is False
        assert "not in ayaiay.json" in message.lower()


class TestSync:
    """Tests for syncing packages."""

    def test_sync_installs_missing_packages(
        self, package_manager: PackageManager
    ) -> None:
        """Test sync installs packages not currently installed."""
        # Create lock file with packages
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        mock_result = InstallResult(
            success=True,
            pack=None,
            version=None,
            install_path=None,
            message="Installed",
        )

        with (
            patch.object(package_manager.installer, "list_installed", return_value=[]),
            patch.object(
                package_manager.installer, "install", return_value=mock_result
            ),
        ):
            results = package_manager.sync()

        assert len(results) == 1
        assert results[0][0] == "acme/test-pack"
        assert results[0][1] is True

    def test_sync_skips_installed_packages(
        self, package_manager: PackageManager
    ) -> None:
        """Test sync skips packages already installed."""
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        with patch.object(
            package_manager.installer,
            "list_installed",
            return_value=[("acme/test-pack", "1.0.0", Path("/tmp/test"))],
        ):
            results = package_manager.sync()

        assert len(results) == 1
        assert results[0][0] == "acme/test-pack"
        assert "Already installed" in results[0][2]


class TestUpdate:
    """Tests for updating packages."""

    def test_update_specific_package(self, package_manager: PackageManager) -> None:
        """Test updating a specific package."""
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        mock_pack = Pack(
            id="pack-1",
            name="test-pack",
            publisher="acme",
            pack_type=PackType.AGENT,
            latest_version="2.0.0",
        )
        mock_version = PackVersion(version="2.0.0")

        with (
            patch.object(package_manager.client, "get_pack", return_value=mock_pack),
            patch.object(
                package_manager.client, "get_pack_versions", return_value=[mock_version]
            ),
            patch.object(
                package_manager.installer,
                "install",
                return_value=InstallResult(
                    success=True,
                    pack=mock_pack,
                    version=mock_version,
                    install_path=None,
                    message="Updated",
                ),
            ),
        ):
            results = package_manager.update(package_name="acme/test-pack")

        assert len(results) == 1
        assert results[0][1] is True
        assert "Updated from 1.0.0 to 2.0.0" in results[0][2]

        # Check lock file was updated
        lock_file = package_manager.load_lock_file()
        assert lock_file.packages["acme/test-pack"].version == "2.0.0"

    def test_update_package_already_latest(
        self, package_manager: PackageManager
    ) -> None:
        """Test updating a package already at latest version."""
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="2.0.0",
                )
            }
        )
        package_manager.save_lock_file(lock_file)

        mock_pack = Pack(
            id="pack-1",
            name="test-pack",
            publisher="acme",
            pack_type=PackType.AGENT,
            latest_version="2.0.0",
        )
        mock_version = PackVersion(version="2.0.0")

        with (
            patch.object(package_manager.client, "get_pack", return_value=mock_pack),
            patch.object(
                package_manager.client, "get_pack_versions", return_value=[mock_version]
            ),
        ):
            results = package_manager.update(package_name="acme/test-pack")

        assert len(results) == 1
        assert "Already at latest version" in results[0][2]


class TestListPackages:
    """Tests for listing packages."""

    def test_list_packages(self, package_manager: PackageManager) -> None:
        """Test listing packages in lock file."""
        lock_file = LockFile(
            packages={
                "acme/test-pack": LockFilePackage(
                    name="acme/test-pack",
                    version="1.0.0",
                    installed_at=datetime.now(UTC),
                ),
                "acme/another-pack": LockFilePackage(
                    name="acme/another-pack",
                    version="2.0.0",
                ),
            }
        )
        package_manager.save_lock_file(lock_file)

        packages = package_manager.list_packages()
        assert len(packages) == 2
        assert any(pkg[0] == "acme/test-pack" for pkg in packages)
        assert any(pkg[0] == "acme/another-pack" for pkg in packages)
