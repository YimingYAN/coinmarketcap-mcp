"""CoinMarketCap MCP Server - expose CoinMarketCap API operations as MCP tools."""

import os
from typing import Any

from fastmcp import FastMCP

from coinmarketcap_mcp.cmc_api import CoinMarketCapClient

mcp = FastMCP(name="CoinMarketCap MCP Server")

_client: CoinMarketCapClient | None = None


@mcp.tool
async def search_cryptocurrency(
    name: str | None = None,
    symbol: str | None = None,
    homepage: str | None = None,
) -> dict[str, Any]:
    """Progressive search to find a cryptocurrency on CoinMarketCap.

    Uses multiple strategies with increasing fuzziness:
    1. Exact symbol match (high confidence)
    2. Symbol variations - common transformations (medium confidence)
    3. Slug match from name (medium confidence)
    4. Fuzzy name matching against listings (low confidence)
    5. Homepage verification to boost confidence

    Args:
        name: Cryptocurrency name (e.g., "Bitcoin", "Render Token")
        symbol: Cryptocurrency symbol (e.g., "BTC", "RNDR")
        homepage: Project homepage URL for verification (recommended for fuzzy matches)

    Returns:
        Dictionary containing search results with match confidence and warnings
    """
    if not (name or symbol):
        raise ValueError("At least one of name or symbol is required")

    client = _get_client()
    candidates: list[dict[str, Any]] = []
    search_log: list[str] = []

    # Strategy 1: Exact symbol match (most reliable)
    if symbol:
        symbol_upper = symbol.upper().strip()
        try:
            result = await client.get_cryptocurrency_map(symbol=symbol_upper)
            data = result.get("data", [])
            if data:
                for item in data:
                    candidates.append({
                        **item,
                        "_match_method": "exact_symbol",
                        "_confidence": "high",
                        "_matched_query": symbol_upper,
                    })
                search_log.append(f"exact_symbol({symbol_upper}): {len(data)} found")
        except Exception as e:
            search_log.append(f"exact_symbol({symbol_upper}): failed - {e}")

    # Strategy 2: Symbol variations (if exact match failed)
    if symbol and not candidates:
        variations = _generate_symbol_variations(symbol)
        for variant in variations:
            if variant == symbol.upper():
                continue  # Skip, already tried
            try:
                result = await client.get_cryptocurrency_map(symbol=variant)
                data = result.get("data", [])
                if data:
                    for item in data:
                        candidates.append({
                            **item,
                            "_match_method": "symbol_variation",
                            "_confidence": "medium",
                            "_matched_query": variant,
                            "_original_query": symbol.upper(),
                        })
                    search_log.append(f"symbol_variation({variant}): {len(data)} found")
                    break  # Stop on first successful variation
            except Exception:
                search_log.append(f"symbol_variation({variant}): no match")

    # Strategy 3: Slug match from name (use /info endpoint which supports slug)
    if name and not candidates:
        slug = _name_to_slug(name)
        try:
            result = await client.get_cryptocurrency_info(slug=slug)
            data = result.get("data", {})
            if data:
                for key, info in data.items():
                    if isinstance(info, list):
                        for item in info:
                            candidates.append({
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "symbol": item.get("symbol"),
                                "slug": item.get("slug"),
                                "_match_method": "slug",
                                "_confidence": "medium",
                                "_matched_query": slug,
                            })
                    else:
                        candidates.append({
                            "id": info.get("id"),
                            "name": info.get("name"),
                            "symbol": info.get("symbol"),
                            "slug": info.get("slug"),
                            "_match_method": "slug",
                            "_confidence": "medium",
                            "_matched_query": slug,
                        })
                search_log.append(f"slug({slug}): {len(candidates)} found")
        except Exception as e:
            search_log.append(f"slug({slug}): no match - {e}")

    # Strategy 4: Fuzzy name matching (search through listings)
    if name and not candidates:
        fuzzy_matches = await _fuzzy_search_by_name(client, name)
        if fuzzy_matches:
            for match in fuzzy_matches:
                candidates.append({
                    **match,
                    "_match_method": "fuzzy_name",
                    "_confidence": "low",
                    "_similarity": match.get("_similarity"),
                    "_warning": "Fuzzy match - verify with homepage or manual check",
                })
            search_log.append(f"fuzzy_name({name}): {len(fuzzy_matches)} found")
        else:
            search_log.append(f"fuzzy_name({name}): no match")

    # Strategy 5: Homepage verification (boosts confidence)
    if homepage and candidates:
        candidates = await _verify_candidates_by_homepage(client, candidates, homepage)
        search_log.append(f"homepage_verification: checked {len(candidates)} candidates")

    # Sort by confidence
    confidence_order = {"verified": 0, "high": 1, "medium": 2, "low": 3}
    candidates.sort(key=lambda x: confidence_order.get(x.get("_confidence", "low"), 3))

    # Add warnings for low confidence results
    warnings = []
    if candidates and candidates[0].get("_confidence") == "low":
        warnings.append("Best match is low confidence - provide homepage URL for verification")
    if len(candidates) > 1 and not homepage:
        warnings.append(f"Multiple matches ({len(candidates)}) - provide homepage URL to disambiguate")

    return {
        "query": {"name": name, "symbol": symbol, "homepage": homepage},
        "found": len(candidates) > 0,
        "match_count": len(candidates),
        "best_match": candidates[0] if candidates else None,
        "all_matches": candidates[:10],
        "search_log": search_log,
        "warnings": warnings if warnings else None,
    }


