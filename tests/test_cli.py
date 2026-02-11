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
        assert "1.3.2" in result.output

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


class TestInitPackCommand:
    """Tests for the init-pack command."""

    def test_init_pack_creates_manifest(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-pack creates a valid manifest file."""
        # Simulate user input for creating a minimal pack
        user_input = (
            "test-pack\n"  # pack name
            "A test pack\n"  # description
            "Test Author\n"  # author
            "MIT\n"  # license
            "https://github.com/test/test-pack\n"  # repository
            "testing,demo\n"  # tags
            "n\n"  # no agents
            "n\n"  # no instructions
            "n\n"  # no prompts
            "n\n"  # no skills
        )

        result = runner.invoke(
            main, ["init-pack", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0
        assert "Created pack manifest" in result.output
        assert "Manifest is valid" in result.output

        manifest_path = tmp_path / "ayaiay.yaml"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
            assert manifest["name"] == "test-pack"
            assert manifest["description"] == "A test pack"
            assert manifest["author"] == "Test Author"
            assert manifest["license"] == "MIT"
            assert manifest["tags"] == ["testing", "demo"]

    def test_init_pack_with_agent(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-pack creates manifest with an agent."""
        user_input = (
            "agent-pack\n"  # pack name
            "\n"  # description (empty)
            "\n"  # author (empty)
            "MIT\n"  # license
            "\n"  # repository (empty)
            "\n"  # tags (empty)
            "y\n"  # add agents
            "test-agent\n"  # agent name
            "A test agent\n"  # agent description
            "You are helpful\n"  # system prompt
            "gpt-4\n"  # model
            "read_file,write_file\n"  # tools
            "n\n"  # no more agents
            "n\n"  # no instructions
            "n\n"  # no prompts
            "n\n"  # no skills
        )

        result = runner.invoke(
            main, ["init-pack", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0

        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
            assert len(manifest.get("agents", [])) == 1
            agent = manifest["agents"][0]
            assert agent["name"] == "test-agent"
            assert agent["description"] == "A test agent"
            assert agent["system_prompt"] == "You are helpful"
            assert agent["model"] == "gpt-4"
            assert agent["tools"] == ["read_file", "write_file"]

    def test_init_pack_with_all_artifacts(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-pack creates manifest with all artifact types."""
        user_input = (
            "full-pack\n"  # pack name
            "Full pack\n"  # description
            "Author\n"  # author
            "MIT\n"  # license
            "\n"  # repository (empty)
            "tag1,tag2\n"  # tags
            "y\n"  # add agents
            "agent1\n"  # agent name
            "Desc\n"  # agent description
            "Prompt\n"  # system prompt
            "gpt-4\n"  # model
            "tool1\n"  # tools
            "n\n"  # no more agents
            "y\n"  # add instructions
            "instr1\n"  # instruction name
            "Instr desc\n"  # instruction description
            "Content\n"  # content
            "n\n"  # no more instructions
            "y\n"  # add prompts
            "prompt1\n"  # prompt name
            "Prompt desc\n"  # prompt description
            "Template {var}\n"  # template
            "var\n"  # variables
            "n\n"  # no more prompts
            "y\n"  # add skills
            "skill1\n"  # skill name
            "Skill desc\n"  # skill description
            "Skill content\n"  # content
            "param1\n"  # parameters
            "n\n"  # no more skills
        )

        result = runner.invoke(
            main, ["init-pack", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0
        assert "1 agent(s)" in result.output
        assert "1 instruction(s)" in result.output
        assert "1 prompt(s)" in result.output
        assert "1 skill(s)" in result.output

        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
            assert len(manifest.get("agents", [])) == 1
            assert len(manifest.get("instructions", [])) == 1
            assert len(manifest.get("prompts", [])) == 1
            assert len(manifest.get("skills", [])) == 1

    def test_init_pack_fails_if_manifest_exists(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-pack fails if manifest already exists."""
        manifest_path = tmp_path / "ayaiay.yaml"
        manifest_path.touch()

        result = runner.invoke(main, ["init-pack", "--path", str(tmp_path)])

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_init_pack_default_path(self, runner: CliRunner) -> None:
        """Test init-pack uses current directory by default."""
        user_input = (
            "test-pack\n"  # pack name
            "\n"  # description (empty)
            "\n"  # author (empty)
            "MIT\n"  # license
            "\n"  # repository (empty)
            "\n"  # tags (empty)
            "n\n"  # no agents
            "n\n"  # no instructions
            "n\n"  # no prompts
            "n\n"  # no skills
        )

        # Use runner's isolated filesystem
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init-pack"], input=user_input)

            assert result.exit_code == 0
            assert Path("ayaiay.yaml").exists()



class TestInitSkillCommand:
    """Tests for the init-skill command."""

    def test_init_skill_creates_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-skill creates a skill file."""
        user_input = (
            "test-skill\n"  # skill name
            "A test skill\n"  # description
            "y\n"  # add parameters
            "input\n"  # parameter name
            "string\n"  # parameter type
            "Input data\n"  # parameter description
            "y\n"  # required
            "n\n"  # no more parameters
            "string\n"  # return type
        )

        result = runner.invoke(
            main, ["init-skill", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0
        assert "Created skill file" in result.output

        skill_path = tmp_path / "test-skill.md"
        assert skill_path.exists()

        with open(skill_path) as f:
            content = f.read()
            assert "# test-skill" in content
            assert "A test skill" in content
            assert "function test_skill(input): string" in content
            assert "**input** (`string`) (required)" in content
            assert "Input data" in content

    def test_init_skill_with_name_option(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-skill with --name option."""
        user_input = (
            "Custom skill description\n"  # description
            "y\n"  # add parameters
            "file_path\n"  # parameter name
            "string\n"  # parameter type
            "Path to file\n"  # parameter description
            "y\n"  # required
            "n\n"  # no more parameters
            "object\n"  # return type
        )

        result = runner.invoke(
            main,
            ["init-skill", "--name", "file-analyzer", "--path", str(tmp_path)],
            input=user_input,
        )

        assert result.exit_code == 0
        assert "Created skill file" in result.output

        skill_path = tmp_path / "file-analyzer.md"
        assert skill_path.exists()

        with open(skill_path) as f:
            content = f.read()
            assert "# file-analyzer" in content
            assert "Custom skill description" in content
            assert "function file_analyzer(file_path): object" in content

    def test_init_skill_with_output_option(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-skill with --output option."""
        user_input = (
            "Skill description\n"  # description
            "n\n"  # no parameters
            "string\n"  # return type
        )

        result = runner.invoke(
            main,
            [
                "init-skill",
                "--name",
                "simple-skill",
                "--path",
                str(tmp_path),
                "--output",
                "custom-name.md",
            ],
            input=user_input,
        )

        assert result.exit_code == 0

        skill_path = tmp_path / "custom-name.md"
        assert skill_path.exists()

    def test_init_skill_multiple_parameters(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-skill with multiple parameters."""
        user_input = (
            "test-skill\n"  # skill name
            "Multi-param skill\n"  # description
            "y\n"  # add parameters
            "param1\n"  # parameter 1 name
            "string\n"  # parameter 1 type
            "First parameter\n"  # parameter 1 description
            "y\n"  # required
            "y\n"  # add another parameter
            "param2\n"  # parameter 2 name
            "number\n"  # parameter 2 type
            "Second parameter\n"  # parameter 2 description
            "n\n"  # not required
            "y\n"  # add another parameter
            "param3\n"  # parameter 3 name
            "boolean\n"  # parameter 3 type
            "Third parameter\n"  # parameter 3 description
            "y\n"  # required
            "n\n"  # no more parameters
            "array\n"  # return type
        )

        result = runner.invoke(
            main, ["init-skill", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0

        skill_path = tmp_path / "test-skill.md"
        assert skill_path.exists()

        with open(skill_path) as f:
            content = f.read()
            assert "function test_skill(param1, param2, param3): array" in content
            assert "**param1** (`string`) (required): First parameter" in content
            assert "**param2** (`number`) (optional): Second parameter" in content
            assert "**param3** (`boolean`) (required): Third parameter" in content

    def test_init_skill_overwrites_with_confirmation(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init-skill overwrites existing file with confirmation."""
        skill_path = tmp_path / "existing-skill.md"
        skill_path.write_text("# Existing content")

        user_input = (
            "New description\n"  # description
            "n\n"  # no parameters
            "string\n"  # return type
            "y\n"  # confirm overwrite
        )

        result = runner.invoke(
            main,
            [
                "init-skill",
                "--name",
                "existing-skill",
                "--path",
                str(tmp_path),
            ],
            input=user_input,
        )

        assert result.exit_code == 0
        assert "Created skill file" in result.output

        with open(skill_path) as f:
            content = f.read()
            assert "# existing-skill" in content
            assert "Existing content" not in content

    def test_init_skill_aborts_overwrite(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test init-skill aborts when user declines overwrite."""
        skill_path = tmp_path / "existing-skill.md"
        skill_path.write_text("# Existing content")

        user_input = (
            "New description\n"  # description
            "n\n"  # no parameters
            "string\n"  # return type
            "n\n"  # decline overwrite
        )

        result = runner.invoke(
            main,
            [
                "init-skill",
                "--name",
                "existing-skill",
                "--path",
                str(tmp_path),
            ],
            input=user_input,
        )

        assert result.exit_code == 0
        assert "Aborted" in result.output

        with open(skill_path) as f:
            content = f.read()
            assert "Existing content" in content

    def test_init_skill_no_parameters(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test init-skill with no parameters."""
        user_input = (
            "no-param-skill\n"  # skill name
            "Skill without parameters\n"  # description
            "n\n"  # no parameters
            "void\n"  # return type
        )

        result = runner.invoke(
            main, ["init-skill", "--path", str(tmp_path)], input=user_input
        )

        assert result.exit_code == 0

        skill_path = tmp_path / "no-param-skill.md"
        assert skill_path.exists()

        with open(skill_path) as f:
            content = f.read()
            assert "function no_param_skill(): void" in content
            assert "## Parameters" not in content

    def test_init_skill_default_path(self, runner: CliRunner) -> None:
        """Test init-skill uses current directory by default."""
        user_input = (
            "default-skill\n"  # skill name
            "Default path test\n"  # description
            "n\n"  # no parameters
            "string\n"  # return type
        )

        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init-skill"], input=user_input)

            assert result.exit_code == 0
            assert Path("default-skill.md").exists()
