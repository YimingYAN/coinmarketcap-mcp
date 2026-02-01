# CoinMarketCap MCP Server

[![PyPI version](https://badge.fury.io/py/coinmarketcap-mcp.svg)](https://pypi.org/project/coinmarketcap-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai/code)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server for querying cryptocurrency data from [CoinMarketCap](https://coinmarketcap.com/). Enables AI assistants like Claude to search tokens, validate metadata, and retrieve market data through natural language.

## Features

- **Progressive Search** - Find tokens by name, symbol, or homepage URL with fuzzy matching
- **Symbol Variation Handling** - Automatically handles rebrands (RNDR→RENDER, MATIC→POL)
- **Homepage Verification** - Verify token identity by matching website URLs
- **Market Data** - Get latest prices, volume, market cap, and price changes
- **Token Metadata** - Retrieve descriptions, logos, social links, and platform info
- **Exchange Info** - Look up exchange metadata and trading data

## Quick Start

### Step 1: Get CoinMarketCap API Key

1. Go to [CoinMarketCap API](https://coinmarketcap.com/api/)
2. Sign up for a free account
3. Copy your API key from the dashboard

### Step 2: Store API Key

Add to your `~/.env.local`:

```bash
COINMARKETCAP_API_KEY=your-api-key-here
```

### Step 3: Configure Claude Code

Add to your `~/.claude.json` under `mcpServers`:

```json
{
  "coinmarketcap": {
    "command": "uvx",
    "args": ["coinmarketcap-mcp"],
    "env": {
      "COINMARKETCAP_API_KEY": "${COINMARKETCAP_API_KEY}"
    }
  }
}
```

### Step 4: Restart Claude Code

Restart Claude Code to load the MCP server. You should now have access to CoinMarketCap tools.

## Available Tools

### Search & Discovery

| Tool | Description |
|------|-------------|
| `search_cryptocurrency` | Progressive search with fuzzy matching and homepage verification |
| `cryptocurrency_map` | Direct lookup by symbol or slug |

### Token Data

| Tool | Description |
|------|-------------|
| `cryptocurrency_info` | Detailed metadata (description, logo, links, platform) |
| `cryptocurrency_quotes_latest` | Latest price, volume, market cap, price changes |

### Exchange Data

| Tool | Description |
|------|-------------|
| `exchange_map` | Search for exchanges |
| `exchange_info` | Exchange metadata and details |

### Market Overview

| Tool | Description |
|------|-------------|
| `global_metrics_quotes_latest` | Total market cap, BTC dominance, active coins |
| `key_info` | API usage and rate limits |

## Progressive Search

The `search_cryptocurrency` tool uses multiple strategies to find tokens:

1. **Exact symbol match** (high confidence)
2. **Symbol variations** - handles rebrands like RNDR→RENDER (medium confidence)
3. **Slug matching** - matches by name slug (medium confidence)
4. **Fuzzy name search** - searches 5000+ tokens by similarity (low confidence)
5. **Homepage verification** - boosts confidence by matching website URLs

### Example

```
Query: name="Render Token", symbol="RNDR", homepage="https://rendernetwork.com"

Search log:
- exact_symbol(RNDR): failed (symbol was renamed)
- symbol_variation(RENDER): 1 found
- homepage_verification: exact match

Result: Render (RENDER) - id=5690, confidence=verified
```

## Example Queries

```
"Search for a token named 'Uniswap' with homepage 'https://uniswap.org'"

"Is RENDER listed on CoinMarketCap?"

"Get the profile and description for Chainlink"

"What's the current price and market cap of BTC and ETH?"

"Check my API usage"
```

## Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` under `mcpServers`:

```json
{
  "coinmarketcap": {
    "command": "uvx",
    "args": ["coinmarketcap-mcp"],
    "env": {
      "COINMARKETCAP_API_KEY": "${COINMARKETCAP_API_KEY}"
    }
  }
}
```

## Development

```bash
# Clone the repo
git clone https://github.com/YimingYAN/coinmarketcap-mcp
cd coinmarketcap-mcp

# Install dependencies
uv sync

# Run the server locally
COINMARKETCAP_API_KEY=your-key uv run coinmarketcap-mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.
