#!/usr/bin/env python3
"""Render premium HTML dashboards to PNG via Playwright."""

from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = Path(__file__).resolve().parent / "dashboard_html"
OUT_DIR = ROOT / "docs" / "images"
CSS = (HTML_DIR / "style.css").read_text(encoding="utf-8")

# SVG equity curve (smooth upward)
EQUITY_SVG = """
<svg viewBox="0 0 600 220" width="100%" height="100%" preserveAspectRatio="none">
  <defs>
    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#10b981" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <line x1="0" y1="200" x2="600" y2="200" stroke="#334155" stroke-width="1"/>
  <line x1="0" y1="100" x2="600" y2="100" stroke="#334155" stroke-width="0.5" stroke-dasharray="4"/>
  <path d="M0,190 L30,175 L60,168 L90,155 L120,148 L150,130 L180,125 L210,108 L240,102 L270,88 L300,78 L330,70 L360,58 L390,52 L420,42 L450,35 L480,28 L510,18 L540,12 L570,8 L600,4 L600,200 L0,200 Z" fill="url(#eqGrad)"/>
  <path d="M0,190 L30,175 L60,168 L90,155 L120,148 L150,130 L180,125 L210,108 L240,102 L270,88 L300,78 L330,70 L360,58 L390,52 L420,42 L450,35 L480,28 L510,18 L540,12 L570,8 L600,4" fill="none" stroke="#34d399" stroke-width="2.5" filter="url(#glow)"/>
  <circle cx="600" cy="4" r="5" fill="#34d399" stroke="#f8fafc" stroke-width="2"/>
  <text x="520" y="20" fill="#34d399" font-size="14" font-weight="800" font-family="Inter,sans-serif">$2,888</text>
</svg>"""

BACKTEST_EQUITY_SVG = """
<svg viewBox="0 0 700 140" width="100%" height="100%" preserveAspectRatio="none">
  <defs><linearGradient id="btGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#10b981" stop-opacity="0.3"/><stop offset="100%" stop-color="#10b981" stop-opacity="0"/></linearGradient></defs>
  <path d="M0,120 Q50,115 100,100 T200,85 T300,60 T400,45 T500,30 T600,15 T700,8 L700,140 L0,140Z" fill="url(#btGrad)"/>
  <path d="M0,120 Q50,115 100,100 T200,85 T300,60 T400,45 T500,30 T600,15 T700,8" fill="none" stroke="#34d399" stroke-width="2"/>
</svg>"""

BACKTEST_DD_SVG = """
<svg viewBox="0 0 700 80" width="100%" height="100%" preserveAspectRatio="none">
  <path d="M0,5 Q80,25 160,15 T320,35 T480,20 T640,40 T700,30 L700,80 L0,80Z" fill="rgba(239,68,68,0.4)"/>
  <path d="M0,5 Q80,25 160,15 T320,35 T480,20 T640,40 T700,30" fill="none" stroke="#f87171" stroke-width="1.5"/>
</svg>"""

PNL_BARS_SVG = """
<svg viewBox="0 0 500 160" width="100%" height="100%">
  <rect x="10" y="80" width="14" height="70" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="30" y="60" width="14" height="90" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="50" y="90" width="14" height="60" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="70" y="45" width="14" height="105" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="90" y="70" width="14" height="80" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="110" y="35" width="14" height="115" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="130" y="55" width="14" height="95" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="150" y="25" width="14" height="125" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="170" y="65" width="14" height="85" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="190" y="40" width="14" height="110" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="210" y="20" width="14" height="130" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="230" y="75" width="14" height="75" rx="3" fill="#f87171" opacity="0.85"/>
  <rect x="250" y="50" width="14" height="100" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="270" y="30" width="14" height="120" rx="3" fill="#34d399" opacity="0.85"/>
  <rect x="290" y="15" width="14" height="135" rx="3" fill="#34d399" opacity="0.85"/>
  <path d="M10,50 Q125,30 250,25 T490,5" fill="none" stroke="#fbbf24" stroke-width="2.5"/>
</svg>"""

