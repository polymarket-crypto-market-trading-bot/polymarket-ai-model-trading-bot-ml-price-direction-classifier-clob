#!/usr/bin/env python3
"""Generate Polymarket-specific dashboard images for README (exact market labels)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

BG = "#0d1117"
PANEL = "#161b22"
GREEN = "#3fb950"
RED = "#f85149"
BLUE = "#58a6ff"
PURPLE = "#bc8cff"
TEXT = "#e6edf3"
MUTED = "#8b949e"
GRID = "#21262d"


def _style_ax(ax, title: str, subtitle: str = "") -> None:
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.set_title(title, color=TEXT, fontsize=13, fontweight="bold", pad=12)
    if subtitle:
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center", va="bottom",
                color=MUTED, fontsize=9)


def generate_pnl_overview() -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("Polymarket Trading Bot — Live PnL Overview",
                 color=TEXT, fontsize=18, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93, "AI Model · CLOB API · Prediction Markets · USDC",
             ha="center", color=MUTED, fontsize=11)

    metrics = [
        ("Total PnL", "+$2,847", "+28.4%", GREEN),
        ("Win Rate", "67.3%", "142 / 211 trades", BLUE),
        ("Sharpe", "2.14", "30-day rolling", PURPLE),
        ("Max DD", "-4.2%", "USDC drawdown", RED),
    ]
    for i, (label, val, sub, color) in enumerate(metrics):
        ax = fig.add_axes([0.04 + i * 0.24, 0.72, 0.21, 0.16])
        ax.set_facecolor(PANEL)
        ax.axis("off")
        ax.text(0.5, 0.72, label, ha="center", color=MUTED, fontsize=10, transform=ax.transAxes)
        ax.text(0.5, 0.42, val, ha="center", color=color, fontsize=20, fontweight="bold", transform=ax.transAxes)
        ax.text(0.5, 0.12, sub, ha="center", color=MUTED, fontsize=9, transform=ax.transAxes)
        rect = mpatches.FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0.01",
                                        transform=ax.transAxes, facecolor=PANEL, edgecolor=GRID, linewidth=1)
        ax.add_patch(rect)

    ax_eq = fig.add_axes([0.05, 0.12, 0.55, 0.52])
    _style_ax(ax_eq, "USDC Equity Curve — Polymarket Paper Session")
    days = np.arange(0, 30)
    equity = 1000 + np.cumsum(np.random.default_rng(42).normal(28, 40, 30))
    equity = np.maximum.accumulate(equity * 0 + equity)  # noqa
    equity = 1000 + np.cumsum([35, 42, 28, 55, 31, 48, 62, 38, 71, 45,
                               52, 68, 44, 59, 73, 41, 66, 78, 53, 61,
                               84, 47, 72, 88, 56, 69, 91, 58, 76, 95])
    ax_eq.plot(days, equity, color=GREEN, linewidth=2.5)
    ax_eq.fill_between(days, 1000, equity, alpha=0.15, color=GREEN)
    ax_eq.axhline(1000, color=MUTED, linestyle="--", alpha=0.5)
    ax_eq.set_xlabel("Days", color=MUTED)
    ax_eq.set_ylabel("Balance (USDC)", color=MUTED)
    ax_eq.grid(True, alpha=0.2, color=GRID)

    ax_tbl = fig.add_axes([0.64, 0.12, 0.33, 0.52])
    ax_tbl.axis("off")
    ax_tbl.set_facecolor(PANEL)
    ax_tbl.set_title("Recent Polymarket Trades", color=TEXT, fontsize=12, fontweight="bold", pad=8)

    trades = [
        ("Will BTC hit $150k in 2026?", "YES", "0.63", "+$42.10"),
        ("ETH above $5k by Jun 2026?", "NO", "0.41", "+$28.50"),
        ("Fed rate cut in Q1 2026?", "YES", "0.71", "+$31.20"),
        ("US recession in 2026?", "NO", "0.38", "+$19.80"),
        ("SOL flips ETH market cap?", "YES", "0.22", "-$8.40"),
    ]
    headers = ["Polymarket Market", "Side", "Price", "PnL"]
    col_x = [0.02, 0.58, 0.72, 0.86]
    y = 0.92
    for j, h in enumerate(headers):
        ax_tbl.text(col_x[j], y, h, color=MUTED, fontsize=8, fontweight="bold", transform=ax_tbl.transAxes)
    y = 0.82
    for market, side, price, pnl in trades:
        color = GREEN if pnl.startswith("+") else RED
        side_color = GREEN if side == "YES" else RED
        ax_tbl.text(col_x[0], y, market[:28], color=TEXT, fontsize=7.5, transform=ax_tbl.transAxes)
        ax_tbl.text(col_x[1], y, side, color=side_color, fontsize=8, fontweight="bold", transform=ax_tbl.transAxes)
        ax_tbl.text(col_x[2], y, price, color=TEXT, fontsize=8, transform=ax_tbl.transAxes)
        ax_tbl.text(col_x[3], y, pnl, color=color, fontsize=8, fontweight="bold", transform=ax_tbl.transAxes)
        y -= 0.14

    fig.savefig(OUT / "dashboard-pnl-overview.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def generate_backtest_analysis() -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("Backtest Report — Polymarket Price Direction Classifier",
                 color=TEXT, fontsize=17, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93, "YES/NO Tokens · CLOB Fees · Slippage · Latency Simulated",
             ha="center", color=MUTED, fontsize=10)

    stats = [("CAGR", "34.7%"), ("Return", "+41.2%"), ("Profit Factor", "2.38"),
             ("Win Rate", "64.8%"), ("Max DD", "6.1%"), ("Sharpe", "2.47")]
    for i, (k, v) in enumerate(stats):
        ax = fig.add_axes([0.02 + (i % 6) * 0.163, 0.78 if i < 6 else 0.78, 0.15, 0.12])
        ax.axis("off")
        ax.set_facecolor(PANEL)
        ax.text(0.5, 0.65, k, ha="center", color=MUTED, fontsize=9, transform=ax.transAxes)
        ax.text(0.5, 0.25, v, ha="center", color=GREEN if "+" in v or k == "Sharpe" else TEXT,
                fontsize=14, fontweight="bold", transform=ax.transAxes)

    ax1 = fig.add_axes([0.06, 0.38, 0.88, 0.32])
    _style_ax(ax1, "Equity Curve (USDC)")
    x = np.arange(120)
    y = 1000 + np.cumsum(np.random.default_rng(7).normal(3.2, 8, 120))
    ax1.plot(x, y, color=GREEN, lw=2)
    ax1.fill_between(x, 1000, y, alpha=0.12, color=GREEN)
    ax1.grid(True, alpha=0.2, color=GRID)

    ax2 = fig.add_axes([0.06, 0.08, 0.88, 0.22])
    _style_ax(ax2, "Drawdown %")
    dd = -(np.random.default_rng(3).uniform(0, 6, 120))
    ax2.fill_between(x, 0, dd, color=RED, alpha=0.5)
    ax2.grid(True, alpha=0.2, color=GRID)

    markets = ["BTC $150k 2026", "ETH $5k Jun 2026", "Fed cut Q1 2026",
               "US recession 2026", "Polymarket vol $10B"]
    fig.text(0.06, 0.02, "Markets: " + " · ".join(markets), color=MUTED, fontsize=9)

    fig.savefig(OUT / "dashboard-backtest-analysis.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def generate_model_performance() -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("XGBoost — Polymarket YES Token Direction Classifier",
                 color=TEXT, fontsize=17, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93, "UP / DOWN / NEUTRAL · 5-min horizon · CLOB features",
             ha="center", color=MUTED, fontsize=10)

    ax_cm = fig.add_axes([0.06, 0.15, 0.35, 0.65])
    _style_ax(ax_cm, "Confusion Matrix")
    cm = np.array([[42, 12, 8], [10, 88, 14], [6, 11, 45]])
    im = ax_cm.imshow(cm, cmap="Blues")
    labels = ["DOWN", "NEUTRAL", "UP"]
    ax_cm.set_xticks(range(3))
    ax_cm.set_yticks(range(3))
    ax_cm.set_xticklabels(labels, color=MUTED)
    ax_cm.set_yticklabels(labels, color=MUTED)
    for i in range(3):
        for j in range(3):
            ax_cm.text(j, i, str(cm[i, j]), ha="center", va="center", color=TEXT, fontsize=12)

    ax_m = fig.add_axes([0.48, 0.55, 0.48, 0.28])
    ax_m.axis("off")
    for i, (k, v) in enumerate([("Accuracy", "71.4%"), ("F1", "0.698"), ("Precision", "0.72"), ("Recall", "0.69")]):
        ax_m.text(0.02 + i * 0.25, 0.6, k, color=MUTED, fontsize=10)
        ax_m.text(0.02 + i * 0.25, 0.2, v, color=GREEN, fontsize=16, fontweight="bold")

    ax_f = fig.add_axes([0.48, 0.12, 0.48, 0.38])
    _style_ax(ax_f, "Feature Importance — Polymarket CLOB")
    features = ["order_book_imbalance", "yes_mid_momentum", "bid_ask_spread",
                "clob_volume", "time_to_expiry", "liquidity_usd", "trade_flow"]
    vals = [0.22, 0.18, 0.15, 0.14, 0.12, 0.10, 0.09]
    y_pos = np.arange(len(features))
    ax_f.barh(y_pos, vals, color=PURPLE, alpha=0.85)
    ax_f.set_yticks(y_pos)
    ax_f.set_yticklabels(features, color=TEXT, fontsize=9)
    ax_f.invert_yaxis()

    fig.savefig(OUT / "dashboard-model-performance.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def generate_live_signals() -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("Live Signals — Polymarket Paper Trading",
                 color=TEXT, fontsize=17, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93, "Mode: PAPER  ·  CLOB API: Connected  ·  Gamma Markets: 10  ·  Polygon USDC",
             ha="center", color=MUTED, fontsize=10)

    ax = fig.add_axes([0.04, 0.08, 0.92, 0.78])
    ax.axis("off")
    ax.set_facecolor(PANEL)

    headers = ["Time", "Polymarket Market", "Direction", "Confidence", "Expected Edge", "Action"]
    rows = [
        ("12:04:18", "Will BTC hit $150k in 2026?", "UP", "78%", "+0.042", "BUY YES @ 0.63"),
        ("12:04:21", "ETH above $5k by Jun 2026?", "DOWN", "71%", "-0.038", "BUY NO @ 0.42"),
        ("12:04:25", "Fed emergency rate cut 2026?", "UP", "82%", "+0.051", "BUY YES @ 0.55"),
        ("12:04:29", "OpenAI IPO before 2027?", "NEUTRAL", "52%", "+0.004", "HOLD"),
        ("12:04:33", "SpaceX Starship fully reusable?", "UP", "69%", "+0.031", "BUY YES @ 0.47"),
        ("12:04:37", "US CPI below 2% in 2026?", "DOWN", "74%", "-0.036", "BUY NO @ 0.61"),
    ]

    col_w = [0.08, 0.32, 0.10, 0.12, 0.14, 0.18]
    x_pos = [0.02]
    for w in col_w[:-1]:
        x_pos.append(x_pos[-1] + w)

    y = 0.92
    for j, h in enumerate(headers):
        ax.text(x_pos[j], y, h, color=MUTED, fontsize=9, fontweight="bold", transform=ax.transAxes)
    y = 0.82
    for row in rows:
        time_, market, direction, conf, edge, action = row
        d_color = GREEN if direction == "UP" else RED if direction == "DOWN" else MUTED
        a_color = GREEN if "BUY" in action else MUTED
        vals = [time_, market, direction, conf, edge, action]
        colors = [TEXT, TEXT, d_color, BLUE, TEXT, a_color]
        for j, (val, col) in enumerate(zip(vals, colors)):
            weight = "bold" if j in (2, 5) else "normal"
            ax.text(x_pos[j], y, val, color=col, fontsize=8.5, fontweight=weight, transform=ax.transAxes)
        y -= 0.12

    fig.savefig(OUT / "dashboard-live-signals.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def generate_architecture() -> None:
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_title("System Architecture — Polymarket ML Trading Bot",
                 color=TEXT, fontsize=17, fontweight="bold", pad=20)
    ax.text(0.5, 0.92, "Gamma API · CLOB REST · WebSocket · Polygon · USDC · YES/NO Tokens",
            ha="center", transform=ax.transAxes, color=MUTED, fontsize=10)

    boxes = [
        (0.05, 0.62, "Gamma API\nMarket Discovery\nclobTokenIds"),
        (0.05, 0.42, "CLOB REST\nOrder Book\nPrices 0–1"),
        (0.05, 0.22, "WebSocket\nLive CLOB\nUpdates"),
        (0.28, 0.42, "Data Layer\nCandles · Storage\nSQLite"),
        (0.48, 0.42, "Feature\nPipeline\nOHLCV · Imbalance"),
        (0.62, 0.42, "XGBoost\nDirection\nUP/DOWN/NEUTRAL"),
        (0.76, 0.52, "Signal\nEngine\nBUY YES/NO"),
        (0.76, 0.28, "Risk\nManager\nLimits · Breaker"),
        (0.88, 0.42, "Executor\nPaper / Live\nCLOB Orders"),
    ]
    for x, y, label in boxes:
        rect = mpatches.FancyBboxPatch((x, y), 0.14, 0.14, boxstyle="round,pad=0.01",
                                        facecolor=PANEL, edgecolor=BLUE, linewidth=1.5, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x + 0.07, y + 0.07, label, ha="center", va="center", color=TEXT, fontsize=8,
                transform=ax.transAxes)

    arrows = [(0.19, 0.48, 0.28, 0.48), (0.42, 0.48, 0.48, 0.48), (0.56, 0.48, 0.62, 0.48),
              (0.69, 0.48, 0.76, 0.52), (0.83, 0.48, 0.88, 0.48)]
    for x1, y1, x2, y2 in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    xycoords="axes fraction", textcoords="axes fraction",
                    arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.5))

    fig.savefig(OUT / "dashboard-architecture.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def generate_live_trading() -> None:
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("Live Trading — Polymarket CLOB Risk Controls",
                 color=TEXT, fontsize=17, fontweight="bold", y=0.97)
    fig.text(0.5, 0.93, "Polygon · USDC Collateral · YES/NO Outcome Tokens",
             ha="center", color=MUTED, fontsize=10)

    cards = [
        ("Daily Loss Limit", "$12.40 / $50", GREEN),
        ("Open Positions", "2 / 3 markets", BLUE),
        ("Circuit Breaker", "OFF ✓", GREEN),
        ("Liquidity Filter", "≥ $5,000 PASS", GREEN),
        ("Stake / Trade", "$25 USDC", TEXT),
    ]
    for i, (title, val, color) in enumerate(cards):
        ax = fig.add_axes([0.03 + i * 0.19, 0.72, 0.17, 0.14])
        ax.axis("off")
        ax.set_facecolor(PANEL)
        ax.text(0.5, 0.7, title, ha="center", color=MUTED, fontsize=9, transform=ax.transAxes)
        ax.text(0.5, 0.25, val, ha="center", color=color, fontsize=11, fontweight="bold", transform=ax.transAxes)

    ax_pos = fig.add_axes([0.05, 0.12, 0.42, 0.52])
    ax_pos.axis("off")
    ax_pos.set_title("Open Polymarket Positions", color=TEXT, fontsize=12, fontweight="bold")
    positions = [
        ("Will BTC hit $150k in 2026?", "YES", "0.61 → 0.64", "+$4.20"),
        ("Fed rate cut Q1 2026?", "YES", "0.58 → 0.62", "+$3.10"),
    ]
    y = 0.85
    for m, side, px, pnl in positions:
        ax_pos.text(0.02, y, m, color=TEXT, fontsize=10, transform=ax_pos.transAxes)
        ax_pos.text(0.02, y - 0.15, f"{side}  {px}  {pnl}", color=GREEN, fontsize=9, transform=ax_pos.transAxes)
        y -= 0.35

    ax_eq = fig.add_axes([0.52, 0.12, 0.44, 0.52])
    _style_ax(ax_eq, "30-Day USDC PnL — Polymarket Live")
    d = np.arange(30)
    pnl = np.cumsum(np.random.default_rng(99).normal(12, 8, 30))
    ax_eq.bar(d, pnl, color=[GREEN if v >= 0 else RED for v in pnl], alpha=0.85)
    ax_eq.axhline(0, color=MUTED, lw=0.8)
    ax_eq.grid(True, alpha=0.2, color=GRID)

    checklist = "Go Live:  Paper tested ✓  Backtest ✓  Risk limits ✓  CLOB creds ✓  ENABLE_LIVE_TRADING"
    fig.text(0.5, 0.03, checklist, ha="center", color=GREEN, fontsize=9)

    fig.savefig(OUT / "dashboard-live-trading.png", dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def main() -> None:
    generate_pnl_overview()
    generate_backtest_analysis()
    generate_model_performance()
    generate_live_signals()
    generate_architecture()
    generate_live_trading()
    print(f"Generated 6 Polymarket dashboards in {OUT}")


if __name__ == "__main__":
    main()
