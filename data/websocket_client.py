"""WebSocket subscriber for live CLOB updates."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

import websocket

from config.settings import Settings
from utils.logging import get_logger

logger = get_logger(__name__)


class ClobWebSocketClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ws_url = settings.clob_ws_url
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._token_ids: list[str] = []
        self._on_message_cb: Callable[[dict[str, Any]], None] | None = None

    def subscribe(
        self,
        token_ids: list[str],
        on_message: Callable[[dict[str, Any]], None],
    ) -> None:
        self._token_ids = token_ids
        self._on_message_cb = on_message
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._ws:
            self._ws.close()

    def _run(self) -> None:
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                logger.warning("WebSocket error: %s", exc)
            if self._running:
                time.sleep(5)

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        logger.info("WebSocket connected")
        payload = {
            "type": "market",
            "assets_ids": self._token_ids,
        }
        ws.send(json.dumps(payload))

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        try:
            data = json.loads(message)
            if self._on_message_cb:
                if isinstance(data, list):
                    for item in data:
                        self._on_message_cb(item)
                else:
                    self._on_message_cb(data)
        except json.JSONDecodeError:
            logger.debug("Non-JSON websocket message ignored")

    def _on_error(self, _ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.warning("WebSocket error event: %s", error)

    def _on_close(
        self,
        _ws: websocket.WebSocketApp,
        status_code: int | None,
        msg: str | None,
    ) -> None:
        logger.info("WebSocket closed: %s %s", status_code, msg)
