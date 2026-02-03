"""Tests for platform-specific artifact validation rules."""

from pathlib import Path

from ayaiay.validator import validate_manifest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "pack-artifacts" / "us2-platforms"


def test_claude_platform_allows_commands() -> None:
    """Claude platform should allow commands."""
    manifest_path = FIXTURE_ROOT / "claude" / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert result.is_valid


def test_github_platform_rejects_commands() -> None:
    """GitHub Copilot platform should reject commands."""
    manifest_path = FIXTURE_ROOT / "github" / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert not result.is_valid
    assert any(issue.artifact_type == "command" for issue in result.errors)
