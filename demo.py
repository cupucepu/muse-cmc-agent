"""Demo for muse-cmc-agent: 5 real keyless calls, in sequence.

Runs the same code path as the MCP tools and the CLI, prints formatted
output, and never invents data — a failed call is reported as failed.

    python3 demo.py

Sleeps 2s between calls: the keyless API shares an IP-based rate pool,
and hammering it returns HTTP 429 (error_code 1022).
"""

import sys
import time

sys.path.insert(0, ".")
from cmc_agent.client import CMCError, WBNB_BSC  # noqa: E402
from cmc_agent.tools import call_tool, new_client  # noqa: E402


def main():
    client = new_client()
    print(f"muse-cmc-agent demo — keyed mode: {client.keyed} "
          "(keyless public API if False)\n")
    steps = [
        ("get_price", {"symbols": ["BTC", "ETH", "BNB"]},
         "1. Prices — BTC / ETH / BNB"),
        ("top_coins", {"limit": 5}, "2. Top 5 coins by market cap"),
        ("fear_greed", {}, "3. Fear & Greed index"),
        ("global_metrics", {}, "4. Global market metrics"),
        ("convert_price", {"amount": 1, "symbol": "BTC", "convert": "USD"},
         "5. Convert 1 BTC -> USD"),
        ("dex_token_price", {"platform": "bsc", "address": WBNB_BSC},
         "6. DEX price — WBNB on BSC"),
    ]
    ok = fail = 0
    for i, (name, args, title) in enumerate(steps):
        print(title)
        print("-" * len(title))
        try:
            _, text = call_tool(client, name, args)
            print(text)
            ok += 1
        except CMCError as exc:
            print(f"FAILED: {exc}")
            fail += 1
        print()
        if i < len(steps) - 1:
            time.sleep(2)
    print(f"Demo done: {ok} ok, {fail} failed.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
