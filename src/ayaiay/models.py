"""Data models for AyAiAy CLI."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


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
    content: str | None = Field(None, description="Inline instruction content (flat format)")
    path: str | None = Field(None, description="Path to instruction file (spec-nested format)")


class ManifestPrompt(BaseModel):
    """Prompt definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Prompt name")
    description: str | None = Field(None, description="Prompt description")
    template: str | None = Field(None, description="Inline prompt template (flat format)")
    path: str | None = Field(None, description="Path to prompt template file (spec-nested format)")
    variables: list[str] = Field(default_factory=list, description="Template variables")


class ManifestSkillCategory(BaseModel):
    """Skill category definition in ayaiay.yaml manifest."""

    slug: str = Field(..., description="Category slug (lowercase, hyphens only)")
    label: str = Field(..., description="Full display label")
    short_label: str | None = Field(None, alias="shortLabel", description="Short label for sidebar")
    description: str | None = Field(None, description="Category description")

    model_config = {"populate_by_name": True}


class ManifestSkill(BaseModel):
    """Skill definition in ayaiay.yaml manifest."""

    name: str = Field(..., description="Skill name")
    display_name: str | None = Field(None, description="Human-readable skill name")
    description: str | None = Field(None, description="Skill description")
    content: str | None = Field(None, description="Inline skill content/implementation (flat format)")
    path: str | None = Field(None, description="Path to skill file (spec-nested format)")
    category: str | None = Field(None, description="Category slug (must match a skillCategories entry)")
    parameters: list[str] = Field(default_factory=list, description="Skill parameters")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")


class Manifest(BaseModel):
    """AyAiAy pack manifest (ayaiay.yaml)."""

    version: str = Field("1.0", description="Manifest schema version")
    name: str = Field(..., description="Pack name")
    description: str | None = Field(None, description="Pack description")
    author: str | None = Field(None, description="Pack author")
    license: str | None = Field(None, description="Pack license")
    repository: str | None = Field(None, description="Repository URL")
    tags: list[str] = Field(default_factory=list, description="Pack tags")
    agents: list[ManifestAgent] = Field(
        default_factory=list, description="Agent definitions"
    )
    instructions: list[ManifestInstruction] = Field(
        default_factory=list, description="Instruction definitions"
    )
    prompts: list[ManifestPrompt] = Field(
        default_factory=list, description="Prompt definitions"
    )
    skill_categories: list[ManifestSkillCategory] = Field(
        default_factory=list,
        alias="skillCategories",
        description="Skill category definitions for grouping and navigation",
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

    model_config = {"populate_by_name": True}


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
