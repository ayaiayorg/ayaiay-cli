"""Tests for the pack installer."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ayaiay.config import Config
from ayaiay.installer import Installer, InstallResult


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
