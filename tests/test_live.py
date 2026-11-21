"""Live verification for muse-cmc-agent.

Runs every tool once against the real CMC API and saves one response
per tool under examples/responses/ — a real JSON response on success,
or a JSON file recording the exact error on failure. Never invents data.

    python3 tests/test_live.py

Prints PASS/FAIL per tool. Exit code 0 only if every *keyless* tool
passes; the two keyed-only tools are expected to fail without a key
and are reported as EXPECTED-KEYED-ONLY, not as failures.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cmc_agent.client import CMCError, WBNB_BSC  # noqa: E402
from cmc_agent.tools import call_tool, new_client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples", "responses")

CASES = [
    ("get_price", {"symbols": ["BTC", "ETH", "BNB"]}),
    ("top_coins", {"limit": 5}),
    ("gainers_losers", {"limit": 5}),
    ("trending", {"limit": 5}),
    ("fear_greed", {}),
    ("global_metrics", {}),
    ("convert_price", {"amount": 1, "symbol": "BTC", "convert": "USD"}),
    ("coin_info", {"symbol": "BTC"}),
    ("dex_token_price", {"platform": "bsc", "address": WBNB_BSC}),
]

KEYED_ONLY = {"gainers_losers", "trending"}


def main():
    os.makedirs(OUT, exist_ok=True)
    client = new_client()
    print(f"keyed mode: {client.keyed} (False = keyless public API)")
    results = {}
    for i, (name, args) in enumerate(CASES):
        path = os.path.join(OUT, f"{name}.json")
        try:
            data, text = call_tool(client, name, args)
            with open(path, "w") as fh:
                json.dump(data, fh, indent=2)
            print(f"PASS {name}: {text.splitlines()[0][:120]}")
            results[name] = "PASS"
        except CMCError as exc:
            err_path = os.path.join(OUT, f"{name}.error.json")
            with open(err_path, "w") as fh:
                json.dump({"tool": name, "arguments": args,
                           "error": str(exc),
                           "http_status": exc.http_status,
                           "error_code": exc.error_code}, fh, indent=2)
            if name in KEYED_ONLY and not client.keyed:
                print(f"EXPECTED-KEYED-ONLY {name}: {exc}")
                results[name] = "EXPECTED-KEYED-ONLY"
            else:
                print(f"FAIL {name}: {exc}")
                results[name] = "FAIL"
        if i < len(CASES) - 1:
            time.sleep(3)  # respect the shared-IP keyless rate pool
    print()
    for name, status in results.items():
        print(f"  {name:16} {status}")
    failed = [n for n, s in results.items() if s == "FAIL"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