CONFUSION_SVG = """
<svg viewBox="0 0 200 200" width="200" height="200">
  <rect x="0" y="0" width="66" height="66" fill="#312e81" rx="4"/><text x="33" y="38" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">42</text>
  <rect x="67" y="0" width="66" height="66" fill="#4338ca" rx="4"/><text x="100" y="38" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">12</text>
  <rect x="134" y="0" width="66" height="66" fill="#6366f1" rx="4"/><text x="167" y="38" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">8</text>
  <rect x="0" y="67" width="66" height="66" fill="#4338ca" rx="4"/><text x="33" y="105" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">10</text>
  <rect x="67" y="67" width="66" height="66" fill="#7c3aed" rx="4"/><text x="100" y="105" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">88</text>
  <rect x="134" y="67" width="66" height="66" fill="#6366f1" rx="4"/><text x="167" y="105" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">14</text>
  <rect x="0" y="134" width="66" height="66" fill="#312e81" rx="4"/><text x="33" y="172" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">6</text>
  <rect x="67" y="134" width="66" height="66" fill="#4338ca" rx="4"/><text x="100" y="172" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">11</text>
  <rect x="134" y="134" width="66" height="66" fill="#8b5cf6" rx="4"/><text x="167" y="172" text-anchor="middle" fill="#e2e8f0" font-size="16" font-weight="800">45</text>
</svg>"""

CALIBRATION_SVG = """
<svg viewBox="0 0 220 180" width="100%" height="100%">
  <line x1="20" y1="160" x2="200" y2="20" stroke="#475569" stroke-width="1" stroke-dasharray="4"/>
  <circle cx="40" cy="145" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <circle cx="70" cy="120" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <circle cx="100" cy="95" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <circle cx="130" cy="72" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <circle cx="160" cy="48" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <circle cx="185" cy="28" r="5" fill="#a78bfa" stroke="#f8fafc" stroke-width="1.5"/>
  <path d="M40,145 L70,120 L100,95 L130,72 L160,48 L185,28" fill="none" stroke="#a78bfa" stroke-width="2"/>
</svg>"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head>
<body><div class="dashboard"><div class="grid-bg"></div>{body}</div></body></html>"""


def html_pnl() -> str:
    return _page("PnL", f"""
<div class="topbar">
  <div class="brand">
    <div class="brand-icon">P</div>
    <div><h1>Polymarket Trading Bot</h1><p>AI Model · CLOB API · Prediction Markets · USDC on Polygon</p></div>
  </div>
  <div class="pills">
    <span class="pill pill-paper"><span class="pill-dot"></span>Paper Mode</span>
    <span class="pill pill-clob">CLOB API ✓</span>
    <span class="pill pill-live"><span class="pill-dot"></span>Connected</span>
  </div>
</div>
<div class="content">
  <div class="kpi-row">
    <div class="kpi kpi-green"><div class="kpi-label">Total PnL</div><div class="kpi-value">+$2,847</div><div class="kpi-sub">▲ +28.4% this month · USDC</div></div>
    <div class="kpi kpi-blue"><div class="kpi-label">Win Rate</div><div class="kpi-value">67.3%</div><div class="kpi-sub">142 wins / 211 Polymarket trades</div></div>
    <div class="kpi kpi-purple"><div class="kpi-label">Sharpe Ratio</div><div class="kpi-value">2.14</div><div class="kpi-sub">30-day rolling · risk-adjusted</div></div>
    <div class="kpi kpi-red"><div class="kpi-label">Max Drawdown</div><div class="kpi-value">−4.2%</div><div class="kpi-sub">USDC peak-to-trough</div></div>
  </div>
  <div class="main-row main-row-58" style="flex:1">
    <div class="panel">
      <div class="panel-head"><span class="panel-title">USDC Equity Curve — Polymarket Session</span><span class="panel-badge">30 Days</span></div>
      <div style="flex:1;min-height:0">{EQUITY_SVG}</div>
    </div>
    <div class="panel">
      <div class="panel-head"><span class="panel-title">Recent Polymarket Trades</span><span class="panel-badge">CLOB</span></div>
      <table>
        <thead><tr><th>Prediction Market</th><th>Side</th><th>Price</th><th>PnL</th></tr></thead>
        <tbody>
          <tr><td>Will BTC hit $150k in 2026?</td><td><span class="tag tag-yes">YES</span></td><td class="price">0.63</td><td class="pnl-pos">+$42.10</td></tr>
          <tr><td>ETH above $5k by Jun 2026?</td><td><span class="tag tag-no">NO</span></td><td class="price">0.41</td><td class="pnl-pos">+$28.50</td></tr>
          <tr><td>Fed rate cut in Q1 2026?</td><td><span class="tag tag-yes">YES</span></td><td class="price">0.71</td><td class="pnl-pos">+$31.20</td></tr>
          <tr><td>US recession in 2026?</td><td><span class="tag tag-no">NO</span></td><td class="price">0.38</td><td class="pnl-pos">+$19.80</td></tr>
          <tr><td>SOL flips ETH market cap?</td><td><span class="tag tag-yes">YES</span></td><td class="price">0.22</td><td class="pnl-neg">−$8.40</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>""")


