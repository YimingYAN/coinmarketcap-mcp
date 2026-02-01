"""Unit tests for CoinMarketCap MCP server.

These tests mock API responses and don't require a real API key.
"""

import os

import httpx
import pytest
import respx

from coinmarketcap_mcp.cmc_api import CoinMarketCapClient, CoinMarketCapAPIError
from coinmarketcap_mcp import server


# Sample API responses
SAMPLE_MAP_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": [
        {
            "id": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "slug": "bitcoin",
            "rank": 1,
            "is_active": 1,
            "first_historical_data": "2013-04-28T00:00:00.000Z",
            "platform": None,
        },
        {
            "id": 1027,
            "name": "Ethereum",
            "symbol": "ETH",
            "slug": "ethereum",
            "rank": 2,
            "is_active": 1,
            "first_historical_data": "2015-08-07T00:00:00.000Z",
            "platform": None,
        },
    ],
}

SAMPLE_INFO_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": {
        "1": {
            "id": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "slug": "bitcoin",
            "category": "coin",
            "description": "Bitcoin is a cryptocurrency...",
            "logo": "https://s2.coinmarketcap.com/static/img/coins/64x64/1.png",
            "urls": {
                "website": ["https://bitcoin.org"],
                "twitter": [],
                "reddit": ["https://reddit.com/r/bitcoin"],
            },
            "tags": ["mineable", "pow"],
            "platform": None,
            "date_added": "2013-04-28T00:00:00.000Z",
            "date_launched": "2009-01-03T00:00:00.000Z",
            "infinite_supply": False,
        }
    },
}

SAMPLE_QUOTES_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": {
        "BTC": [
            {
                "id": 1,
                "name": "Bitcoin",
                "symbol": "BTC",
                "slug": "bitcoin",
                "cmc_rank": 1,
                "circulating_supply": 19500000,
                "total_supply": 21000000,
                "max_supply": 21000000,
                "is_active": 1,
                "last_updated": "2024-01-15T00:00:00.000Z",
                "quote": {
                    "USD": {
                        "price": 42000.50,
                        "volume_24h": 25000000000,
                        "volume_change_24h": 5.5,
                        "percent_change_1h": 0.5,
                        "percent_change_24h": 2.1,
                        "percent_change_7d": -1.3,
                        "percent_change_30d": 10.5,
                        "market_cap": 820000000000,
                        "market_cap_dominance": 52.5,
                        "fully_diluted_market_cap": 882000000000,
                        "last_updated": "2024-01-15T00:00:00.000Z",
                    }
                },
            }
        ]
    },
}

SAMPLE_EXCHANGE_MAP_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": [
        {
            "id": 270,
            "name": "Binance",
            "slug": "binance",
            "is_active": 1,
            "first_historical_data": "2017-07-14T00:00:00.000Z",
        }
    ],
}

SAMPLE_EXCHANGE_INFO_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": {
        "270": {
            "id": 270,
            "name": "Binance",
            "slug": "binance",
            "description": "Binance is a cryptocurrency exchange...",
            "logo": "https://s2.coinmarketcap.com/static/img/exchanges/64x64/270.png",
            "urls": {"website": ["https://binance.com"]},
            "date_launched": "2017-07-14T00:00:00.000Z",
            "maker_fee": 0.1,
            "taker_fee": 0.1,
            "spot_volume_usd": 10000000000,
        }
    },
}

SAMPLE_GLOBAL_METRICS_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": {
        "total_cryptocurrencies": 10000,
        "active_cryptocurrencies": 8500,
        "active_market_pairs": 75000,
        "active_exchanges": 500,
        "btc_dominance": 52.5,
        "eth_dominance": 18.3,
        "defi_volume_24h": 5000000000,
        "defi_market_cap": 50000000000,
        "stablecoin_volume_24h": 30000000000,
        "stablecoin_market_cap": 150000000000,
        "quote": {
            "USD": {
                "total_market_cap": 1700000000000,
                "total_volume_24h": 80000000000,
                "altcoin_market_cap": 800000000000,
                "altcoin_volume_24h": 40000000000,
            }
        },
    },
}

SAMPLE_KEY_INFO_RESPONSE = {
    "status": {"error_code": 0, "error_message": None},
    "data": {
        "plan": {
            "credit_limit_daily": 333,
            "credit_limit_monthly": 10000,
            "rate_limit_minute": 30,
        },
        "usage": {
            "current_minute": {"requests_made": 5},
            "current_day": {"credits_used": 50},
            "current_month": {"credits_used": 500},
        },
    },
}


