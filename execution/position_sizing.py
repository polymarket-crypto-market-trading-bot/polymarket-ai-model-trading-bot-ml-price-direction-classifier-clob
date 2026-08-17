"""Position sizing utilities."""

from __future__ import annotations

from config.settings import Settings


def compute_stake_usd(
    settings: Settings,
    *,
    confidence: float,
    expected_edge: float,
    available_capital: float,
) -> float:
    if settings.position_sizing == "fixed":
        stake = settings.fixed_stake_usd
    else:
        edge = max(expected_edge, 0.0)
        kelly = edge * settings.kelly_fraction
        stake = available_capital * min(kelly, 0.25)

    stake = min(stake, settings.max_position_size_usd, available_capital)
    if confidence < settings.confidence_threshold:
        return 0.0
    return max(stake, 0.0)