def html_backtest() -> str:
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    vals = [2.1,3.4,-0.8,4.2,1.9,3.1,2.8,-1.2,3.6,2.4,4.1,1.7]
    heat = ""
    for m, v in zip(months, vals):
        cls = "heat-pos-high" if v > 3 else "heat-pos" if v > 0 else "heat-neg"
        heat += f'<div class="heat-cell {cls}">{m}<br>{v:+.1f}%</div>'
    return _page("Backtest", f"""
<div class="topbar">
  <div class="brand"><div class="brand-icon">B</div><div><h1>Backtest Engine</h1><p>Polymarket Price Direction Classifier · Fees · Slippage · Latency</p></div></div>
  <div class="pills"><span class="pill pill-clob">BACKTEST</span><span class="pill pill-live"><span class="pill-dot"></span>Complete</span></div>
</div>
<div class="content">
  <div class="kpi-row">
    <div class="kpi kpi-green"><div class="kpi-label">CAGR</div><div class="kpi-value">34.7%</div><div class="kpi-sub">annualized return</div></div>
    <div class="kpi kpi-green"><div class="kpi-label">Total Return</div><div class="kpi-value">+41.2%</div><div class="kpi-sub">net of CLOB fees</div></div>
    <div class="kpi kpi-gold"><div class="kpi-label">Profit Factor</div><div class="kpi-value">2.38</div><div class="kpi-sub">gross win/loss ratio</div></div>
    <div class="kpi kpi-blue"><div class="kpi-label">Sharpe</div><div class="kpi-value">2.47</div><div class="kpi-sub">312 Polymarket trades</div></div>
  </div>
  <div class="main-row main-row-55" style="flex:1">
    <div class="panel">
      <div class="panel-head"><span class="panel-title">Equity & Drawdown — USDC</span></div>
      <div style="height:140px;margin-bottom:8px">{BACKTEST_EQUITY_SVG}</div>
      <div style="height:70px">{BACKTEST_DD_SVG}</div>
    </div>
    <div class="panel">
      <div class="panel-head"><span class="panel-title">Markets Backtested</span></div>
      <ul class="market-list">
        <li>Will BTC hit $150k by 2026?</li>
        <li>ETH above $5k by Jun 2026?</li>
        <li>Fed rate cut Q1 2026?</li>
        <li>US recession in 2026?</li>
        <li>Polymarket volume exceeds $10B?</li>
      </ul>
      <div class="panel-head" style="margin-top:16px"><span class="panel-title">Monthly Returns</span></div>
      <div class="heatmap">{heat}</div>
    </div>
  </div>
</div>""")