@pytest.fixture(autouse=True)
def reset_server_client() -> None:
    """Reset server client before and after each test."""
    server._client = None
    yield
    server._client = None


@pytest.fixture
def mock_api_key() -> str:
    """Set up mock API key."""
    os.environ["COINMARKETCAP_API_KEY"] = "test-api-key"
    return "test-api-key"


class TestCoinMarketCapClientUnit:
    """Unit tests for the API client with mocked responses."""

    @respx.mock
    async def test_get_cryptocurrency_map(self, mock_api_key: str) -> None:
        """Test get_cryptocurrency_map with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map").mock(
            return_value=httpx.Response(200, json=SAMPLE_MAP_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_cryptocurrency_map(symbol="BTC")
        await client.close()

        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["symbol"] == "BTC"

    @respx.mock
    async def test_get_cryptocurrency_info(self, mock_api_key: str) -> None:
        """Test get_cryptocurrency_info with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_INFO_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_cryptocurrency_info(id="1")
        await client.close()

        assert "data" in result
        assert "1" in result["data"]
        assert result["data"]["1"]["symbol"] == "BTC"

    @respx.mock
    async def test_get_cryptocurrency_quotes_latest(self, mock_api_key: str) -> None:
        """Test get_cryptocurrency_quotes_latest with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUOTES_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_cryptocurrency_quotes_latest(symbol="BTC")
        await client.close()

        assert "data" in result
        assert "BTC" in result["data"]
        assert result["data"]["BTC"][0]["quote"]["USD"]["price"] == 42000.50

    @respx.mock
    async def test_get_exchange_map(self, mock_api_key: str) -> None:
        """Test get_exchange_map with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v1/exchange/map").mock(
            return_value=httpx.Response(200, json=SAMPLE_EXCHANGE_MAP_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_exchange_map()
        await client.close()

        assert "data" in result
        assert result["data"][0]["slug"] == "binance"

    @respx.mock
    async def test_get_exchange_info(self, mock_api_key: str) -> None:
        """Test get_exchange_info with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v1/exchange/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_EXCHANGE_INFO_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_exchange_info(slug="binance")
        await client.close()

        assert "data" in result
        assert "270" in result["data"]

    @respx.mock
    async def test_get_global_metrics(self, mock_api_key: str) -> None:
        """Test get_global_metrics_quotes_latest with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest").mock(
            return_value=httpx.Response(200, json=SAMPLE_GLOBAL_METRICS_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_global_metrics_quotes_latest()
        await client.close()

        assert "data" in result
        assert result["data"]["btc_dominance"] == 52.5

    @respx.mock
    async def test_get_key_info(self, mock_api_key: str) -> None:
        """Test get_key_info with mocked response."""
        respx.get("https://pro-api.coinmarketcap.com/v1/key/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_KEY_INFO_RESPONSE)
        )

        client = CoinMarketCapClient(mock_api_key)
        result = await client.get_key_info()
        await client.close()

        assert "data" in result
        assert result["data"]["plan"]["credit_limit_daily"] == 333

    @respx.mock
    async def test_api_error_handling(self, mock_api_key: str) -> None:
        """Test API error handling."""
        error_response = {
            "status": {
                "error_code": 400,
                "error_message": "Invalid value for \"symbol\"",
            }
        }
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/info").mock(
            return_value=httpx.Response(400, json=error_response)
        )

        client = CoinMarketCapClient(mock_api_key)

        with pytest.raises(CoinMarketCapAPIError) as exc_info:
            await client.get_cryptocurrency_info(symbol="INVALID")

        await client.close()

        assert exc_info.value.status_code == 400
        assert "Invalid value" in str(exc_info.value)

    async def test_missing_parameter_error(self, mock_api_key: str) -> None:
        """Test that missing required parameters raise ValueError."""
        client = CoinMarketCapClient(mock_api_key)

        with pytest.raises(ValueError, match="At least one of"):
            await client.get_cryptocurrency_info()

        with pytest.raises(ValueError, match="At least one of"):
            await client.get_cryptocurrency_quotes_latest()

        with pytest.raises(ValueError, match="At least one of"):
            await client.get_exchange_info()

        await client.close()


class TestMCPToolsUnit:
    """Unit tests for MCP tool functions with mocked responses."""

    @respx.mock
    async def test_search_cryptocurrency_exact_symbol(self, mock_api_key: str) -> None:
        """Test search with exact symbol match."""
        respx.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map").mock(
            return_value=httpx.Response(200, json=SAMPLE_MAP_RESPONSE)
        )

        result = await server.search_cryptocurrency.fn(symbol="BTC")

        assert result["found"] is True
        assert result["best_match"]["symbol"] == "BTC"
        assert result["best_match"]["_confidence"] == "high"
        assert result["best_match"]["_match_method"] == "exact_symbol"

    @respx.mock
    async def test_search_cryptocurrency_not_found(self, mock_api_key: str) -> None:
        """Test search when cryptocurrency not found."""
        empty_response = {"status": {"error_code": 0}, "data": []}
        respx.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map").mock(
            return_value=httpx.Response(200, json=empty_response)
        )
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/info").mock(
            return_value=httpx.Response(400, json={"status": {"error_code": 400, "error_message": "Not found"}})
        )

        result = await server.search_cryptocurrency.fn(symbol="NOTEXIST")

        assert result["found"] is False
        assert result["best_match"] is None

    @respx.mock
    async def test_cryptocurrency_map_tool(self, mock_api_key: str) -> None:
        """Test cryptocurrency_map MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map").mock(
            return_value=httpx.Response(200, json=SAMPLE_MAP_RESPONSE)
        )

        result = await server.cryptocurrency_map.fn(symbol="BTC,ETH")

        assert "cryptocurrencies" in result
        assert result["count"] == 2
        symbols = {c["symbol"] for c in result["cryptocurrencies"]}
        assert "BTC" in symbols
        assert "ETH" in symbols

    @respx.mock
    async def test_cryptocurrency_info_tool(self, mock_api_key: str) -> None:
        """Test cryptocurrency_info MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_INFO_RESPONSE)
        )

        result = await server.cryptocurrency_info.fn(id="1")

        assert "cryptocurrencies" in result
        assert result["count"] == 1
        assert result["cryptocurrencies"][0]["symbol"] == "BTC"
        assert "description" in result["cryptocurrencies"][0]

    @respx.mock
    async def test_cryptocurrency_quotes_tool(self, mock_api_key: str) -> None:
        """Test cryptocurrency_quotes_latest MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest").mock(
            return_value=httpx.Response(200, json=SAMPLE_QUOTES_RESPONSE)
        )

        result = await server.cryptocurrency_quotes_latest.fn(symbol="BTC")

        assert "quotes" in result
        assert result["count"] == 1
        assert result["quotes"][0]["symbol"] == "BTC"
        assert result["quotes"][0]["quote"]["price"] == 42000.50

    @respx.mock
    async def test_exchange_map_tool(self, mock_api_key: str) -> None:
        """Test exchange_map MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v1/exchange/map").mock(
            return_value=httpx.Response(200, json=SAMPLE_EXCHANGE_MAP_RESPONSE)
        )

        result = await server.exchange_map.fn()

        assert "exchanges" in result
        assert result["count"] == 1
        assert result["exchanges"][0]["slug"] == "binance"

    @respx.mock
    async def test_exchange_info_tool(self, mock_api_key: str) -> None:
        """Test exchange_info MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v1/exchange/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_EXCHANGE_INFO_RESPONSE)
        )

        result = await server.exchange_info.fn(slug="binance")

        assert "exchanges" in result
        assert result["count"] == 1
        assert result["exchanges"][0]["slug"] == "binance"

    @respx.mock
    async def test_global_metrics_tool(self, mock_api_key: str) -> None:
        """Test global_metrics_quotes_latest MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest").mock(
            return_value=httpx.Response(200, json=SAMPLE_GLOBAL_METRICS_RESPONSE)
        )

        result = await server.global_metrics_quotes_latest.fn()

        assert result["btc_dominance"] == 52.5
        assert result["total_cryptocurrencies"] == 10000
        assert result["quote"]["total_market_cap"] == 1700000000000

    @respx.mock
    async def test_key_info_tool(self, mock_api_key: str) -> None:
        """Test key_info MCP tool."""
        respx.get("https://pro-api.coinmarketcap.com/v1/key/info").mock(
            return_value=httpx.Response(200, json=SAMPLE_KEY_INFO_RESPONSE)
        )

        result = await server.key_info.fn()

        assert result["plan"]["credit_limit_daily"] == 333
        assert result["usage"]["current_day"] == 50


