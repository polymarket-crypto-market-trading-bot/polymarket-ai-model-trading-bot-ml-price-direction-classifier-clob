"""Model evaluation metrics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)

from models.classifier import PriceDirectionClassifier
from utils.logging import get_logger

logger = get_logger(__name__)


def evaluate_classifier(
    classifier: PriceDirectionClassifier,
    X: np.ndarray,
    y: np.ndarray,
) -> dict:
    y_pred = classifier.model.predict(X)
    y_proba = classifier.model.predict_proba(X)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y, y_pred, average="weighted", zero_division=0
    )

    metrics = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix": confusion_matrix(y, y_pred).tolist(),
        "classification_report": classification_report(
            y, y_pred, zero_division=0, output_dict=True
        ),
    }

    try:
        prob_true, prob_pred = calibration_curve(
            (y == 2).astype(int),
            y_proba[:, 2],
            n_bins=5,
            strategy="uniform",
        )
        metrics["calibration"] = {
            "prob_true": prob_true.tolist(),
            "prob_pred": prob_pred.tolist(),
        }
    except ValueError:
        metrics["calibration"] = {}

    logger.info(
        "Eval — accuracy=%.3f f1=%.3f precision=%.3f recall=%.3f",
        metrics["accuracy"],
        metrics["f1"],
        metrics["precision"],
        metrics["recall"],
    )
    return metrics


def save_evaluation_plots(metrics: dict, output_dir: Path, prefix: str = "eval") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cm = np.array(metrics.get("confusion_matrix", [[0]]))
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title("Confusion Matrix")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(output_dir / f"{prefix}_confusion_matrix.png")
    plt.close(fig)

    calibration = metrics.get("calibration") or {}
    if calibration.get("prob_true"):
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.plot(calibration["prob_pred"], calibration["prob_true"], marker="o")
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
        ax.set_title("Calibration Curve (UP class)")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Fraction of positives")
        fig.tight_layout()
        fig.savefig(output_dir / f"{prefix}_calibration.png")
        plt.close(fig)
