"""Bubble Data API HTTP client."""
from __future__ import annotations

import json
from typing import Any, Iterator, Optional

import httpx

from .config import Config

PAGE_SIZE = 100  # max do Bubble por request


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

    def get_meta(self) -> dict[str, Any]:
        r = self._client.get("/meta")
        if r.status_code != 200:
            raise BubbleAPIError(
                f"/meta retornou {r.status_code}: {r.text[:200]}"
            )
        return r.json()

    def count(
        self,
        type_name: str,
        constraints: Optional[list[dict]] = None,
    ) -> int:
        """Total de registros via probe (limit=1)."""
        params: dict[str, Any] = {"limit": 1, "cursor": 0}
        if constraints:
            params["constraints"] = json.dumps(constraints)
        r = self._client.get(f"/obj/{type_name}", params=params)
        if r.status_code != 200:
            raise BubbleAPIError(
                f"GET {type_name} falhou ({r.status_code}): {r.text[:200]}"
            )
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
            r = self._client.get(f"/obj/{type_name}", params=params)
            if r.status_code != 200:
                raise BubbleAPIError(
                    f"GET {type_name} falhou ({r.status_code}): {r.text[:200]}"
                )
            body = r.json().get("response", {})
            results = body.get("results", []) or []
            for rec in results:
                yield rec
            count = int(body.get("count", len(results)))
            remaining = int(body.get("remaining", 0))
            if count == 0 or remaining <= 0:
                return
            cursor += count