class TestHelperFunctionsUnit:
    """Unit tests for helper functions."""

    def test_generate_symbol_variations_rndr(self) -> None:
        """Test RNDR -> RENDER variation."""
        variations = server._generate_symbol_variations("RNDR")
        assert "RENDER" in variations

    def test_generate_symbol_variations_matic(self) -> None:
        """Test MATIC -> POL variation (Polygon rebrand)."""
        variations = server._generate_symbol_variations("MATIC")
        assert "POL" in variations

    def test_generate_symbol_variations_fet(self) -> None:
        """Test FET -> ASI variation (ASI alliance merger)."""
        variations = server._generate_symbol_variations("FET")
        assert "ASI" in variations

    def test_generate_symbol_variations_luna(self) -> None:
        """Test LUNA variations (Terra rebrand)."""
        variations = server._generate_symbol_variations("LUNA")
        assert "LUNC" in variations
        assert "LUNA2" in variations

    def test_generate_symbol_variations_suffix_removal(self) -> None:
        """Test removal of common suffixes."""
        variations = server._generate_symbol_variations("BTCTOKEN")
        assert "BTC" in variations

    def test_generate_symbol_variations_suffix_addition(self) -> None:
        """Test addition of common suffixes for short symbols."""
        variations = server._generate_symbol_variations("SOL")
        assert "SOLTOKEN" in variations
        assert "SOLCOIN" in variations

    def test_name_to_slug_simple(self) -> None:
        """Test simple name to slug conversion."""
        assert server._name_to_slug("Bitcoin") == "bitcoin"
        assert server._name_to_slug("Ethereum") == "ethereum"

    def test_name_to_slug_with_spaces(self) -> None:
        """Test name with spaces to slug conversion."""
        assert server._name_to_slug("Render Token") == "render-token"
        assert server._name_to_slug("The Graph") == "the-graph"

    def test_name_to_slug_special_characters(self) -> None:
        """Test name with special characters."""
        assert server._name_to_slug("USD Coin (USDC)") == "usd-coin-usdc"

    def test_normalize_url_https(self) -> None:
        """Test URL normalization with https."""
        assert server._normalize_url("https://ethereum.org/") == "ethereum.org"
        assert server._normalize_url("https://ethereum.org") == "ethereum.org"

    def test_normalize_url_http(self) -> None:
        """Test URL normalization with http."""
        assert server._normalize_url("http://ethereum.org/") == "ethereum.org"

    def test_normalize_url_www(self) -> None:
        """Test URL normalization with www."""
        assert server._normalize_url("https://www.ethereum.org") == "ethereum.org"
        assert server._normalize_url("www.ethereum.org") == "ethereum.org"

    def test_normalize_url_case_insensitive(self) -> None:
        """Test URL normalization is case insensitive."""
        assert server._normalize_url("HTTPS://ETHEREUM.ORG") == "ethereum.org"

    def test_extract_domain_simple(self) -> None:
        """Test simple domain extraction."""
        assert server._extract_domain("https://ethereum.org") == "ethereum.org"

    def test_extract_domain_with_path(self) -> None:
        """Test domain extraction with path."""
        assert server._extract_domain("https://ethereum.org/en/") == "ethereum.org"
        assert server._extract_domain("https://docs.ethereum.org/guide") == "docs.ethereum.org"

    def test_extract_domain_with_port(self) -> None:
        """Test domain extraction with port."""
        assert server._extract_domain("https://localhost:8080/api") == "localhost"
        assert server._extract_domain("https://binance.com:443/trade") == "binance.com"

    def test_extract_domain_with_www(self) -> None:
        """Test domain extraction with www prefix."""
        assert server._extract_domain("https://www.binance.com") == "binance.com"


