"""Tests for the CLI interface."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from ayaiay.cli import main
from ayaiay.models import Pack, PackType, SearchResult


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self, runner: CliRunner) -> None:
        """Test --version flag."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "ayaiay" in result.output
        assert "1.1.0" in result.output

    def test_help(self, runner: CliRunner) -> None:
        """Test --help flag."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "AyAiAy CLI" in result.output
        assert "search" in result.output
        assert "install" in result.output
        assert "validate" in result.output


class TestSearchCommand:
    """Tests for the search command."""

    def test_search_no_results(self, runner: CliRunner) -> None:
        """Test search with no results."""
        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.search_packs.return_value = SearchResult(
                packs=[], total=0, page=1, per_page=20
            )

            result = runner.invoke(main, ["search", "nonexistent"])

            assert result.exit_code == 0
            assert "No packs found" in result.output

    def test_search_with_results(self, runner: CliRunner) -> None:
        """Test search with results."""
        mock_pack = Pack(
            id="pack-1",
            name="test-pack",
            publisher="test-user",
            pack_type=PackType.AGENT,
            description="A test pack",
            latest_version="1.0.0",
            downloads=100,
        )

        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.search_packs.return_value = SearchResult(
                packs=[mock_pack], total=1, page=1, per_page=20
            )

            result = runner.invoke(main, ["search", "test"])

            assert result.exit_code == 0
            assert "test-user/test-pack" in result.output
            assert "agent" in result.output.lower()

    def test_search_with_type_filter(self, runner: CliRunner) -> None:
        """Test search with type filter."""
        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.search_packs.return_value = SearchResult(
                packs=[], total=0, page=1, per_page=20
            )

            runner.invoke(main, ["search", "--type", "agent", "test"])

            mock_client.search_packs.assert_called_once()
            call_kwargs = mock_client.search_packs.call_args.kwargs
            assert call_kwargs["pack_type"] == "agent"

    def test_search_connection_error(self, runner: CliRunner) -> None:
        """Test search handles connection errors gracefully."""
        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            import httpx

            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.search_packs.side_effect = httpx.ConnectError(
                "Connection failed"
            )

            result = runner.invoke(main, ["search", "test"])

            assert result.exit_code == 1
            assert "Unable to connect" in result.output
            assert "internet connection" in result.output


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_manifest(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test validating a valid manifest."""
        manifest_data = {
            "name": "test-pack",
            "agents": [{"name": "test-agent"}],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = runner.invoke(main, ["validate", str(manifest_path)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_invalid_manifest(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test validating an invalid manifest."""
        manifest_data = {
            "description": "Missing name field",
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = runner.invoke(main, ["validate", str(manifest_path)])

        assert result.exit_code == 1
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_validate_quiet_mode(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test validate with quiet flag."""
        manifest_data = {
            "name": "test-pack",
            "agents": [{"name": "test-agent"}],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = runner.invoke(main, ["validate", "--quiet", str(manifest_path)])

        assert result.exit_code == 0
        # In quiet mode, minimal output
        assert len(result.output.strip()) < 100 or result.output.strip() == ""


class TestInstallCommand:
    """Tests for the install command."""

    def test_install_invalid_reference(self, runner: CliRunner) -> None:
        """Test install with invalid pack reference."""
        result = runner.invoke(main, ["install", "invalid-reference"])

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    def test_install_success(self, runner: CliRunner) -> None:
        """Test successful installation."""
        with patch("ayaiay.cli.Installer") as mock_installer_class:
            mock_installer = MagicMock()
            mock_installer_class.return_value = mock_installer

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.message = "Successfully installed test-user/test-pack@1.0.0"
            mock_result.install_path = Path(
                "/home/user/.ayaiay/packs/test-user/test-pack"
            )
            mock_installer.install.return_value = mock_result

            result = runner.invoke(main, ["install", "test-user/test-pack@1.0.0"])

            assert result.exit_code == 0
            assert "success" in result.output.lower()

    def test_install_failure(self, runner: CliRunner) -> None:
        """Test failed installation."""
        with patch("ayaiay.cli.Installer") as mock_installer_class:
            mock_installer = MagicMock()
            mock_installer_class.return_value = mock_installer

            mock_result = MagicMock()
            mock_result.success = False
            mock_result.message = "Pack not found: test-user/nonexistent"
            mock_installer.install.return_value = mock_result

            result = runner.invoke(main, ["install", "test-user/nonexistent"])

            assert result.exit_code == 1

    def test_install_connection_error(self, runner: CliRunner) -> None:
        """Test installation with connection error."""
        with patch("ayaiay.cli.Installer") as mock_installer_class:
            mock_installer = MagicMock()
            mock_installer_class.return_value = mock_installer

            mock_result = MagicMock()
            mock_result.success = False
            mock_result.message = (
                "Unable to connect to the AyAiAy API server at https://ayaiay.org. "
                "Please check your internet connection and try again."
            )
            mock_installer.install.return_value = mock_result

            result = runner.invoke(main, ["install", "test-user/test-pack"])

            assert result.exit_code == 1
            assert (
                "unable to connect" in result.output.lower()
                or "error" in result.output.lower()
            )


class TestListCommand:
    """Tests for the list command."""

    def test_list_no_packs(self, runner: CliRunner) -> None:
        """Test list with no installed packs."""
        with patch("ayaiay.cli.Installer") as mock_installer_class:
            mock_installer = MagicMock()
            mock_installer_class.return_value = mock_installer
            mock_installer.list_installed.return_value = []

            result = runner.invoke(main, ["list"])

            assert result.exit_code == 0
            assert "no packs installed" in result.output.lower()

    def test_list_with_packs(self, runner: CliRunner) -> None:
        """Test list with installed packs."""
        with patch("ayaiay.cli.Installer") as mock_installer_class:
            mock_installer = MagicMock()
            mock_installer_class.return_value = mock_installer
            mock_installer.list_installed.return_value = [
                (
                    "test-user/pack-one",
                    "1.0.0",
                    Path("/home/.ayaiay/packs/test-user/pack-one"),
                ),
                (
                    "test-user/pack-two",
                    "2.0.0",
                    Path("/home/.ayaiay/packs/test-user/pack-two"),
                ),
            ]

            result = runner.invoke(main, ["list"])

            assert result.exit_code == 0
            assert "test-user/pack-one" in result.output
            assert "test-user/pack-two" in result.output
            assert "1.0.0" in result.output
            assert "2.0.0" in result.output


class TestShowCommand:
    """Tests for the show command."""

    def test_show_connection_error(self, runner: CliRunner) -> None:
        """Test show handles connection errors gracefully."""
        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            import httpx

            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get_pack.side_effect = httpx.ConnectError("Connection failed")

            result = runner.invoke(main, ["show", "test-user/test-pack"])

            assert result.exit_code == 1
            assert "Unable to connect" in result.output
            assert "internet connection" in result.output


class TestInfoCommand:
    """Tests for the info command."""

    def test_info_display(self, runner: CliRunner) -> None:
        """Test info command displays configuration."""
        with patch("ayaiay.cli.AyAiAyClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.health_check.return_value = True

            result = runner.invoke(main, ["info"])

            assert result.exit_code == 0
            assert "api" in result.output.lower()
            assert "ayaiay.org" in result.output.lower()
