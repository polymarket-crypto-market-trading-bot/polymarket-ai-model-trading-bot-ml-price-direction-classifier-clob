"""ML classifiers for price direction."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from config.settings import Settings
from features.pipeline import INV_DIRECTION_MAP, FeaturePipeline
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DirectionPrediction:
    direction: str
    confidence: float
    expected_edge: float
    probabilities: dict[str, float]


class PriceDirectionClassifier:
    def __init__(self, settings: Settings, pipeline: FeaturePipeline) -> None:
        self.settings = settings
        self.pipeline = pipeline
        self.model: Any = None
        self.classes_: list[str] = ["DOWN", "NEUTRAL", "UP"]

    def build_model(self) -> Any:
        if self.settings.model_type == "lstm":
            try:
                from models.lstm_model import build_lstm_classifier

                return build_lstm_classifier(self.settings)
            except ImportError:
                logger.warning("PyTorch not installed; falling back to XGBoost")
        return XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=3,
            random_state=42,
            n_jobs=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = self.build_model()
        self.model.fit(X, y)

    def predict_one(self, row: pd.Series) -> DirectionPrediction:
        if self.model is None:
            raise RuntimeError("Model not trained or loaded")

        df = pd.DataFrame([row])
        featured = self.pipeline.transform(df)
        if featured.empty:
            return DirectionPrediction("NEUTRAL", 0.0, 0.0, {"DOWN": 0.33, "NEUTRAL": 0.34, "UP": 0.33})

        X = self.pipeline.scale(featured)
        proba = self.model.predict_proba(X)[0]
        class_idx = int(np.argmax(proba))
        direction = INV_DIRECTION_MAP.get(class_idx, self.classes_[class_idx])
        confidence = float(proba[class_idx])
        expected_edge = float(proba[2] - proba[0])
        probabilities = {
            self.classes_[i]: float(proba[i]) for i in range(len(proba))
        }
        return DirectionPrediction(direction, confidence, expected_edge, probabilities)

    def predict_batch(self, df: pd.DataFrame) -> list[DirectionPrediction]:
        featured = self.pipeline.transform(df)
        if featured.empty or self.model is None:
            return []
        X = self.pipeline.scale(featured)
        probas = self.model.predict_proba(X)
        results: list[DirectionPrediction] = []
        for proba in probas:
            class_idx = int(np.argmax(proba))
            direction = INV_DIRECTION_MAP.get(class_idx, self.classes_[class_idx])
            confidence = float(proba[class_idx])
            expected_edge = float(proba[2] - proba[0])
            probabilities = {
                self.classes_[i]: float(proba[i]) for i in range(len(proba))
            }
            results.append(
                DirectionPrediction(direction, confidence, expected_edge, probabilities)
            )
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": self.model,
            "pipeline": self.pipeline,
            "settings_snapshot": {
                "model_type": self.settings.model_type,
                "feature_windows": self.settings.feature_windows,
            },
        }
        with path.open("wb") as f:
            pickle.dump(payload, f)
        meta = {
            "model_type": self.settings.model_type,
            "classes": self.classes_,
            "feature_columns": self.pipeline.feature_columns,
        }
        path.with_suffix(".json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, path: Path, settings: Settings) -> PriceDirectionClassifier:
        with path.open("rb") as f:
            payload = pickle.load(f)
        pipeline = payload["pipeline"]
        classifier = cls(settings=settings, pipeline=pipeline)
        classifier.model = payload["model"]
        return classifier


class FallbackClassifier(PriceDirectionClassifier):
    """Simple momentum baseline when no trained model exists."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model = RandomForestClassifier(n_estimators=50, random_state=42)
        self.model.fit(X, y)
