import asyncio
import json
import os
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .dependencies import get_broadcaster, get_stores, get_websocket_manager
from .models import AgentEvent, EventsResponse

app = FastAPI(title="Ikoma Dashboard", version="0.1.0")

# Set up static files and templates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    broadcaster: Any = Depends(get_broadcaster),
    ws_manager: Any = Depends(get_websocket_manager),
) -> None:
    """WebSocket endpoint for real-time dashboard updates"""
    await ws_manager.connect(websocket)

    # Send recent events on connect
    recent_events = broadcaster.get_recent_events()
    for event in recent_events[-10:]:  # Last 10 events
        await websocket.send_text(event.model_dump_json())

    # Subscribe to new events
    def on_new_event(event: AgentEvent) -> None:
        asyncio.create_task(ws_manager.broadcast_event(event))

    broadcaster.subscribe("all", on_new_event)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        # Note: We can't easily remove the callback, but it's not critical


@app.get("/api/v1/events", response_model=EventsResponse)
async def get_events(
    since: datetime | None = Query(None),
    limit: int = Query(50, le=500),
    broadcaster: Any = Depends(get_broadcaster),
) -> EventsResponse:
    """Fallback polling endpoint for events"""
    events = broadcaster.get_recent_events(since)

    # Apply limit
    events = events[-limit:] if len(events) > limit else events

    return EventsResponse(
        events=events,
        latest_timestamp=events[-1].timestamp if events else datetime.utcnow(),
        has_more=len(broadcaster.event_cache) > limit,
    )


@app.get("/api/v1/plans")
async def get_plans(stores: Any = Depends(get_stores)) -> dict[str, Any]:
    """Get plans from existing SQLite checkpointer"""
    try:
        # TODO: Implement actual plan retrieval from checkpointer
        # checkpointer = stores["checkpointer"]
        plans: list[Any] = []

        # For now, return a placeholder response
        return {"plans": plans}
    except Exception as e:
        return {"error": f"Failed to retrieve plans: {e}"}


@app.get("/api/v1/trace/{execution_id}")
async def get_trace(execution_id: str, stores: Any = Depends(get_stores)) -> dict[str, Any]:
    """Get execution trace from existing stores"""
    try:
        vector_store = stores["vector_store"]

        # Search for execution context
        results = vector_store.search(
            namespace=("executions", execution_id), query="execution trace", limit=10
        )

        return {"execution_id": execution_id, "trace_events": results}
    except Exception as e:
        return {"error": f"Failed to retrieve trace: {e}"}


@app.get("/")
async def dashboard(request: Request) -> Any:
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}