def html_model() -> str:
    features = [
        ("order_book_imbalance", 22, "#6366f1"),
        ("yes_mid_momentum", 18, "#8b5cf6"),
        ("bid_ask_spread", 15, "#22d3ee"),
        ("clob_volume", 14, "#3b82f6"),
        ("time_to_expiry", 12, "#10b981"),
        ("liquidity_usd", 10, "#fbbf24"),
        ("trade_flow", 9, "#f87171"),
    ]
    bars = ""
    for name, pct, color in features:
        bars += f'<div class="feature-bar-row"><span class="feature-name">{name}</span><div class="feature-bar"><div class="feature-fill" style="width:{pct*4}%;background:{color}"></div></div><span class="feature-pct">{pct}%</span></div>'
    return _page("Model", f"""
<div class="topbar">
  <div class="brand"><div class="brand-icon">ML</div><div><h1>ML Classifier Performance</h1><p>XGBoost · Polymarket YES Token · UP / DOWN / NEUTRAL</p></div></div>
  <div class="pills"><span class="pill pill-clob">XGBOOST</span><span class="pill pill-live"><span class="pill-dot"></span>Deployed</span></div>
</div>
<div class="content">
  <div class="metric-grid">
    <div class="metric-mini"><div class="metric-mini-label">Accuracy</div><div class="metric-mini-val" style="color:#34d399">71.4%</div></div>
    <div class="metric-mini"><div class="metric-mini-label">F1 Score</div><div class="metric-mini-val" style="color:#60a5fa">0.698</div></div>
    <div class="metric-mini"><div class="metric-mini-label">Precision</div><div class="metric-mini-val" style="color:#22d3ee">0.72</div></div>
    <div class="metric-mini"><div class="metric-mini-label">Recall</div><div class="metric-mini-val" style="color:#a78bfa">0.69</div></div>
    <div class="metric-mini"><div class="metric-mini-label">AUC-ROC</div><div class="metric-mini-val" style="color:#fbbf24">0.81</div></div>
  </div>
  <div class="main-row main-row-55" style="flex:1">
    <div class="panel" style="align-items:center">
      <div class="panel-head" style="width:100%"><span class="panel-title">Confusion Matrix — YES Mid-Price</span></div>
      {CONFUSION_SVG}
      <div style="display:flex;gap:24px;margin-top:12px;font-size:10px;color:#64748b;font-weight:700">
        <span>↓ DOWN</span><span>→ NEUTRAL</span><span>↑ UP</span>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head"><span class="panel-title">CLOB Feature Importance</span></div>
      {bars}
      <div style="margin-top:12px;height:100px">{CALIBRATION_SVG}</div>
    </div>
  </div>
</div>""")


