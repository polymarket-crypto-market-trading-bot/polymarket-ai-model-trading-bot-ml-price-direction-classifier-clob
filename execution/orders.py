"""Order execution — paper and live modes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from config.settings import Settings
from data.storage import Storage
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OrderResult:
    order_id: str
    mode: Literal["paper", "live"]
    token_id: str
    side: str
    price: float
    size: float
    status: str
    timestamp: datetime


class OrderExecutor:
    def __init__(self, settings: Settings, storage: Storage) -> None:
        self.settings = settings
        self.storage = storage
        self._paper_balance = settings.initial_capital_usd
        self._live_client = None

    def _get_live_client(self):
        if self._live_client is not None:
            return self._live_client
        self.settings.assert_live_allowed()
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            creds = None
            if self.settings.clob_api_key:
                creds = ApiCreds(
                    api_key=self.settings.clob_api_key,
                    api_secret=self.settings.clob_api_secret,
                    api_passphrase=self.settings.clob_api_passphrase,
                )
            self._live_client = ClobClient(
                self.settings.clob_api_url,
                key=self.settings.polymarket_private_key,
                chain_id=self.settings.polygon_chain_id,
                creds=creds,
                signature_type=2,
                funder=self.settings.polymarket_funder_address or None,
            )
            if creds is None:
                self._live_client.set_api_creds(self._live_client.create_or_derive_api_creds())
            return self._live_client
        except ImportError as exc:
            raise RuntimeError(
                "py-clob-client is required for live trading. pip install py-clob-client"
            ) from exc

    def place_limit_order(
        self,
        *,
        mode: Literal["paper", "live"],
        market_id: str,
        token_id: str,
        side: str,
        price: float,
        size_usd: float,
        maker_first: bool = True,
    ) -> OrderResult:
        size_shares = size_usd / max(price, 0.01)
        order_id = str(uuid.uuid4())

        if mode == "paper":
            self._paper_balance -= size_usd
            result = OrderResult(
                order_id=order_id,
                mode="paper",
                token_id=token_id,
                side=side,
                price=price,
                size=size_shares,
                status="filled",
                timestamp=datetime.utcnow(),
            )
            self.storage.log_trade(
                mode="paper",
                market_id=market_id,
                token_id=token_id,
                side=side,
                price=price,
                size=size_shares,
                metadata={"order_id": order_id, "size_usd": size_usd},
            )
            logger.info(
                "PAPER %s %s @ %.4f size=$%.2f (balance=$%.2f)",
                side,
                token_id[:8],
                price,
                size_usd,
                self._paper_balance,
            )
            return result

        self.settings.assert_live_allowed()
        client = self._get_live_client()
        from py_clob_client.clob_types import OrderArgs, OrderType

        order_side = "BUY"
        order = OrderArgs(
            token_id=token_id,
            price=round(price, 4),
            size=round(size_shares, 2),
            side=order_side,
        )
        signed = client.create_order(order)
        order_type = OrderType.GTC if maker_first else OrderType.FOK
        resp = client.post_order(signed, order_type)
        result = OrderResult(
            order_id=str(resp.get("orderID", order_id)),
            mode="live",
            token_id=token_id,
            side=side,
            price=price,
            size=size_shares,
            status=str(resp.get("status", "submitted")),
            timestamp=datetime.utcnow(),
        )
        self.storage.log_trade(
            mode="live",
            market_id=market_id,
            token_id=token_id,
            side=side,
            price=price,
            size=size_shares,
            metadata={"response": resp},
        )
        logger.info("LIVE order placed: %s", result)
        return result

    @property
    def paper_balance(self) -> float:
        return self._paper_balance
