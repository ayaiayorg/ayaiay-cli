"""Tests for manifest validation."""

from pathlib import Path

import pytest
import yaml

from ayaiay.models import Manifest
from ayaiay.validator import ValidationResult, load_manifest, validate_manifest


class TestValidateManifest:
    """Tests for validate_manifest function."""

    def test_valid_minimal_manifest(self, tmp_path: Path) -> None:
        """Test validation of a minimal valid manifest."""
        manifest_data = {
            "name": "test-pack",
            "agents": [{"name": "test-agent", "description": "A test agent"}],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert result.is_valid
        assert result.manifest is not None
        assert result.manifest.name == "test-pack"
        assert len(result.errors) == 0

    def test_valid_full_manifest(self, tmp_path: Path) -> None:
        """Test validation of a complete manifest."""
        manifest_data = {
            "version": "1.0",
            "name": "my-pack",
            "description": "A comprehensive test pack",
            "author": "Test Author",
            "license": "MIT",
            "repository": "https://github.com/test/my-pack",
            "tags": ["test", "example"],
            "agents": [
                {
                    "name": "code-reviewer",
                    "description": "Reviews code for quality",
                    "system_prompt": "You are a code reviewer.",
                    "model": "gpt-4",
                    "tools": ["read_file", "write_file"],
                }
            ],
            "instructions": [
                {
                    "name": "coding-standards",
                    "description": "Coding standards to follow",
                    "content": "Follow PEP 8 for Python code.",
                }
            ],
            "prompts": [
                {
                    "name": "review-prompt",
                    "description": "Prompt for code review",
                    "template": "Review this {language} code: {code}",
                    "variables": ["language", "code"],
                }
            ],
            "skills": [
                {
                    "name": "code-analyzer",
                    "description": "Analyzes code for patterns",
                    "content": "Analyze code structure and patterns.",
                    "parameters": ["file_path", "language"],
                }
            ],
            "dependencies": {
                "base-pack": "^1.0.0",
            },
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert result.is_valid
        assert result.manifest is not None
        assert result.manifest.name == "my-pack"
        assert len(result.manifest.agents) == 1
        assert len(result.manifest.instructions) == 1
        assert len(result.manifest.prompts) == 1
        assert len(result.manifest.skills) == 1

    def test_missing_required_name(self, tmp_path: Path) -> None:
        """Test validation fails when name is missing."""
        manifest_data = {
            "description": "A pack without a name",
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("name" in error.lower() for error in result.errors)

    def test_invalid_name_format(self, tmp_path: Path) -> None:
        """Test validation fails for invalid pack name."""
        manifest_data = {
            "name": "Invalid Pack Name!",  # Contains spaces and special chars
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test validation fails for non-existent file."""
        result = validate_manifest(tmp_path / "nonexistent.yaml")

        assert not result.is_valid
        assert any("not found" in error.lower() for error in result.errors)

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Test validation fails for invalid YAML."""
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            f.write("name: test\n  invalid: yaml: syntax")

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("yaml" in error.lower() for error in result.errors)

    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Test validation fails for empty manifest."""
        manifest_path = tmp_path / "ayaiay.yaml"
        manifest_path.touch()

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("empty" in error.lower() for error in result.errors)

    def test_warning_for_empty_content(self, tmp_path: Path) -> None:
        """Test warning is issued when no agents/instructions/prompts defined."""
        manifest_data = {
            "name": "empty-pack",
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert result.is_valid  # Still valid, just a warning
        assert len(result.warnings) > 0

    def test_duplicate_agent_names(self, tmp_path: Path) -> None:
        """Test validation fails for duplicate agent names."""
        manifest_data = {
            "name": "dup-pack",
            "agents": [
                {"name": "agent-one"},
                {"name": "agent-one"},  # Duplicate
            ],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("duplicate" in error.lower() for error in result.errors)

    def test_invalid_dependency_version(self, tmp_path: Path) -> None:
        """Test validation fails for invalid dependency version constraint."""
        manifest_data = {
            "name": "dep-pack",
            "dependencies": {
                "other-pack": "invalid-version",
            },
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("version constraint" in error.lower() for error in result.errors)

    def test_valid_skill_definition(self, tmp_path: Path) -> None:
        """Test validation succeeds for valid skill definition."""
        manifest_data = {
            "name": "skill-pack",
            "skills": [
                {
                    "name": "file-reader",
                    "description": "Reads files from the filesystem",
                    "content": "Read and return file contents.",
                    "parameters": ["file_path", "encoding"],
                }
            ],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert result.is_valid
        assert result.manifest is not None
        assert len(result.manifest.skills) == 1
        assert result.manifest.skills[0].name == "file-reader"
        assert result.manifest.skills[0].parameters == ["file_path", "encoding"]

    def test_skill_missing_required_field(self, tmp_path: Path) -> None:
        """Test validation fails when skill is missing required content field."""
        manifest_data = {
            "name": "bad-skill-pack",
            "skills": [
                {
                    "name": "incomplete-skill",
                    "description": "Missing content field",
                }
            ],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("content" in error.lower() for error in result.errors)

    def test_duplicate_skill_names(self, tmp_path: Path) -> None:
        """Test validation fails for duplicate skill names."""
        manifest_data = {
            "name": "dup-skill-pack",
            "skills": [
                {"name": "skill-one", "content": "First skill"},
                {"name": "skill-one", "content": "Duplicate skill"},
            ],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        result = validate_manifest(manifest_path)

        assert not result.is_valid
        assert any("duplicate" in error.lower() for error in result.errors)


class TestLoadManifest:
    """Tests for load_manifest function."""

    def test_load_valid_manifest(self, tmp_path: Path) -> None:
        """Test loading a valid manifest returns Manifest object."""
        manifest_data = {
            "name": "test-pack",
            "agents": [{"name": "test-agent"}],
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        manifest = load_manifest(manifest_path)

        assert isinstance(manifest, Manifest)
        assert manifest.name == "test-pack"

    def test_load_invalid_manifest_raises(self, tmp_path: Path) -> None:
        """Test loading an invalid manifest raises ValueError."""
        manifest_data = {
            "description": "Missing name",
        }
        manifest_path = tmp_path / "ayaiay.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest_data, f)

        with pytest.raises(ValueError, match="validation failed"):
            load_manifest(manifest_path)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_is_valid_with_no_errors(self) -> None:
        """Test is_valid returns True when no errors."""
        result = ValidationResult()
        assert result.is_valid

    def test_is_valid_with_errors(self) -> None:
        """Test is_valid returns False when errors exist."""
        result = ValidationResult()
        result.add_error("Test error")
        assert not result.is_valid

    def test_is_valid_with_warnings_only(self) -> None:
        """Test is_valid returns True with only warnings."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert result.is_valid
