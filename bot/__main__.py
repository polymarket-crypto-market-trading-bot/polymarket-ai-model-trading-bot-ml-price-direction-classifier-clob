"""CLI entry point for the trading bot."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from bot.loop import TradingBot
from config.settings import get_settings
from models.train import fetch_candles_for_market, train_model
from utils.logging import setup_logging


@click.group()
def cli() -> None:
    """Polymarket ML Price Direction Classifier Bot."""


@cli.command("train")
@click.option("--market-id", required=True, help="Gamma market ID to train on")
def train_cmd(market_id: str) -> None:
    """Train XGBoost classifier on historical market data."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_file)
    result = train_model(market_id, settings)
    click.echo(json.dumps(result, indent=2, default=str))


@cli.command("backtest")
@click.option("--market-id", required=True, help="Gamma market ID")
@click.option("--from", "from_date", required=True, help="Start date YYYY-MM-DD")
@click.option("--to", "to_date", required=True, help="End date YYYY-MM-DD")
def backtest_cmd(market_id: str, from_date: str, to_date: str) -> None:
    """Run event-driven backtest with fees and slippage."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_file)

    from backtest.engine import BacktestEngine
    from backtest.report import generate_backtest_report
    from features.pipeline import FeaturePipeline, build_training_dataset
    from models.classifier import PriceDirectionClassifier

    start = datetime.fromisoformat(from_date)
    end = datetime.fromisoformat(to_date)

    artifact = settings.artifacts_path / f"model_{market_id}.pkl"
    candles, token_id, resolved_id = fetch_candles_for_market(market_id, settings)

    if artifact.exists():
        classifier = PriceDirectionClassifier.load(artifact, settings)
        pipeline = classifier.pipeline
    else:
        click.echo("No saved model found — training inline...")
        train_result = train_model(market_id, settings)
        classifier = PriceDirectionClassifier.load(Path(train_result["artifact"]), settings)
        pipeline = classifier.pipeline

    engine = BacktestEngine(settings)
    result = engine.run(candles, classifier, pipeline, start=start, end=end)
    report = generate_backtest_report(result, settings)
    click.echo(json.dumps(report, indent=2))


@cli.command("paper")
@click.option("--interval", default=60, help="Loop interval seconds")
def paper_cmd(interval: int) -> None:
    """Run paper trading loop (default safe mode)."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_file)
    bot = TradingBot(settings, mode="paper")
    bot.run(interval_seconds=interval)


@cli.command("live")
@click.option("--interval", default=60, help="Loop interval seconds")
def live_cmd(interval: int) -> None:
    """Run live trading loop (requires ENABLE_LIVE_TRADING=true)."""
    settings = get_settings()
    settings.assert_live_allowed()
    setup_logging(settings.log_level, settings.log_file)
    bot = TradingBot(settings, mode="live")
    bot.run(interval_seconds=interval)


@cli.command("dashboard")
def dashboard_cmd() -> None:
    """Show live summary stats."""
    from dashboard.cli import render_dashboard

    settings = get_settings()
    setup_logging(settings.log_level, settings.log_file)
    render_dashboard(settings)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
