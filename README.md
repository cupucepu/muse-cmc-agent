# muse-cmc-agent

A lightweight **MCP server + CLI that puts live CoinMarketCap data in front of
an LLM**. No API key, no signup, no dependencies — it runs on the CMC
**Keyless Public API** (`https://pro-api.coinmarketcap.com/public-api`).

**Track:** AI Agents and Automation — *Build with CMC: API Hackathon, Round 2*
(18 Nov – 9 Dec 2026)

**What it is:** nine MCP tools, each mapping to exactly one named CMC
endpoint, plus a CLI that uses the same code path. Ask your agent
"what's BTC doing?" and it calls the real API instead of guessing.
Read-only: prices, rankings, sentiment, conversion, metadata, DEX
prices. No wallet, no signing, no trading, no execution.

## Quick start

Requirements: **Python 3.8+ only. No pip packages, no `requirements.txt`.**

```bash
git clone https://github.com/cupucepu/muse-cmc-agent.git
cd muse-cmc-agent
python3 -m cmc_agent price BTC ETH BNB
python3 -m cmc_agent top 5
python3 -m cmc_agent fear
python3 demo.py
```

## Example output (real — captured 2026-11-21 14:40–14:41 UTC)

```
$ python3 -m cmc_agent price BTC ETH BNB
BTC (Bitcoin): $60,181.18
ETH (Ethereum): $1,684.80
BNB (BNB): $546.18

$ python3 -m cmc_agent top 5
#1 BTC $60,181.18 (-2.54% 24h) mcap $1,210,564,543,328.14
#2 ETH $1,684.80 (-3.48% 24h) mcap $205,948,225,049.48
#3 USDT $1.00 (-0.09% 24h) mcap $174,505,437,176.99
#4 BNB $546.18 (-4.08% 24h) mcap $71,828,487,426.93
#5 USDC $1.00 (-0.03% 24h) mcap $68,415,052,071.95

$ python3 -m cmc_agent fear
Fear & Greed: 8 (Extreme fear) — updated 2026-11-21T14:38:10.044Z

$ python3 -m cmc_agent global
Total market cap: $2,058,461,775,964.99
24h volume: $156,621,867,150.91
BTC dominance: 58.75%
ETH dominance: 9.99%
Active cryptocurrencies: 7949

$ python3 -m cmc_agent convert 1 BTC USD
1.0 BTC = $60,197.81

$ python3 -m cmc_agent dex
WBNB on BSC (DEX): $546.88 (-3.58% 24h)
24h volume: $250,321,424.92
Liquidity: $46,979,935.04
Market cap: $856,807,675.79
```

One real (redacted, keyless) response per tool is saved under
[`examples/responses/`](examples/responses/) — see
[`tests/test_live.py`](tests/test_live.py) to re-run the verification.

## MCP config

Claude Desktop (`claude_desktop_config.json`) / any MCP client:

```json
{
  "mcpServers": {
    "muse-cmc-agent": {
      "command": "python3",
      "args": ["-m", "cmc_agent.server"],
      "cwd": "/path/to/muse-cmc-agent"
    }
  }
}
```

With a key (optional — unlocks the two keyed-only tools):

```json
{
  "mcpServers": {
    "muse-cmc-agent": {
      "command": "python3",
      "args": ["-m", "cmc_agent.server"],
      "cwd": "/path/to/muse-cmc-agent",
      "env": { "CMC_PRO_API_KEY": "your-key-here" }
    }
  }
}
```

## Tools and the exact CMC endpoints they use

| Tool | CMC endpoint | Keyless? |
| --- | --- | --- |
| `get_price` | `GET /v2/simple/price` (keyed: `GET /v3/cryptocurrency/quotes/latest`) | ✅ yes |
| `top_coins` | `GET /v3/cryptocurrency/listings/latest` | ✅ yes |
| `fear_greed` | `GET /v3/fear-and-greed/latest` | ✅ yes |
| `global_metrics` | `GET /v1/global-metrics/quotes/latest` | ✅ yes |
| `convert_price` | `GET /v2/tools/price-conversion` | ✅ yes |
| `coin_info` | `GET /v2/cryptocurrency/info` | ✅ yes |
| `dex_token_price` | `GET /v1/dex/token/price` (`platform` + `address`, e.g. `platform=bsc`) | ✅ yes |
| `gainers_losers` | `GET /v1/cryptocurrency/trending/gainers-losers` | ❌ keyed only |
| `trending` | `GET /v1/cryptocurrency/trending/latest` | ❌ keyed only |

Keyless base: `https://pro-api.coinmarketcap.com/public-api` (no header).
Keyed base: `https://pro-api.coinmarketcap.com` + `X-CMC_PRO_API_KEY`
from the `CMC_PRO_API_KEY` environment variable. **Never commit a key** —
`.gitignore` blocks `.env` and credential files, and the client never
writes the key anywhere.

## CLI

```
python3 -m cmc_agent price BTC ETH [--convert IDR]
python3 -m cmc_agent top 10
python3 -m cmc_agent fear
python3 -m cmc_agent global
python3 -m cmc_agent convert 1 BTC USD
python3 -m cmc_agent info BTC
python3 -m cmc_agent gainers 10        # keyed only
python3 -m cmc_agent trending 10       # keyed only
python3 -m cmc_agent dex [platform] [address]   # default: bsc WBNB
python3 -m cmc_agent tools              # list tools + endpoints
python3 -m cmc_agent server             # start the MCP server (stdio)
python3 -m cmc_agent price BTC --json   # raw CMC JSON
```

