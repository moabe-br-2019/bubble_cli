"""Bubble Data API HTTP client."""
from __future__ import annotations

import json
import time
from typing import Any, Iterator, Optional
from urllib.parse import quote

import httpx

from .config import Config

PAGE_SIZE = 100  # max do Bubble por request
MAX_RETRIES = 5  # tentativas extras em 429/5xx antes de desistir
RETRY_STATUSES = {429, 500, 502, 503, 504}


class BubbleAPIError(Exception):
    pass


class BubbleClient:
    def __init__(self, config: Config, timeout: float = 30.0):
        self.config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._client.close()

    def _get(self, url: str, params: Optional[dict] = None, *, label: str = "") -> httpx.Response:
        """GET com retry/backoff em 429 e 5xx. Respeita Retry-After. Levanta em falha final."""
        for attempt in range(MAX_RETRIES + 1):
            try:
                r = self._client.get(url, params=params)
            except httpx.HTTPError as e:
                if attempt == MAX_RETRIES:
                    raise BubbleAPIError(f"{label or url}: {e}") from e
                time.sleep(min(2 ** attempt, 30))
                continue
            if r.status_code == 200:
                return r
            if r.status_code in RETRY_STATUSES and attempt < MAX_RETRIES:
                retry_after = r.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 30)
                time.sleep(delay)
                continue
            raise BubbleAPIError(
                f"{label or url} falhou ({r.status_code}): {r.text[:200]}"
            )
        raise BubbleAPIError(f"{label or url}: esgotou as tentativas")  # pragma: no cover

    def get_meta(self) -> dict[str, Any]:
        return self._get("/meta", label="/meta").json()

    def count(
        self,
        type_name: str,
        constraints: Optional[list[dict]] = None,
    ) -> int:
        """Total de registros via probe (limit=1)."""
        params: dict[str, Any] = {"limit": 1, "cursor": 0}
        if constraints:
            params["constraints"] = json.dumps(constraints)
        r = self._get(f"/obj/{quote(type_name, safe='')}", params=params, label=f"GET {type_name}")
        body = r.json().get("response", {})
        return int(body.get("remaining", 0)) + int(body.get("count", 0))

    def iter_records(
        self,
        type_name: str,
        constraints: Optional[list[dict]] = None,
    ) -> Iterator[dict[str, Any]]:
        cursor = 0
        while True:
            params: dict[str, Any] = {"cursor": cursor, "limit": PAGE_SIZE}
            if constraints:
                params["constraints"] = json.dumps(constraints)
            r = self._get(f"/obj/{quote(type_name, safe='')}", params=params, label=f"GET {type_name}")
            body = r.json().get("response", {})
            results = body.get("results", []) or []
            for rec in results:
                yield rec
            count = int(body.get("count", len(results)))
            remaining = int(body.get("remaining", 0))
            if count == 0 or remaining <= 0:
                return
            cursor += count
