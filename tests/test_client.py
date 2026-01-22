"""Tests for the AyAiAy API client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ayaiay.client import (
    APIError,
    AuthenticationError,
    AyAiAyClient,
    NotFoundError,
)
from ayaiay.config import Config
from ayaiay.models import Pack, PackType, PackVersion, SearchResult


@pytest.fixture
def config() -> Config:
    """Create a test configuration."""
    return Config(
        api_base_url="https://api.test.ayaiay.org",
        timeout=10.0,
    )


@pytest.fixture
def client(config: Config) -> AyAiAyClient:
    """Create a test client."""
    return AyAiAyClient(config=config)


class TestAyAiAyClient:
    """Tests for AyAiAyClient class."""

    def test_client_initialization(self, config: Config) -> None:
        """Test client initializes with config."""
        client = AyAiAyClient(config=config)
        assert client.config == config
        assert client._client is None

    def test_client_context_manager(self, config: Config) -> None:
        """Test client works as context manager."""
        with AyAiAyClient(config=config) as client:
            assert client is not None
        # Client should be closed after context

    def test_health_check_success(self, client: AyAiAyClient) -> None:
        """Test health check returns True when API is healthy."""
        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            assert client.health_check() is True
            mock_client.get.assert_called_with("/api/health")

    def test_health_check_failure(self, client: AyAiAyClient) -> None:
        """Test health check returns False when API is down."""
        with patch.object(client, "client") as mock_client:
            mock_client.get.side_effect = httpx.RequestError("Connection failed")

            assert client.health_check() is False

    def test_search_packs(self, client: AyAiAyClient) -> None:
        """Test searching for packs."""
        mock_response_data = {
            "items": [
                {
                    "id": "pack-1",
                    "name": "test-pack",
                    "publisher": "test-user",
                    "pack_type": "agent",
                    "downloads": 100,
                }
            ],
            "total": 1,
        }

        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.get.return_value = mock_response

            result = client.search_packs(query="test")

            assert isinstance(result, SearchResult)
            assert len(result.packs) == 1
            assert result.packs[0].name == "test-pack"
            assert result.total == 1

    def test_search_packs_with_filters(self, client: AyAiAyClient) -> None:
        """Test searching with filters."""
        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"items": [], "total": 0}
            mock_client.get.return_value = mock_response

            client.search_packs(
                query="code",
                pack_type="agent",
                tags=["python", "review"],
                page=2,
                per_page=10,
            )

            call_args = mock_client.get.call_args
            params = call_args.kwargs.get("params", call_args[1].get("params", {}))
            assert params["q"] == "code"
            assert params["type"] == "agent"
            assert params["tags"] == "python,review"
            assert params["page"] == 2
            assert params["per_page"] == 10

    def test_get_pack(self, client: AyAiAyClient) -> None:
        """Test getting a specific pack."""
        mock_response_data = {
            "id": "pack-1",
            "name": "test-pack",
            "publisher": "test-user",
            "pack_type": "agent",
            "description": "A test pack",
            "downloads": 50,
        }

        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.get.return_value = mock_response

            pack = client.get_pack("test-user/test-pack")

            assert isinstance(pack, Pack)
            assert pack.name == "test-pack"
            assert pack.publisher == "test-user"
            mock_client.get.assert_called_with("/api/packs/test-user/test-pack")

    def test_get_pack_not_found(self, client: AyAiAyClient) -> None:
        """Test getting a non-existent pack raises NotFoundError."""
        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            with pytest.raises(NotFoundError):
                client.get_pack("nonexistent/pack")

    def test_get_pack_versions(self, client: AyAiAyClient) -> None:
        """Test getting pack versions."""
        mock_response_data = {
            "versions": [
                {"version": "1.0.0", "downloads": 100},
                {"version": "0.9.0", "downloads": 50},
            ]
        }

        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            mock_client.get.return_value = mock_response

            versions = client.get_pack_versions("test-user/test-pack")

            assert len(versions) == 2
            assert versions[0].version == "1.0.0"
            assert versions[1].version == "0.9.0"

    def test_authentication_error(self, client: AyAiAyClient) -> None:
        """Test authentication error is raised for 401."""
        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            with pytest.raises(AuthenticationError):
                client.get_pack("test/pack")

    def test_api_error(self, client: AyAiAyClient) -> None:
        """Test API error is raised for other error codes."""
        with patch.object(client, "client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.json.side_effect = Exception("Not JSON")
            mock_client.get.return_value = mock_response

            with pytest.raises(APIError) as exc_info:
                client.get_pack("test/pack")

            assert exc_info.value.status_code == 500


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_has_more_true(self) -> None:
        """Test has_more returns True when more results exist."""
        result = SearchResult(packs=[], total=100, page=1, per_page=20)
        assert result.has_more is True

    def test_has_more_false(self) -> None:
        """Test has_more returns False when on last page."""
        result = SearchResult(packs=[], total=15, page=1, per_page=20)
        assert result.has_more is False

    def test_has_more_exact(self) -> None:
        """Test has_more when exactly on boundary."""
        result = SearchResult(packs=[], total=20, page=1, per_page=20)
        assert result.has_more is False
