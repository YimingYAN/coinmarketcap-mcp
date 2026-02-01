# CoinMarketCap MCP Server

MCP server for [CoinMarketCap API](https://coinmarketcap.com/api/) - search tokens, get metadata, and market data for cryptocurrency validation workflows.

## Features

- **Token Lookup**: Efficiently check if a cryptocurrency is listed on CoinMarketCap
- **Metadata Retrieval**: Get detailed token profiles including description, logos, links, and platform info
- **Market Data**: Get latest prices, volume, market cap, and price changes
- **Exchange Info**: Look up exchange metadata and trading data
- **Global Metrics**: Access total market cap, BTC dominance, and other global stats

## Installation

```bash
# Using uv (recommended)
uv pip install coinmarketcap-mcp

# Using pip
pip install coinmarketcap-mcp
```

## Configuration

### API Key Setup

Get your free API key from [CoinMarketCap API](https://coinmarketcap.com/api/).

Set the environment variable:

```bash
export COINMARKETCAP_API_KEY=your-api-key-here
# Or alternatively:
export CMC_API_KEY=your-api-key-here
```

## Usage

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "coinmarketcap": {
      "command": "uvx",
      "args": ["coinmarketcap-mcp"],
      "env": {
        "COINMARKETCAP_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Claude Code

Add to your Claude Code MCP configuration (`~/.claude.json`):

```json
{
  "mcpServers": {
    "coinmarketcap": {
      "type": "stdio",
      "command": "uvx",
      "args": ["coinmarketcap-mcp"],
      "env": {
        "COINMARKETCAP_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Run Directly

```bash
COINMARKETCAP_API_KEY=your-key coinmarketcap-mcp
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_cryptocurrency` | Progressive search by name, symbol, and/or homepage URL |
| `cryptocurrency_map` | Search if a token is listed on CoinMarketCap by symbol or slug |
| `cryptocurrency_info` | Get detailed metadata/profile for cryptocurrencies |
| `cryptocurrency_quotes_latest` | Get latest market data (price, volume, market cap) |
| `exchange_map` | Search for exchanges on CoinMarketCap |
| `exchange_info` | Get detailed metadata for exchanges |
| `global_metrics_quotes_latest` | Get global market metrics (total market cap, BTC dominance) |
| `key_info` | Get API key usage and limits |

## Example Queries

```
# Progressive search with name and homepage verification
"Search for a token named 'Uniswap' with homepage 'https://uniswap.org'"

# Check if a token is listed
"Is SOL listed on CoinMarketCap?"

# Get token metadata
"Get the profile and description for Ethereum"

# Check current prices
"What's the current price and market cap of BTC?"
```

## Development

```bash
# Clone the repo
git clone https://github.com/YimingYAN/coinmarketcap-mcp
cd coinmarketcap-mcp

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run the server locally
uv run coinmarketcap-mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.
