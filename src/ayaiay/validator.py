"""Manifest validation for AyAiAy packs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import yaml

# Note: We use Draft7Validator.iter_errors() which returns error objects directly,
# so we don't need to import or catch ValidationError from jsonschema
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from ayaiay.artifact_rules import ARTIFACT_FOLDERS, DEFAULT_PLATFORM, get_platform_rules
from ayaiay.models import Manifest, normalize_artifact_path, normalize_platforms

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
        "platforms": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Target platforms for this pack",
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
                    "type": {"type": "string"},
                    "instructions": {"type": "string"},
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
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "content": {"type": "string", "minLength": 1},
                    "path": {"type": "string"},
                },
                "anyOf": [
                    {"required": ["content"]},
                    {"required": ["path"]},
                ],
            },
            "description": "Instruction definitions",
        },
        "prompts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "template": {"type": "string", "minLength": 1},
                    "path": {"type": "string"},
                    "variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "anyOf": [
                    {"required": ["template"]},
                    {"required": ["path"]},
                ],
            },
            "description": "Prompt template definitions",
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "content": {"type": "string", "minLength": 1},
                    "path": {"type": "string"},
                    "parameters": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "anyOf": [
                    {"required": ["content"]},
                    {"required": ["path"]},
                ],
            },
            "description": "Skill definitions",
        },
        "commands": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "path"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
            "description": "Command definitions",
        },
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "path"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
            "description": "Tool definitions",
        },
        "workflows": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "path"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
            "description": "Workflow definitions",
        },
        "mcp_servers": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "path": {"type": "string"},
                },
            },
            "description": "MCP server definitions",
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


class ValidationIssue(BaseModel):
    """Detailed validation issue for artifact checks."""

    severity: str = Field(..., description="error or warning")
    message: str = Field(..., description="Human-readable issue description")
    artifact_type: str | None = Field(default=None, description="Artifact type")
    name: str | None = Field(default=None, description="Artifact name")
    expected_path: str | None = Field(default=None, description="Expected path")
    actual_path: str | None = Field(default=None, description="Actual path")


class ValidationResult(BaseModel):
    """Result of manifest validation."""

    errors: list[ValidationIssue] = Field(
        default_factory=list, description="Validation errors"
    )
    warnings: list[ValidationIssue] = Field(
        default_factory=list, description="Validation warnings"
    )
    manifest: Manifest | None = Field(
        default=None, description="Parsed manifest if valid"
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_valid(self) -> bool:
        """Check if validation passed without errors."""
        return len(self.errors) == 0

    def add_error(self, message: str, **kwargs: str | None) -> None:
        """Add a validation error.

        Args:
            message: Error message to add.
            kwargs: Optional artifact metadata.
        """
        self.errors.append(ValidationIssue(severity="error", message=message, **kwargs))

    def add_warning(self, message: str, **kwargs: str | None) -> None:
        """Add a validation warning.

        Args:
            message: Warning message to add.
            kwargs: Optional artifact metadata.
        """
        self.warnings.append(
            ValidationIssue(severity="warning", message=message, **kwargs)
        )


def format_issue(issue: ValidationIssue) -> str:
    """Format a validation issue for CLI output."""

    details = []
    if issue.artifact_type:
        details.append(f"type={issue.artifact_type}")
    if issue.name:
        details.append(f"name={issue.name}")
    if issue.expected_path:
        details.append(f"expected={issue.expected_path}")
    if issue.actual_path:
        details.append(f"actual={issue.actual_path}")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"{issue.message}{suffix}"


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
    schema = MANIFEST_SCHEMA
    is_spec_format = _is_spec_format(data)
    if is_spec_format:
        spec_schema = _load_pack_schema()
        if spec_schema:
            schema = spec_schema
        else:
            result.add_warning(
                "Pack spec schema not found; skipping strict schema validation"
            )
            schema = {"type": "object"}

    validator = Draft7Validator(schema)
    for error in validator.iter_errors(data):
        path_str = " -> ".join(str(p) for p in error.absolute_path) or "root"
        result.add_error(f"[{path_str}] {error.message}")

    # If JSON Schema validation failed, don't try Pydantic
    if not result.is_valid:
        return result

    # Pydantic validation for additional type safety (legacy format only)
    if not is_spec_format:
        try:
            result.manifest = Manifest.model_validate(data)
        except PydanticValidationError as e:
            for error in e.errors():
                loc = " -> ".join(str(location) for location in error["loc"])
                result.add_error(f"[{loc}] {error['msg']}")
            return result

    # Additional semantic validations
    spec_data = _extract_spec_section(data)
    platforms = _extract_platforms(data)
    pack_root = path.parent
    rule_sets = _resolve_platform_rules(platforms)

    _validate_semantic_rules(result, spec_data)
    _validate_artifact_structure(
        result=result,
        spec_data=spec_data,
        pack_root=pack_root,
        rule_sets=rule_sets,
    )

    return result


def _validate_semantic_rules(result: ValidationResult, data: dict[str, Any]) -> None:
    """Perform semantic validation rules."""
    # Check for at least one content type
    has_content = any(
        data.get(key) for key in ("agents", "instructions", "prompts", "skills")
    )
    if not has_content:
        result.add_warning(
            "Pack has no agents, instructions, prompts, or skills defined. "
            "Consider adding at least one."
        )

    # Check for duplicate names within categories
    for category in ("agents", "instructions", "prompts", "skills"):
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


def _extract_spec_section(data: dict[str, Any]) -> dict[str, Any]:
    """Return the manifest section that contains artifact lists."""

    spec_section = data.get("spec")
    return spec_section if isinstance(spec_section, dict) else data


def _is_spec_format(data: dict[str, Any]) -> bool:
    """Detect pack-v1 spec format with apiVersion/kind/metadata/spec."""

    return any(key in data for key in ("apiVersion", "kind", "metadata", "spec"))


def _load_pack_schema() -> dict[str, Any] | None:
    """Load pack-v1 JSON schema if available in the repo."""

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packages" / "spec" / "schema" / "pack-v1.json"
        if candidate.exists():
            with open(candidate) as schema_file:
                return json.load(schema_file)
    return None


def _extract_platforms(data: dict[str, Any]) -> list[str]:
    """Extract platform identifiers from manifest data."""

    platforms: list[str] = []
    if isinstance(data.get("platforms"), list):
        platforms.extend(data.get("platforms", []))

    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        if isinstance(metadata.get("platforms"), list):
            platforms.extend(metadata.get("platforms", []))
        elif isinstance(metadata.get("platform"), str):
            platforms.append(metadata.get("platform"))

    spec_section = data.get("spec")
    if isinstance(spec_section, dict) and isinstance(
        spec_section.get("platforms"), list
    ):
        platforms.extend(spec_section.get("platforms", []))

    normalized = normalize_platforms(platforms)
    return normalized


def _resolve_platform_rules(platforms: list[str]) -> list[Any]:
    """Resolve platform rule sets for the provided platform list."""

    if not platforms:
        return [get_platform_rules(DEFAULT_PLATFORM)]
    return [get_platform_rules(platform) for platform in platforms]


def _validate_artifact_structure(
    *,
    result: ValidationResult,
    spec_data: dict[str, Any],
    pack_root: Path,
    rule_sets: list[Any],
) -> None:
    """Validate declared artifact files and folder placement."""

    artifact_sections: dict[str, list[dict[str, Any]]] = {
        "agent": spec_data.get("agents", []) or [],
        "instruction": spec_data.get("instructions", []) or [],
        "prompt": spec_data.get("prompts", []) or [],
        "skill": spec_data.get("skills", []) or [],
        "command": spec_data.get("commands", []) or [],
        "tool": spec_data.get("tools", []) or [],
        "workflow": spec_data.get("workflows", []) or [],
        "mcp_server": spec_data.get("mcp_servers", []) or [],
    }

    allowed_types: set[str] = set()
    for rules in rule_sets:
        allowed_types.update(rules.allowed_artifacts)

    declared_paths: dict[str, set[str]] = {key: set() for key in artifact_sections}
    declared_entries: list[tuple[str, str | None, str | None]] = []

    for artifact_type, items in artifact_sections.items():
        for item in items:
            name = item.get("name")
            raw_path = None
            if artifact_type == "agent":
                raw_path = item.get("instructions") or item.get("path")
            else:
                raw_path = item.get("path")

            if (
                artifact_type == "skill"
                and not raw_path
                and name
                and not item.get("content")
            ):
                raw_path = f"skills/{name}/SKILL.md"

            normalized_path = normalize_artifact_path(raw_path)
            if normalized_path:
                declared_paths[artifact_type].add(normalized_path)
            declared_entries.append((artifact_type, name, normalized_path))

    for rules in rule_sets:
        for artifact_type, items in artifact_sections.items():
            if items and artifact_type not in rules.allowed_artifacts:
                result.add_error(
                    "Artifact type not supported by platform",
                    artifact_type=artifact_type,
                    expected_path=ARTIFACT_FOLDERS.get(artifact_type),
                    actual_path=ARTIFACT_FOLDERS.get(artifact_type),
                )

    for artifact_type, name, normalized_path in declared_entries:
        if not normalized_path:
            continue

        expected_folder = ARTIFACT_FOLDERS.get(artifact_type)
        if expected_folder and not normalized_path.startswith(f"{expected_folder}/"):
            result.add_error(
                "Artifact path is outside expected folder",
                artifact_type=artifact_type,
                name=name,
                expected_path=f"{expected_folder}/",
                actual_path=normalized_path,
            )

        artifact_path = pack_root / normalized_path
        if not artifact_path.exists():
            result.add_error(
                "Declared artifact file is missing",
                artifact_type=artifact_type,
                name=name,
                expected_path=normalized_path,
            )

    for artifact_type, folder_name in ARTIFACT_FOLDERS.items():
        if artifact_type not in allowed_types:
            continue
        folder_path = pack_root / folder_name
        if not folder_path.exists():
            continue

        if artifact_type == "skill":
            files = list(folder_path.rglob("SKILL.md"))
        else:
            files = [path for path in folder_path.rglob("*") if path.is_file()]

        for file_path in files:
            relative_path = normalize_artifact_path(
                str(file_path.relative_to(pack_root))
            )
            if not relative_path:
                continue
            if relative_path not in declared_paths.get(artifact_type, set()):
                result.add_error(
                    "Artifact file not declared in manifest",
                    artifact_type=artifact_type,
                    actual_path=relative_path,
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
        errors = "\n".join(f"  - {format_issue(e)}" for e in result.errors)
        raise ValueError(f"Manifest validation failed:\n{errors}")
    if result.manifest is None:
        raise ValueError("Manifest parsing failed")
    return result.manifest
