"""Tests for the pack installer."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ayaiay.config import Config
from ayaiay.installer import (
    Installer,
    generate_skill_file_content,
    normalize_skill_filename,
)
from ayaiay.models import ManifestSkill, Pack, PackType, PackVersion


@pytest.fixture
def config() -> Config:
    """Create a test configuration."""
    return Config(
        api_base_url="https://api.test.ayaiay.org",
        timeout=10.0,
    )


@pytest.fixture
def installer(config: Config) -> Installer:
    """Create a test installer."""
    return Installer(config=config)


class TestSkillGeneration:
    """Tests for skill file generation."""

    def test_normalize_skill_filename(self) -> None:
        """Test skill name normalization to filename."""
        assert normalize_skill_filename("code-analyzer") == "code-analyzer.md"
        assert normalize_skill_filename("Code Analyzer") == "code-analyzer.md"
        assert normalize_skill_filename("file_reader") == "file-reader.md"
        assert normalize_skill_filename("My_Skill Name") == "my-skill-name.md"

    def test_generate_skill_file_content(self) -> None:
        """Test generating skill file content from ManifestSkill."""
        skill = ManifestSkill(
            name="code-analyzer",
            description="Analyzes code structure and patterns",
            content="Analyze the provided code and identify design patterns used.",
            parameters=["file_path", "language"],
        )

        content = generate_skill_file_content(skill)

        # Check that all key sections are present
        assert "# code-analyzer" in content
        assert "Analyzes code structure and patterns" in content
        assert "## Overview" in content
        assert "## Function Signature" in content
        assert "## Parameters" in content
        assert "file_path" in content
        assert "language" in content
        assert "## Implementation" in content
        assert "Analyze the provided code and identify design patterns used." in content
        assert "## Example Usage" in content

    def test_generate_skill_file_content_no_parameters(self) -> None:
        """Test generating skill file content without parameters."""
        skill = ManifestSkill(
            name="simple-skill",
            description="A simple skill",
            content="Does something simple.",
            parameters=[],
        )

        content = generate_skill_file_content(skill)

        # Check that the file is generated properly without parameters
        assert "# simple-skill" in content
        assert "A simple skill" in content
        assert "Does something simple." in content
        # Parameters section should be minimal or absent
        assert "## Returns" in content


class TestInstaller:
    """Tests for Installer class."""

    def test_install_specific_version_from_registry(self, tmp_path: Path) -> None:
        """Test installing a specific version by reference."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            timeout=10.0,
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-awesome-pack",
            publisher="philippfrenzel",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/philippfrenzel/my-awesome-pack",
        )
        version = PackVersion(version="1.0.1")

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(installer.client, "get_pack", return_value=pack) as mock_get,
            patch.object(
                installer.client,
                "get_pack_version",
                return_value=version,
            ) as mock_get_version,
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("philippfrenzel/my-awesome-pack@1.0.1")

        mock_get.assert_called_once_with("philippfrenzel/my-awesome-pack")
        mock_get_version.assert_called_once_with(
            "philippfrenzel/my-awesome-pack",
            "1.0.1",
        )

        assert result.success is True
        assert result.pack == pack
        assert result.version == version
        assert (
            result.install_path
            == config.install_dir / "philippfrenzel" / "my-awesome-pack"
        )
        assert result.install_path.exists()
        assert "Successfully installed" in result.message

    def test_install_copies_agents_to_project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying agents folder into the current project's platform directory."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            timeout=10.0,
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-awesome-pack",
            publisher="philippfrenzel",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/philippfrenzel/my-awesome-pack",
        )
        version = PackVersion(version="1.0.1")

        project_path = tmp_path / "project"
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            agents_path = install_path / "agents"
            agents_path.mkdir(parents=True, exist_ok=True)
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(
                installer.client,
                "get_pack_version",
                return_value=version,
            ),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("philippfrenzel/my-awesome-pack@1.0.1")

        assert result.success is True
        # Default platform is github-copilot when ayaiay.json exists
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()
        assert copied_agent.read_text() == "# Agent Instructions"

    def test_uninstall_removes_project_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test uninstall removes files copied into the project."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            timeout=10.0,
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-awesome-pack",
            publisher="philippfrenzel",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/philippfrenzel/my-awesome-pack",
        )
        version = PackVersion(version="1.0.1")

        project_path = tmp_path / "project"
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            agents_path = install_path / "agents"
            agents_path.mkdir(parents=True, exist_ok=True)
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(
                installer.client,
                "get_pack_version",
                return_value=version,
            ),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("philippfrenzel/my-awesome-pack@1.0.1")

        assert result.success is True
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()

        uninstall_result = installer.uninstall("philippfrenzel/my-awesome-pack")
        assert uninstall_result.success is True
        assert not copied_agent.exists()

    def test_install_with_connection_error(self, installer: Installer) -> None:
        """Test install handles connection errors gracefully."""
        with patch.object(installer.client, "get_pack") as mock_get_pack:
            mock_get_pack.side_effect = httpx.ConnectError(
                "[Errno -2] Name or service not known"
            )

            result = installer.install("test-user/test-pack")

            assert result.success is False
            assert "unable to connect" in result.message.lower()
            assert "api.test.ayaiay.org" in result.message
            assert result.pack is None
            assert result.version is None
            assert result.install_path is None

    def test_install_with_request_error(self, installer: Installer) -> None:
        """Test install handles request errors gracefully."""
        with patch.object(installer.client, "get_pack") as mock_get_pack:
            mock_get_pack.side_effect = httpx.RequestError("Connection timeout")

            result = installer.install("test-user/test-pack")

            assert result.success is False
            assert "unable to connect" in result.message.lower()
            assert result.pack is None

    def test_install_with_connection_error_on_version_fetch(
        self, installer: Installer
    ) -> None:
        """Test install handles connection errors when fetching versions."""
        mock_pack = MagicMock()
        mock_pack.full_name = "test-user/test-pack"

        with (
            patch.object(installer.client, "get_pack") as mock_get_pack,
            patch.object(installer.client, "get_pack_versions") as mock_get_versions,
        ):
            mock_get_pack.return_value = mock_pack
            mock_get_versions.side_effect = httpx.ConnectError(
                "[Errno -2] Name or service not known"
            )

            result = installer.install("test-user/test-pack")

            assert result.success is False
            assert "unable to connect" in result.message.lower()
            assert result.pack == mock_pack
            assert result.version is None

    def test_install_invalid_reference(self, installer: Installer) -> None:
        """Test install with invalid pack reference."""
        result = installer.install("invalid-reference")

        assert result.success is False
        assert "invalid pack reference" in result.message.lower()
        assert result.pack is None

    @pytest.mark.integration
    @pytest.mark.skipif(
        os.environ.get("AYAIAY_INTEGRATION_TESTS") != "1",
        reason="Integration test disabled (set AYAIAY_INTEGRATION_TESTS=1)",
    )
    def test_install_real_package(self, tmp_path: Path) -> None:
        """Integration test: install a real package from the registry."""
        config = Config(
            api_base_url=os.environ.get("AYAIAY_API_URL", "https://ayaiay.org"),
            registry_url=os.environ.get("AYAIAY_REGISTRY_URL", "ghcr.io/ayaiayorg"),
            timeout=float(os.environ.get("AYAIAY_TIMEOUT", "30")),
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        result = installer.install("philippfrenzel/senior-python-developer@1.0.0")

        if (not result.success) and "unable to connect" in result.message.lower():
            pytest.skip("AyAiAy API not reachable from test environment")

        assert result.success is True
        assert result.pack is not None
        assert result.version is not None
        assert result.version.version == "1.0.0"
        assert result.install_path is not None
        assert result.install_path.exists()


class TestPlatformDetection:
    """Tests for platform detection functionality."""

    def test_detect_github_copilot_by_directory(self, tmp_path: Path) -> None:
        """Test detection of GitHub Copilot by .github directory."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()

        platforms = installer._detect_platforms(project_path)
        assert "github-copilot" in platforms

    def test_detect_claude_by_directory(self, tmp_path: Path) -> None:
        """Test detection of Claude by .claude directory."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()

        platforms = installer._detect_platforms(project_path)
        assert "claude" in platforms

    def test_detect_cursor_by_file(self, tmp_path: Path) -> None:
        """Test detection of Cursor by .cursorrules file."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".cursorrules").write_text("rules")

        platforms = installer._detect_platforms(project_path)
        assert "cursor" in platforms

    def test_detect_multiple_platforms(self, tmp_path: Path) -> None:
        """Test detection of multiple platforms."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / ".claude").mkdir()

        platforms = installer._detect_platforms(project_path)
        assert "github-copilot" in platforms
        assert "claude" in platforms

    def test_default_to_github_copilot_with_lockfile(self, tmp_path: Path) -> None:
        """Test default to github-copilot when only ayaiay.json exists."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "ayaiay.json").write_text("{}")

        platforms = installer._detect_platforms(project_path)
        assert "github-copilot" in platforms


class TestPlatformFileCopying:
    """Tests for platform-specific file copying."""

    def test_copy_agents_to_github_copilot(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying agents directory to .github/agents for GitHub Copilot."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir()
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()
        assert copied_agent.read_text() == "# Agent Instructions"

    def test_copy_agents_to_claude(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying agents directory to .claude/agents for Claude."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".claude").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir()
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        copied_agent = project_path / ".claude" / "agents" / "my-agent.md"
        assert copied_agent.exists()
        assert copied_agent.read_text() == "# Agent Instructions"

    def test_copy_to_multiple_platforms(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying files to multiple platforms simultaneously."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / ".claude").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir()
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        # Check both platforms received the files
        assert (project_path / ".github" / "agents" / "my-agent.md").exists()
        assert (project_path / ".claude" / "agents" / "my-agent.md").exists()

    def test_copy_instructions_to_platform_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that instructions are copied directly to platform root."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.INSTRUCTION,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            instructions_path = install_path / "instructions"
            instructions_path.mkdir()
            (instructions_path / "copilot-instructions.md").write_text("# Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        # Instructions go directly to .github/ not .github/instructions/
        copied_instruction = project_path / ".github" / "copilot-instructions.md"
        assert copied_instruction.exists()
        assert copied_instruction.read_text() == "# Instructions"

    def test_uninstall_removes_platform_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that uninstall removes files from all platforms."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / ".claude").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir()
            (agents_path / "my-agent.md").write_text("# Agent Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        github_agent = project_path / ".github" / "agents" / "my-agent.md"
        claude_agent = project_path / ".claude" / "agents" / "my-agent.md"
        assert github_agent.exists()
        assert claude_agent.exists()

        # Uninstall
        uninstall_result = installer.uninstall("test/my-pack")
        assert uninstall_result.success is True
        assert not github_agent.exists()
        assert not claude_agent.exists()

    def test_force_reinstall_updates_project_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that force reinstall properly updates project files."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version_1 = PackVersion(version="1.0.0")
        version_2 = PackVersion(version="2.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        # First install with version 1.0.0
        def fake_pull_v1(
            _pack: Pack, _version: PackVersion, install_path: Path
        ) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir()
            (agents_path / "old-agent.md").write_text("# Old Agent v1")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version_1),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull_v1),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        old_agent = project_path / ".github" / "agents" / "old-agent.md"
        assert old_agent.exists()
        assert old_agent.read_text() == "# Old Agent v1"

        # Now force reinstall with version 2.0.0 (different file)
        def fake_pull_v2(
            _pack: Pack, _version: PackVersion, install_path: Path
        ) -> None:
            # Simulate real _clone_from_github behavior: clear and recreate
            import shutil

            if install_path.exists():
                shutil.rmtree(install_path)
            install_path.mkdir(parents=True, exist_ok=True)
            agents_path = install_path / "agents"
            agents_path.mkdir(exist_ok=True)
            (agents_path / "new-agent.md").write_text("# New Agent v2")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version_2),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull_v2),
        ):
            result = installer.install("test/my-pack@2.0.0", force=True)

        assert result.success is True
        # Old file should be removed
        assert not old_agent.exists()
        # New file should exist
        new_agent = project_path / ".github" / "agents" / "new-agent.md"
        assert new_agent.exists()
        assert new_agent.read_text() == "# New Agent v2"


class TestPlatformSpecificPackStructure:
    """Tests for packs that use platform-specific directory structures.

    Real-world packs from GitHub repos often store files under
    platform-specific directories (e.g., .github/agents/) rather than
    top-level directories (agents/).
    """

    def test_copy_agents_from_github_dir_in_pack(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying agents from .github/agents/ inside the pack."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            # Pack uses platform-specific structure: .github/agents/
            agents_path = install_path / ".github" / "agents"
            agents_path.mkdir(parents=True)
            (agents_path / "my-agent.md").write_text("# Agent from .github")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()
        assert copied_agent.read_text() == "# Agent from .github"

    def test_copy_instructions_from_github_dir_in_pack(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying instructions from .github/instructions/ inside the pack."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.INSTRUCTION,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            # Pack uses platform-specific structure: .github/instructions/
            instructions_path = install_path / ".github" / "instructions"
            instructions_path.mkdir(parents=True)
            (instructions_path / "copilot-instructions.md").write_text("# Instructions")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        # Instructions mapping is "" so they go directly to .github/
        copied = project_path / ".github" / "copilot-instructions.md"
        assert copied.exists()
        assert copied.read_text() == "# Instructions"

    def test_top_level_dir_takes_priority_over_platform_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that top-level agents/ is preferred over .github/agents/."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            # Pack has BOTH top-level and platform-specific agents
            top_agents = install_path / "agents"
            top_agents.mkdir()
            (top_agents / "my-agent.md").write_text("# Top-level agent")

            gh_agents = install_path / ".github" / "agents"
            gh_agents.mkdir(parents=True)
            (gh_agents / "my-agent.md").write_text("# Platform agent")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()
        # Top-level should take priority
        assert copied_agent.read_text() == "# Top-level agent"

    def test_github_pack_files_copied_to_multiple_platforms(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that .github/agents/ files are also copied to other detected platforms."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / ".claude").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            # Pack only has .github/agents/ (no top-level agents/)
            gh_agents = install_path / ".github" / "agents"
            gh_agents.mkdir(parents=True)
            (gh_agents / "my-agent.md").write_text("# Agent content")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        # Should be copied to .github/agents/ (from pack's .github/agents/)
        assert (project_path / ".github" / "agents" / "my-agent.md").exists()
        # Should also be copied to .claude/agents/ (using .github/agents/ as fallback)
        assert (project_path / ".claude" / "agents" / "my-agent.md").exists()

    def test_uninstall_removes_files_from_platform_specific_pack(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test uninstall works for packs that used platform-specific dirs."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="my-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/my-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            gh_agents = install_path / ".github" / "agents"
            gh_agents.mkdir(parents=True)
            (gh_agents / "my-agent.md").write_text("# Agent content")

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/my-pack@1.0.0")

        assert result.success is True
        copied_agent = project_path / ".github" / "agents" / "my-agent.md"
        assert copied_agent.exists()

        # Uninstall should clean up
        uninstall_result = installer.uninstall("test/my-pack")
        assert uninstall_result.success is True
        assert not copied_agent.exists()

    def test_generate_skills_from_manifest(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that skills defined in manifest are generated as files."""
        config = Config(
            api_base_url="https://api.test.ayaiay.org",
            install_dir=tmp_path / "packs",
            cache_dir=tmp_path / "cache",
        )
        installer = Installer(config=config)

        pack = Pack(
            id="pack-123",
            name="skills-pack",
            publisher="test",
            pack_type=PackType.AGENT,
            repository_url="https://github.com/test/skills-pack",
        )
        version = PackVersion(version="1.0.0")

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / ".github").mkdir()
        (project_path / "ayaiay.json").write_text("{}")
        monkeypatch.chdir(project_path)

        def fake_pull(_pack: Pack, _version: PackVersion, install_path: Path) -> None:
            install_path.mkdir(parents=True, exist_ok=True)
            # Create a manifest with skills
            manifest_content = """version: "1.0"
name: skills-pack
description: A pack with skills
author: Test Author

skills:
  - name: code-analyzer
    description: Analyzes code structure
    content: |
      Analyze the provided code and identify design patterns.
    parameters:
      - file_path
      - language
  - name: file-reader
    description: Reads file contents
    content: |
      Read and return the contents of the specified file.
    parameters:
      - path
"""
            (install_path / "ayaiay.yaml").write_text(manifest_content)

        with (
            patch.object(installer.client, "get_pack", return_value=pack),
            patch.object(installer.client, "get_pack_version", return_value=version),
            patch.object(installer, "_pull_from_registry", side_effect=fake_pull),
        ):
            result = installer.install("test/skills-pack@1.0.0")

        assert result.success is True
        
        # Check that skill files were generated in the pack install directory
        install_path = config.install_dir / "test" / "skills-pack"
        skill1 = install_path / "skills" / "code-analyzer.md"
        skill2 = install_path / "skills" / "file-reader.md"
        
        assert skill1.exists(), "code-analyzer.md should be generated"
        assert skill2.exists(), "file-reader.md should be generated"
        
        # Check content of one skill file
        skill1_content = skill1.read_text()
        assert "# code-analyzer" in skill1_content
        assert "Analyzes code structure" in skill1_content
        assert "file_path" in skill1_content
        assert "language" in skill1_content
        
        # Check that skills were copied to project
        project_skill1 = project_path / ".github" / "skills" / "code-analyzer.md"
        project_skill2 = project_path / ".github" / "skills" / "file-reader.md"
        
        assert project_skill1.exists(), "Skills should be copied to project .github/skills/"
        assert project_skill2.exists(), "Skills should be copied to project .github/skills/"
