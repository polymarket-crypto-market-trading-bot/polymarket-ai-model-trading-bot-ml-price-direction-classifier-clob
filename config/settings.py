"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot
    bot_mode: Literal["train", "backtest", "paper", "live"] = "paper"
    enable_live_trading: bool = False

    # API endpoints
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    clob_ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/"

    # Wallet / auth (live only)
    polymarket_private_key: str = ""
    polymarket_funder_address: str = ""
    clob_api_key: str = ""
    clob_api_secret: str = ""
    clob_api_passphrase: str = ""
    polygon_chain_id: int = 137

    # Markets
    market_ids: str = ""
    max_markets: int = 10
    min_liquidity_usd: float = 5000.0

    # Model
    model_type: Literal["xgboost", "lstm"] = "xgboost"
    confidence_threshold: float = 0.65
    direction_return_threshold: float = 0.005
    label_horizon_minutes: int = 5
    feature_windows: str = "5,15,30"

    # Risk
    max_position_size_usd: float = 100.0
    max_daily_loss_usd: float = 50.0
    max_open_trades: int = 3
    max_consecutive_losses: int = 5
    position_sizing: Literal["fixed", "kelly"] = "fixed"
    fixed_stake_usd: float = 25.0
    kelly_fraction: float = 0.25

    # Backtest
    backtest_fee_bps: float = 20.0
    backtest_slippage_bps: float = 10.0
    backtest_latency_ms: int = 250
    initial_capital_usd: float = 1000.0

    # Storage
    database_url: str = "sqlite:///data/db/polymarket_bot.sqlite"
    artifacts_dir: str = "models/artifacts"
    exports_dir: str = "exports"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"

    @field_validator("enable_live_trading", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def feature_window_list(self) -> list[int]:
        return [int(w.strip()) for w in self.feature_windows.split(",") if w.strip()]

    @property
    def market_id_list(self) -> list[str]:
        if not self.market_ids.strip():
            return []
        return [m.strip() for m in self.market_ids.split(",") if m.strip()]

    @property
    def artifacts_path(self) -> Path:
        path = Path(self.artifacts_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def exports_path(self) -> Path:
        path = Path(self.exports_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def assert_live_allowed(self) -> None:
        if not self.enable_live_trading:
            raise RuntimeError(
                "LIVE trading blocked. Set ENABLE_LIVE_TRADING=true in .env to proceed."
            )
        if not self.polymarket_private_key:
            raise RuntimeError("POLYMARKET_PRIVATE_KEY is required for live trading.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
