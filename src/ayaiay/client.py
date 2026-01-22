"""HTTP client for the AyAiAy API."""

from __future__ import annotations

from typing import Any

import httpx

from ayaiay.config import Config
from ayaiay.models import Pack, PackVersion, SearchResult


class AyAiAyError(Exception):
    """Base exception for AyAiAy client errors."""

    pass


class APIError(AyAiAyError):
    """API request error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(AyAiAyError):
    """Resource not found error."""

    pass


class AuthenticationError(AyAiAyError):
    """Authentication error."""

    pass


class AyAiAyClient:
    """Client for interacting with the AyAiAy API."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize the client.

        Args:
            config: Configuration object. If None, loads from default locations.
        """
        self.config = config or Config.load()
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {
                "User-Agent": "ayaiay-cli/0.1.0",
                "Accept": "application/json",
            }
            if self.config.token:
                headers["Authorization"] = f"Bearer {self.config.token}"

            self._client = httpx.Client(
                base_url=self.config.api_base_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> AyAiAyClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        if response.status_code == 404:
            raise NotFoundError("Resource not found")
        if response.status_code == 401:
            raise AuthenticationError("Authentication required or invalid token")
        if response.status_code == 403:
            raise AuthenticationError("Access denied")
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", response.text)
            except Exception:
                message = response.text
            raise APIError(message, status_code=response.status_code)

        return response.json()

    def health_check(self) -> bool:
        """Check if the API is healthy.

        Returns:
            True if the API is healthy, False otherwise.
        """
        try:
            response = self.client.get("/api/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def search_packs(
        self,
        query: str | None = None,
        pack_type: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """Search for packs in the marketplace.

        Args:
            query: Search query string.
            pack_type: Filter by pack type (agent, instruction, prompt).
            tags: Filter by tags.
            page: Page number (1-indexed).
            per_page: Results per page.

        Returns:
            SearchResult containing matching packs.
        """
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }
        if query:
            params["q"] = query
        if pack_type:
            params["type"] = pack_type
        if tags:
            params["tags"] = ",".join(tags)

        response = self.client.get("/api/packs", params=params)
        data = self._handle_response(response)

        packs = [Pack.model_validate(p) for p in data.get("items", [])]
        return SearchResult(
            packs=packs,
            total=data.get("total", len(packs)),
            page=page,
            per_page=per_page,
        )

    def get_pack(self, pack_id: str) -> Pack:
        """Get details for a specific pack.

        Args:
            pack_id: Pack identifier (can be id or publisher/name).

        Returns:
            Pack details.

        Raises:
            NotFoundError: If the pack doesn't exist.
        """
        response = self.client.get(f"/api/packs/{pack_id}")
        data = self._handle_response(response)
        return Pack.model_validate(data)

    def get_pack_versions(self, pack_id: str) -> list[PackVersion]:
        """Get all versions for a pack.

        Args:
            pack_id: Pack identifier.

        Returns:
            List of pack versions.

        Raises:
            NotFoundError: If the pack doesn't exist.
        """
        response = self.client.get(f"/api/packs/{pack_id}/versions")
        data = self._handle_response(response)
        return [PackVersion.model_validate(v) for v in data.get("versions", [])]

    def get_pack_version(self, pack_id: str, version: str) -> PackVersion:
        """Get a specific version of a pack.

        Args:
            pack_id: Pack identifier.
            version: Version string or 'latest'.

        Returns:
            Pack version details.

        Raises:
            NotFoundError: If the pack or version doesn't exist.
        """
        response = self.client.get(f"/api/packs/{pack_id}/versions/{version}")
        data = self._handle_response(response)
        return PackVersion.model_validate(data)
