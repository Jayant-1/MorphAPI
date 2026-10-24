"""
MorphAPI Telemetry Routes & WebSocket Stream
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.database import get_telemetry_summary
from backend.app.services.telemetry import telemetry_hub

logger = logging.getLogger("morphapi.routes.telemetry")
router = APIRouter(tags=["Telemetry"])


@router.get("/api/v1/telemetry")
async def get_telemetry_data():
    """
    Returns aggregated metrics, active/degraded endpoint counts, and recent event logs.
    """
    summary = await get_telemetry_summary()
    recent_events = await telemetry_hub.get_recent_events()
    summary["recent_events"] = recent_events
    return summary


@router.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket):
    """
    Real-time streaming WebSocket endpoint for Next.js Mission Control dashboard.
    """
    await telemetry_hub.connect(websocket)
    try:
        while True:
            # Keep connection open and receive optional ping/pong messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        telemetry_hub.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        telemetry_hub.disconnect(websocket)
