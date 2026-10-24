"""
MorphAPI Live Telemetry Broadcaster
Manages WebSocket connections and recent event memory ring-buffer.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, List
from fastapi import WebSocket

logger = logging.getLogger("morphapi.telemetry")

class TelemetryBroadcaster:
    def __init__(self, max_recent: int = 50):
        self._active_connections: List[WebSocket] = []
        self._recent_events: List[dict[str, Any]] = []
        self._max_recent = max_recent
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self._active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self._active_connections)}")

    async def emit_event(
        self,
        event_type: str,
        endpoint_id: str,
        message: str,
        details: dict[str, Any] | None = None,
        latency_ms: int | None = None,
        request_id: str | None = None,
    ):
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint_id": endpoint_id,
            "message": message,
            "latency_ms": latency_ms,
            "request_id": request_id,
            "details": details or {},
        }

        async with self._lock:
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_recent:
                self._recent_events.pop(0)

        # Broadcast to all live WebSocket subscribers
        dead_connections = []
        for connection in list(self._active_connections):
            try:
                await connection.send_json(event)
            except Exception as e:
                logger.warning(f"Failed to send telemetry event to client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def get_recent_events(self) -> list[dict[str, Any]]:
        async with self._lock:
            return list(reversed(self._recent_events))

telemetry_hub = TelemetryBroadcaster()
