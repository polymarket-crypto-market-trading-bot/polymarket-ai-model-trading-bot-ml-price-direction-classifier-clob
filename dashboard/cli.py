"""Minimal CLI dashboard."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.table import Table

from config.settings import Settings
from data.storage import Storage
from utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


def render_dashboard(settings: Settings) -> None:
    storage = Storage(settings)
    trades = storage.get_trades_df()
    predictions = storage.get_predictions_df()

    table = Table(title="Polymarket Trading Bot — Summary")
    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Mode", settings.bot_mode)
    table.add_row("Live enabled", str(settings.enable_live_trading))
    table.add_row("Markets configured", str(len(settings.market_id_list) or settings.max_markets))
    table.add_row("Confidence threshold", f"{settings.confidence_threshold:.2f}")
    table.add_row("Total trades logged", str(len(trades)))
    table.add_row("Total predictions", str(len(predictions)))
    table.add_row("Generated at", datetime.utcnow().isoformat())

    if not trades.empty:
        pnl = trades["pnl"].fillna(0).sum()
        table.add_row("Total PnL (logged)", f"${pnl:.2f}")

    console.print(table)

    if not predictions.empty:
        recent = predictions.tail(10)
        pred_table = Table(title="Latest Signals")
        pred_table.add_column("Time")
        pred_table.add_column("Token")
        pred_table.add_column("Direction")
        pred_table.add_column("Confidence")
        pred_table.add_column("Edge")

        for _, row in recent.iterrows():
            pred_table.add_row(
                str(row["timestamp"]),
                str(row["token_id"])[:12] + "...",
                str(row["direction"]),
                f"{float(row['confidence']):.2f}",
                f"{float(row['expected_edge']):.3f}",
            )
        console.print(pred_table)

    if not trades.empty:
        trade_table = Table(title="Recent Trades")
        trade_table.add_column("Time")
        trade_table.add_column("Mode")
        trade_table.add_column("Side")
        trade_table.add_column("Price")
        trade_table.add_column("Size")
        for _, row in trades.tail(10).iterrows():
            trade_table.add_row(
                str(row["timestamp"]),
                str(row["mode"]),
                str(row["side"]),
                f"{float(row['price']):.4f}",
                f"{float(row['size']):.2f}",
            )
        console.print(trade_table)
