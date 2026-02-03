"""Data models for AyAiAy CLI."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class PackType(str, Enum):
    """Type of pack."""

    AGENT = "agent"
    INSTRUCTION = "instruction"
    PROMPT = "prompt"


class PackVersion(BaseModel):
    """A specific version of a pack."""

    version: str = Field(..., description="Semantic version string")
    published_at: datetime | None = Field(None, description="Publication timestamp")
    digest: str | None = Field(None, description="OCI image digest")
    changelog: str | None = Field(None, description="Version changelog")
    downloads: int = Field(0, description="Download count")


class Pack(BaseModel):
    """An AyAiAy pack (agent, instruction, or prompt pack)."""

    id: int | str = Field(..., description="Unique pack identifier")
    name: str = Field(..., description="Pack name")
    publisher: str = Field(..., description="Publisher username or organization")
    description: str | None = Field(None, description="Pack description")
    pack_type: PackType | None = Field(None, description="Type of pack")
    repository_url: HttpUrl | None = Field(None, description="GitHub repository URL")
    latest_version: str | None = Field(None, description="Latest version string")
    tags: list[str] = Field(default_factory=list, description="Pack tags")
    downloads: int = Field(0, description="Total download count")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    @field_validator("publisher", mode="before")
    @classmethod
    def normalize_publisher(cls, value: Any) -> Any:
        """Normalize publisher field from API v1 payloads."""
        if isinstance(value, dict):
            return value.get("name") or value.get("display_name")
        return value

    @property
    def full_name(self) -> str:
        """Return the full pack name in publisher/name format."""
        return f"{self.publisher}/{self.name}"


class SearchResult(BaseModel):
    """Search results from the API."""

    packs: list[Pack] = Field(default_factory=list, description="Matching packs")
    total: int = Field(0, description="Total number of matches")
    page: int = Field(1, description="Current page")
    per_page: int = Field(20, description="Results per page")

    @property
    def has_more(self) -> bool:
        """Check if there are more results available."""
        return self.page * self.per_page < self.total


class ManifestAgent(BaseModel):
    """Agent definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Agent name")
    description: str | None = Field(None, description="Agent description")
    system_prompt: str | None = Field(None, description="System prompt for the agent")
    model: str | None = Field(None, description="Preferred model")
    tools: list[str] = Field(default_factory=list, description="Required tools")


class ManifestInstruction(BaseModel):
    """Instruction definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Instruction name")
    description: str | None = Field(None, description="Instruction description")
    content: str | None = Field(None, description="Instruction content")
    path: str | None = Field(None, description="Instruction file path")

    @model_validator(mode="after")
    def validate_content_or_path(self) -> ManifestInstruction:
        if not self.content and not self.path:
            raise ValueError("Instruction requires content or path")
        return self


class ManifestPrompt(BaseModel):
    """Prompt definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Prompt name")
    description: str | None = Field(None, description="Prompt description")
    template: str | None = Field(None, description="Prompt template")
    path: str | None = Field(None, description="Prompt file path")
    variables: list[str] = Field(default_factory=list, description="Template variables")

    @model_validator(mode="after")
    def validate_template_or_path(self) -> ManifestPrompt:
        if not self.template and not self.path:
            raise ValueError("Prompt requires template or path")
        return self


class ManifestSkill(BaseModel):
    """Skill definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Skill name")
    description: str | None = Field(None, description="Skill description")
    content: str | None = Field(None, description="Skill content/implementation")
    path: str | None = Field(None, description="Skill file path")
    parameters: list[str] = Field(default_factory=list, description="Skill parameters")

    @model_validator(mode="after")
    def validate_content_or_path(self) -> ManifestSkill:
        if not self.content and not self.path:
            raise ValueError("Skill requires content or path")
        return self


class Manifest(BaseModel):
    """AyAiAy pack manifest (ayaiay.yaml)."""

    version: str = Field("1.0", description="Manifest schema version")
    name: str = Field(..., description="Pack name")
    description: str | None = Field(None, description="Pack description")
    author: str | None = Field(None, description="Pack author")
    license: str | None = Field(None, description="Pack license")
    repository: str | None = Field(None, description="Repository URL")
    tags: list[str] = Field(default_factory=list, description="Pack tags")
    platforms: list[str] = Field(
        default_factory=list, description="Target platforms for this pack"
    )
    agents: list[ManifestAgent] = Field(
        default_factory=list, description="Agent definitions"
    )
    instructions: list[ManifestInstruction] = Field(
        default_factory=list, description="Instruction definitions"
    )
    prompts: list[ManifestPrompt] = Field(
        default_factory=list, description="Prompt definitions"
    )
    skills: list[ManifestSkill] = Field(
        default_factory=list, description="Skill definitions"
    )
    dependencies: dict[str, str] = Field(
        default_factory=dict, description="Pack dependencies"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


def normalize_artifact_path(path: str | None) -> str | None:
    """Normalize a manifest artifact path to a relative, POSIX-style path."""

    if path is None:
        return None
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def normalize_platforms(platforms: Iterable[str] | None) -> list[str]:
    """Normalize platform identifiers to lowercase slugs."""

    if not platforms:
        return []
    normalized = []
    for platform in platforms:
        if not platform:
            continue
        slug = platform.strip().lower().replace(" ", "-").replace("_", "-")
        normalized.append(slug)
    return normalized


class LockFilePackage(BaseModel):
    """Package entry in ayaiay.json lock file."""

    name: str = Field(..., description="Package full name (publisher/name)")
    version: str = Field(..., description="Installed version")
    installed_at: datetime | None = Field(None, description="Installation timestamp")
    digest: str | None = Field(None, description="Package digest/hash")
    dependencies: dict[str, str] = Field(
        default_factory=dict, description="Package dependencies"
    )


class LockFile(BaseModel):
    """AyAiAy lock file (ayaiay.json) for tracking installed packages."""

    version: str = Field("1.0", description="Lock file schema version")
    packages: dict[str, LockFilePackage] = Field(
        default_factory=dict, description="Installed packages keyed by full name"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")
