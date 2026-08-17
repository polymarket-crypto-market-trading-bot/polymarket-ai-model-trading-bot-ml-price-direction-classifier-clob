FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/db logs exports models/artifacts

ENV PYTHONPATH=/app
ENV BOT_MODE=paper
ENV ENABLE_LIVE_TRADING=false

CMD ["python", "-m", "bot", "paper", "--interval", "60"]