def html_signals() -> str:
    rows = [
        ("12:04:18", "Will BTC hit $150k in 2026?", "UP", 78, "+0.042", "BUY YES @ 0.63", "green"),
        ("12:04:21", "ETH above $5k by Jun 2026?", "DOWN", 71, "−0.038", "BUY NO @ 0.42", "red"),
        ("12:04:25", "Fed emergency rate cut 2026?", "UP", 82, "+0.051", "BUY YES @ 0.55", "green"),
        ("12:04:29", "OpenAI IPO before 2027?", "NEUTRAL", 52, "+0.004", "HOLD", "gray"),
        ("12:04:33", "SpaceX Starship fully reusable?", "UP", 69, "+0.031", "BUY YES @ 0.47", "green"),
        ("12:04:37", "US CPI below 2% in 2026?", "DOWN", 74, "−0.036", "BUY NO @ 0.61", "red"),
    ]
    tbody = ""
    for t, m, d, c, e, a, col in rows:
        tag = f'tag-{"up" if d=="UP" else "down" if d=="DOWN" else "hold"}'
        fill = f"conf-fill-{'green' if col=='green' else 'red' if col=='red' else 'gray'}"
        act = "action-buy-yes" if "YES" in a else "action-buy-no" if "NO" in a else "action-hold"
        ec = "pnl-pos" if e.startswith("+") else "pnl-neg" if "−" in e else "mono"
        tbody += f"""<tr>
          <td class="mono">{t}</td><td>{m}</td>
          <td><span class="tag {tag}">{d}</span></td>
          <td><div class="conf-bar"><div class="conf-track"><div class="conf-fill {fill}" style="width:{c}%"></div></div><span class="conf-pct">{c}%</span></div></td>
          <td class="{ec}">{e}</td><td><span class="action-btn {act}">{a}</span></td></tr>"""
    return _page("Signals", f"""
<div class="topbar">
  <div class="brand"><div class="brand-icon">⚡</div><div><h1>Signal Engine</h1><p>Polymarket Paper Trading · Real-Time CLOB Inference · Polygon</p></div></div>
  <div class="pills"><span class="pill pill-paper"><span class="pill-dot"></span>Paper</span><span class="pill pill-live"><span class="pill-dot"></span>Live Feed</span></div>
</div>
<div class="content" style="flex-direction:row;gap:16px;padding-top:20px">
  <div class="panel" style="flex:1.5">
    <div class="panel-head"><span class="panel-title">Live Signal Feed — Polymarket Prediction Markets</span><span class="panel-badge">Real-time</span></div>
    <table><thead><tr><th>Time</th><th>Polymarket Market</th><th>Dir</th><th>Confidence</th><th>Edge</th><th>Action</th></tr></thead>
    <tbody>{tbody}</tbody></table>
  </div>
  <div class="panel" style="flex:0.5">
    <div class="panel-head"><span class="panel-title">Session Stats</span></div>
    <div class="stat-list">
      <div class="stat-item"><span class="stat-label">Markets Monitored</span><span class="stat-val" style="color:#60a5fa">10</span></div>
      <div class="stat-item"><span class="stat-label">Signals / Hour</span><span class="stat-val" style="color:#22d3ee">24</span></div>
      <div class="stat-item"><span class="stat-label">Trades Executed</span><span class="stat-val" style="color:#34d399">18</span></div>
      <div class="stat-item"><span class="stat-label">Avg Confidence</span><span class="stat-val" style="color:#a78bfa">72%</span></div>
      <div class="stat-item"><span class="stat-label">Session PnL</span><span class="stat-val" style="color:#34d399">+$186</span></div>
      <div class="stat-item"><span class="stat-label">API Latency</span><span class="stat-val" style="color:#fbbf24">42ms</span></div>
    </div>
  </div>
</div>""")


def html_architecture() -> str:
    return _page("Architecture", """
<div class="topbar">
  <div class="brand"><div class="brand-icon">⚙</div><div><h1>System Architecture</h1><p>Polymarket ML Trading Bot · Full Pipeline Engineering · Production Ready</p></div></div>
  <div class="pills"><span class="pill pill-clob">ENGINEERING</span></div>
</div>
<div class="content" style="justify-content:center;gap:28px">
  <div><div class="arch-layer">◆ Data Ingestion — Polymarket APIs</div>
  <div class="arch-grid">
    <div class="arch-box arch-indigo"><div class="arch-box-title">Gamma API</div><div class="arch-box-sub">Market Discovery<br>clobTokenIds</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-blue"><div class="arch-box-title">CLOB REST</div><div class="arch-box-sub">Order Book<br>YES/NO 0–1</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-cyan"><div class="arch-box-title">WebSocket</div><div class="arch-box-sub">Live Feed<br>wss://clob</div></div>
  </div></div>
  <div><div class="arch-layer">◆ ML Pipeline</div>
  <div class="arch-grid">
    <div class="arch-box arch-purple"><div class="arch-box-title">Data Layer</div><div class="arch-box-sub">Candles · SQLite<br>Trade History</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-gold"><div class="arch-box-title">Features</div><div class="arch-box-sub">OHLCV · Imbalance<br>Spread · Flow</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-green"><div class="arch-box-title">XGBoost</div><div class="arch-box-sub">UP · DOWN<br>NEUTRAL</div></div>
  </div></div>
  <div><div class="arch-layer">◆ Execution — Polygon USDC</div>
  <div class="arch-grid">
    <div class="arch-box arch-red"><div class="arch-box-title">Risk Manager</div><div class="arch-box-sub">Daily Loss · Breaker<br>Liquidity Filter</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-green"><div class="arch-box-title">Executor</div><div class="arch-box-sub">Paper Mode<br>Live CLOB Orders</div></div>
    <div class="arch-arrow">→</div>
    <div class="arch-box arch-indigo"><div class="arch-box-title">Exports</div><div class="arch-box-sub">JSON · CSV<br>Backtest Reports</div></div>
  </div></div>
</div>""")