def _generate_symbol_variations(symbol: str) -> list[str]:
    """Generate common symbol variations to try.

    Handles cases like RNDR -> RENDER, TOKEN suffix removal, etc.
    """
    symbol = symbol.upper().strip()
    variations = []

    # Common abbreviation expansions (known rebrands/merges)
    expansions = {
        "RNDR": ["RENDER"],
        "GRT": ["GRAPH"],
        "FET": ["FETCH", "ASI"],  # FET merged into ASI alliance
        "AGIX": ["ASI"],  # AGIX merged into ASI alliance
        "OCEAN": ["ASI"],  # OCEAN merged into ASI alliance
        "LUNA": ["LUNC", "LUNA2"],  # Terra rebrand
        "UST": ["USTC"],
        "MATIC": ["POL"],  # Polygon rebrand
    }
    if symbol in expansions:
        variations.extend(expansions[symbol])

    # Remove common suffixes
    suffixes = ["TOKEN", "COIN", "PROTOCOL", "NETWORK", "FINANCE", "SWAP", "DAO"]
    for suffix in suffixes:
        if symbol.endswith(suffix) and len(symbol) > len(suffix):
            variations.append(symbol[:-len(suffix)])

    # Add common suffixes if symbol is short
    if len(symbol) <= 4:
        for suffix in ["TOKEN", "COIN"]:
            variations.append(symbol + suffix)

    # Try without numbers at the end (e.g., USDT2 -> USDT)
    if symbol and symbol[-1].isdigit():
        variations.append(symbol.rstrip("0123456789"))

    # Try expanding single letters at end (e.g., if pattern suggests)
    if len(symbol) >= 3 and symbol.endswith("R"):
        variations.append(symbol[:-1] + "ER")  # RNDR -> RENDER pattern

    # Try common letter expansions
    if len(symbol) >= 3 and symbol.endswith("N"):
        variations.append(symbol + "ET")  # Possible network pattern

    return variations


