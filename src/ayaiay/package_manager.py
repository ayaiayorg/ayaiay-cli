"""Package management for ayaiay.json lock file."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from ayaiay.client import AyAiAyClient
from ayaiay.config import Config
from ayaiay.installer import Installer, InstallResult, PackReference
from ayaiay.models import LockFile, LockFilePackage

# Constants
LOCK_FILENAME: Final[str] = "ayaiay.json"


class PackageManager:
    """Manages packages in ayaiay.json lock file."""

    def __init__(
        self,
        config: Config | None = None,
        lock_file_path: Path | None = None,
    ) -> None:
        """Initialize the package manager.

        Args:
            config: Configuration object.
            lock_file_path: Path to ayaiay.json file. Defaults to current directory.
        """
        self.config = config or Config.load()
        self.lock_file_path = lock_file_path or Path.cwd() / LOCK_FILENAME
        self.installer = Installer(config=self.config)
        self.client = AyAiAyClient(config=self.config)

    def load_lock_file(self) -> LockFile:
        """Load the lock file from disk.

        Returns:
            LockFile object. Returns empty lock file if file doesn't exist.
        """
        if not self.lock_file_path.exists():
            return LockFile()

        try:
            with open(self.lock_file_path) as f:
                data = json.load(f)
            return LockFile.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            # Return empty lock file if invalid
            return LockFile()

    def save_lock_file(self, lock_file: LockFile) -> None:
        """Save the lock file to disk.

        Args:
            lock_file: LockFile object to save.
        """
        lock_file.updated_at = datetime.now(UTC)
        with open(self.lock_file_path, "w") as f:
            json.dump(
                lock_file.model_dump(mode="json"),
                f,
                indent=2,
                default=str,
            )

    def init(self) -> bool:
        """Initialize a new ayaiay.json file.

        Returns:
            True if created, False if already exists.
        """
        if self.lock_file_path.exists():
            return False

        lock_file = LockFile()
        self.save_lock_file(lock_file)
        return True

    def add_package(
        self,
        reference: str,
        force: bool = False,
    ) -> tuple[bool, str, InstallResult]:
        """Add a package to lock file and install it.

        Args:
            reference: Pack reference (publisher/name@version).
            force: Force reinstall if already installed.

        Returns:
            Tuple of (success, message, install_result).
        """
        # Parse reference
        try:
            pack_ref = PackReference.parse(reference)
        except ValueError as e:
            return (False, str(e), InstallResult(False, None, None, None, str(e)))

        # Load lock file
        lock_file = self.load_lock_file()

        # Check if already in lock file
        if pack_ref.full_name in lock_file.packages and not force:
            existing = lock_file.packages[pack_ref.full_name]
            return (
                False,
                (
                    f"Package already in ayaiay.json: "
                    f"{pack_ref.full_name}@{existing.version}"
                ),
                InstallResult(False, None, None, None, "Already in lock file"),
            )

        # Install the package
        result = self.installer.install(reference, force=force)

        if not result.success:
            return (False, result.message, result)

        # Add to lock file
        if result.pack and result.version:
            lock_file.packages[pack_ref.full_name] = LockFilePackage(
                name=pack_ref.full_name,
                version=result.version.version,
                installed_at=result.version.published_at,
                digest=result.version.digest,
            )
            self.save_lock_file(lock_file)

        return (True, result.message, result)

    def record_installation(
        self,
        reference: str,
        result: InstallResult,
    ) -> tuple[bool, str]:
        """Record an installation in the lock file without reinstalling.

        Args:
            reference: Pack reference used for installation.
            result: Install result from the installer.

        Returns:
            Tuple of (success, message).
        """
        if not result.success:
            return (False, "Installation was not successful")

        if result.version is None:
            return (False, "Missing version information from installation")

        try:
            pack_ref = PackReference.parse(reference)
            full_name = pack_ref.full_name
        except ValueError:
            if result.pack is None:
                return (False, "Unable to determine package name")
            full_name = result.pack.full_name

        lock_file = self.load_lock_file()
        lock_file.packages[full_name] = LockFilePackage(
            name=full_name,
            version=result.version.version,
            installed_at=result.version.published_at or datetime.now(UTC),
            digest=result.version.digest,
        )
        self.save_lock_file(lock_file)

        return (True, f"Updated ayaiay.json for {full_name}@{result.version.version}")

    def remove_package(self, reference: str) -> tuple[bool, str]:
        """Remove a package from lock file and uninstall it.

        Args:
            reference: Pack reference (publisher/name).

        Returns:
            Tuple of (success, message).
        """
        # Parse reference
        try:
            pack_ref = PackReference.parse(reference)
        except ValueError as e:
            return (False, str(e))

        # Load lock file
        lock_file = self.load_lock_file()

        # Check if in lock file
        if pack_ref.full_name not in lock_file.packages:
            return (
                False,
                f"Package not in ayaiay.json: {pack_ref.full_name}",
            )

        # Uninstall the package
        result = self.installer.uninstall(reference)

        if not result.success:
            return (False, result.message)

        # Remove from lock file
        del lock_file.packages[pack_ref.full_name]
        self.save_lock_file(lock_file)

        return (True, result.message)

    def sync(self) -> list[tuple[str, bool, str]]:
        """Sync installed packages with lock file.

        Installs packages listed in lock file that aren't installed.

        Returns:
            List of (package_name, success, message) tuples.
        """
        lock_file = self.load_lock_file()
        results: list[tuple[str, bool, str]] = []

        for package_name, package in lock_file.packages.items():
            # Check if installed
            installed = self.installer.list_installed()
            is_installed = any(name == package_name for name, _, _ in installed)

            if not is_installed:
                # Install the package
                reference = f"{package_name}@{package.version}"
                result = self.installer.install(reference, force=False)
                results.append((package_name, result.success, result.message))
            else:
                results.append((package_name, True, "Already installed"))

        return results

    def update(
        self,
        package_name: str | None = None,
    ) -> list[tuple[str, bool, str]]:
        """Update packages to their latest versions.

        Args:
            package_name: Specific package to update. If None, updates all.

        Returns:
            List of (package_name, success, message) tuples.
        """
        lock_file = self.load_lock_file()
        results: list[tuple[str, bool, str]] = []

        packages_to_update = (
            [package_name] if package_name else list(lock_file.packages.keys())
        )

        for pkg_name in packages_to_update:
            if pkg_name not in lock_file.packages:
                results.append((pkg_name, False, "Package not in lock file"))
                continue

            try:
                # Get latest version from API
                versions = self.client.get_pack_versions(pkg_name)
                if not versions:
                    results.append((pkg_name, False, "No versions available"))
                    continue

                latest_version = versions[0]

                # Check if update needed
                current_version = lock_file.packages[pkg_name].version
                if current_version == latest_version.version:
                    results.append(
                        (
                            pkg_name,
                            True,
                            f"Already at latest version {current_version}",
                        )
                    )
                    continue

                # Install new version
                reference = f"{pkg_name}@{latest_version.version}"
                result = self.installer.install(reference, force=True)

                if result.success and result.version:
                    # Update lock file
                    lock_file.packages[pkg_name] = LockFilePackage(
                        name=pkg_name,
                        version=result.version.version,
                        installed_at=result.version.published_at,
                        digest=result.version.digest,
                    )
                    self.save_lock_file(lock_file)
                    results.append(
                        (
                            pkg_name,
                            True,
                            (
                                f"Updated from {current_version} "
                                f"to {latest_version.version}"
                            ),
                        )
                    )
                else:
                    results.append((pkg_name, False, result.message))

            except Exception as e:
                results.append((pkg_name, False, str(e)))

        return results

    def list_packages(self) -> list[tuple[str, str, str | None]]:
        """List packages in lock file.

        Returns:
            List of (name, version, installed_at) tuples.
        """
        lock_file = self.load_lock_file()
        return [
            (
                pkg.name,
                pkg.version,
                pkg.installed_at.isoformat() if pkg.installed_at else None,
            )
            for pkg in lock_file.packages.values()
        ]
