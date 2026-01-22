"""Configuration management for AyAiAy CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """AyAiAy CLI configuration with validation."""

    api_base_url: str = Field(
        default="https://api.ayaiay.org",
        description="API base URL",
    )
    registry_url: str = Field(
        default="ghcr.io/ayaiayorg",
        description="OCI registry URL",
    )
    install_dir: Path = Field(
        default_factory=lambda: Path.home() / ".ayaiay" / "packs",
        description="Pack installation directory",
    )
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".ayaiay" / "cache",
        description="Cache directory",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        le=300,
        description="Request timeout in seconds",
    )
    token: str | None = Field(
        default=None,
        description="Authentication token",
    )

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("api_base_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("API URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("install_dir", "cache_dir")
    @classmethod
    def expand_paths(cls, v: Path) -> Path:
        """Expand user paths."""
        return v.expanduser().resolve()

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        """Load configuration from file and environment variables.

        Priority (highest to lowest):
        1. Environment variables (AYAIAY_*)
        2. Config file (~/.ayaiay/config.yaml)
        3. Default values

        Args:
            config_path: Optional path to config file.

        Returns:
            Validated Config instance.

        Raises:
            ValueError: If configuration is invalid.
        """
        config_data: dict[str, Any] = {}

        # Load from config file
        if config_path is None:
            config_path = Path.home() / ".ayaiay" / "config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)

        # Override with environment variables
        env_mappings = {
            "AYAIAY_API_URL": "api_base_url",
            "AYAIAY_REGISTRY_URL": "registry_url",
            "AYAIAY_INSTALL_DIR": "install_dir",
            "AYAIAY_CACHE_DIR": "cache_dir",
            "AYAIAY_TIMEOUT": "timeout",
            "AYAIAY_TOKEN": "token",
        }

        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                if config_key in ("install_dir", "cache_dir"):
                    config_data[config_key] = Path(value)
                elif config_key == "timeout":
                    try:
                        config_data[config_key] = float(value)
                    except ValueError as e:
                        raise ValueError(
                            f"Invalid timeout value in {env_var}: {value}"
                        ) from e
                else:
                    config_data[config_key] = value

        return cls(**config_data)

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to file.

        Args:
            config_path: Optional path to save config to.
        """
        if config_path is None:
            config_path = Path.home() / ".ayaiay" / "config.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Use model_dump to get serializable data
        data = {
            "api_base_url": self.api_base_url,
            "registry_url": self.registry_url,
            "install_dir": str(self.install_dir),
            "cache_dir": str(self.cache_dir),
            "timeout": self.timeout,
        }

        if self.token:
            data["token"] = self.token

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
