"""Gamma API client for market discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from config.settings import Settings
from utils.logging import get_logger
from utils.retry import with_retry

logger = get_logger(__name__)


@dataclass
class MarketInfo:
    market_id: str
    condition_id: str
    question: str
    yes_token_id: str
    no_token_id: str
    end_date: datetime | None
    liquidity_usd: float
    volume_usd: float
    slug: str
    raw: dict[str, Any]


class GammaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.gamma_api_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    @with_retry
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_market(self, market_id: str) -> MarketInfo | None:
        data = self._get(f"/markets/{market_id}")
        if not data:
            return None
        return self._parse_market(data)

    def list_active_markets(
        self,
        *,
        limit: int = 100,
        min_liquidity_usd: float | None = None,
    ) -> list[MarketInfo]:
        params: dict[str, Any] = {
            "active": "true",
            "closed": "false",
            "limit": limit,
            "order": "liquidity",
            "ascending": "false",
        }
        raw_markets = self._get("/markets", params=params)
        markets: list[MarketInfo] = []
        for item in raw_markets:
            market = self._parse_market(item)
            if market is None:
                continue
            if min_liquidity_usd and market.liquidity_usd < min_liquidity_usd:
                continue
            markets.append(market)
        return markets

    def discover_markets(self) -> list[MarketInfo]:
        if self.settings.market_id_list:
            markets: list[MarketInfo] = []
            for market_id in self.settings.market_id_list:
                market = self.get_market(market_id)
                if market:
                    markets.append(market)
            return markets

        return self.list_active_markets(
            limit=self.settings.max_markets * 3,
            min_liquidity_usd=self.settings.min_liquidity_usd,
        )[: self.settings.max_markets]

    def _parse_market(self, item: dict[str, Any]) -> MarketInfo | None:
        try:
            token_ids = item.get("clobTokenIds")
            if isinstance(token_ids, str):
                token_ids = json.loads(token_ids)
            if not token_ids or len(token_ids) < 2:
                return None

            end_date = None
            if item.get("endDate"):
                end_date = datetime.fromisoformat(item["endDate"].replace("Z", "+00:00"))

            liquidity = float(item.get("liquidity") or item.get("liquidityNum") or 0)
            volume = float(item.get("volume") or item.get("volumeNum") or 0)

            return MarketInfo(
                market_id=str(item.get("id", "")),
                condition_id=str(item.get("conditionId", "")),
                question=str(item.get("question", "")),
                yes_token_id=str(token_ids[0]),
                no_token_id=str(token_ids[1]),
                end_date=end_date,
                liquidity_usd=liquidity,
                volume_usd=volume,
                slug=str(item.get("slug", "")),
                raw=item,
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Failed to parse market: %s", exc)
            return None