## Architecture (10 lines)

1. `cmc_agent/client.py` — one stdlib `urllib` HTTP client, keyless/keyed
   base switching, exponential backoff on 429/500.
2. `cmc_agent/tools.py` — the 9 tool definitions (name, description,
   JSON schema) + one handler + one formatter per tool.
3. `cmc_agent/server.py` — MCP over stdio (JSON-RPC 2.0): `initialize`,
   `tools/list`, `tools/call`. No framework.
4. `cmc_agent/__main__.py` — CLI that calls the exact same handlers.
5. `demo.py` — 6 real calls in sequence, formatted, failures reported.
6. `tests/test_live.py` — runs all 9 tools live, saves one response each.
7. No database, no cache, no state: every call is a fresh live API call.
8. Errors are returned as errors, never as invented numbers.
9. Keyed-only tools refuse *before* sending any request when no key
   is set, with the exact CMC error explained.
10. Total: ~850 lines of Python, stdlib only.

## Verification (2026-11-21, keyless, no key)

Run it yourself: `python3 tests/test_live.py` (saves fresh responses).

| Tool | Result | Live value seen |
| --- | --- | --- |
| `get_price` | ✅ PASS | BTC $60,181.18, ETH $1,684.80, BNB $546.18 |
| `top_coins` | ✅ PASS | #1 BTC, #2 ETH, #3 USDT, #4 BNB, #5 USDC |
| `fear_greed` | ✅ PASS | 8 — Extreme fear |
| `global_metrics` | ✅ PASS | Total mcap $2.058T, 24h vol $156.6B |
| `convert_price` | ✅ PASS | 1 BTC = $60,197.81 |
| `coin_info` | ✅ PASS | Bitcoin metadata (36 KB response) |
| `dex_token_price` | ✅ PASS | WBNB/BSC $546.88, −3.58% 24h |
| `gainers_losers` | ⚠️ KEYED-ONLY | HTTP 403, error_code 1005: "An API Key is required for this call" |
| `trending` | ⚠️ KEYED-ONLY | HTTP 403, error_code 1005 (same) |

The two keyed-only tools are *not* in the keyless list published at
<https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api>
(18 standard + 17 DEX endpoints) — they were probed live and failed
exactly as documented, so the server reports that instead of faking
a response. The files
`examples/responses/gainers_losers.error.json` and
`examples/responses/trending.error.json` record the tool's own
keyed-only guard error (no request was sent); the live 403 / error_code
1005 behaviour is described in prose above, no raw 403 payload is saved.

## What the API made possible / where it got in the way

**Made possible**

- The keyless API genuinely works with zero setup: no account, no key,
  no header. The first `curl` in the docs returned real BTC/ETH prices
  in seconds, and the same envelope as the keyed API means the code
  switches bases with one `if`.
- One base URL covers CEX *and* DEX — the WBNB price on BSC came back
  from the same host, same envelope, no second integration.
- Proprietary data is in the keyless set: Fear & Greed (8, Extreme fear)
  and global metrics are the most "agent-useful" calls here, and they
  need no key at all.
- The official skills repo
  (`coinmarketcap-official/skills-for-ai-agents-by-CoinMarketCap`)
  confirmed the shape of the ecosystem (MCP / x402 / API skills), which
  is why this entry is a plain MCP server instead of another dashboard.

**Got in the way**

- **The shared-IP anonymous pool is small.** After ~15 calls in a
  minute the API returned HTTP 429, error_code 1022: *"You've reached
  the limit for anonymous access. Sign in to activate a free API plan
  or upgrade for higher limits."* The client now retries 429/500 with
  exponential backoff (1s–16s) and every script sleeps 2–3s between
  calls — but a busy shared IP can still stall a demo. A free key
  (or the hackathon Startup tier) is the real fix, not more retries.
- **Two endpoints in the brief are not keyless at all.**
  `gainers-losers` and `trending/latest` are absent from the keyless
  list and return HTTP 403 error_code 1005 without a key. They are
  implemented as keyed-only tools that explain this instead of
  pretending to work.
- **Response shapes differ between v1 and v3.** `/v3/.../listings/latest`
  returns `quote` as a *list* (one entry per convert currency) while
  v1 endpoints return it as a dict — the formatter has to handle both.
  The DEX token-price response also uses terse keys (`p`, `pc24h`,
  `v24h`, `l`, `mc`) that are only documented in the OpenAPI spec,
  not on the endpoint page — and its first probe with the wrong
  parameters (`network_id`/`contract_address`) returned a bare
  HTTP 500 "system is busy" instead of a parameter error. The correct
  parameters are `platform` + `address` (from `openapi-keyless.json`).
- **`price-conversion` matches loosely on symbol:** `symbol=BTC`
  also returns "Bitcoin Base" as a second row. The tool takes the
  first (canonical, id 1) match and the raw JSON is kept so the
  caller can see the ambiguity.

## Submission checklist

- [x] Public GitHub repo (this repo — push it, it is submission-ready)
- [x] Working demo: `python3 demo.py` (6 real calls) / screen-record it
- [x] Endpoints used, named explicitly (table above)
- [x] Visible evidence of a real API call (code + `examples/responses/`)
- [ ] X/Twitter post with the DoraHacks link, demo video, `#BuildwithCMC`
- [ ] DoraHacks submission form (track: **AI Agents and Automation**)

## License

Apache-2.0 — see [LICENSE](LICENSE).