async def _fuzzy_search_by_name(client: CoinMarketCapClient, name: str) -> list[dict[str, Any]]:
    """Search for cryptocurrency by fuzzy name matching.

    Fetches top cryptocurrencies and matches by name similarity.
    Uses multiple matching strategies with different thresholds.
    """
    import re

    name_lower = name.lower().strip()
    name_clean = re.sub(r'[^a-z0-9]', '', name_lower)

    matches = []

    try:
        # Get top 5000 cryptocurrencies to search through
        result = await client.get_cryptocurrency_map(limit=5000)
        data = result.get("data", [])

        for item in data:
            item_name = item.get("name", "").lower()
            item_symbol = item.get("symbol", "").lower()
            item_slug = item.get("slug", "").lower()
            item_name_clean = re.sub(r'[^a-z0-9]', '', item_name)
            item_slug_clean = re.sub(r'[^a-z0-9]', '', item_slug)

            similarity = 0.0
            match_type = None

            # Exact match (case-insensitive)
            if name_clean == item_name_clean or name_clean == item_slug_clean:
                similarity = 1.0
                match_type = "exact"
            # Query contained in name/slug
            elif name_clean in item_name_clean or name_clean in item_slug_clean:
                similarity = 0.9
                match_type = "contains"
            # Name/slug contained in query (e.g., "SingularityNET" contains "singularity")
            elif item_name_clean in name_clean or item_slug_clean in name_clean:
                if len(item_name_clean) >= 5:  # Avoid short false positives
                    similarity = 0.85
                    match_type = "reverse_contains"
            # Word overlap
            else:
                query_words = set(re.findall(r'\w{3,}', name_lower))  # Words 3+ chars
                name_words = set(re.findall(r'\w{3,}', item_name))
                if query_words and name_words:
                    overlap = query_words & name_words
                    if overlap:
                        similarity = 0.6 + (len(overlap) / max(len(query_words), len(name_words)) * 0.3)
                        match_type = "word_overlap"

            if similarity >= 0.6:
                matches.append({
                    **item,
                    "_similarity": round(similarity, 2),
                    "_match_type": match_type,
                })

        # Sort by similarity and return top matches
        matches.sort(key=lambda x: (-x.get("_similarity", 0), x.get("rank", 99999)))
        return matches[:5]

    except Exception:
        return []


def _calculate_similarity(query: str, name: str, symbol: str, slug: str) -> float:
    """Calculate similarity score between query and cryptocurrency.

    Returns value between 0 and 1.
    """
    import re

    query_clean = re.sub(r'[^a-z0-9]', '', query.lower())
    name_clean = re.sub(r'[^a-z0-9]', '', name.lower())
    slug_clean = re.sub(r'[^a-z0-9]', '', slug.lower())

    # Exact matches
    if query_clean == name_clean or query_clean == slug_clean:
        return 1.0

    # Query is contained in name or slug
    if query_clean in name_clean or query_clean in slug_clean:
        return 0.9

    # Name or slug starts with query
    if name_clean.startswith(query_clean) or slug_clean.startswith(query_clean):
        return 0.85

    # Word-based matching
    query_words = set(re.findall(r'\w+', query.lower()))
    name_words = set(re.findall(r'\w+', name.lower()))

    if query_words and name_words:
        intersection = query_words & name_words
        union = query_words | name_words
        jaccard = len(intersection) / len(union)
        if jaccard >= 0.5:
            return 0.7 + (jaccard * 0.2)

    # Levenshtein-like similarity for short strings
    if len(query_clean) <= 10 and len(name_clean) <= 15:
        max_len = max(len(query_clean), len(name_clean))
        if max_len > 0:
            common_prefix = 0
            for i in range(min(len(query_clean), len(name_clean))):
                if query_clean[i] == name_clean[i]:
                    common_prefix += 1
                else:
                    break
            prefix_ratio = common_prefix / max_len
            if prefix_ratio >= 0.6:
                return 0.7 + (prefix_ratio * 0.1)

    return 0.0


