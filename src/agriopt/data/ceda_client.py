"""Client for the CEDA Agmarknet API (https://api.ceda.ashoka.edu.in/documentation/).

Auth: Bearer token from CEDA_API_KEY (.env, loaded via python-dotenv). The key
is never printed or logged, and is scrubbed out of any exception message
before it is raised, even if the underlying requests exception happened to
echo request details.

The published OpenAPI schema is wrong in two ways verified against the live
API (do not trust it blindly):
- response *shapes*: it documents `{"commodities": [{"id", "name"}]}` but the
  live API returns `{"output": {"data": [{"commodity_id", "commodity_name"}]}}`.
- rate limit: nothing in the docs states a number. The live API returns
  `RateLimit-Policy: 40;w=3600` (40 requests per rolling hour) on every
  response, and a `Retry-After` header (seconds) on 429s. This client reads
  those headers rather than guessing a requests/sec figure.
"""
from __future__ import annotations

import os
import time

import requests
from dotenv import load_dotenv

from agriopt.config import CEDA_BASE_URL, ENV_FILE

# Small courteous gap between calls. The real constraint is the server's
# 40-requests/rolling-hour policy (see RateLimit-Policy response header),
# not a requests/sec figure -- callers that need many requests should pace
# themselves against that budget, and handle CedaRateLimitError (raised
# immediately on 429, using the server's own Retry-After) rather than expect
# this client to blindly retry through a rate-limit window.
RATE_LIMIT_SECONDS = 1.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0

load_dotenv(ENV_FILE)


class CedaAuthError(RuntimeError):
    """Raised on 401 (invalid/missing API key), or if CEDA_API_KEY is unset."""


class CedaApiError(RuntimeError):
    """Raised on a non-auth API failure (bad request, exhausted retries, ...)."""


class CedaRateLimitError(CedaApiError):
    """Raised immediately on 429 (no point retrying within a 40-req/hour
    window). retry_after_seconds comes from the server's Retry-After header,
    if present."""

    def __init__(self, message: str, retry_after_seconds: int | None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _get_api_key() -> str:
    key = os.environ.get("CEDA_API_KEY")
    if not key:
        raise CedaAuthError("CEDA_API_KEY is not set (check .env against .env.example)")
    return key


def _scrub(text: str, secret: str | None) -> str:
    """Defense in depth: strip the literal key value out of any message we raise."""
    if not secret:
        return text
    return text.replace(secret, "***")


class CedaClient:
    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or _get_api_key()
        self._session = requests.Session()
        self._last_request_time = 0.0

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        for attempt in range(1, MAX_RETRIES + 1):
            self._throttle()
            try:
                resp = self._session.request(
                    method, f"{CEDA_BASE_URL}{path}", headers=self._headers(), timeout=60, **kwargs
                )
            except requests.RequestException as exc:
                self._last_request_time = time.monotonic()
                if attempt >= MAX_RETRIES:
                    raise CedaApiError(
                        _scrub(f"CEDA API request to {path} failed after {MAX_RETRIES} attempts: {type(exc).__name__}", self._api_key)
                    ) from None
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue

            self._last_request_time = time.monotonic()

            if resp.status_code == 401:
                raise CedaAuthError("CEDA API returned 401 Unauthorized (check CEDA_API_KEY)")

            if resp.status_code == 429:
                # Retrying immediately is futile against a 40-req/rolling-hour
                # policy -- surface the server's own wait time and let the
                # caller (which knows the overall fetch budget/plan) decide.
                retry_after = resp.headers.get("Retry-After")
                retry_after_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                raise CedaRateLimitError(
                    _scrub(
                        f"CEDA API rate limit hit on {path} (Retry-After={retry_after_seconds}s, "
                        f"policy={resp.headers.get('RateLimit-Policy')})",
                        self._api_key,
                    ),
                    retry_after_seconds,
                )

            if resp.status_code >= 500:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                raise CedaApiError(
                    _scrub(f"CEDA API request to {path} failed after {MAX_RETRIES} attempts (status {resp.status_code})", self._api_key)
                )

            if not resp.ok:
                raise CedaApiError(
                    _scrub(f"CEDA API request to {path} failed (status {resp.status_code}): {resp.text[:300]}", self._api_key)
                )

            return resp.json()

        raise CedaApiError(_scrub(f"CEDA API request to {path} failed after {MAX_RETRIES} attempts", self._api_key))

    def get_commodities(self) -> list[dict]:
        """GET /agmarknet/commodities -> [{commodity_id, commodity_name}, ...]."""
        return self._request("GET", "/agmarknet/commodities")["output"]["data"]

    def get_geographies(self) -> list[dict]:
        """GET /agmarknet/geographies -> [{census_state_id, census_state_name,
        census_district_id, census_district_name}, ...] (one row per district,
        NOT nested as the published schema claims)."""
        return self._request("GET", "/agmarknet/geographies")["output"]["data"]

    def get_prices(
        self,
        commodity_id: int,
        state_id: int,
        from_date: str,
        to_date: str,
        district_id: list[int] | None = None,
        market_id: list[int] | None = None,
    ) -> list[dict]:
        """POST /agmarknet/prices -> DAILY records (state-level when
        district_id/market_id are omitted):
        [{date, commodity_id, census_state_id, min_price, max_price, modal_price}, ...]
        """
        body = {
            "commodity_id": commodity_id,
            "state_id": state_id,
            "from_date": from_date,
            "to_date": to_date,
        }
        if district_id is not None:
            body["district_id"] = district_id
        if market_id is not None:
            body["market_id"] = market_id
        return self._request("POST", "/agmarknet/prices", json=body)["output"]["data"]


def resolve_commodity_id(name: str, commodities: list[dict]) -> int:
    """Exact (case-insensitive) match against commodity_name. Raises if the
    match is missing or ambiguous -- callers should treat that as a STOP
    condition, not guess."""
    matches = [c for c in commodities if c["commodity_name"].strip().lower() == name.strip().lower()]
    if len(matches) == 0:
        raise ValueError(f"No CEDA commodity found matching {name!r}")
    if len(matches) > 1:
        raise ValueError(f"Ambiguous CEDA commodity match for {name!r}: {matches}")
    return matches[0]["commodity_id"]


def resolve_state_id(state_name: str, geographies: list[dict]) -> int:
    """Resolve a unique census_state_id for state_name from /agmarknet/geographies
    (which lists one row per district, so many rows share the same state_id)."""
    matches = {
        g["census_state_id"] for g in geographies if g["census_state_name"].strip().lower() == state_name.strip().lower()
    }
    if len(matches) != 1:
        raise ValueError(f"Could not uniquely resolve state_id for {state_name!r}: {matches}")
    return matches.pop()
