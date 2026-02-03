"""Tests for demo pack validation."""

from pathlib import Path

from ayaiay.validator import validate_manifest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "pack-artifacts" / "us3-demo"


def test_demo_pack_fixture_validates() -> None:
    """Demo pack fixture should validate without errors."""
    manifest_path = FIXTURE_ROOT / "ayaiay.yaml"

    result = validate_manifest(manifest_path)

    assert result.is_valid
    assert len(result.errors) == 0