async def _verify_candidates_by_homepage(
    client: CoinMarketCapClient,
    candidates: list[dict[str, Any]],
    homepage: str,
) -> list[dict[str, Any]]:
    """Verify candidates by checking if homepage URL matches."""
    normalized_homepage = _normalize_url(homepage)

    # Get info for top candidates
    ids_to_check = [str(c["id"]) for c in candidates[:10]]
    if not ids_to_check:
        return candidates

    try:
        info_result = await client.get_cryptocurrency_info(id=",".join(ids_to_check))
        info_data = info_result.get("data", {})

        for candidate in candidates:
            cid = str(candidate["id"])
            if cid in info_data:
                info = info_data[cid]
                urls = info.get("urls", {})
                website_urls = urls.get("website", [])

                # Check for exact match
                exact_match = any(
                    _normalize_url(url) == normalized_homepage
                    for url in website_urls
                )

                # Check for domain match (more lenient)
                domain_match = any(
                    _extract_domain(url) == _extract_domain(homepage)
                    for url in website_urls
                )

                if exact_match:
                    candidate["_confidence"] = "verified"
                    candidate["_homepage_match"] = "exact"
                    candidate["_website_urls"] = website_urls
                    candidate.pop("_warning", None)  # Remove warning if verified
                elif domain_match:
                    if candidate["_confidence"] == "low":
                        candidate["_confidence"] = "medium"
                    candidate["_homepage_match"] = "domain"
                    candidate["_website_urls"] = website_urls
                else:
                    candidate["_homepage_match"] = False
                    candidate["_website_urls"] = website_urls

    except Exception:
        pass  # Keep original candidates if verification fails

    return candidates


