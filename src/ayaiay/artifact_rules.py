"""Artifact folder rules for pack validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformRuleSet:
    """Defines expected artifact folders per platform."""

    platform: str
    root_dir: str
    artifact_folders: Mapping[str, str]
    allowed_artifacts: set[str]


ARTIFACT_FOLDERS: dict[str, str] = {
    "agent": "agents",
    "instruction": "instructions",
    "prompt": "prompts",
    "skill": "skills",
    "command": "commands",
    "tool": "tools",
    "workflow": "workflows",
    "mcp_server": "mcp-servers",
}

PLATFORM_ROOTS: dict[str, str] = {
    "github-copilot": ".github",
    "claude": ".claude",
    "cursor": ".cursor",
    "windsurf": ".windsurf",
    "aider": ".aider",
}

DEFAULT_PLATFORM = "github-copilot"


def supported_platforms() -> set[str]:
    """Return the supported platform identifiers."""

    return set(PLATFORM_ROOTS.keys())


def get_platform_rules(platform: str) -> PlatformRuleSet:
    """Return the rules for a specific platform."""

    normalized = platform.strip().lower()
    root_dir = PLATFORM_ROOTS.get(normalized, PLATFORM_ROOTS[DEFAULT_PLATFORM])

    allowed = set(ARTIFACT_FOLDERS.keys())
    if normalized != "claude":
        allowed.discard("command")

    return PlatformRuleSet(
        platform=normalized,
        root_dir=root_dir,
        artifact_folders=ARTIFACT_FOLDERS,
        allowed_artifacts=allowed,
    )
