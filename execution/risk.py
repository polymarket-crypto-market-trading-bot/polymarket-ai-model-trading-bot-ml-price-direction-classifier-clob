"""Risk controls and circuit breakers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from config.settings import Settings
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskState:
    open_trades: int = 0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    kill_switch: bool = False
    last_reset: date = field(default_factory=date.today)


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = RiskState()

    def reset_daily_if_needed(self) -> None:
        today = date.today()
        if self.state.last_reset != today:
            self.state.daily_pnl = 0.0
            self.state.last_reset = today

    def can_trade(self, *, liquidity_usd: float) -> tuple[bool, str]:
        self.reset_daily_if_needed()
        if self.state.kill_switch:
            return False, "Kill switch active"
        if liquidity_usd < self.settings.min_liquidity_usd:
            return False, f"Liquidity ${liquidity_usd:.0f} below minimum"
        if self.state.open_trades >= self.settings.max_open_trades:
            return False, "Max open trades reached"
        if self.state.daily_pnl <= -self.settings.max_daily_loss_usd:
            return False, "Max daily loss reached"
        if self.state.consecutive_losses >= self.settings.max_consecutive_losses:
            self.state.kill_switch = True
            logger.error("Circuit breaker triggered after consecutive losses")
            return False, "Circuit breaker triggered"
        return True, "OK"

    def register_open(self) -> None:
        self.state.open_trades += 1

    def register_close(self, pnl: float) -> None:
        self.state.open_trades = max(0, self.state.open_trades - 1)
        self.state.daily_pnl += pnl
        if pnl < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

    def activate_kill_switch(self) -> None:
        self.state.kill_switch = True
        logger.warning("Kill switch manually activated at %s", datetime.utcnow())