def _name_to_slug(name: str) -> str:
    """Convert a cryptocurrency name to CoinMarketCap slug format."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def _normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    url = url.lower().strip()
    url = url.rstrip('/')
    for prefix in ['https://', 'http://', 'www.']:
        if url.startswith(prefix):
            url = url[len(prefix):]
    return url


def _extract_domain(url: str) -> str:
    """Extract domain from URL for comparison."""
    url = _normalize_url(url)
    # Remove path
    domain = url.split('/')[0]
    # Remove port
    domain = domain.split(':')[0]
    return domain


@mcp.tool
async def cryptocurrency_map(
    symbol: str | None = None,
    slug: str | None = None,
    listing_status: str = "active",
    limit: int = 100,
) -> dict[str, Any]:
    """Search if a cryptocurrency is listed on CoinMarketCap.

    This is the most efficient way to check if a token exists and get its
    CoinMarketCap ID. Use symbol for quick lookups (e.g., "BTC", "ETH").

    Args:
        symbol: Comma-separated cryptocurrency symbols (e.g., "BTC,ETH,SOL")
        slug: Comma-separated cryptocurrency slugs (e.g., "bitcoin,ethereum")
        listing_status: Filter by status: "active", "inactive", or "untracked"
        limit: Maximum results to return (1-5000, default 100)

    Returns:
        Dictionary containing matching cryptocurrencies with their CMC IDs,
        names, symbols, slugs, and platform info (for tokens)
    """
    client = _get_client()
    result = await client.get_cryptocurrency_map(
        symbol=symbol,
        slug=slug,
        listing_status=listing_status,
        limit=limit,
    )

    cryptos = result.get("data", [])
    return {
        "cryptocurrencies": [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "symbol": c.get("symbol"),
                "slug": c.get("slug"),
                "rank": c.get("rank"),
                "is_active": c.get("is_active"),
                "first_historical_data": c.get("first_historical_data"),
                "platform": c.get("platform"),
            }
            for c in cryptos
        ],
        "count": len(cryptos),
    }


@mcp.tool
async def cryptocurrency_info(
    id: str | None = None,
    symbol: str | None = None,
    slug: str | None = None,
    address: str | None = None,
) -> dict[str, Any]:
    """Get detailed metadata/profile for cryptocurrencies.

    Returns comprehensive information including description, logo, website,
    social links, technical documentation, tags, and platform details.

    Args:
        id: Comma-separated CoinMarketCap IDs (e.g., "1,1027")
        symbol: Comma-separated symbols (e.g., "BTC,ETH")
        slug: Comma-separated slugs (e.g., "bitcoin,ethereum")
        address: Contract address for token lookup

    Returns:
        Dictionary containing detailed cryptocurrency metadata
    """
    client = _get_client()
    result = await client.get_cryptocurrency_info(
        id=id,
        symbol=symbol,
        slug=slug,
        address=address,
    )

    data = result.get("data", {})
    cryptos = []

    for key, c in data.items():
        # Handle both dict format (by symbol) and direct format (by id)
        if isinstance(c, list):
            # When querying by symbol, results can be a list
            for item in c:
                cryptos.append(_extract_crypto_info(item))
        else:
            cryptos.append(_extract_crypto_info(c))

    return {"cryptocurrencies": cryptos, "count": len(cryptos)}


@mcp.tool
async def cryptocurrency_quotes_latest(
    id: str | None = None,
    symbol: str | None = None,
    slug: str | None = None,
    convert: str = "USD",
) -> dict[str, Any]:
    """Get latest market data for cryptocurrencies.

    Returns current price, volume, market cap, supply, and price changes.

    Args:
        id: Comma-separated CoinMarketCap IDs (e.g., "1,1027")
        symbol: Comma-separated symbols (e.g., "BTC,ETH")
        slug: Comma-separated slugs (e.g., "bitcoin,ethereum")
        convert: Currency for price conversion (default "USD")

    Returns:
        Dictionary containing latest market quotes and price data
    """
    client = _get_client()
    result = await client.get_cryptocurrency_quotes_latest(
        id=id,
        symbol=symbol,
        slug=slug,
        convert=convert,
    )

    data = result.get("data", {})
    quotes = []

    for key, c in data.items():
        if isinstance(c, list):
            for item in c:
                quotes.append(_extract_quote(item, convert))
        else:
            quotes.append(_extract_quote(c, convert))

    return {"quotes": quotes, "count": len(quotes), "convert": convert}


@mcp.tool
async def exchange_map(
    slug: str | None = None,
    listing_status: str = "active",
    limit: int = 100,
) -> dict[str, Any]:
    """Search for exchanges on CoinMarketCap.

    Args:
        slug: Comma-separated exchange slugs to search
        listing_status: Filter by status: "active", "inactive", "untracked"
        limit: Maximum results (1-5000, default 100)

    Returns:
        Dictionary containing matching exchanges with CMC IDs and metadata
    """
    client = _get_client()
    result = await client.get_exchange_map(
        slug=slug,
        listing_status=listing_status,
        limit=limit,
    )

    exchanges = result.get("data", [])
    return {
        "exchanges": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "slug": e.get("slug"),
                "is_active": e.get("is_active"),
                "first_historical_data": e.get("first_historical_data"),
            }
            for e in exchanges
        ],
        "count": len(exchanges),
    }


@mcp.tool
async def exchange_info(
    id: str | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Get detailed metadata for exchanges.

    Args:
        id: Comma-separated CoinMarketCap exchange IDs
        slug: Comma-separated exchange slugs (e.g., "binance,coinbase-exchange")

    Returns:
        Dictionary containing exchange metadata including description and URLs
    """
    client = _get_client()
    result = await client.get_exchange_info(id=id, slug=slug)

    data = result.get("data", {})
    exchanges = []

    for key, e in data.items():
        exchanges.append({
            "id": e.get("id"),
            "name": e.get("name"),
            "slug": e.get("slug"),
            "description": e.get("description"),
            "logo": e.get("logo"),
            "urls": e.get("urls", {}),
            "date_launched": e.get("date_launched"),
            "maker_fee": e.get("maker_fee"),
            "taker_fee": e.get("taker_fee"),
            "spot_volume_usd": e.get("spot_volume_usd"),
        })

    return {"exchanges": exchanges, "count": len(exchanges)}


