"""CoinMarketCap client for muse-cmc-agent.

Python 3 standard library only. No API key is needed for the keyless
endpoints: requests go to https://pro-api.coinmarketcap.com/public-api
with no auth header, exactly as documented at
https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api

If CMC_PRO_API_KEY is set in the environment, keyed endpoints are used
instead (base https://pro-api.coinmarketcap.com + X-CMC_PRO_API_KEY
header). The key is never logged, never written to disk, and never
committed — see .gitignore.

Rate limits: keyless requests share an IP-based pool. A 429 means
"back off and retry" (docs) — this client retries 429/500/502/503 with
exponential backoff (1s, 2s, 4s, 8s, 16s). A 429 with error_code 1022
means the anonymous pool for this IP is exhausted for now; the only
fix is to wait or add a (free) API key.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

KEYLESS_BASE = "https://pro-api.coinmarketcap.com/public-api"
KEYED_BASE = "https://pro-api.coinmarketcap.com"

# Default BSC wrapped BNB, used by dex_token_price when no address given.
WBNB_BSC = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"


class CMCError(Exception):
    """An error returned by the CMC API (or by our own keyed-only guard)."""

    def __init__(self, message, http_status=None, error_code=None):
        super().__init__(message)
        self.http_status = http_status
        self.error_code = error_code


class CMCClient:
    def __init__(self, api_key=None, timeout=15):
        self.api_key = api_key or os.environ.get("CMC_PRO_API_KEY") or ""
        self.timeout = timeout

    @property
    def keyed(self):
        return bool(self.api_key)

    def _request(self, path, params=None, keyed_path=None):
        """GET one endpoint. `keyed_path` is the path to use when a key
        is present and it differs from the keyless path (rare)."""
        if self.keyed:
            base = KEYED_BASE
            use_path = keyed_path or path
            headers = {
                "Accept": "application/json",
                "X-CMC_PRO_API_KEY": self.api_key,
            }
        else:
            base = KEYLESS_BASE
            use_path = path
            headers = {"Accept": "application/json"}
        url = base + use_path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        last_error = None
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                try:
                    payload = json.loads(body)
                    status = payload.get("status", {})
                    message = status.get("error_message") or body
                    code = status.get("error_code")
                except json.JSONDecodeError:
                    message, code = body, None
                last_error = CMCError(
                    f"CMC API HTTP {exc.code}: {message}",
                    http_status=exc.code,
                    error_code=str(code) if code is not None else None,
                )
                # Retry transient errors (429 rate limit, 500 "system is busy").
                if exc.code in (429, 500, 502, 503) and attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise last_error
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = CMCError(f"Network error calling CMC: {exc}")
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise last_error
        raise last_error

    # -- Keyless endpoints (documented in the Keyless Public API list) --

    def get_price(self, symbols, convert="USD"):
        """GET /v2/simple/price (keyless) — or, when keyed,
        GET /v3/cryptocurrency/quotes/latest (richer quote object)."""
        symbols = ",".join(s.upper() for s in symbols)
        if self.keyed:
            return self._request(
                "/v3/cryptocurrency/quotes/latest",
                {"symbol": symbols, "convert": convert},
            )
        return self._request(
            "/v2/simple/price", {"symbol": symbols, "convert": convert}
        )

    def top_coins(self, limit=10, convert="USD"):
        """GET /v3/cryptocurrency/listings/latest (keyless)."""
        return self._request(
            "/v3/cryptocurrency/listings/latest",
            {"start": 1, "limit": limit, "convert": convert},
        )

    def fear_greed(self):
        """GET /v3/fear-and-greed/latest (keyless)."""
        return self._request("/v3/fear-and-greed/latest")

    def global_metrics(self, convert="USD"):
        """GET /v1/global-metrics/quotes/latest (keyless)."""
        return self._request(
            "/v1/global-metrics/quotes/latest", {"convert": convert}
        )

    def convert_price(self, amount, symbol, convert="USD"):
        """GET /v2/tools/price-conversion (keyless)."""
        return self._request(
            "/v2/tools/price-conversion",
            {"amount": amount, "symbol": symbol.upper(), "convert": convert},
        )

    def coin_info(self, symbol):
        """GET /v2/cryptocurrency/info (keyless)."""
        return self._request(
            "/v2/cryptocurrency/info", {"symbol": symbol.upper()}
        )

    def dex_token_price(self, platform="bsc", address=WBNB_BSC):
        """GET /v1/dex/token/price (keyless, per the Keyless OpenAPI spec:
        query params are `platform` + `address`, e.g. platform=bsc).
        NOTE: verified 2026-11-21 — the endpoint is listed keyless, but
        the shared-IP anonymous pool 429s (error 1022) easily, so this
        tool may report a rate-limit error keyless. Add a free key to
        make it reliable."""
        return self._request(
            "/v1/dex/token/price", {"platform": platform, "address": address}
        )

    # -- Keyed-only endpoints (NOT in the keyless list) --

    def _require_key(self, endpoint):
        raise CMCError(
            f"{endpoint} is NOT available on the keyless public API — "
            "CoinMarketCap returns HTTP 403 error_code 1005 "
            "('An API Key is required for this call'). "
            "Set CMC_PRO_API_KEY (free Basic, or the free Startup tier "
            "from the hackathon) to use it. No request was sent."
        )

    def gainers_losers(self, limit=10, time_period="24h", convert="USD"):
        """GET /v1/cryptocurrency/trending/gainers-losers — KEYED ONLY."""
        if not self.keyed:
            self._require_key("/v1/cryptocurrency/trending/gainers-losers")
        return self._request(
            "/v1/cryptocurrency/trending/gainers-losers",
            {"start": 1, "limit": limit, "time_period": time_period,
             "convert": convert},
        )

    def trending(self, limit=10, time_period="24h"):
        """GET /v1/cryptocurrency/trending/latest — KEYED ONLY."""
        if not self.keyed:
            self._require_key("/v1/cryptocurrency/trending/latest")
        return self._request(
            "/v1/cryptocurrency/trending/latest",
            {"start": 1, "limit": limit, "time_period": time_period},
        )
