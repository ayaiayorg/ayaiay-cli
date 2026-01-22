"""Configuration management for AyAiAy CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    """AyAiAy CLI configuration."""

    api_base_url: str = "https://api.ayaiay.org"
    registry_url: str = "ghcr.io/ayaiayorg"
    install_dir: Path = field(default_factory=lambda: Path.home() / ".ayaiay" / "packs")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".ayaiay" / "cache")
    timeout: float = 30.0
    token: str | None = None

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        """Load configuration from file and environment variables.

        Priority (highest to lowest):
        1. Environment variables (AYAIAY_*)
        2. Config file (~/.ayaiay/config.yaml)
        3. Default values
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
                    config_data[config_key] = float(value)
                else:
                    config_data[config_key] = value

        return cls(**config_data)

    def save(self, config_path: Path | None = None) -> None:
        """Save configuration to file."""
        if config_path is None:
            config_path = Path.home() / ".ayaiay" / "config.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)

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
