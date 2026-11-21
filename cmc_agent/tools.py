"""Tool definitions for muse-cmc-agent.

Each tool maps to exactly ONE named CoinMarketCap endpoint (see
ENDPOINTS in README.md). The same functions back the MCP server and
the CLI, so a judge can verify either path hits the same endpoint.

Keyless vs keyed (verified live 2026-11-21 against the keyless API):
  keyless: get_price, top_coins, fear_greed, global_metrics,
           convert_price, coin_info, dex_token_price
  keyed-only (403 error 1005 without a key): gainers_losers, trending
"""

from .client import CMCClient, CMCError, WBNB_BSC

# Tool name -> (CMC endpoint, keyless?, one-line description)
TOOL_ENDPOINTS = {
    "get_price": ("/v2/simple/price  [keyed: /v3/cryptocurrency/quotes/latest]",
                  True),
    "top_coins": ("/v3/cryptocurrency/listings/latest", True),
    "gainers_losers": ("/v1/cryptocurrency/trending/gainers-losers", False),
    "trending": ("/v1/cryptocurrency/trending/latest", False),
    "fear_greed": ("/v3/fear-and-greed/latest", True),
    "global_metrics": ("/v1/global-metrics/quotes/latest", True),
    "convert_price": ("/v2/tools/price-conversion", True),
    "coin_info": ("/v2/cryptocurrency/info", True),
    "dex_token_price": ("/v1/dex/token/price", True),
}

TOOLS = [
    {
        "name": "get_price",
        "description": "Current price of one or more coins by symbol. "
                       "Keyless: GET /v2/simple/price. With a key: "
                       "GET /v3/cryptocurrency/quotes/latest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"},
                            "description": 'e.g. ["BTC", "ETH"]'},
                "convert": {"type": "string", "default": "USD"},
            },
            "required": ["symbols"],
        },
    },
    {
        "name": "top_coins",
        "description": "Top cryptocurrencies by market cap. "
                       "Keyless: GET /v3/cryptocurrency/listings/latest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "convert": {"type": "string", "default": "USD"},
            },
        },
    },
    {
        "name": "gainers_losers",
        "description": "Top gainers and losers. KEYED ONLY: "
                       "GET /v1/cryptocurrency/trending/gainers-losers. "
                       "Requires CMC_PRO_API_KEY; without a key it returns "
                       "a clear error and sends no request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "time_period": {"type": "string", "default": "24h"},
                "convert": {"type": "string", "default": "USD"},
            },
        },
    },
    {
        "name": "trending",
        "description": "Trending cryptocurrencies. KEYED ONLY: "
                       "GET /v1/cryptocurrency/trending/latest. "
                       "Requires CMC_PRO_API_KEY.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "time_period": {"type": "string", "default": "24h"},
            },
        },
    },
    {
        "name": "fear_greed",
        "description": "CMC Crypto Fear and Greed Index. "
                       "Keyless: GET /v3/fear-and-greed/latest.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "global_metrics",
        "description": "Total crypto market cap, volume, BTC/ETH dominance. "
                       "Keyless: GET /v1/global-metrics/quotes/latest.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "convert": {"type": "string", "default": "USD"},
            },
        },
    },
    {
        "name": "convert_price",
        "description": "Convert an amount of one coin to another currency. "
                       "Keyless: GET /v2/tools/price-conversion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "default": 1},
                "symbol": {"type": "string", "description": 'e.g. "BTC"'},
                "convert": {"type": "string", "default": "USD"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "coin_info",
        "description": "Metadata for a coin: description, links, logo, tags. "
                       "Keyless: GET /v2/cryptocurrency/info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": 'e.g. "BTC"'},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "dex_token_price",
        "description": "On-chain DEX price of a token by contract address. "
                       "Keyless: GET /v1/dex/token/price "
                       "(params: platform + address, e.g. platform=bsc). "
                       "May 429 on the shared anonymous IP pool; a free key "
                       "makes it reliable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "default": "bsc"},
                "address": {"type": "string", "default": WBNB_BSC,
                            "description": "Token contract address"},
            },
        },
    },
]


