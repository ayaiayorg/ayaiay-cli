"""Pack installation functionality for AyAiAy CLI."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

import yaml

from ayaiay.client import AyAiAyClient, NotFoundError
from ayaiay.config import Config
from ayaiay.models import Pack, PackVersion
from ayaiay.validator import load_manifest


class PackReference(NamedTuple):
    """Parsed pack reference (publisher/name@version)."""

    publisher: str
    name: str
    version: str | None

    @classmethod
    def parse(cls, reference: str) -> PackReference:
        """Parse a pack reference string.

        Formats:
        - publisher/name@version
        - publisher/name@latest
        - publisher/name (defaults to latest)

        Args:
            reference: Pack reference string.

        Returns:
            Parsed PackReference.

        Raises:
            ValueError: If the reference format is invalid.
        """
        pattern = r"^([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(?:@(.+))?$"
        match = re.match(pattern, reference)
        if not match:
            raise ValueError(
                f"Invalid pack reference: {reference}. "
                f"Expected format: publisher/name[@version]"
            )
        return cls(
            publisher=match.group(1),
            name=match.group(2),
            version=match.group(3),
        )

    @property
    def full_name(self) -> str:
        """Return publisher/name."""
        return f"{self.publisher}/{self.name}"

    @property
    def versioned_name(self) -> str:
        """Return publisher/name@version."""
        version = self.version or "latest"
        return f"{self.full_name}@{version}"


class InstallResult(NamedTuple):
    """Result of pack installation."""

    success: bool
    pack: Pack | None
    version: PackVersion | None
    install_path: Path | None
    message: str


class Installer:
    """Handles pack installation from the AyAiAy registry."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the installer.

        Args:
            config: Configuration object.
        """
        self.config = config or Config.load()
        self.client = AyAiAyClient(config=self.config)

    def install(
        self,
        reference: str,
        force: bool = False,
    ) -> InstallResult:
        """Install a pack from the registry.

        Args:
            reference: Pack reference (publisher/name@version).
            force: Force reinstall if already installed.

        Returns:
            InstallResult with installation details.
        """
        try:
            pack_ref = PackReference.parse(reference)
        except ValueError as e:
            return InstallResult(
                success=False,
                pack=None,
                version=None,
                install_path=None,
                message=str(e),
            )

        # Fetch pack info
        try:
            pack = self.client.get_pack(pack_ref.full_name)
        except NotFoundError:
            return InstallResult(
                success=False,
                pack=None,
                version=None,
                install_path=None,
                message=f"Pack not found: {pack_ref.full_name}",
            )

        # Resolve version
        version_str = pack_ref.version or "latest"
        try:
            if version_str == "latest":
                versions = self.client.get_pack_versions(pack_ref.full_name)
                if not versions:
                    return InstallResult(
                        success=False,
                        pack=pack,
                        version=None,
                        install_path=None,
                        message=f"No versions available for {pack_ref.full_name}",
                    )
                version = versions[0]  # Assume sorted by newest first
            else:
                version = self.client.get_pack_version(pack_ref.full_name, version_str)
        except NotFoundError:
            return InstallResult(
                success=False,
                pack=pack,
                version=None,
                install_path=None,
                message=f"Version not found: {pack_ref.versioned_name}",
            )

        # Check if already installed
        install_path = self._get_install_path(pack_ref.publisher, pack_ref.name)
        if install_path.exists() and not force:
            installed_version = self._get_installed_version(install_path)
            if installed_version == version.version:
                return InstallResult(
                    success=True,
                    pack=pack,
                    version=version,
                    install_path=install_path,
                    message=f"Already installed: {pack_ref.full_name}@{version.version}",
                )

        # Ensure directories exist
        self.config.ensure_directories()

        # Pull from OCI registry
        try:
            self._pull_from_registry(pack, version, install_path)
        except Exception as e:
            return InstallResult(
                success=False,
                pack=pack,
                version=version,
                install_path=None,
                message=f"Failed to pull from registry: {e}",
            )

        # Write installation metadata
        self._write_install_metadata(install_path, pack, version)

        return InstallResult(
            success=True,
            pack=pack,
            version=version,
            install_path=install_path,
            message=f"Successfully installed {pack_ref.full_name}@{version.version}",
        )

    def uninstall(self, reference: str) -> InstallResult:
        """Uninstall a pack.

        Args:
            reference: Pack reference (publisher/name).

        Returns:
            InstallResult with uninstallation details.
        """
        try:
            pack_ref = PackReference.parse(reference)
        except ValueError as e:
            return InstallResult(
                success=False,
                pack=None,
                version=None,
                install_path=None,
                message=str(e),
            )

        install_path = self._get_install_path(pack_ref.publisher, pack_ref.name)
        if not install_path.exists():
            return InstallResult(
                success=False,
                pack=None,
                version=None,
                install_path=None,
                message=f"Pack not installed: {pack_ref.full_name}",
            )

        shutil.rmtree(install_path)

        return InstallResult(
            success=True,
            pack=None,
            version=None,
            install_path=install_path,
            message=f"Successfully uninstalled {pack_ref.full_name}",
        )

    def list_installed(self) -> list[tuple[str, str, Path]]:
        """List all installed packs.

        Returns:
            List of (full_name, version, path) tuples.
        """
        installed = []
        install_dir = self.config.install_dir

        if not install_dir.exists():
            return installed

        for publisher_dir in install_dir.iterdir():
            if not publisher_dir.is_dir():
                continue
            for pack_dir in publisher_dir.iterdir():
                if not pack_dir.is_dir():
                    continue
                version = self._get_installed_version(pack_dir)
                full_name = f"{publisher_dir.name}/{pack_dir.name}"
                installed.append((full_name, version or "unknown", pack_dir))

        return installed

    def _get_install_path(self, publisher: str, name: str) -> Path:
        """Get the installation path for a pack."""
        return self.config.install_dir / publisher / name

    def _get_installed_version(self, install_path: Path) -> str | None:
        """Get the installed version from metadata."""
        metadata_path = install_path / ".ayaiay-metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                return data.get("version")
            except Exception:
                pass
        return None

    def _pull_from_registry(
        self,
        pack: Pack,
        version: PackVersion,
        install_path: Path,
    ) -> None:
        """Pull pack from OCI registry (GHCR).

        This is a simplified implementation. In production, this would use
        the oras library or similar for proper OCI registry interactions.
        """
        # For now, we'll try to clone from GitHub if available
        if pack.repository_url:
            self._clone_from_github(str(pack.repository_url), version.version, install_path)
        else:
            # Fallback: try OCI pull with oras or docker
            self._pull_oci(pack, version, install_path)

    def _clone_from_github(
        self,
        repo_url: str,
        version: str,
        install_path: Path,
    ) -> None:
        """Clone pack from GitHub repository."""
        install_path.parent.mkdir(parents=True, exist_ok=True)

        if install_path.exists():
            shutil.rmtree(install_path)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Clone with specific tag/version
            tag = f"v{version}" if not version.startswith("v") else version
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", tag, repo_url, tmp_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                # Try without 'v' prefix
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", version, repo_url, tmp_dir],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            # Move to install path (excluding .git)
            tmp_path = Path(tmp_dir)
            shutil.copytree(
                tmp_path,
                install_path,
                ignore=shutil.ignore_patterns(".git"),
            )

    def _pull_oci(
        self,
        pack: Pack,
        version: PackVersion,
        install_path: Path,
    ) -> None:
        """Pull pack from OCI registry."""
        image = f"{self.config.registry_url}/{pack.publisher}/{pack.name}:{version.version}"

        install_path.parent.mkdir(parents=True, exist_ok=True)

        # Try using oras if available
        try:
            subprocess.run(
                ["oras", "pull", image, "-o", str(install_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback error
        raise RuntimeError(
            f"Cannot pull from OCI registry. Install 'oras' CLI or ensure "
            f"the pack has a GitHub repository URL."
        )

    def _write_install_metadata(
        self,
        install_path: Path,
        pack: Pack,
        version: PackVersion,
    ) -> None:
        """Write installation metadata file."""
        metadata = {
            "pack_id": pack.id,
            "full_name": pack.full_name,
            "version": version.version,
            "installed_at": version.published_at.isoformat() if version.published_at else None,
            "digest": version.digest,
        }
        metadata_path = install_path / ".ayaiay-metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
