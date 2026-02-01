"""CoinMarketCap API client using httpx."""

from typing import Any

import httpx


class CoinMarketCapAPIError(Exception):
    """CoinMarketCap API error with status code and detailed message."""

    def __init__(self, status_code: int, message: str, error_code: int | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(f"CoinMarketCap API error ({status_code}): {message}")


class CoinMarketCapClient:
    """Async HTTP client for CoinMarketCap REST API.

    API Documentation: https://coinmarketcap.com/api/documentation/v1/
    """

    BASE_URL = "https://pro-api.coinmarketcap.com"

    def __init__(self, api_key: str) -> None:
        """Initialize the CoinMarketCap API client.

        Args:
            api_key: CoinMarketCap Pro API key
        """
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "X-CMC_PRO_API_KEY": api_key,
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_cryptocurrency_map(
        self,
        symbol: str | None = None,
        slug: str | None = None,
        listing_status: str = "active",
        start: int = 1,
        limit: int = 100,
        sort: str = "cmc_rank",
    ) -> dict[str, Any]:
        """Get a mapping of all cryptocurrencies to CoinMarketCap IDs.

        Use this to efficiently look up if a token is listed on CoinMarketCap
        by symbol or slug.

        Args:
            symbol: Comma-separated cryptocurrency symbols (e.g., "BTC,ETH")
            slug: Comma-separated cryptocurrency slugs (e.g., "bitcoin,ethereum")
            listing_status: "active", "inactive", or "untracked"
            start: Offset for pagination (1-indexed)
            limit: Number of results (1-5000)
            sort: Sort by "id" or "cmc_rank"

        Returns:
            Dictionary containing cryptocurrency mapping data
        """
        params: dict[str, Any] = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
            "sort": sort,
        }
        if symbol:
            params["symbol"] = symbol
        if slug:
            params["slug"] = slug

        return await self._request("GET", "/v1/cryptocurrency/map", params=params)

    async def get_cryptocurrency_info(
        self,
        id: str | None = None,
        symbol: str | None = None,
        slug: str | None = None,
        address: str | None = None,
    ) -> dict[str, Any]:
        """Get metadata for one or more cryptocurrencies.

        Returns static metadata including name, logo, description, website URLs,
        social links, technical documentation, and other info.

        Args:
            id: Comma-separated CoinMarketCap IDs (e.g., "1,2,3")
            symbol: Comma-separated symbols (e.g., "BTC,ETH")
            slug: Comma-separated slugs (e.g., "bitcoin,ethereum")
            address: Contract address (for tokens)

        Returns:
            Dictionary containing cryptocurrency metadata
        """
        params: dict[str, Any] = {}
        if id:
            params["id"] = id
        if symbol:
            params["symbol"] = symbol
        if slug:
            params["slug"] = slug
        if address:
            params["address"] = address

        if not params:
            raise ValueError("At least one of id, symbol, slug, or address is required")

        return await self._request("GET", "/v2/cryptocurrency/info", params=params)

    async def get_cryptocurrency_quotes_latest(
        self,
        id: str | None = None,
        symbol: str | None = None,
        slug: str | None = None,
        convert: str = "USD",
    ) -> dict[str, Any]:
        """Get latest market quote for one or more cryptocurrencies.

        Returns price, volume, market cap, and other market data.

        Args:
            id: Comma-separated CoinMarketCap IDs (e.g., "1,2,3")
            symbol: Comma-separated symbols (e.g., "BTC,ETH")
            slug: Comma-separated slugs (e.g., "bitcoin,ethereum")
            convert: Currency to convert prices to (e.g., "USD,BTC")

        Returns:
            Dictionary containing latest market quotes
        """
        params: dict[str, Any] = {"convert": convert}
        if id:
            params["id"] = id
        if symbol:
            params["symbol"] = symbol
        if slug:
            params["slug"] = slug

        if not (id or symbol or slug):
            raise ValueError("At least one of id, symbol, or slug is required")

        return await self._request("GET", "/v2/cryptocurrency/quotes/latest", params=params)

    async def get_exchange_map(
        self,
        slug: str | None = None,
        listing_status: str = "active",
        start: int = 1,
        limit: int = 100,
        sort: str = "volume_24h",
    ) -> dict[str, Any]:
        """Get a mapping of all exchanges to CoinMarketCap IDs.

        Args:
            slug: Comma-separated exchange slugs
            listing_status: "active", "inactive", or "untracked"
            start: Offset for pagination (1-indexed)
            limit: Number of results (1-5000)
            sort: Sort field

        Returns:
            Dictionary containing exchange mapping data
        """
        params: dict[str, Any] = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
            "sort": sort,
        }
        if slug:
            params["slug"] = slug

        return await self._request("GET", "/v1/exchange/map", params=params)

    async def get_exchange_info(
        self,
        id: str | None = None,
        slug: str | None = None,
    ) -> dict[str, Any]:
        """Get metadata for one or more exchanges.

        Args:
            id: Comma-separated CoinMarketCap exchange IDs
            slug: Comma-separated exchange slugs

        Returns:
            Dictionary containing exchange metadata
        """
        params: dict[str, Any] = {}
        if id:
            params["id"] = id
        if slug:
            params["slug"] = slug

        if not params:
            raise ValueError("At least one of id or slug is required")

        return await self._request("GET", "/v1/exchange/info", params=params)

    async def get_global_metrics_quotes_latest(
        self,
        convert: str = "USD",
    ) -> dict[str, Any]:
        """Get global cryptocurrency market metrics.

        Returns total market cap, BTC dominance, and other global metrics.

        Args:
            convert: Currency to convert values to

        Returns:
            Dictionary containing global market metrics
        """
        return await self._request(
            "GET",
            "/v1/global-metrics/quotes/latest",
            params={"convert": convert},
        )

    async def get_key_info(self) -> dict[str, Any]:
        """Get information about your API key usage.

        Returns:
            Dictionary containing API key usage and limits
        """
        return await self._request("GET", "/v1/key/info")

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request and return the JSON response.

        Raises:
            CoinMarketCapAPIError: When the API returns an error response
        """
        response = await self._client.request(method, path, params=params)

        data = response.json()

        # CoinMarketCap returns status info in the response
        status = data.get("status", {})
        error_code = status.get("error_code", 0)

        if error_code != 0 or not response.is_success:
            error_msg = status.get("error_message", "Unknown error")
            raise CoinMarketCapAPIError(
                response.status_code,
                error_msg,
                error_code=error_code,
            )

        return data
