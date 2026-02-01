"""Integration tests for CoinMarketCap MCP server.

These tests run against the real CoinMarketCap API.
Requires COINMARKETCAP_API_KEY or CMC_API_KEY environment variable.
"""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from coinmarketcap_mcp.cmc_api import CoinMarketCapClient, CoinMarketCapAPIError
from coinmarketcap_mcp import server


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    key = os.environ.get("COINMARKETCAP_API_KEY") or os.environ.get("CMC_API_KEY")
    if not key:
        pytest.skip("COINMARKETCAP_API_KEY or CMC_API_KEY not set")
    return key


@pytest_asyncio.fixture
async def client(api_key: str) -> AsyncGenerator[CoinMarketCapClient, None]:
    """Create API client."""
    client = CoinMarketCapClient(api_key)
    yield client
    await client.close()


@pytest.fixture(autouse=True)
def setup_server_client(api_key: str) -> None:
    """Set up server client before each test."""
    os.environ["COINMARKETCAP_API_KEY"] = api_key
    server._client = None  # Reset cached client


class TestCoinMarketCapClient:
    """Tests for the low-level API client."""

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_map_by_symbol(self, client: CoinMarketCapClient) -> None:
        """Test fetching cryptocurrency map by symbol."""
        result = await client.get_cryptocurrency_map(symbol="BTC", limit=1)

        assert "data" in result
        assert len(result["data"]) >= 1

        btc = result["data"][0]
        assert btc["symbol"] == "BTC"
        assert btc["name"] == "Bitcoin"
        assert btc["slug"] == "bitcoin"
        assert btc["id"] == 1

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_map_multiple_symbols(self, client: CoinMarketCapClient) -> None:
        """Test fetching cryptocurrency map with multiple symbols."""
        result = await client.get_cryptocurrency_map(symbol="BTC,ETH", limit=10)

        assert "data" in result
        assert len(result["data"]) >= 2

        symbols = {c["symbol"] for c in result["data"]}
        assert "BTC" in symbols
        assert "ETH" in symbols

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_info_by_id(self, client: CoinMarketCapClient) -> None:
        """Test fetching cryptocurrency info by ID."""
        result = await client.get_cryptocurrency_info(id="1")

        assert "data" in result
        assert "1" in result["data"]

        btc = result["data"]["1"]
        assert btc["symbol"] == "BTC"
        assert btc["name"] == "Bitcoin"
        assert "description" in btc
        assert "urls" in btc

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_info_by_symbol(self, client: CoinMarketCapClient) -> None:
        """Test fetching cryptocurrency info by symbol."""
        result = await client.get_cryptocurrency_info(symbol="ETH")

        assert "data" in result
        assert "ETH" in result["data"]

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_info_by_slug(self, client: CoinMarketCapClient) -> None:
        """Test fetching cryptocurrency info by slug."""
        result = await client.get_cryptocurrency_info(slug="bitcoin")

        assert "data" in result
        # Slug query returns keyed by ID
        assert len(result["data"]) >= 1

    @pytest.mark.asyncio
    async def test_get_cryptocurrency_quotes_latest(self, client: CoinMarketCapClient) -> None:
        """Test fetching latest quotes."""
        result = await client.get_cryptocurrency_quotes_latest(symbol="BTC")

        assert "data" in result
        assert "BTC" in result["data"]

        btc = result["data"]["BTC"][0]  # Symbol query returns a list
        assert "quote" in btc
        assert "USD" in btc["quote"]

        quote = btc["quote"]["USD"]
        assert "price" in quote
        assert quote["price"] > 0
        assert "market_cap" in quote
        assert "volume_24h" in quote

    @pytest.mark.asyncio
    async def test_get_exchange_map(self, client: CoinMarketCapClient) -> None:
        """Test fetching exchange map."""
        result = await client.get_exchange_map(limit=10)

        assert "data" in result
        assert len(result["data"]) >= 1

        exchange = result["data"][0]
        assert "id" in exchange
        assert "name" in exchange
        assert "slug" in exchange

    @pytest.mark.asyncio
    async def test_get_exchange_info(self, client: CoinMarketCapClient) -> None:
        """Test fetching exchange info."""
        result = await client.get_exchange_info(slug="binance")

        assert "data" in result
        assert len(result["data"]) >= 1

    @pytest.mark.asyncio
    async def test_get_global_metrics(self, client: CoinMarketCapClient) -> None:
        """Test fetching global metrics."""
        result = await client.get_global_metrics_quotes_latest()

        assert "data" in result
        data = result["data"]
        assert "total_cryptocurrencies" in data
        assert "btc_dominance" in data
        assert "quote" in data

    @pytest.mark.asyncio
    async def test_get_key_info(self, client: CoinMarketCapClient) -> None:
        """Test fetching API key info."""
        result = await client.get_key_info()

        assert "data" in result
        data = result["data"]
        assert "plan" in data
        assert "usage" in data

    @pytest.mark.asyncio
    async def test_invalid_symbol_returns_error(self, client: CoinMarketCapClient) -> None:
        """Test that invalid symbol returns API error."""
        with pytest.raises(CoinMarketCapAPIError) as exc_info:
            await client.get_cryptocurrency_info(symbol="ZZZZNOTEXIST999")

        assert exc_info.value.status_code in (400, 404)


