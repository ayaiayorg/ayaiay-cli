"""Tests for pack artifact placement validation."""

from pathlib import Path

from ayaiay.validator import validate_manifest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "pack-artifacts"


def test_valid_artifact_pack() -> None:
    """Valid fixture should pass without errors."""
    manifest_path = FIXTURE_ROOT / "us1-valid" / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert result.is_valid
    assert len(result.errors) == 0


def test_missing_artifact_file() -> None:
    """Missing artifact file should raise a validation error."""
    manifest_path = FIXTURE_ROOT / "us1-missing" / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert not result.is_valid
    assert any(
        issue.artifact_type == "agent" and issue.name == "missing-agent"
        for issue in result.errors
    )


def test_extra_artifact_file() -> None:
    """Extra files in artifact folders should raise a validation error."""
    manifest_path = FIXTURE_ROOT / "us1-extra" / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert not result.is_valid
    assert any(
        issue.actual_path and "agents/extra.md" in issue.actual_path
        for issue in result.errors
    )