class TestAPIKeyHandling:
    """Tests for API key handling."""

    def test_missing_api_key_raises_error(self) -> None:
        """Test that missing API key raises appropriate error."""
        # Clear any existing API key
        os.environ.pop("COINMARKETCAP_API_KEY", None)
        os.environ.pop("CMC_API_KEY", None)
        server._client = None

        with pytest.raises(ValueError, match="COINMARKETCAP_API_KEY or CMC_API_KEY"):
            server._get_client()

    def test_primary_api_key(self) -> None:
        """Test that COINMARKETCAP_API_KEY is used."""
        os.environ["COINMARKETCAP_API_KEY"] = "primary-key"
        os.environ.pop("CMC_API_KEY", None)
        server._client = None

        client = server._get_client()
        assert client is not None

    def test_fallback_api_key(self) -> None:
        """Test that CMC_API_KEY is used as fallback."""
        os.environ.pop("COINMARKETCAP_API_KEY", None)
        os.environ["CMC_API_KEY"] = "fallback-key"
        server._client = None

        client = server._get_client()
        assert client is not None

    def test_client_caching(self) -> None:
        """Test that client is cached."""
        os.environ["COINMARKETCAP_API_KEY"] = "test-key"
        server._client = None

        client1 = server._get_client()
        client2 = server._get_client()

        assert client1 is client2
