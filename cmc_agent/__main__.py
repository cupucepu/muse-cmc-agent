"""CLI wrapper for muse-cmc-agent — same code path as the MCP tools.

Usage:
    python3 -m cmc_agent price BTC ETH
    python3 -m cmc_agent price BTC --convert IDR
    python3 -m cmc_agent top 10
    python3 -m cmc_agent fear
    python3 -m cmc_agent global
    python3 -m cmc_agent convert 1 BTC USD
    python3 -m cmc_agent info BTC
    python3 -m cmc_agent gainers 10
    python3 -m cmc_agent trending 10
    python3 -m cmc_agent dex [platform] [address]   # default: bsc WBNB
    python3 -m cmc_agent tools                      # list tools + endpoints
    python3 -m cmc_agent server                     # start the MCP server

No API key needed for price/top/fear/global/convert/info/dex (keyless).
gainers/trending need CMC_PRO_API_KEY. Add --json to print raw JSON.
"""

import argparse
import json
import sys

from .client import CMCError, WBNB_BSC
from .tools import TOOL_ENDPOINTS, call_tool, new_client


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="cmc_agent",
        description="Live CoinMarketCap data from the CLI (keyless by default).")
    parser.add_argument("--json", action="store_true",
                        help="Print the raw CMC JSON response.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("price", help="Price of one or more coins")
    p.add_argument("symbols", nargs="+")
    p.add_argument("--convert", default="USD")

    p = sub.add_parser("top", help="Top coins by market cap")
    p.add_argument("limit", nargs="?", type=int, default=10)
    p.add_argument("--convert", default="USD")

    sub.add_parser("fear", help="Fear & Greed index")
    p = sub.add_parser("global", help="Global market metrics")
    p.add_argument("--convert", default="USD")

    p = sub.add_parser("convert", help="Convert an amount of a coin")
    p.add_argument("amount", type=float)
    p.add_argument("symbol")
    p.add_argument("convert", nargs="?", default="USD")

    p = sub.add_parser("info", help="Metadata for a coin")
    p.add_argument("symbol")

    p = sub.add_parser("gainers", help="Top gainers/losers (KEYED ONLY)")
    p.add_argument("limit", nargs="?", type=int, default=10)
    p.add_argument("--time-period", default="24h")

    p = sub.add_parser("trending", help="Trending coins (KEYED ONLY)")
    p.add_argument("limit", nargs="?", type=int, default=10)
    p.add_argument("--time-period", default="24h")

    p = sub.add_parser("dex", help="DEX token price (default: BSC WBNB)")
    p.add_argument("platform", nargs="?", default="bsc")
    p.add_argument("address", nargs="?", default=WBNB_BSC)

    sub.add_parser("tools", help="List tools and their CMC endpoints")
    sub.add_parser("server", help="Start the MCP server over stdio")

    args = parser.parse_args(argv)

    if args.command == "tools":
        for name, (endpoint, keyless) in TOOL_ENDPOINTS.items():
            print(f"{name:16} {'keyless' if keyless else 'KEYED-ONLY'}  {endpoint}")
        return 0

    if args.command == "server":
        from .server import main as server_main
        server_main()
        return 0

    # NOTE: dispatch lazily (if/elif) — a dict literal here would evaluate
    # every branch's args.* access and crash on attributes that belong to
    # other subcommands (e.g. args.limit on the `price` command).
    cmd = args.command
    if cmd == "price":
        name, tool_args = "get_price", {"symbols": args.symbols,
                                        "convert": args.convert}
    elif cmd == "top":
        name, tool_args = "top_coins", {"limit": args.limit,
                                        "convert": args.convert}
    elif cmd == "fear":
        name, tool_args = "fear_greed", {}
    elif cmd == "global":
        name, tool_args = "global_metrics", {"convert": args.convert}
    elif cmd == "convert":
        name, tool_args = "convert_price", {"amount": args.amount,
                                            "symbol": args.symbol,
                                            "convert": args.convert}
    elif cmd == "info":
        name, tool_args = "coin_info", {"symbol": args.symbol}
    elif cmd == "gainers":
        name, tool_args = "gainers_losers", {"limit": args.limit,
                                             "time_period": args.time_period}
    elif cmd == "trending":
        name, tool_args = "trending", {"limit": args.limit,
                                       "time_period": args.time_period}
    elif cmd == "dex":
        name, tool_args = "dex_token_price", {"platform": args.platform,
                                             "address": args.address}
    else:  # unreachable: argparse requires a subcommand
        parser.error(f"unknown command: {cmd}")
    try:
        data, text = call_tool(new_client(), name, tool_args)
    except CMCError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