def _fmt_usd(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(value):
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return str(value)


def _quote(row, convert="USD"):
    """Return the quote object for `convert`.

    v3 endpoints (/v3/.../listings/latest, /v3/.../quotes/latest)
    return `quote` as a LIST (one entry per convert currency);
    v1 endpoints return it as a DICT keyed by currency. Handle both.
    """
    q = row.get("quote")
    if isinstance(q, list):
        for item in q:
            if isinstance(item, dict) and item.get("symbol") == convert:
                return item
        return q[0] if q else {}
    if isinstance(q, dict):
        return q.get(convert) or next(iter(q.values()), {})
    return {}


def format_result(name, data):
    """Short human-readable rendering of a tool's raw CMC response."""
    try:
        if name == "get_price":
            rows = data.get("data", [])
            if isinstance(rows, dict):
                rows = list(rows.values())
            lines = []
            for row in rows:
                quotes = row.get("quotes") or []
                q = quotes[0] if quotes else {}
                lines.append(f"{row.get('symbol')} ({row.get('name')}): "
                             f"{_fmt_usd(q.get('price'))}")
            return "\n".join(lines) or str(data)
        if name == "top_coins":
            lines = []
            for row in data.get("data", []):
                q = _quote(row)
                lines.append(
                    f"#{row.get('cmc_rank')} {row.get('symbol')} "
                    f"{_fmt_usd(q.get('price'))} "
                    f"({_fmt_pct(q.get('percent_change_24h'))} 24h) "
                    f"mcap {_fmt_usd(q.get('market_cap'))}")
            return "\n".join(lines)
        if name in ("gainers_losers", "trending"):
            lines = []
            for row in data.get("data", []):
                q = _quote(row)
                lines.append(f"{row.get('symbol')} {_fmt_usd(q.get('price'))} "
                             f"({_fmt_pct(q.get('percent_change_24h'))} 24h)")
            return "\n".join(lines) or str(data)
        if name == "fear_greed":
            d = data.get("data", {})
            return (f"Fear & Greed: {d.get('value')} "
                    f"({d.get('value_classification')}) "
                    f"— updated {d.get('update_time')}")
        if name == "global_metrics":
            d = data.get("data") or {}
            q = (d.get("quote") or {}).get("USD") or {}
            return (
                f"Total market cap: {_fmt_usd(q.get('total_market_cap'))}\n"
                f"24h volume: {_fmt_usd(q.get('total_volume_24h'))}\n"
                f"BTC dominance: {d.get('btc_dominance')}%\n"
                f"ETH dominance: {d.get('eth_dominance')}%\n"
                f"Active cryptocurrencies: {d.get('active_cryptocurrencies')}")
        if name == "convert_price":
            rows = data.get("data", [])
            row = rows[0] if rows else {}
            q = (row.get("quote") or {}).get("USD") or {}
            return (f"{row.get('amount')} {row.get('symbol')} = "
                    f"{_fmt_usd(q.get('price'))}")
        if name == "coin_info":
            d = data.get("data", {})
            row = next(iter(d.values()), [{}])[0] if d else {}
            desc = (row.get("description") or "")[:300]
            return f"{row.get('name')} ({row.get('symbol')}): {desc}"
        if name == "dex_token_price":
            # DEX response uses short keys: p = price, pc24h = 24h change
            # as a fraction, v24h = 24h volume, l = liquidity, mc = mcap.
            d = data.get("data", {})
            if isinstance(d, dict) and "p" in d:
                pc = d.get("pc24h")
                pct = f"{float(pc) * 100:+.2f}%" if pc is not None else "n/a"
                return (f"WBNB on {d.get('pdex', '?')} (DEX): "
                        f"{_fmt_usd(d.get('p'))} ({pct} 24h)\n"
                        f"24h volume: {_fmt_usd(d.get('v24h'))}\n"
                        f"Liquidity: {_fmt_usd(d.get('l'))}\n"
                        f"Market cap: {_fmt_usd(d.get('mc'))}")
            return str(data)
    except Exception:
        pass
    return str(data)


def call_tool(client, name, args):
    """Run one tool. Returns (raw_response_dict, formatted_text).
    Raises CMCError on API / keyed-only errors — never invents data."""
    args = dict(args or {})
    if name == "get_price":
        data = client.get_price(args["symbols"],
                                args.get("convert", "USD"))
    elif name == "top_coins":
        data = client.top_coins(int(args.get("limit", 10)),
                                args.get("convert", "USD"))
    elif name == "gainers_losers":
        data = client.gainers_losers(int(args.get("limit", 10)),
                                     args.get("time_period", "24h"),
                                     args.get("convert", "USD"))
    elif name == "trending":
        data = client.trending(int(args.get("limit", 10)),
                               args.get("time_period", "24h"))
    elif name == "fear_greed":
        data = client.fear_greed()
    elif name == "global_metrics":
        data = client.global_metrics(args.get("convert", "USD"))
    elif name == "convert_price":
        data = client.convert_price(float(args.get("amount", 1)),
                                    args["symbol"],
                                    args.get("convert", "USD"))
    elif name == "coin_info":
        data = client.coin_info(args["symbol"])
    elif name == "dex_token_price":
        data = client.dex_token_price(args.get("platform", "bsc"),
                                      args.get("address", WBNB_BSC))
    else:
        raise CMCError(f"Unknown tool: {name}")
    return data, format_result(name, data)


def new_client():
    return CMCClient()
