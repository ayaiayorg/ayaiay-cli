"""Tests for the pack installer."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ayaiay.config import Config
from ayaiay.installer import Installer
from ayaiay.models import Pack, PackType, PackVersion


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

    def test_install_copies_github_directory_to_project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test copying .github folder into the current project."""
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
            workflow_path = install_path / ".github" / "workflows"
            workflow_path.mkdir(parents=True, exist_ok=True)
            (workflow_path / "agent.yml").write_text("name: Test")

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
        copied_workflow = project_path / ".github" / "workflows" / "agent.yml"
        assert copied_workflow.exists()
        assert copied_workflow.read_text() == "name: Test"

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
            workflow_path = install_path / ".github" / "workflows"
            workflow_path.mkdir(parents=True, exist_ok=True)
            (workflow_path / "agent.yml").write_text("name: Test")

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
        copied_workflow = project_path / ".github" / "workflows" / "agent.yml"
        assert copied_workflow.exists()

        uninstall_result = installer.uninstall("philippfrenzel/my-awesome-pack")
        assert uninstall_result.success is True
        assert not copied_workflow.exists()

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
