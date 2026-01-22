"""Manifest validation for AyAiAy packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import yaml
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from ayaiay.models import Manifest

# Constants
DEFAULT_MANIFEST_VERSION: Final[str] = "1.0"
MAX_NAME_LENGTH: Final[int] = 64
MAX_DESCRIPTION_LENGTH: Final[int] = 500
MAX_TAGS: Final[int] = 10

# JSON Schema for ayaiay.yaml manifest files
MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AyAiAy Manifest",
    "description": "Schema for ayaiay.yaml manifest files",
    "type": "object",
    "required": ["name"],
    "properties": {
        "version": {
            "type": "string",
            "description": "Manifest schema version",
            "default": DEFAULT_MANIFEST_VERSION,
        },
        "name": {
            "type": "string",
            "description": "Pack name",
            "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$",
            "minLength": 1,
            "maxLength": MAX_NAME_LENGTH,
        },
        "description": {
            "type": "string",
            "description": "Pack description",
            "maxLength": MAX_DESCRIPTION_LENGTH,
        },
        "author": {
            "type": "string",
            "description": "Pack author",
        },
        "license": {
            "type": "string",
            "description": "SPDX license identifier",
        },
        "repository": {
            "type": "string",
            "format": "uri",
            "description": "Repository URL",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-z0-9-]+$"},
            "maxItems": MAX_TAGS,
            "description": "Pack tags for discovery",
        },
        "agents": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "system_prompt": {"type": "string"},
                    "model": {"type": "string"},
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "description": "Agent definitions",
        },
        "instructions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "content"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "content": {"type": "string", "minLength": 1},
                },
            },
            "description": "Instruction definitions",
        },
        "prompts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "template"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "template": {"type": "string", "minLength": 1},
                    "variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "description": "Prompt template definitions",
        },
        "dependencies": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "Pack dependencies (pack_name: version_constraint)",
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata",
        },
    },
    "additionalProperties": False,
}


class ValidationResult(BaseModel):
    """Result of manifest validation."""

    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    manifest: Manifest | None = Field(default=None, description="Parsed manifest if valid")

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_valid(self) -> bool:
        """Check if validation passed without errors."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add a validation error.

        Args:
            message: Error message to add.
        """
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a validation warning.

        Args:
            message: Warning message to add.
        """
        self.warnings.append(message)


def validate_manifest(path: Path | str) -> ValidationResult:
    """Validate an ayaiay.yaml manifest file.

    Args:
        path: Path to the manifest file.

    Returns:
        ValidationResult containing errors, warnings, and parsed manifest.
    """
    result = ValidationResult()
    path = Path(path)

    # Check file exists
    if not path.exists():
        result.add_error(f"Manifest file not found: {path}")
        return result

    # Check file extension
    if path.suffix not in (".yaml", ".yml"):
        result.add_warning(f"Expected .yaml or .yml extension, got: {path.suffix}")

    # Load YAML
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        result.add_error(f"Invalid YAML syntax: {e}")
        return result

    if data is None:
        result.add_error("Manifest file is empty")
        return result

    if not isinstance(data, dict):
        result.add_error("Manifest must be a YAML mapping (dictionary)")
        return result

    # JSON Schema validation
    validator = Draft7Validator(MANIFEST_SCHEMA)
    for error in validator.iter_errors(data):
        path_str = " -> ".join(str(p) for p in error.absolute_path) or "root"
        result.add_error(f"[{path_str}] {error.message}")

    # If JSON Schema validation failed, don't try Pydantic
    if not result.is_valid:
        return result

    # Pydantic validation for additional type safety
    try:
        result.manifest = Manifest.model_validate(data)
    except PydanticValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(location) for location in error["loc"])
            result.add_error(f"[{loc}] {error['msg']}")
        return result

    # Additional semantic validations
    _validate_semantic_rules(result, data)

    return result


def _validate_semantic_rules(result: ValidationResult, data: dict[str, Any]) -> None:
    """Perform semantic validation rules."""
    # Check for at least one content type
    has_content = any(
        data.get(key) for key in ("agents", "instructions", "prompts")
    )
    if not has_content:
        result.add_warning(
            "Pack has no agents, instructions, or prompts defined. "
            "Consider adding at least one."
        )

    # Check for duplicate names within categories
    for category in ("agents", "instructions", "prompts"):
        items = data.get(category, [])
        names = [item.get("name") for item in items if item.get("name")]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        for dup in duplicates:
            result.add_error(f"Duplicate {category[:-1]} name: {dup}")

    # Validate dependency version constraints
    dependencies = data.get("dependencies", {})
    for pack_name, version_constraint in dependencies.items():
        if not _is_valid_version_constraint(version_constraint):
            result.add_error(
                f"Invalid version constraint for dependency '{pack_name}': "
                f"{version_constraint}"
            )


def _is_valid_version_constraint(constraint: str) -> bool:
    """Check if a version constraint is valid.

    Supports:
    - Exact: "1.0.0"
    - Range: ">=1.0.0", "<=2.0.0", ">1.0.0", "<2.0.0"
    - Caret: "^1.0.0" (compatible with 1.x.x)
    - Tilde: "~1.0.0" (compatible with 1.0.x)
    - Wildcard: "*", "1.*", "1.0.*"
    """
    import re

    patterns = [
        r"^\d+\.\d+\.\d+$",  # Exact version
        r"^[<>=]+\d+\.\d+\.\d+$",  # Comparison
        r"^[\^~]\d+\.\d+\.\d+$",  # Caret/Tilde
        r"^\*$",  # Wildcard all
        r"^\d+\.\*$",  # Major wildcard
        r"^\d+\.\d+\.\*$",  # Minor wildcard
        r"^latest$",  # Latest
    ]

    return any(re.match(pattern, constraint) for pattern in patterns)


def load_manifest(path: Path | str) -> Manifest:
    """Load and validate a manifest file, raising on errors.

    Args:
        path: Path to the manifest file.

    Returns:
        Parsed Manifest object.

    Raises:
        ValueError: If validation fails.
        FileNotFoundError: If file doesn't exist.
    """
    result = validate_manifest(path)
    if not result.is_valid:
        errors = "\n".join(f"  - {e}" for e in result.errors)
        raise ValueError(f"Manifest validation failed:\n{errors}")
    if result.manifest is None:
        raise ValueError("Manifest parsing failed")
    return result.manifest
