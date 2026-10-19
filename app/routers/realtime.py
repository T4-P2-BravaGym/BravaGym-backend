"""Websocket for live free spots (HU-16): WS /api/v1/ws/sessions/{session_id}.

Public, like the schedule. The server only sends messages; the client just listens.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.realtime import session_updates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/sessions/{session_id}")
async def session_updates_ws(websocket: WebSocket, session_id: int) -> None:
    await session_updates.connect(session_id, websocket)
    try:
        # Wait until the client leaves; any text it sends is ignored
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("A client stopped watching session %s", session_id)
    finally:
        session_updates.disconnect(session_id, websocket)