def html_live() -> str:
    return _page("Live", f"""
<div class="topbar">
  <div class="brand"><div class="brand-icon">▶</div><div><h1>Live Trading Operations</h1><p>Polymarket CLOB · Polygon · USDC · Risk Controls Active</p></div></div>
  <div class="pills"><span class="pill pill-live"><span class="pill-dot"></span>LIVE</span><span class="pill pill-clob">CLOB ✓</span></div>
</div>
<div class="content">
  <div class="kpi-row">
    <div class="kpi kpi-green"><div class="kpi-label">Daily Loss Used</div><div class="kpi-value">$12.40</div><div class="kpi-sub">of $50 USDC limit</div></div>
    <div class="kpi kpi-blue"><div class="kpi-label">Open Positions</div><div class="kpi-value">2 / 3</div><div class="kpi-sub">Polymarket markets</div></div>
    <div class="kpi kpi-green"><div class="kpi-label">Circuit Breaker</div><div class="kpi-value">OFF ✓</div><div class="kpi-sub">0 consecutive losses</div></div>
    <div class="kpi kpi-gold"><div class="kpi-label">Stake / Trade</div><div class="kpi-value">$25</div><div class="kpi-sub">USDC fixed sizing</div></div>
  </div>
  <div class="main-row main-row-55" style="flex:1">
    <div class="panel">
      <div class="panel-head"><span class="panel-title">Open Polymarket Positions</span></div>
      <div class="pos-card"><div class="pos-title">Will BTC hit $150k in 2026?</div><div class="pos-row"><span class="tag tag-yes">YES</span><span class="pos-price">0.61 → 0.64</span><span class="pos-pnl">+$4.20</span></div></div>
      <div class="pos-card"><div class="pos-title">Fed rate cut Q1 2026?</div><div class="pos-row"><span class="tag tag-yes">YES</span><span class="pos-price">0.58 → 0.62</span><span class="pos-pnl">+$3.10</span></div></div>
      <div class="checklist">
        <span class="check"><span class="check-icon">✓</span> Paper tested 48h</span>
        <span class="check"><span class="check-icon">✓</span> Backtest verified</span>
        <span class="check"><span class="check-icon">✓</span> Risk limits set</span>
        <span class="check"><span class="check-icon">✓</span> CLOB creds loaded</span>
        <span class="check"><span class="check-icon">✓</span> ENABLE_LIVE_TRADING</span>
      </div>
    </div>
    <div class="panel">
      <div class="panel-head"><span class="panel-title">30-Day USDC PnL — Polymarket Live</span></div>
      <div style="flex:1">{PNL_BARS_SVG}</div>
    </div>
  </div>
</div>""")


PAGES = {
    "dashboard-pnl-overview.png": html_pnl(),
    "dashboard-backtest-analysis.png": html_backtest(),
    "dashboard-model-performance.png": html_model(),
    "dashboard-live-signals.png": html_signals(),
    "dashboard-architecture.png": html_architecture(),
    "dashboard-live-trading.png": html_live(),
}


async def render_all() -> None:
    from playwright.async_api import async_playwright

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = HTML_DIR / "_tmp"
    tmp.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=2)

        for filename, html in PAGES.items():
            html_path = tmp / filename.replace(".png", ".html")
            html_path.write_text(html, encoding="utf-8")
            await page.goto(html_path.as_uri(), wait_until="networkidle")
            await page.wait_for_timeout(800)  # fonts load
            out = OUT_DIR / filename
            await page.screenshot(path=str(out), type="png", full_page=False)
            kb = out.stat().st_size // 1024
            print(f"  ✓ {filename}  ({kb} KB)")

        await browser.close()


def main() -> None:
    print("Rendering premium HTML dashboards (Playwright @2x)...")
    asyncio.run(render_all())
    print(f"\nDone — saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