class TestMCPTools:
    """Tests for the MCP tool functions.

    FastMCP wraps functions with @mcp.tool decorator.
    Access underlying function via .fn attribute.
    """

    @pytest.mark.asyncio
    async def test_search_cryptocurrency_by_symbol(self, api_key: str) -> None:
        """Test progressive search by symbol."""
        result = await server.search_cryptocurrency.fn(symbol="BTC")

        assert result["found"] is True
        assert result["match_count"] >= 1
        assert result["best_match"] is not None
        assert result["best_match"]["symbol"] == "BTC"
        assert result["best_match"]["_confidence"] == "high"
        assert result["best_match"]["_match_method"] == "exact_symbol"

    @pytest.mark.asyncio
    async def test_search_cryptocurrency_by_name(self, api_key: str) -> None:
        """Test progressive search by name."""
        result = await server.search_cryptocurrency.fn(name="Bitcoin")

        assert result["found"] is True
        assert result["best_match"] is not None
        assert result["best_match"]["name"] == "Bitcoin"

    @pytest.mark.asyncio
    async def test_search_cryptocurrency_with_homepage_verification(self, api_key: str) -> None:
        """Test search with homepage verification."""
        result = await server.search_cryptocurrency.fn(
            symbol="ETH",
            homepage="https://ethereum.org"
        )

        assert result["found"] is True
        assert result["best_match"] is not None
        assert result["best_match"]["symbol"] == "ETH"
        # Should be verified or at least high confidence
        assert result["best_match"]["_confidence"] in ("verified", "high")

    @pytest.mark.asyncio
    async def test_search_cryptocurrency_known_rebrand(self, api_key: str) -> None:
        """Test that symbol variations work for known rebrands (RNDR -> RENDER)."""
        result = await server.search_cryptocurrency.fn(symbol="RNDR")

        assert result["found"] is True
        assert result["best_match"] is not None
        # Should find either RNDR directly or RENDER as variation
        assert result["best_match"]["symbol"] in ("RNDR", "RENDER")

    @pytest.mark.asyncio
    async def test_search_cryptocurrency_not_found(self, api_key: str) -> None:
        """Test search for non-existent cryptocurrency."""
        result = await server.search_cryptocurrency.fn(symbol="ZZZZNOTEXIST999")

        assert result["found"] is False
        assert result["match_count"] == 0
        assert result["best_match"] is None

    @pytest.mark.asyncio
    async def test_cryptocurrency_map_tool(self, api_key: str) -> None:
        """Test cryptocurrency_map MCP tool."""
        result = await server.cryptocurrency_map.fn(symbol="BTC,ETH")

        assert "cryptocurrencies" in result
        assert result["count"] >= 2

        symbols = {c["symbol"] for c in result["cryptocurrencies"]}
        assert "BTC" in symbols
        assert "ETH" in symbols

    @pytest.mark.asyncio
    async def test_cryptocurrency_info_tool(self, api_key: str) -> None:
        """Test cryptocurrency_info MCP tool."""
        result = await server.cryptocurrency_info.fn(id="1")

        assert "cryptocurrencies" in result
        assert result["count"] == 1

        btc = result["cryptocurrencies"][0]
        assert btc["symbol"] == "BTC"
        assert btc["name"] == "Bitcoin"
        assert "description" in btc
        assert "urls" in btc

    @pytest.mark.asyncio
    async def test_cryptocurrency_quotes_tool(self, api_key: str) -> None:
        """Test cryptocurrency_quotes_latest MCP tool."""
        result = await server.cryptocurrency_quotes_latest.fn(symbol="BTC")

        assert "quotes" in result
        assert result["count"] >= 1

        btc = result["quotes"][0]
        assert btc["symbol"] == "BTC"
        assert "quote" in btc
        assert btc["quote"]["price"] > 0

    @pytest.mark.asyncio
    async def test_exchange_map_tool(self, api_key: str) -> None:
        """Test exchange_map MCP tool."""
        result = await server.exchange_map.fn(limit=10)

        assert "exchanges" in result
        assert result["count"] >= 1

    @pytest.mark.asyncio
    async def test_exchange_info_tool(self, api_key: str) -> None:
        """Test exchange_info MCP tool."""
        result = await server.exchange_info.fn(slug="binance")

        assert "exchanges" in result
        assert result["count"] >= 1

        binance = result["exchanges"][0]
        assert binance["slug"] == "binance"
        assert "name" in binance

    @pytest.mark.asyncio
    async def test_global_metrics_tool(self, api_key: str) -> None:
        """Test global_metrics_quotes_latest MCP tool."""
        result = await server.global_metrics_quotes_latest.fn()

        assert "total_cryptocurrencies" in result
        assert "btc_dominance" in result
        assert "quote" in result
        assert result["quote"]["total_market_cap"] > 0

    @pytest.mark.asyncio
    async def test_key_info_tool(self, api_key: str) -> None:
        """Test key_info MCP tool."""
        result = await server.key_info.fn()

        assert "plan" in result
        assert "usage" in result
        assert "credit_limit_daily" in result["plan"]


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_symbol_variations(self) -> None:
        """Test symbol variation generation."""
        variations = server._generate_symbol_variations("RNDR")
        assert "RENDER" in variations

        variations = server._generate_symbol_variations("MATIC")
        assert "POL" in variations

    def test_name_to_slug(self) -> None:
        """Test name to slug conversion."""
        assert server._name_to_slug("Bitcoin") == "bitcoin"
        assert server._name_to_slug("Render Token") == "render-token"
        assert server._name_to_slug("The Graph") == "the-graph"

    def test_normalize_url(self) -> None:
        """Test URL normalization."""
        assert server._normalize_url("https://ethereum.org/") == "ethereum.org"
        assert server._normalize_url("http://www.ethereum.org") == "ethereum.org"
        assert server._normalize_url("HTTPS://Ethereum.org") == "ethereum.org"

    def test_extract_domain(self) -> None:
        """Test domain extraction."""
        assert server._extract_domain("https://ethereum.org/en/") == "ethereum.org"
        assert server._extract_domain("https://www.binance.com:443/trade") == "binance.com"