@mcp.tool
async def global_metrics_quotes_latest(
    convert: str = "USD",
) -> dict[str, Any]:
    """Get global cryptocurrency market metrics.

    Returns total market cap, 24h volume, BTC/ETH dominance, active currencies count.

    Args:
        convert: Currency for value conversion (default "USD")

    Returns:
        Dictionary containing global market metrics
    """
    client = _get_client()
    result = await client.get_global_metrics_quotes_latest(convert=convert)

    data = result.get("data", {})
    quote = data.get("quote", {}).get(convert, {})

    return {
        "total_cryptocurrencies": data.get("total_cryptocurrencies"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
        "active_market_pairs": data.get("active_market_pairs"),
        "active_exchanges": data.get("active_exchanges"),
        "btc_dominance": data.get("btc_dominance"),
        "eth_dominance": data.get("eth_dominance"),
        "defi_volume_24h": data.get("defi_volume_24h"),
        "defi_market_cap": data.get("defi_market_cap"),
        "stablecoin_volume_24h": data.get("stablecoin_volume_24h"),
        "stablecoin_market_cap": data.get("stablecoin_market_cap"),
        "quote": {
            "total_market_cap": quote.get("total_market_cap"),
            "total_volume_24h": quote.get("total_volume_24h"),
            "altcoin_market_cap": quote.get("altcoin_market_cap"),
            "altcoin_volume_24h": quote.get("altcoin_volume_24h"),
        },
        "convert": convert,
    }


@mcp.tool
async def key_info() -> dict[str, Any]:
    """Get information about your CoinMarketCap API key usage.

    Returns:
        Dictionary containing API key plan info and credit usage
    """
    client = _get_client()
    result = await client.get_key_info()

    data = result.get("data", {})
    plan = data.get("plan", {})
    usage = data.get("usage", {})

    return {
        "plan": {
            "credit_limit_daily": plan.get("credit_limit_daily"),
            "credit_limit_monthly": plan.get("credit_limit_monthly"),
            "rate_limit_minute": plan.get("rate_limit_minute"),
        },
        "usage": {
            "current_minute": usage.get("current_minute", {}).get("requests_made"),
            "current_day": usage.get("current_day", {}).get("credits_used"),
            "current_month": usage.get("current_month", {}).get("credits_used"),
        },
    }


def main() -> None:
    """Run the MCP server."""
    mcp.run()


def _get_client() -> CoinMarketCapClient:
    """Get or create the CoinMarketCap API client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("COINMARKETCAP_API_KEY") or os.environ.get("CMC_API_KEY")
    if not api_key:
        raise ValueError(
            "COINMARKETCAP_API_KEY or CMC_API_KEY environment variable is required. "
            "Get your free API key at https://coinmarketcap.com/api/"
        )

    _client = CoinMarketCapClient(api_key)
    return _client


def _extract_crypto_info(c: dict[str, Any]) -> dict[str, Any]:
    """Extract cryptocurrency info from API response."""
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "symbol": c.get("symbol"),
        "slug": c.get("slug"),
        "category": c.get("category"),
        "description": c.get("description"),
        "logo": c.get("logo"),
        "urls": c.get("urls", {}),
        "tags": c.get("tags", []),
        "platform": c.get("platform"),
        "date_added": c.get("date_added"),
        "date_launched": c.get("date_launched"),
        "is_infinite_supply": c.get("infinite_supply"),
        "self_reported_circulating_supply": c.get("self_reported_circulating_supply"),
        "self_reported_market_cap": c.get("self_reported_market_cap"),
    }


def _extract_quote(c: dict[str, Any], convert: str) -> dict[str, Any]:
    """Extract quote data from API response."""
    quote = c.get("quote", {}).get(convert, {})
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "symbol": c.get("symbol"),
        "slug": c.get("slug"),
        "cmc_rank": c.get("cmc_rank"),
        "circulating_supply": c.get("circulating_supply"),
        "total_supply": c.get("total_supply"),
        "max_supply": c.get("max_supply"),
        "is_active": c.get("is_active"),
        "last_updated": c.get("last_updated"),
        "quote": {
            "price": quote.get("price"),
            "volume_24h": quote.get("volume_24h"),
            "volume_change_24h": quote.get("volume_change_24h"),
            "percent_change_1h": quote.get("percent_change_1h"),
            "percent_change_24h": quote.get("percent_change_24h"),
            "percent_change_7d": quote.get("percent_change_7d"),
            "percent_change_30d": quote.get("percent_change_30d"),
            "market_cap": quote.get("market_cap"),
            "market_cap_dominance": quote.get("market_cap_dominance"),
            "fully_diluted_market_cap": quote.get("fully_diluted_market_cap"),
            "last_updated": quote.get("last_updated"),
        },
    }


if __name__ == "__main__":
    main()
