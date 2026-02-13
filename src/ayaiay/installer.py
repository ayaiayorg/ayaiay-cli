"""Pack installation functionality for AyAiAy CLI."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, NamedTuple

import httpx

from ayaiay.client import AyAiAyClient, NotFoundError
from ayaiay.config import Config
from ayaiay.models import ManifestSkill, Pack, PackVersion
from ayaiay.validator import load_manifest

# Constants
METADATA_FILENAME: Final[str] = ".ayaiay-metadata.json"
LOCK_FILENAME: Final[str] = "ayaiay.json"
PROJECT_MANIFEST_FILENAMES: Final[tuple[str, ...]] = ("ayaiay.yaml", "ayaiay.yml")
PROJECT_COPY_DIRS: Final[tuple[str, ...]] = (".github",)
GIT_CLONE_DEPTH: Final[int] = 1
VERSION_PREFIX: Final[str] = "v"

# Pack source directories
PACK_SOURCE_DIRS: Final[tuple[str, ...]] = (
    "agents",
    "prompts",
    "instructions",
    "skills",
    "tools",
    "workflows",
)


@dataclass
class PlatformConfig:
    """Configuration for a supported AI platform."""

    name: str
    target_dir: str
    detection_files: tuple[str, ...] = field(default_factory=tuple)
    detection_dirs: tuple[str, ...] = field(default_factory=tuple)
    # Mapping from pack source dir to target subdir within platform dir
    # e.g., {"agents": "agents", "instructions": ""} means agents go to .github/agents,
    # instructions go directly to .github/
    dir_mapping: dict[str, str] = field(default_factory=dict)
    # File patterns to look for in pack directories
    file_patterns: tuple[str, ...] = ("*.md", "*.yaml", "*.yml", "*.json", "*.txt")


# Supported AI platforms and their configurations
PLATFORMS: dict[str, PlatformConfig] = {
    "github-copilot": PlatformConfig(
        name="GitHub Copilot",
        target_dir=".github",
        detection_files=("copilot-instructions.md",),
        detection_dirs=(".github",),
        dir_mapping={
            "agents": "agents",
            "prompts": "prompts",
            "instructions": "",  # Instructions go directly to .github/
            "skills": "skills",
            "tools": "tools",
            "workflows": "workflows",
        },
    ),
    "claude": PlatformConfig(
        name="Claude",
        target_dir=".claude",
        detection_files=("CLAUDE.md", "claude.md"),
        detection_dirs=(".claude",),
        dir_mapping={
            "agents": "agents",
            "prompts": "prompts",
            "instructions": "",
            "skills": "skills",
            "tools": "tools",
            "workflows": "workflows",
        },
    ),
    "cursor": PlatformConfig(
        name="Cursor",
        target_dir=".cursor",
        detection_files=(".cursorrules", "cursor.md"),
        detection_dirs=(".cursor",),
        dir_mapping={
            "agents": "agents",
            "prompts": "prompts",
            "instructions": "",
            "skills": "skills",
            "tools": "tools",
            "workflows": "workflows",
        },
    ),
    "windsurf": PlatformConfig(
        name="Windsurf",
        target_dir=".windsurf",
        detection_files=(".windsurfrules",),
        detection_dirs=(".windsurf", ".codeium"),
        dir_mapping={
            "agents": "agents",
            "prompts": "prompts",
            "instructions": "",
            "skills": "skills",
            "tools": "tools",
            "workflows": "workflows",
        },
    ),
    "aider": PlatformConfig(
        name="Aider",
        target_dir=".aider",
        detection_files=(".aider.conf.yml", "aider.md", ".aiderignore"),
        detection_dirs=(".aider",),
        dir_mapping={
            "agents": "agents",
            "prompts": "prompts",
            "instructions": "",
            "skills": "skills",
            "tools": "tools",
            "workflows": "workflows",
        },
    ),
}


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

    def _format_connection_error(self, error: Exception) -> str:
        """Format a connection error message.

        Args:
            error: The connection error exception.

        Returns:
            A user-friendly error message.
        """
        return (
            f"Unable to connect to the AyAiAy API server at "
            f"{self.config.api_base_url}. "
            f"Please check your internet connection and try again. "
            f"Error: {error}"
        )

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
        except (httpx.ConnectError, httpx.RequestError) as e:
            return InstallResult(
                success=False,
                pack=None,
                version=None,
                install_path=None,
                message=self._format_connection_error(e),
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
        except (httpx.ConnectError, httpx.RequestError) as e:
            return InstallResult(
                success=False,
                pack=pack,
                version=None,
                install_path=None,
                message=self._format_connection_error(e),
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
                    message=(
                        f"Already installed: " f"{pack_ref.full_name}@{version.version}"
                    ),
                )

        # Remove old project files before reinstalling (for updates)
        if install_path.exists() and force:
            self._remove_project_files(install_path)

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

        # Generate skill files from manifest if they don't already exist
        try:
            self._generate_skills_from_manifest(install_path)
        except Exception:
            # Skills from manifest are optional, silently ignore errors
            pass

        # Copy pack files into project workspace when applicable
        try:
            project_path = Path.cwd()
            project_files: list[Path] = []
            if self._should_apply_to_project(project_path):
                project_files = self._copy_pack_project_files(
                    install_path,
                    project_path,
                )
        except Exception as e:
            return InstallResult(
                success=False,
                pack=pack,
                version=version,
                install_path=install_path,
                message=f"Failed to apply pack files to project: {e}",
            )

        # Write installation metadata
        self._write_install_metadata(install_path, pack, version, project_files)

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

        self._remove_project_files(install_path)
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
        installed: list[tuple[str, str, Path]] = []
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
        """Get the installed version from metadata.

        Args:
            install_path: Path to the installed pack.

        Returns:
            Version string or None if not found.
        """
        metadata_path = install_path / METADATA_FILENAME
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                version_value: str | None = data.get("version")
                return version_value
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _pull_from_registry(
        self,
        pack: Pack,
        version: PackVersion,
        install_path: Path,
    ) -> None:
        """Pull pack from OCI registry or GitHub.

        This method attempts to pull a pack first from GitHub if a repository
        URL is available, then falls back to OCI registry if necessary.

        Args:
            pack: Pack information.
            version: Version to install.
            install_path: Target installation path.

        Raises:
            RuntimeError: If both GitHub and OCI pulls fail.
        """
        # For now, we'll try to clone from GitHub if available
        if pack.repository_url:
            self._clone_from_github(
                str(pack.repository_url), version.version, install_path
            )
        else:
            # Fallback: try OCI pull with oras or docker
            self._pull_oci(pack, version, install_path)

    def _clone_from_github(
        self,
        repo_url: str,
        version: str,
        install_path: Path,
    ) -> None:
        """Clone pack from GitHub repository.

        Args:
            repo_url: GitHub repository URL.
            version: Version tag to clone.
            install_path: Path to install the pack.

        Raises:
            subprocess.CalledProcessError: If git clone fails.
        """
        install_path.parent.mkdir(parents=True, exist_ok=True)

        if install_path.exists():
            shutil.rmtree(install_path)

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Clone with specific tag/version
            tag = (
                f"{VERSION_PREFIX}{version}"
                if not version.startswith(VERSION_PREFIX)
                else version
            )
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        str(GIT_CLONE_DEPTH),
                        "--branch",
                        tag,
                        repo_url,
                        tmp_dir,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError:
                # Try without version prefix
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        str(GIT_CLONE_DEPTH),
                        "--branch",
                        version,
                        repo_url,
                        tmp_dir,
                    ],
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
        """Pull pack from OCI registry using oras CLI.

        Args:
            pack: Pack information.
            version: Version to pull.
            install_path: Target installation path.

        Raises:
            RuntimeError: If oras is not installed or pull fails.
        """
        image = (
            f"{self.config.registry_url}/{pack.publisher}/{pack.name}:{version.version}"
        )

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

        # Fallback error with helpful message
        raise RuntimeError(
            "Cannot pull from OCI registry. Install 'oras' CLI or ensure "
            "the pack has a GitHub repository URL."
        )

    def _write_install_metadata(
        self,
        install_path: Path,
        pack: Pack,
        version: PackVersion,
        project_files: list[Path] | None = None,
    ) -> None:
        """Write installation metadata file.

        Args:
            install_path: Path to the installed pack.
            pack: Pack information.
            version: Version information.
        """
        metadata = {
            "pack_id": pack.id,
            "full_name": pack.full_name,
            "version": version.version,
            "installed_at": (
                version.published_at.isoformat() if version.published_at else None
            ),
            "digest": version.digest,
            "project_files": [str(path) for path in (project_files or [])],
        }
        metadata_path = install_path / METADATA_FILENAME
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _should_apply_to_project(self, project_path: Path) -> bool:
        """Determine whether pack files should be applied to the project.

        Args:
            project_path: Path to the current project.

        Returns:
            True if the project should receive pack files.
        """
        if (project_path / LOCK_FILENAME).exists():
            return True
        return any(
            (project_path / filename).exists()
            for filename in PROJECT_MANIFEST_FILENAMES
        )

    def _detect_platforms(self, project_path: Path) -> list[str]:
        """Detect which AI platforms are configured in the project.

        Detection is based on presence of platform-specific files or directories.
        If no platforms are detected but ayaiay.json exists, defaults to github-copilot.

        Args:
            project_path: Path to the project root.

        Returns:
            List of detected platform identifiers.
        """
        detected: list[str] = []

        for platform_id, config in PLATFORMS.items():
            # Check for detection files
            for filename in config.detection_files:
                # Check in project root
                if (project_path / filename).exists():
                    detected.append(platform_id)
                    break
                # Check in platform target dir
                if (project_path / config.target_dir / filename).exists():
                    detected.append(platform_id)
                    break
            else:
                # Check for detection directories
                for dirname in config.detection_dirs:
                    if (project_path / dirname).is_dir():
                        detected.append(platform_id)
                        break

        # Default to github-copilot if ayaiay.json exists but no platform detected
        if not detected and (project_path / LOCK_FILENAME).exists():
            detected.append("github-copilot")

        return detected

    def _copy_pack_project_files(
        self,
        install_path: Path,
        project_path: Path,
    ) -> list[Path]:
        """Copy pack project files into the current workspace.

        Copies files based on detected platforms. This method detects which
        AI platforms are configured in the project
        and copies pack files (agents, prompts, instructions, etc.) to the
        appropriate target directories for each platform.

        Args:
            install_path: Installed pack path.
            project_path: Target project path.

        Returns:
            List of target paths that were copied.
        """
        copied: list[Path] = []

        # Detect configured platforms
        platforms = self._detect_platforms(project_path)

        if not platforms:
            # No platforms detected, use legacy behavior (copy .github if exists)
            return self._copy_legacy_project_files(install_path, project_path)

        # For each detected platform, copy the appropriate files
        for platform_id in platforms:
            platform_config = PLATFORMS.get(platform_id)
            if not platform_config:
                continue

            platform_copied = self._copy_files_for_platform(
                install_path, project_path, platform_config
            )
            copied.extend(platform_copied)

        return copied

    def _copy_files_for_platform(
        self,
        install_path: Path,
        project_path: Path,
        platform: PlatformConfig,
    ) -> list[Path]:
        """Copy pack files to the target directories for a specific platform.

        Checks two source locations for each artifact directory:
        1. Top-level pack directory (e.g., install_path/agents/)
           - platform-agnostic format
        2. Platform-specific directory (e.g., install_path/.github/agents/)
           - native format

        Args:
            install_path: Installed pack path.
            project_path: Target project path.
            platform: Platform configuration.

        Returns:
            List of target paths that were copied.
        """
        copied: list[Path] = []
        target_base = project_path / platform.target_dir

        for source_dir_name in PACK_SOURCE_DIRS:
            # Check top-level pack directory first (platform-agnostic format)
            source_dir = install_path / source_dir_name
            if not source_dir.is_dir():
                # Fall back to platform-specific directories within the pack.
                # First check the current platform's dir (e.g., .claude/agents/),
                # then check other platform dirs (e.g., .github/agents/) so packs
                # authored for one platform still work for others.
                source_dir = self._find_platform_source_dir(
                    install_path, source_dir_name, platform
                )
                if source_dir is None:
                    continue

            # Determine target subdirectory from mapping
            target_subdir = platform.dir_mapping.get(source_dir_name, source_dir_name)

            # Empty string means copy directly to platform target dir
            target_dir = target_base / target_subdir if target_subdir else target_base

            # Copy all matching files from source directory
            for source_file in source_dir.rglob("*"):
                if source_file.is_dir():
                    continue

                # Check if file matches any of the file patterns
                if not any(
                    source_file.match(pattern) for pattern in platform.file_patterns
                ):
                    continue

                # Calculate relative path within the source directory
                relative_in_source = source_file.relative_to(source_dir)
                target_path = target_dir / relative_in_source

                target_path.parent.mkdir(parents=True, exist_ok=True)
                existed_before = target_path.exists()
                shutil.copy2(source_file, target_path)

                if not existed_before:
                    copied.append(target_path)

        return copied

    def _find_platform_source_dir(
        self,
        install_path: Path,
        source_dir_name: str,
        platform: PlatformConfig,
    ) -> Path | None:
        """Find a source directory for artifacts within platform-specific pack dirs.

        Checks for the source directory (e.g., "agents") inside platform-specific
        directories in the pack. Prioritises the current platform's directory,
        then falls back to any other platform directory that contains the
        requested source dir.

        Args:
            install_path: Installed pack path.
            source_dir_name: Name of the source directory to find (e.g., "agents").
            platform: The target platform configuration.

        Returns:
            Path to the source directory, or None if not found.
        """
        # Check the current platform's dir first (e.g., .github/agents/)
        candidate = install_path / platform.target_dir / source_dir_name
        if candidate.is_dir():
            return candidate

        # Check other platform directories in the pack
        for other_platform in PLATFORMS.values():
            if other_platform.target_dir == platform.target_dir:
                continue
            candidate = install_path / other_platform.target_dir / source_dir_name
            if candidate.is_dir():
                return candidate

        return None

    def _copy_legacy_project_files(
        self,
        install_path: Path,
        project_path: Path,
    ) -> list[Path]:
        """Legacy copy behavior: copy .github directory directly.

        This is used when no platforms are detected but the pack
        contains a .github directory.

        Args:
            install_path: Installed pack path.
            project_path: Target project path.

        Returns:
            List of target paths that were copied.
        """
        copied: list[Path] = []

        for rel_path in PROJECT_COPY_DIRS:
            source = install_path / rel_path
            if not source.exists():
                continue

            if source.is_file():
                target = project_path / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                existed_before = target.exists()
                shutil.copy2(source, target)
                if not existed_before:
                    copied.append(target)
                continue

            for source_path in source.rglob("*"):
                if source_path.is_dir():
                    continue
                relative = source_path.relative_to(install_path)
                target_path = project_path / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                existed_before = target_path.exists()
                shutil.copy2(source_path, target_path)
                if not existed_before:
                    copied.append(target_path)

        return copied

    def _generate_skills_from_manifest(self, install_path: Path) -> None:
        """Generate skill files from manifest skill definitions.

        Reads the ayaiay.yaml manifest from the installed pack and generates
        individual skill .md files in the skills/ directory for each skill
        defined in the manifest. Only generates files if they don't already exist.

        Args:
            install_path: Path to the installed pack.
        """
        # Look for manifest file in the install path
        manifest_path = None
        for filename in PROJECT_MANIFEST_FILENAMES:
            candidate = install_path / filename
            if candidate.exists():
                manifest_path = candidate
                break

        if not manifest_path:
            # No manifest found, nothing to do
            return

        # Load the manifest
        try:
            manifest = load_manifest(manifest_path)
        except Exception:
            # If we can't load the manifest, skip skill generation
            return

        # Check if there are any skills defined
        if not manifest.skills:
            return

        # Create skills directory in the install path
        skills_dir = install_path / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Generate a file for each skill
        for skill in manifest.skills:
            filename = normalize_skill_filename(skill.name)
            skill_file = skills_dir / filename

            # Only create if it doesn't already exist
            if not skill_file.exists():
                content = generate_skill_file_content(skill)
                with open(skill_file, "w", encoding="utf-8") as f:
                    f.write(content)

    def _remove_project_files(self, install_path: Path) -> None:
        """Remove project files that were copied during installation.

        Args:
            install_path: Installed pack path.
        """
        metadata_path = install_path / METADATA_FILENAME
        if not metadata_path.exists():
            return

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        project_files = metadata.get("project_files", [])
        if not isinstance(project_files, list):
            return

        # Collect all platform target directories for cleanup
        platform_dirs = {config.target_dir for config in PLATFORMS.values()}
        platform_dirs.add(".github")  # Always include .github for legacy support

        for file_path in project_files:
            try:
                target = Path(file_path)
            except TypeError:
                continue
            if target.exists() and target.is_file():
                target.unlink()

            # Clean up empty parent directories up to the platform dir
            parent = target.parent
            while parent.exists() and parent.name not in platform_dirs and parent.name:
                if any(parent.iterdir()):
                    break
                parent.rmdir()
                parent = parent.parent

            # Clean up platform dir if empty
            if (
                parent.exists()
                and parent.name in platform_dirs
                and not any(parent.iterdir())
            ):
                parent.rmdir()


def normalize_skill_filename(skill_name: str) -> str:
    """Convert a skill name to a normalized kebab-case filename.

    Args:
        skill_name: The skill name to normalize.

    Returns:
        Normalized filename with .md extension.

    Example:
        >>> normalize_skill_filename("Code Analyzer")
        'code-analyzer.md'
        >>> normalize_skill_filename("file_reader")
        'file-reader.md'
    """
    return skill_name.lower().replace(" ", "-").replace("_", "-") + ".md"


def generate_skill_file_content(skill: ManifestSkill) -> str:
    """Generate skill file content from a ManifestSkill definition.

    Args:
        skill: ManifestSkill object from manifest.

    Returns:
        Formatted skill content as markdown.
    """
    # Convert skill name for display
    skill_name_display = skill.name.lower().replace("-", " ").replace("_", " ")

    # Generate parameters documentation if any
    params_doc = ""
    param_signature = ""
    if skill.parameters:
        param_signature = ", ".join(skill.parameters)
        params_doc = "\n## Parameters\n\n"
        for param in skill.parameters:
            params_doc += f"- **{param}** (required)\n"

    # Build the skill content
    description = (
        skill.description
        or f"A custom skill that performs a {skill_name_display}"
    )

    content = f"""# {skill.name}

{description}

## Overview

This skill provides functionality for {skill_name_display}.

## Function Signature

```typescript
function {skill.name.replace('-', '_').replace(' ', '_')}({param_signature}): any
```
{params_doc}
## Returns

- **Type**: `any`
- **Description**: The result of the {skill_name_display} operation.

## Implementation

{skill.content}

## Example Usage

```typescript
// Example usage
const result = {skill.name.replace('-', '_').replace(' ', '_')}({param_signature});
console.log(result);
```

## Best Practices

- Use appropriate error handling
- Validate all inputs
- Follow security best practices
- Document any assumptions
"""

    return content
