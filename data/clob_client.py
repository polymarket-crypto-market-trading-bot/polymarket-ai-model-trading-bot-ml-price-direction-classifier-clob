"""CLOB REST API client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from config.settings import Settings
from utils.logging import get_logger
from utils.retry import with_retry

logger = get_logger(__name__)


@dataclass
class OrderBookSnapshot:
    token_id: str
    bids: list[tuple[float, float]]
    asks: list[tuple[float, float]]
    timestamp: datetime

    @property
    def best_bid(self) -> float | None:
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0][0] if self.asks else None

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2.0

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def bid_volume(self) -> float:
        return sum(size for _, size in self.bids)

    @property
    def ask_volume(self) -> float:
        return sum(size for _, size in self.asks)

    @property
    def imbalance(self) -> float:
        total = self.bid_volume + self.ask_volume
        if total <= 0:
            return 0.0
        return (self.bid_volume - self.ask_volume) / total


@dataclass
class Trade:
    token_id: str
    price: float
    size: float
    side: str
    timestamp: datetime


class ClobClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.clob_api_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    @with_retry
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self._client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_midpoint(self, token_id: str) -> float | None:
        data = self._get("/midpoint", params={"token_id": token_id})
        if not data:
            return None
        return float(data.get("mid", 0))

    def get_price(self, token_id: str, side: str = "buy") -> float | None:
        data = self._get("/price", params={"token_id": token_id, "side": side})
        if not data:
            return None
        return float(data.get("price", 0))

    def get_order_book(self, token_id: str) -> OrderBookSnapshot | None:
        data = self._get("/book", params={"token_id": token_id})
        if not data:
            return None

        bids = [(float(b["price"]), float(b["size"])) for b in data.get("bids", [])]
        asks = [(float(a["price"]), float(a["size"])) for a in data.get("asks", [])]
        bids.sort(key=lambda x: x[0], reverse=True)
        asks.sort(key=lambda x: x[0])

        return OrderBookSnapshot(
            token_id=token_id,
            bids=bids,
            asks=asks,
            timestamp=datetime.utcnow(),
        )

    def get_trades(
        self,
        token_id: str,
        *,
        limit: int = 500,
    ) -> list[Trade]:
        data = self._get(
            "/trades",
            params={"asset_id": token_id, "limit": limit},
        )
        if not data:
            return []

        trades: list[Trade] = []
        for item in data:
            try:
                ts = item.get("match_time") or item.get("timestamp")
                if isinstance(ts, (int, float)):
                    timestamp = datetime.utcfromtimestamp(ts / 1000 if ts > 1e12 else ts)
                else:
                    timestamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                trades.append(
                    Trade(
                        token_id=token_id,
                        price=float(item.get("price", 0)),
                        size=float(item.get("size", 0)),
                        side=str(item.get("side", "")).lower(),
                        timestamp=timestamp,
                    )
                )
            except (ValueError, TypeError):
                continue
        trades.sort(key=lambda t: t.timestamp)
        return trades

    def get_prices_history(
        self,
        token_id: str,
        *,
        interval: str = "1m",
        fidelity: int = 60,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[tuple[datetime, float]]:
        params: dict[str, Any] = {
            "market": token_id,
            "interval": interval,
            "fidelity": fidelity,
        }
        if start_ts:
            params["startTs"] = start_ts
        if end_ts:
            params["endTs"] = end_ts

        data = self._get("/prices-history", params=params)
        if not data:
            return []

        history = data.get("history") or data
        if isinstance(history, dict):
            history = history.get("history", [])

        points: list[tuple[datetime, float]] = []
        for point in history:
            try:
                ts = int(point["t"])
                price = float(point["p"])
                points.append((datetime.utcfromtimestamp(ts), price))
            except (KeyError, ValueError, TypeError):
                continue
        points.sort(key=lambda x: x[0])
        return points
