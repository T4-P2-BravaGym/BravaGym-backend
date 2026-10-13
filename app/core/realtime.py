"""Live updates over websockets (HU-16): who is watching each class session.

The booking services are sync and run in a worker thread, while websockets live in the
event loop. notify_from_sync() is the bridge: it schedules the message on that loop.
"""
import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SessionConnectionManager:
    """Keeps the open websockets of each class session and tells them when it changes."""

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, session_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._loop = asyncio.get_running_loop()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: int, websocket: WebSocket) -> None:
        watchers = self._connections.get(session_id)
        if watchers is None:
            return
        watchers.discard(websocket)
        if not watchers:
            del self._connections[session_id]

    def watchers(self, session_id: int) -> int:
        return len(self._connections.get(session_id, ()))

    async def broadcast(self, session_id: int, message: dict) -> None:
        for websocket in list(self._connections.get(session_id, ())):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                # The browser already closed this tab: forget the connection
                logger.info("Dropping a closed websocket of session %s", session_id)
                self.disconnect(session_id, websocket)

    def notify_from_sync(self, session_id: int) -> None:
        """Tell everyone watching this session that its free spots or waitlist changed."""
        if self._loop is None or self.watchers(session_id) == 0:
            return
        message = {"type": "session_updated", "session_id": session_id}
        asyncio.run_coroutine_threadsafe(self.broadcast(session_id, message), self._loop)


session_updates = SessionConnectionManager()