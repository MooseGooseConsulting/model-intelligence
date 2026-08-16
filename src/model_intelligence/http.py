from __future__ import annotations

import asyncio
import email.utils
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

import httpx

_RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class HttpFetch:
    url: str
    fetched_at: datetime
    status_code: int
    headers: dict[str, str]
    body: bytes | None

    @property
    def not_modified(self) -> bool:
        return self.status_code == 304


class ConditionalHttpClient:
    """Small, explicit transport for durable collectors.

    It supports connection pooling, HTTP/2, conditional GETs, bounded retries,
    Retry-After, and a stable user agent. Source-specific parsing deliberately
    lives outside this transport.
    """

    def __init__(
        self,
        *,
        user_agent: str = "MooseGoose-Model-Intelligence/0.1 (+https://github.com/MooseGooseConsulting/model-intelligence)",
        timeout_seconds: float = 30.0,
        max_attempts: int = 4,
    ) -> None:
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(
            http2=True,
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate, br",
            },
        )

    async def __aenter__(self) -> ConditionalHttpClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpFetch:
        request_headers = dict(headers or {})
        if etag:
            request_headers["If-None-Match"] = etag
        if last_modified:
            request_headers["If-Modified-Since"] = last_modified

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await self._client.get(url, headers=request_headers)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError, httpx.ReadTimeout):
                if attempt == self._max_attempts:
                    raise
                await asyncio.sleep(_backoff_seconds(attempt))
                continue

            if response.status_code in _RETRYABLE_STATUSES and attempt < self._max_attempts:
                await asyncio.sleep(_retry_delay(response, attempt))
                continue

            if response.status_code not in {200, 304}:
                response.raise_for_status()

            return HttpFetch(
                url=str(response.url),
                fetched_at=datetime.now(timezone.utc),
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=None if response.status_code == 304 else response.content,
            )

        raise RuntimeError("HTTP retry loop exhausted unexpectedly")


def _backoff_seconds(attempt: int) -> float:
    base = min(2 ** (attempt - 1), 16)
    return base + random.uniform(0.0, 0.5)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After")
    if raw:
        try:
            return max(float(raw), 0.0)
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(raw)
            if parsed is not None:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return max((parsed - datetime.now(timezone.utc)).total_seconds(), 0.0)
    return _backoff_seconds(attempt)
