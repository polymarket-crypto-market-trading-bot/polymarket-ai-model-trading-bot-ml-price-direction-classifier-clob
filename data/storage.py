"""SQLite storage for candles, trades, and predictions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import Settings
from utils.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class CandleRow(Base):
    __tablename__ = "candles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(String(128), index=True)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    buy_volume = Column(Float)
    sell_volume = Column(Float)
    spread = Column(Float, nullable=True)
    order_book_imbalance = Column(Float, nullable=True)
    liquidity_usd = Column(Float, nullable=True)


class TradeRow(Base):
    __tablename__ = "trades_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(String(16))
    market_id = Column(String(64))
    token_id = Column(String(128))
    side = Column(String(8))
    price = Column(Float)
    size = Column(Float)
    pnl = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text, nullable=True)


class PredictionRow(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(String(128), index=True)
    timestamp = Column(DateTime, index=True)
    direction = Column(String(16))
    confidence = Column(Float)
    expected_edge = Column(Float)
    features_json = Column(Text, nullable=True)


class Storage:
    def __init__(self, settings: Settings) -> None:
        db_url = settings.database_url
        if db_url.startswith("sqlite:///"):
            path = Path(db_url.replace("sqlite:///", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(db_url, future=True)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def save_candles(self, token_id: str, candles: pd.DataFrame) -> int:
        if candles.empty:
            return 0
        rows = []
        for _, row in candles.iterrows():
            rows.append(
                CandleRow(
                    token_id=token_id,
                    timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
                    buy_volume=float(row.get("buy_volume", 0)),
                    sell_volume=float(row.get("sell_volume", 0)),
                    spread=float(row["spread"]) if "spread" in row and pd.notna(row["spread"]) else None,
                    order_book_imbalance=float(row["order_book_imbalance"])
                    if "order_book_imbalance" in row and pd.notna(row["order_book_imbalance"])
                    else None,
                    liquidity_usd=float(row["liquidity_usd"])
                    if "liquidity_usd" in row and pd.notna(row["liquidity_usd"])
                    else None,
                )
            )
        with Session(self.engine) as session:
            session.add_all(rows)
            session.commit()
        return len(rows)

    def load_candles(self, token_id: str, limit: int = 5000) -> pd.DataFrame:
        query = text(
            """
            SELECT timestamp, open, high, low, close, volume, buy_volume, sell_volume,
                   spread, order_book_imbalance, liquidity_usd
            FROM candles
            WHERE token_id = :token_id
            ORDER BY timestamp DESC
            LIMIT :limit
            """
        )
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"token_id": token_id, "limit": limit})
        if df.empty:
            return df
        return df.sort_values("timestamp").reset_index(drop=True)

    def log_trade(
        self,
        *,
        mode: str,
        market_id: str,
        token_id: str,
        side: str,
        price: float,
        size: float,
        pnl: float | None = None,
        metadata: dict | None = None,
    ) -> None:
        with Session(self.engine) as session:
            session.add(
                TradeRow(
                    mode=mode,
                    market_id=market_id,
                    token_id=token_id,
                    side=side,
                    price=price,
                    size=size,
                    pnl=pnl,
                    metadata_json=json.dumps(metadata or {}),
                )
            )
            session.commit()

    def log_prediction(
        self,
        *,
        token_id: str,
        direction: str,
        confidence: float,
        expected_edge: float,
        features: dict | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        with Session(self.engine) as session:
            session.add(
                PredictionRow(
                    token_id=token_id,
                    timestamp=timestamp or datetime.utcnow(),
                    direction=direction,
                    confidence=confidence,
                    expected_edge=expected_edge,
                    features_json=json.dumps(features or {}),
                )
            )
            session.commit()

    def get_trades_df(self, mode: str | None = None) -> pd.DataFrame:
        query = "SELECT * FROM trades_log"
        params: dict = {}
        if mode:
            query += " WHERE mode = :mode"
            params["mode"] = mode
        query += " ORDER BY timestamp"
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)

    def get_predictions_df(self, token_id: str | None = None) -> pd.DataFrame:
        query = "SELECT * FROM predictions"
        params: dict = {}
        if token_id:
            query += " WHERE token_id = :token_id"
            params["token_id"] = token_id
        query += " ORDER BY timestamp"
        with self.engine.connect() as conn:
            return pd.read_sql(text(query), conn, params=params)
