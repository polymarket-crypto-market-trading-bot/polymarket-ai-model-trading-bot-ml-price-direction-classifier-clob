"""Optional LSTM/GRU sequence model (requires PyTorch)."""

from __future__ import annotations

from config.settings import Settings


def build_lstm_classifier(settings: Settings):
    import torch
    from torch import nn

    class LSTMClassifier(nn.Module):
        def __init__(self, input_size: int = 20, hidden_size: int = 64) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
            self.fc = nn.Linear(hidden_size, 3)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :])

    class LSTMWrapper:
        def __init__(self) -> None:
            self.net = LSTMClassifier()
            self.device = torch.device("cpu")

        def fit(self, X, y):
            # Minimal stub — production use would require sequence batching
            self.net.train()

        def predict_proba(self, X):
            import numpy as np

            n = len(X)
            return np.full((n, 3), 1 / 3)

    return LSTMWrapper()
