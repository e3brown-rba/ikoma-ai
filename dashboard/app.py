import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import escape
from pydantic import BaseModel
try:
    from sse_starlette import EventSourceResponse  # type: ignore[import-untyped,unused-ignore]
except ImportError:
    # Fallback for environments where sse_starlette is not available
    from starlette.responses import StreamingResponse as EventSourceResponse

from dashboard.metrics import metrics_router
from tools.citation_manager import ProductionCitationManager

# Global state for agent configuration and demo management
agent_config: dict[str, Any] = {
    "internet_enabled": True,
    "active_agents": {},
    "execution_status": "idle",
}

# Demo management
demo_processes: dict[str, subprocess.Popen] = {}
demo_status: dict[str, dict[str, Any]] = {}

# SSE connection management
sse_connections: list[dict[str, Any]] = []


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Application lifespan manager"""
    # Startup
    print("Starting HTMX Dashboard...")
    yield
    # Shutdown - cleanup demo processes
    print("Shutting down HTMX Dashboard...")
    for process in demo_processes.values():
        if process.poll() is None:  # Still running
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


app = FastAPI(lifespan=lifespan)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Set up templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include metrics router
app.include_router(metrics_router)

# Simple in-memory cache for citation HTML, keyed by conversation_id
_citation_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 60  # seconds


# Pydantic models for type safety
class AgentCommand(BaseModel):
    action: str
    agent_id: str | None = None
    parameters: dict = {}

    def validate_action(self) -> str:
        allowed_actions = ["start", "stop", "pause", "resume"]
        if self.action not in allowed_actions:
            raise ValueError("Invalid action")
        return self.action


class DemoCommand(BaseModel):
    demo_type: str  # 'online', 'offline', 'continuous'
    agent_id: str | None = None


class InternetToggle(BaseModel):
    enabled: bool


async def broadcast_state_change(event_data: dict) -> None:
    """Broadcast state changes to all SSE connections"""
    message = {
        "event": "state_change",
        "data": json.dumps(event_data),
        "id": str(int(time.time() * 1000)),
    }

    # Send to all active SSE connections
    for connection in sse_connections[
        :
    ]:  # Copy list to avoid modification during iteration
        try:
            await connection["queue"].put(message)
        except Exception:
            # Remove dead connections
            sse_connections.remove(connection)


def launch_demo(demo_type: str, agent_id: str) -> subprocess.Popen:
    """Launch a demo process and return the process object"""
    env = os.environ.copy()
    env["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    env["IKOMA_DASHBOARD_MODE"] = "true"  # Signal to agent that dashboard is active

    # Build the command
    cmd = [sys.executable, "-m", "agent.agent", "--demo", demo_type]

    # Start the process
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    # Store process info
    demo_processes[agent_id] = process
    demo_status[agent_id] = {
        "type": demo_type,
        "status": "starting",
        "start_time": datetime.now().isoformat(),
        "output": [],
        "error": None,
    }

    # Start monitoring thread
    def monitor_demo() -> None:
        try:
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        demo_status[agent_id]["output"].append(line.strip())
                        # Store output for now, will be retrieved via polling
                        print(f"Demo output: {line.strip()}")

            # Process finished
            demo_status[agent_id]["status"] = "completed"
            demo_status[agent_id]["end_time"] = datetime.now().isoformat()
            print(f"Demo {agent_id} completed")

        except Exception as e:
            demo_status[agent_id]["status"] = "error"
            demo_status[agent_id]["error"] = str(e)
            print(f"Demo {agent_id} error: {e}")

    monitor_thread = threading.Thread(target=monitor_demo, daemon=True)
    monitor_thread.start()

    return process


@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request) -> HTMLResponse:
    """Render the main dashboard with three-panel layout."""
    return templates.TemplateResponse(
        request, "dashboard.html", {"agent_config": agent_config}
    )


@app.get("/agents/list", response_class=HTMLResponse)
def get_agents_list(request: Request) -> HTMLResponse:
    """HTMX endpoint for agent list panel."""
    # Combine mock agents with active demo processes
    agents = [
        {
            "id": "agent-1",
            "name": "Research Agent",
            "status": "running",
            "last_activity": datetime.now().strftime("%H:%M:%S"),
            "progress": 75,
        },
        {
            "id": "agent-2",
            "name": "Planning Agent",
            "status": "idle",
            "last_activity": datetime.now().strftime("%H:%M:%S"),
            "progress": 0,
        },
    ]

    # Add active demo processes
    for agent_id, status in demo_status.items():
        agents.append(
            {
                "id": agent_id,
                "name": f"{status['type'].title()} Demo",
                "status": status["status"],
                "last_activity": status.get("start_time", ""),
                "progress": 50 if status["status"] == "running" else 0,
                "is_demo": True,
                "demo_type": status["type"],
            }
        )

    return templates.TemplateResponse(request, "agents_list.html", {"agents": agents})


@app.get("/agent-details/{agent_id}", response_class=HTMLResponse)
def get_agent_details(request: Request, agent_id: str) -> HTMLResponse:
    """HTMX endpoint for agent details panel."""
    # Check if this is a demo agent
    if agent_id in demo_status:
        demo_info = demo_status[agent_id]
        agent_details = {
            "id": agent_id,
            "name": f"{demo_info['type'].title()} Demo",
            "status": demo_info["status"],
            "current_step": f"Running {demo_info['type']} demo",
            "progress": 50 if demo_info["status"] == "running" else 0,
            "execution_time": "00:05:30",
            "steps_completed": 3,
            "total_steps": 4,
            "is_demo": True,
            "demo_type": demo_info["type"],
            "output": demo_info.get("output", [])[-10:],  # Last 10 lines
            "error": demo_info.get("error"),
        }
    else:
        # Mock agent details - replace with actual agent data
        agent_details = {
            "id": agent_id,
            "name": f"Agent {agent_id}",
            "status": "running",
            "current_step": "Analyzing research data",
            "progress": 75,
            "execution_time": "00:05:30",
            "steps_completed": 3,
            "total_steps": 4,
        }

    return templates.TemplateResponse(
        request, "agent_details.html", {"agent": agent_details}
    )


@app.get("/agent-stream")
async def stream_agent_execution() -> EventSourceResponse:
    """Real-time agent execution streaming via SSE."""

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        queue: asyncio.Queue = asyncio.Queue()
        connection = {"queue": queue}
        sse_connections.append(connection)

        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps(
                    {
                        "message": "SSE connection established",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            }

            # Keep connection alive and stream events
            while True:
                try:
                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except TimeoutError:
                    # Send keepalive
                    yield {
                        "event": "keepalive",
                        "data": json.dumps({"timestamp": datetime.now().isoformat()}),
                    }

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
        finally:
            if connection in sse_connections:
                sse_connections.remove(connection)

    return EventSourceResponse(event_generator())


@app.post("/demo/launch")
async def launch_demo_endpoint(command: DemoCommand) -> dict[str, Any]:
    """Launch a demo agent."""
    try:
        agent_id = command.agent_id or f"demo-{command.demo_type}-{int(time.time())}"

        # Launch the demo
        launch_demo(command.demo_type, agent_id)

        # Broadcast demo start
        await broadcast_state_change(
            {
                "event": "demo_started",
                "agent_id": agent_id,
                "demo_type": command.demo_type,
            }
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "demo_type": command.demo_type,
            "message": f"Demo {command.demo_type} started",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to launch demo: {str(e)}"
        ) from e


@app.post("/demo/stop/{agent_id}")
async def stop_demo(agent_id: str) -> dict[str, Any]:
    """Stop a running demo."""
    try:
        if agent_id in demo_processes:
            process = demo_processes[agent_id]
            if process.poll() is None:  # Still running
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

            # Update status
            demo_status[agent_id]["status"] = "stopped"
            demo_status[agent_id]["end_time"] = datetime.now().isoformat()

            # Broadcast demo stop
            await broadcast_state_change(
                {"event": "demo_stopped", "agent_id": agent_id}
            )

            return {"status": "success", "message": f"Demo {agent_id} stopped"}
        else:
            raise HTTPException(status_code=404, detail="Demo not found")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop demo: {str(e)}"
        ) from e


@app.get("/demo/status/{agent_id}")
async def get_demo_status(agent_id: str) -> dict[str, Any]:
    """Get status of a specific demo."""
    if agent_id in demo_status:
        return demo_status[agent_id]
    else:
        raise HTTPException(status_code=404, detail="Demo not found")


@app.get("/demo/list")
async def list_demos() -> dict[str, Any]:
    """List all active demos."""
    return {"active_demos": list(demo_status.keys()), "demo_status": demo_status}


@app.post("/agent-control")
async def control_agent(command: AgentCommand) -> dict[str, Any]:
    """Control agent actions."""
    try:
        command.validate_action()

        # Mock agent control - replace with actual agent management
        if command.action == "start":
            agent_config["execution_status"] = "running"
            # Simulate agent execution events
            await broadcast_state_change(
                {
                    "event": "agent_started",
                    "agent_id": command.agent_id,
                    "status": "running",
                }
            )

        elif command.action == "stop":
            agent_config["execution_status"] = "stopped"
            await broadcast_state_change(
                {
                    "event": "agent_stopped",
                    "agent_id": command.agent_id,
                    "status": "stopped",
                }
            )

        return {"status": "success", "action": command.action}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/settings/internet-toggle")
async def toggle_internet_access() -> dict[str, Any]:
    """Toggle internet access for agents."""
    global agent_config
    agent_config["internet_enabled"] = not agent_config.get("internet_enabled", True)

    # Broadcast state change
    await broadcast_state_change(
        {"event": "internet_toggle", "enabled": agent_config["internet_enabled"]}
    )

    return {"status": "success", "internet_enabled": agent_config["internet_enabled"]}


@app.get("/agent-status")
async def get_agent_status() -> dict[str, Any]:
    """Get current agent status for polling fallback."""
    return {
        "execution_status": agent_config["execution_status"],
        "internet_enabled": agent_config["internet_enabled"],
        "active_agents": len(agent_config.get("active_agents", {})),
        "active_demos": len(demo_status),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/citations/{conversation_id}", response_class=HTMLResponse)
def get_citations(request: Request, conversation_id: str) -> HTMLResponse:
    """HTMX endpoint for dynamic citation loading with simple caching and demo data."""
    now = time.time()
    cache_entry = _citation_cache.get(conversation_id)
    if cache_entry:
        html_citations, timestamp = cache_entry
        if now - timestamp < _CACHE_TTL:
            return HTMLResponse(html_citations)
    citation_mgr = ProductionCitationManager()
    citations = citation_mgr.get_conversation_citations(conversation_id)
    # DEMO: If no citations, add demo data
    if not citations:
        citation_mgr.add_citation(
            url="https://example.com/article1",
            title="Sample Article 1",
            content_preview="This is a sample article for testing...",
            domain="example.com",
        )
        citation_mgr.add_citation(
            url="https://example.com/article2",
            title="Sample Article 2",
            content_preview="Another sample article for testing...",
            domain="example.com",
        )
        citation_mgr.add_citation(
            url="https://example.com/article3",
            title="Sample Article 3",
            content_preview="Third sample article for testing...",
            domain="example.com",
        )
        citations = citation_mgr.get_all_citations()
    html_citations = ""
    for citation in citations:
        safe_url = escape(citation.url)
        safe_title = escape(citation.title)
        html_citations += f'''
        <div class="citation" id="citation-{citation.id}">
            <a href="{safe_url}" target="_blank" rel="noopener noreferrer">
                <sup>{citation.id}</sup> {safe_title}
            </a>
        </div>
        '''
    _citation_cache[conversation_id] = (html_citations, now)
    return HTMLResponse(html_citations)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "sse_connections": len(sse_connections),
        "active_demos": len(demo_status),
    }


@app.get("/metrics", response_class=HTMLResponse)
def get_metrics_dashboard(request: Request) -> HTMLResponse:
    """Metrics dashboard page"""
    return templates.TemplateResponse(request, "metrics.html")


@app.get("/metrics-panel", response_class=HTMLResponse)
def get_metrics_panel(request: Request) -> HTMLResponse:
    """HTMX endpoint for metrics panel"""
    return templates.TemplateResponse(request, "metrics.html")
