# CoinMarketCap MCP Server - Development Guide

## Release Process

### 1. Update Version

Edit `pyproject.toml` and `src/coinmarketcap_mcp/__init__.py`:

```bash
# pyproject.toml
version = "X.Y.Z"

# src/coinmarketcap_mcp/__init__.py
__version__ = "X.Y.Z"
```

### 2. Commit Changes

```bash
git add -A
git commit -m "chore: bump version to vX.Y.Z"
git push
```

### 3. Create GitHub Release

```bash
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes here"
```

**Note:** PyPI publish is automated via GitHub Actions when a release is created.

### Manual PyPI Publish (if needed)

```bash
uv build
uv publish dist/coinmarketcap_mcp-X.Y.Z*
```

## Environment Variables

- `COINMARKETCAP_API_KEY` - Primary API key
- `CMC_API_KEY` - Alternative API key (fallback)

## Testing

```bash
# Load env and run live tests
source .env && uv run python -c "
from coinmarketcap_mcp.cmc_api import CoinMarketCapClient
import asyncio

async def test():
    client = CoinMarketCapClient(os.environ['COINMARKETCAP_API_KEY'])
    result = await client.get_cryptocurrency_map(symbol='BTC', limit=1)
    print(result)
    await client.close()

import os
asyncio.run(test())
"
```

## Project Structure

```
src/coinmarketcap_mcp/
├── __init__.py      # Version
├── cmc_api.py       # CoinMarketCap API client
└── server.py        # FastMCP server with tools
```
