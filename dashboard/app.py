import asyncio
import json
import os
import re  # Added for regex in progress calculation
import subprocess
import sys
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import escape
from pydantic import BaseModel

try:
    from sse_starlette import EventSourceResponse
except ImportError:
    # Fallback for environments where sse_starlette is not available
    from starlette.responses import (
        StreamingResponse as EventSourceResponse,  # type: ignore[assignment]
    )

from dashboard.metrics import metrics_router
from dashboard.sse_manager import sse_manager
from dashboard.state_manager import AgentStatus, state_manager
from dashboard.unified_state import AgentStatus as UnifiedAgentStatus
from dashboard.unified_state import unified_state
from tools.citation_manager import ProductionCitationManager

# Global state for agent configuration
agent_config: dict[str, Any] = {
    "internet_enabled": True,
    "execution_status": "idle",
}

# Demo process management
demo_processes: dict[str, subprocess.Popen] = {}

# Plan management - separate from agents
plans_storage: dict[str, dict[str, Any]] = {}

# Plan synchronization tracking
plan_sync: dict[str, list[str]] = {}  # agent_id -> list of plan_ids

# Track currently selected agent for auto-refresh
selected_agent_id: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager"""
    # Startup
    print("Starting HTMX Dashboard...")

    # Start periodic status update task
    async def periodic_status_updates() -> None:
        while True:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds
                await broadcast_agent_status_update()
            except Exception as e:
                print(f"Error in periodic status updates: {e}")

    # Start the periodic task
    status_task = asyncio.create_task(periodic_status_updates())

    yield

    # Shutdown - cleanup demo processes and tasks
    print("Shutting down HTMX Dashboard...")

    # Cancel periodic task
    status_task.cancel()
    try:
        await status_task
    except asyncio.CancelledError:
        pass

    # Shutdown SSE manager
    sse_manager.shutdown()

    # Cleanup demo processes
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


# Enhanced error handling
@app.exception_handler(ValueError)
async def validation_exception_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc), "type": "validation_error"},
    )


@app.exception_handler(subprocess.SubprocessError)
async def subprocess_exception_handler(
    request: Request, exc: subprocess.SubprocessError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Process execution failed", "type": "subprocess_error"},
    )


async def launch_demo_with_timeout(
    demo_type: str, agent_id: str, timeout: int = 300
) -> subprocess.Popen:
    """Launch demo with timeout and proper error handling."""
    try:
        process = launch_demo(demo_type, agent_id)

        # Monitor with timeout
        start_time = time.time()
        while process.poll() is None and (time.time() - start_time) < timeout:
            await asyncio.sleep(1)

        if process.poll() is None:
            process.terminate()
            raise TimeoutError(f"Demo {demo_type} timed out after {timeout}s")

        return process
    except Exception as e:
        agent = state_manager.get_agent(agent_id)
        if agent:
            agent.set_error(str(e))
        raise


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


def launch_demo(demo_type: str, agent_id: str) -> subprocess.Popen:
    """Enhanced demo launch with unified state management"""
    env = os.environ.copy()
    env["LMSTUDIO_MODEL"] = "meta-llama-3-8b-instruct"
    env["IKOMA_DASHBOARD_MODE"] = "true"  # Signal to agent that dashboard is active
    env["IKOMA_DISABLE_CHECKPOINT"] = "true"  # Disable all prompts for demo mode
    env["IKOMA_TUI_MODE"] = "true"  # Enable TUI mode for logging
    env["IKOMA_TUI_LOG_FILE"] = "ikoma_tui_debug.log"  # Set the correct log filename

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

    # Create unified agent state
    agent_name = f"{demo_type.title()} Demo Agent"
    unified_state.create_agent(agent_id, agent_name, demo_type)

    # Also create legacy agent for backward compatibility
    legacy_agent = state_manager.create_agent(agent_id, agent_name, demo_type)
    legacy_agent.status = AgentStatus.RUNNING
    legacy_agent.current_step = "Executing plan"

    # Set initial progress
    if demo_type == "online":
        legacy_agent.update_progress(5, 1, 6)
    elif demo_type == "offline":
        legacy_agent.update_progress(10, 1, 3)
    else:  # continuous
        legacy_agent.update_progress(5, 1, 8)

    # Store process info
    demo_processes[agent_id] = process

    # Store initial plan entry (only if no plan exists yet)
    if agent_id not in plan_sync or not plan_sync[agent_id]:
        extract_and_store_plan(agent_id, legacy_agent.to_dict())
    else:
        # Update existing plan
        update_existing_plan(agent_id, legacy_agent.to_dict())

    # Subscribe to unified state changes for SSE broadcasting
    def broadcast_state_change(agent_id: str, changes: dict[str, Any]) -> None:
        agent = unified_state.get_agent(agent_id)
        if agent:
            sse_manager.broadcast_from_thread(
                agent_id,
                "state_change",
                {
                    "agent_id": agent_id,
                    "changes": changes,
                    "agent": agent.to_dict(),
                },
            )

    unified_state.subscribe(broadcast_state_change)

    # Enhanced monitoring thread
    def monitor_demo() -> None:
        try:
            plan_data = []

            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    if line:
                        line_stripped = line.strip()

                        # Update unified state (triggers broadcasts automatically)
                        unified_state.update_from_output(agent_id, line_stripped)

                        # Also update legacy state for backward compatibility
                        legacy_agent.add_output_line(line_stripped)

                        # Capture TUI debug output and plan data
                        if any(
                            keyword in line_stripped
                            for keyword in [
                                "PLAN:",
                                "Planning:",
                                "Goal:",
                                "Ikoma will pursue",
                                "Broadcasting plan_generated:",
                                "Plan generated:",
                                "Broadcasting step_start:",
                                "Step start:",
                                "Broadcasting step_complete:",
                                "Step complete:",
                                "Reflection:",
                                "TUI DEBUG",
                            ]
                        ):
                            plan_data.append(line_stripped)
                        elif "Step" in line_stripped and (
                            "plan" in line_stripped.lower()
                            or "goal" in line_stripped.lower()
                        ):
                            plan_data.append(line_stripped)
                        elif "Ikoma will pursue the goal:" in line_stripped:
                            plan_data.append(line_stripped)

                        # Update legacy progress calculation
                        output_count = len(legacy_agent.output_lines)

                        # Track actual step completion from agent events
                        if "Broadcasting step_start:" in line_stripped:
                            # Extract step number from step_start event
                            step_match = re.search(
                                r"step_start.*?step_index.*?(\d+)", line_stripped
                            )
                            if step_match:
                                current_step = int(step_match.group(1))
                                legacy_agent.steps_completed = max(
                                    0, current_step - 1
                                )  # Step started, so previous step completed

                        elif "Broadcasting step_complete:" in line_stripped:
                            # Extract step number from step_complete event
                            step_match = re.search(
                                r"step_complete.*?step_index.*?(\d+)", line_stripped
                            )
                            if step_match:
                                current_step = int(step_match.group(1))
                                legacy_agent.steps_completed = current_step

                        # Also look for step completion indicators in execution details
                        elif (
                            "✓ Step" in line_stripped
                            or "Step" in line_stripped
                            and ":" in line_stripped
                        ):
                            # Extract step number from execution details like "✓ Step 1: Create a new text file..."
                            step_match = re.search(r"✓ Step (\d+):", line_stripped)
                            if step_match:
                                current_step = int(step_match.group(1))
                                legacy_agent.steps_completed = current_step

                        # Calculate progress based on actual steps completed vs total expected steps
                        if demo_type == "online":
                            total_steps = 6
                        elif demo_type == "offline":
                            total_steps = 3
                        else:  # continuous
                            total_steps = 8

                        # Update total steps if we have actual step tracking
                        legacy_agent.total_steps = total_steps

                        # Calculate progress based on actual steps completed
                        if total_steps > 0:
                            progress = min(
                                int((legacy_agent.steps_completed / total_steps) * 100),
                                100,
                            )
                        else:
                            # Fallback to output-based calculation if no step tracking
                            if demo_type == "online":
                                progress = min(int((output_count / 60) * 100), 100)
                            elif demo_type == "offline":
                                progress = min(int((output_count / 40) * 100), 100)
                            else:  # continuous
                                progress = min(int((output_count / 80) * 100), 100)

                        legacy_agent.update_progress(
                            progress, legacy_agent.steps_completed, total_steps
                        )

                        # Only show demo output if debug is enabled
                        if os.getenv("IKOMA_TUI_DEBUG") == "true":
                            print(f"Demo output: {line_stripped}")

            # Demo completed
            unified_state.set_completed(agent_id)
            legacy_agent.status = AgentStatus.COMPLETED
            legacy_agent.end_time = datetime.now()
            legacy_agent.update_execution_time()

            # Store captured plan data
            if plan_data:
                legacy_agent.current_step = "Plan execution completed"
            else:
                # Fallback: use first few lines as plan data, focusing on goal and setup
                output_lines = legacy_agent.output_lines
                if output_lines:
                    # Extract goal and initial setup lines
                    plan_lines = []
                    for line in output_lines[:10]:  # Check first 10 lines
                        if any(
                            keyword in line
                            for keyword in [
                                "Goal:",
                                "Demo mode:",
                                "Ikoma will pursue",
                                "Max iterations:",
                                "Time limit:",
                            ]
                        ):
                            plan_lines.append(line)

                    if plan_lines:
                        legacy_agent.current_step = "Plan execution completed"
                    else:
                        legacy_agent.current_step = "Demo execution completed"

            # Update existing plan instead of creating a new one
            update_existing_plan(agent_id, legacy_agent.to_dict())

        except Exception as e:
            error_msg = f"Demo monitoring error: {e}"
            unified_state.set_error(agent_id, error_msg)
            legacy_agent.set_error(error_msg)
            print(error_msg)

    monitor_thread = threading.Thread(target=monitor_demo, daemon=True)
    monitor_thread.start()

    return process


def extract_and_store_plan(
    agent_id: str, demo_info: dict[str, Any], plan_version: int | None = None
) -> str:
    """Extract plan data from demo output and store it separately with version tracking."""

    # Extract plan data from current output
    output_lines = demo_info.get("output", [])
    plan_lines = []

    # Look for goal and planning information in output
    for line in output_lines:
        if any(
            keyword in line
            for keyword in [
                "Goal:",
                "Demo mode:",
                "Ikoma will pursue",
                "Max iterations:",
                "Time limit:",
                "Broadcasting plan_generated:",
                "Plan generated:",
                "Broadcasting step_start:",
                "Step start:",
                "Broadcasting step_complete:",
                "Step complete:",
                "Reflection:",
                "TUI DEBUG",
            ]
        ):
            plan_lines.append(line)

    if plan_lines:
        plan_data = "\n".join(plan_lines)
    else:
        plan_data = demo_info.get("plan", "No plan data available")

    # Generate plan version if not provided
    if plan_version is None:
        # Get existing plans for this agent
        existing_plans = plan_sync.get(agent_id, [])
        plan_version = len(existing_plans) + 1

    # Create plan entry with version tracking
    plan_id = f"plan-{agent_id}-v{plan_version}"

    plan_entry = {
        "plan_id": plan_id,
        "agent_id": agent_id,
        "plan_version": plan_version,
        "agent_name": demo_info.get("name", f"Agent {agent_id}"),
        "status": demo_info.get("status", "inactive"),
        "goal": demo_info.get("goal", "User-defined goal"),
        "current_step": demo_info.get("current_step", "No active execution"),
        "plan_data": plan_data,
        "progress": demo_info.get("progress", 0),
        "start_time": demo_info.get("start_time", ""),
        "end_time": demo_info.get("end_time", ""),
        "demo_type": demo_info.get("demo_type", "live"),
        "is_active": demo_info.get("status") == "running",
        "created_at": datetime.now().isoformat(),
    }

    # Store plan separately
    plans_storage[plan_id] = plan_entry

    # Update synchronization tracking
    if agent_id not in plan_sync:
        plan_sync[agent_id] = []
    plan_sync[agent_id].append(plan_id)

    return plan_id


def update_existing_plan(agent_id: str, demo_info: dict[str, Any]) -> None:
    """Update an existing plan for an agent without creating a new one."""
    # Get the latest plan for this agent
    latest_plan = get_latest_agent_plan(agent_id)
    if not latest_plan:
        return

    plan_id = latest_plan["plan_id"]
    if plan_id not in plans_storage:
        return

    plan = plans_storage[plan_id]

    # Update plan status based on agent state
    agent_status = demo_info["status"]

    if agent_status == "running":
        plan["status"] = "running"
        plan["is_active"] = True
        plan["current_step"] = "Executing plan"
    elif agent_status == "completed":
        plan["status"] = "completed"
        plan["is_active"] = False
        plan["current_step"] = "Plan completed"
    elif agent_status == "error":
        plan["status"] = "error"
        plan["is_active"] = False
        plan["current_step"] = "Plan failed"
    elif agent_status == "stopped":
        plan["status"] = "stopped"
        plan["is_active"] = False
        plan["current_step"] = "Plan stopped"
    else:
        # idle or other states
        plan["status"] = "inactive"
        plan["is_active"] = False
        plan["current_step"] = "No active execution"

    # Update progress
    plan["progress"] = demo_info.get("progress", 0)

    # Update end time if completed/stopped/error
    if agent_status in ["completed", "error", "stopped"]:
        plan["end_time"] = demo_info.get("end_time", datetime.now().isoformat())

    # Update plan data with latest output
    output_lines = demo_info.get("output", [])
    plan_lines = []
    for line in output_lines:
        if any(
            keyword in line
            for keyword in [
                "Goal:",
                "Demo mode:",
                "Ikoma will pursue",
                "Max iterations:",
                "Time limit:",
                "Broadcasting plan_generated:",
                "Plan generated:",
                "Broadcasting step_start:",
                "Step start:",
                "Broadcasting step_complete:",
                "Step complete:",
                "Reflection:",
                "TUI DEBUG",
            ]
        ):
            plan_lines.append(line)
        elif "Step" in line and ("plan" in line.lower() or "goal" in line.lower()):
            plan_lines.append(line)
        elif "Ikoma will pursue the goal:" in line:
            plan_lines.append(line)

    if plan_lines:
        plan["plan_data"] = plan_lines

    # Persist the updated plan back to storage
    plans_storage[plan_id] = plan

    # Use thread-safe broadcast for plan updates
    sse_manager.broadcast_from_thread(
        agent_id,
        "plan_updated",
        {"plan_id": plan_id, "plan": plan, "agent_status": agent_status},
    )


def sync_agent_plans(agent_id: str, demo_info: dict[str, Any]) -> None:
    """Synchronize agent state with its plans."""
    # Update existing plans for this agent
    agent_plans = plan_sync.get(agent_id, [])

    for plan_id in agent_plans:
        if plan_id in plans_storage:
            plan = plans_storage[plan_id]

            # Update plan status to match agent exactly
            plan["status"] = demo_info["status"]
            plan["is_active"] = demo_info["status"] == "running"

            # Update progress
            plan["progress"] = demo_info.get("progress", 0)

            # Update current step
            if demo_info["status"] == "running":
                plan["current_step"] = "Executing plan"
            elif demo_info["status"] == "completed":
                plan["current_step"] = "Plan completed"
            elif demo_info["status"] == "error":
                plan["current_step"] = "Plan failed"
            elif demo_info["status"] == "stopped":
                plan["current_step"] = "Plan stopped"
            else:
                plan["current_step"] = "No active execution"

            # Update end time if completed
            if demo_info["status"] in ["completed", "error"]:
                plan["end_time"] = demo_info.get("end_time", datetime.now().isoformat())

            # Persist the updated plan back to storage
            plans_storage[plan_id] = plan

            # Update plan data with latest output
            output_lines = demo_info.get("output", [])
            plan_lines = []

            for line in output_lines:
                if any(
                    keyword in line
                    for keyword in [
                        "Goal:",
                        "Demo mode:",
                        "Ikoma will pursue",
                        "Max iterations:",
                        "Time limit:",
                        "Broadcasting plan_generated:",
                        "Plan generated:",
                        "Broadcasting step_start:",
                        "Step start:",
                        "Broadcasting step_complete:",
                        "Step complete:",
                        "Reflection:",
                        "TUI DEBUG",
                    ]
                ):
                    plan_lines.append(line)

            if plan_lines:
                plan["plan_data"] = "\n".join(plan_lines)

            # Update storage
            plans_storage[plan_id] = plan


def get_agent_plans(agent_id: str) -> list[dict[str, Any]]:
    """Get all plans for a specific agent."""
    agent_plans = plan_sync.get(agent_id, [])
    return [
        plans_storage[plan_id] for plan_id in agent_plans if plan_id in plans_storage
    ]


def get_latest_agent_plan(agent_id: str) -> dict[str, Any] | None:
    """Get the most recent plan for a specific agent."""
    agent_plans = get_agent_plans(agent_id)
    if agent_plans:
        # Sort by plan_version and return the latest
        return max(agent_plans, key=lambda p: p.get("plan_version", 0))
    return None


@app.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request) -> HTMLResponse:
    """Render the main dashboard with three-panel layout."""
    return templates.TemplateResponse(
        request, "dashboard.html", {"agent_config": agent_config}
    )


@app.get("/agents/list", response_class=HTMLResponse)
def get_agents_list(request: Request) -> HTMLResponse:
    """HTMX endpoint for agent list panel with unified state."""
    # Use unified state for primary data, fallback to legacy state
    agents = unified_state.list_agents()
    if not agents:
        agents = state_manager.list_agents()

    # Return empty list if no agents - template will handle empty state
    return templates.TemplateResponse(request, "agents_list.html", {"agents": agents})


@app.get("/agent-details/{agent_id}", response_class=HTMLResponse)
def get_agent_details(request: Request, agent_id: str) -> HTMLResponse:
    """HTMX endpoint for agent details panel with unified state."""
    global selected_agent_id

    # Set the selected agent
    selected_agent_id = agent_id

    # Get agent details from unified state, fallback to legacy state
    unified_agent = unified_state.get_agent(agent_id)
    legacy_agent = state_manager.get_agent(agent_id)

    # Use unified agent if available, otherwise use legacy agent
    agent = unified_agent if unified_agent else legacy_agent

    if agent:
        agent_dict = agent.to_dict()
        # Add selection metadata
        agent_dict["is_selected"] = True

        # Broadcast selection change for UI sync
        try:
            from dashboard.sse_manager import sse_manager

            sse_manager.broadcast_from_thread(
                agent_id,
                "agent_selected",
                {"selected_agent_id": agent_id, "agent": agent_dict},
            )
        except Exception as e:
            print(f"Failed to broadcast selection change: {e}")

        response = templates.TemplateResponse(
            request, "agent_details.html", {"agent": agent_dict}
        )
        # Add selection tracking to response
        response.headers["X-Selected-Agent"] = agent_id
        return response
    else:
        return templates.TemplateResponse(
            request, "agent_details.html", {"agent": None}
        )


@app.get("/agent-details/selected", response_class=HTMLResponse)
def get_selected_agent_details(request: Request) -> HTMLResponse:
    """Get details for the currently selected agent using unified state."""
    global selected_agent_id

    # Get available agents
    agents = unified_state.list_agents()
    if not agents:
        agents = state_manager.list_agents()

    # If no agents exist, return empty state
    if not agents:
        return templates.TemplateResponse(
            request, "agent_details.html", {"agent": None}
        )

    # If no agent selected, auto-select the first available agent
    if not selected_agent_id or selected_agent_id == "selected":
        selected_agent_id = (
            agents[0]["id"] if isinstance(agents[0], dict) else agents[0].agent_id
        )

    # Get the agent from unified state, fallback to legacy state
    unified_agent = None
    legacy_agent = None
    if selected_agent_id:
        unified_agent = unified_state.get_agent(selected_agent_id)
        legacy_agent = state_manager.get_agent(selected_agent_id)

    # Use unified agent if available, otherwise use legacy agent
    agent = unified_agent if unified_agent else legacy_agent

    if agent:
        agent_dict = agent.to_dict()
        # Add selection metadata
        agent_dict["is_selected"] = True

        return templates.TemplateResponse(
            request, "agent_details.html", {"agent": agent_dict}
        )
    else:
        return templates.TemplateResponse(
            request, "agent_details.html", {"agent": None}
        )


@app.post("/agent-event")
async def receive_agent_event(event: dict[str, Any]) -> dict[str, Any]:
    """Receive agent events and forward to SSE stream."""
    try:
        # Forward event to SSE manager
        await sse_manager.broadcast_agent_event(
            event.get("agent_id", "unknown"), event.get("type", "agent_event"), event
        )

        return {"status": "success", "message": "Event forwarded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def broadcast_agent_status_update() -> None:
    """Broadcast current agent status to all SSE connections."""
    # Use unified state for primary data, fallback to legacy state
    agents = unified_state.list_agents()
    if not agents:
        agents = state_manager.list_agents()

    if agents:
        await sse_manager.broadcast_status_update(
            {
                "agents": agents,
                "timestamp": datetime.now().isoformat(),
            }
        )


@app.get("/agent-stream")
async def stream_agent_execution() -> EventSourceResponse:
    """Real-time agent execution streaming via SSE."""

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        global selected_agent_id
        queue: asyncio.Queue = asyncio.Queue()

        try:
            # Add connection to SSE manager
            await sse_manager.add_connection(queue)

            # Send initial connection event
            initial_event = {
                "event": "connected",
                "data": json.dumps(
                    {
                        "message": "SSE connection established",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            }
            yield initial_event

            # Keep connection alive and stream events
            while True:
                try:
                    # Process any pending events from threads
                    await sse_manager.process_pending_events()

                    # Wait for events with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    yield event
                except TimeoutError:
                    # Send periodic agent status updates
                    agents = state_manager.list_agents()
                    if agents:
                        # Clear selected agent if it no longer exists
                        agent_ids = [agent["id"] for agent in agents]
                        if selected_agent_id and selected_agent_id not in agent_ids:
                            selected_agent_id = None

                        # Send status update event
                        yield {
                            "event": "agent_status_update",
                            "data": json.dumps(
                                {
                                    "agents": agents,
                                    "timestamp": datetime.now().isoformat(),
                                }
                            ),
                        }
                    else:
                        # Clear selected agent if no agents exist
                        selected_agent_id = None

                        # Send keepalive if no agents
                        yield {
                            "event": "keepalive",
                            "data": json.dumps(
                                {"timestamp": datetime.now().isoformat()}
                            ),
                        }

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
        finally:
            # Remove connection from SSE manager
            await sse_manager.remove_connection(queue)

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.get("/test-sse")
async def test_sse() -> EventSourceResponse:
    """Simple SSE test endpoint."""

    async def test_event_generator() -> AsyncGenerator[dict[str, str], None]:
        # Send initial event
        yield {
            "event": "test",
            "data": json.dumps(
                {"message": "Test SSE event", "timestamp": datetime.now().isoformat()}
            ),
        }

        # Send periodic test events
        for i in range(5):
            await asyncio.sleep(2)
            yield {
                "event": "test",
                "data": json.dumps(
                    {
                        "message": f"Test event {i + 1}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            }

    return EventSourceResponse(test_event_generator())


@app.post("/demo/launch")
async def launch_demo_endpoint(request: Request) -> dict[str, Any]:
    """Launch a demo agent with immediate card creation."""
    try:
        # Handle both form data and JSON data
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # JSON data
            body = await request.json()
            demo_type = body.get("demo_type")
            agent_id = body.get("agent_id")
        else:
            # Form data (from HTMX)
            form_data = await request.form()
            demo_type = form_data.get("demo_type")
            agent_id = form_data.get("agent_id")

        if not demo_type:
            raise HTTPException(status_code=422, detail="demo_type is required")

        # Validate demo_type
        if demo_type not in ["online", "offline", "continuous"]:
            raise HTTPException(
                status_code=422,
                detail="demo_type must be one of: online, offline, continuous",
            )

        agent_id = agent_id or f"demo-{demo_type}-{int(time.time())}"

        # Create immediate agent in unified state
        agent_name = f"{demo_type.title()} Demo Agent"
        unified_state.create_agent(
            agent_id=agent_id, name=agent_name, demo_type=demo_type
        )

        # Update additional fields after creation
        unified_state.update_agent(
            agent_id=agent_id,
            current_step="Initializing...",
            goal=f"Demo mode: {demo_type.title()} Demo",
        )

        # Launch the demo process
        launch_demo(demo_type, agent_id)

        # Get current state after agent creation for comprehensive event data
        all_agents = unified_state.list_agents()
        if not all_agents:
            all_agents = state_manager.list_agents()

        # Broadcast demo start with comprehensive state data
        agent = unified_state.get_agent(agent_id)
        agent_dict = agent.to_dict() if agent else None

        await sse_manager.broadcast_agent_event(
            agent_id,
            "demo_started",
            {
                "demo_type": demo_type,
                "agent": agent_dict,
                "all_agents": all_agents,
                "agent_count": len(all_agents),
                "is_first_agent": len(all_agents) == 1,
                "should_auto_select": True,  # Auto-select newly created agents
            },
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "demo_type": demo_type,
            "message": f"Demo {demo_type} started",
        }

    except HTTPException:
        raise
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

            # Update status in state manager
            agent = state_manager.get_agent(agent_id)
            if agent:
                agent.status = AgentStatus.STOPPED
                agent.end_time = datetime.now()
                agent.update_execution_time()

            # Get current state after stopping for comprehensive event data
            all_agents = unified_state.list_agents()
            if not all_agents:
                all_agents = state_manager.list_agents()

            # Broadcast demo stop with comprehensive state data
            await sse_manager.broadcast_agent_event(
                agent_id,
                "demo_stopped",
                {
                    "agent_id": agent_id,
                    "all_agents": all_agents,
                    "agent_count": len(all_agents),
                    "is_empty": len(all_agents) == 0,
                    "was_selected": selected_agent_id == agent_id,
                },
            )

            return {"status": "success", "message": f"Demo {agent_id} stopped"}
        else:
            raise HTTPException(status_code=404, detail="Demo not found")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop demo: {str(e)}"
        ) from e


@app.delete("/agent/{agent_id}")
async def delete_agent(request: Request, agent_id: str) -> HTMLResponse:
    """Delete an agent and stop its process."""
    try:
        # Stop the process if it's running
        if agent_id in demo_processes:
            process = demo_processes[agent_id]
            if process.poll() is None:  # Still running
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

            # Remove from tracking
            del demo_processes[agent_id]

        # Remove from unified state manager (primary)
        unified_state.delete_agent(agent_id)

        # Remove from legacy state manager (fallback)
        state_manager.delete_agent(agent_id)

        # Remove all plans for this agent
        if agent_id in plan_sync:
            agent_plans = plan_sync[agent_id]
            for plan_id in agent_plans:
                if plan_id in plans_storage:
                    del plans_storage[plan_id]
            del plan_sync[agent_id]

        # Clear selected agent if it was the deleted one
        global selected_agent_id
        if selected_agent_id == agent_id:
            selected_agent_id = None

        # Get current state after deletion for comprehensive event data
        remaining_agents = unified_state.list_agents()
        if not remaining_agents:
            remaining_agents = state_manager.list_agents()

        # Broadcast agent deletion event with comprehensive state data
        await sse_manager.broadcast_agent_event(
            agent_id,
            "agent_deleted",
            {
                "agent_id": agent_id,
                "was_selected": selected_agent_id is None,
                "remaining_agents": remaining_agents,
                "agent_count": len(remaining_agents),
                "is_empty": len(remaining_agents) == 0,
            },
        )

        # Return HTML response to clear the agent details panel
        return templates.TemplateResponse(
            request, "agent_details.html", {"agent": None}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete agent: {str(e)}"
        ) from e


@app.delete("/plan/{plan_id}")
async def delete_plan(plan_id: str) -> dict[str, Any]:
    """Delete a plan entry without affecting the agent."""
    try:
        if plan_id in plans_storage:
            # Get plan info before deletion
            plan_info = plans_storage[plan_id]
            agent_id = plan_info.get("agent_id")

            # Remove plan from storage
            del plans_storage[plan_id]

            # Remove from sync tracking
            if agent_id and agent_id in plan_sync:
                if plan_id in plan_sync[agent_id]:
                    plan_sync[agent_id].remove(plan_id)

            # Broadcast plan deletion
            if agent_id:
                await sse_manager.broadcast_agent_event(
                    agent_id, "plan_deleted", {"plan_id": plan_id}
                )

            return {"status": "success", "message": f"Plan {plan_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Plan not found")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete plan: {str(e)}"
        ) from e


@app.get("/agent/{agent_id}/plans")
async def get_agent_plans_endpoint(agent_id: str) -> dict[str, Any]:
    """Get all plans for a specific agent."""
    try:
        agent_plans = get_agent_plans(agent_id)
        latest_plan = get_latest_agent_plan(agent_id)

        return {
            "agent_id": agent_id,
            "plans": agent_plans,
            "latest_plan": latest_plan,
            "total_plans": len(agent_plans),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get agent plans: {str(e)}"
        ) from e


@app.get("/demo/status/{agent_id}")
async def get_demo_status(agent_id: str) -> dict[str, Any]:
    """Get status of a specific demo."""
    # Try unified state first, fallback to legacy state manager
    unified_agent = unified_state.get_agent(agent_id)
    if unified_agent:
        return unified_agent.to_dict()

    # Fallback to legacy state manager
    legacy_agent = state_manager.get_agent(agent_id)
    if legacy_agent:
        return legacy_agent.to_dict()
    else:
        raise HTTPException(status_code=404, detail="Demo not found")


@app.get("/demo/list")
async def list_demos() -> dict[str, Any]:
    """List all active demos."""
    # Use unified state for demo agents
    agents = unified_state.list_agents()
    demo_agents = [agent for agent in agents if agent.get("is_demo")]

    return {
        "active_demos": [agent["id"] for agent in demo_agents],
        "demo_status": {agent["id"]: agent for agent in demo_agents},
    }


@app.get("/plans", response_class=HTMLResponse)
def get_plans_panel(request: Request) -> HTMLResponse:
    """Plans page with full dashboard layout."""
    # Get plans from separate storage
    plans = []
    for _plan_id, plan_info in plans_storage.items():
        plans.append(plan_info)

    # Add agent_config for template compatibility
    agent_config = {"internet_enabled": True}  # Default value

    return templates.TemplateResponse(
        request, "plans_page.html", {"plans": plans, "agent_config": agent_config}
    )


@app.get("/plans-page", response_class=HTMLResponse)
def get_plans_page(request: Request) -> RedirectResponse:
    """Redirect to the main plans page."""
    return RedirectResponse(url="/plans")


@app.post("/agent-control")
async def control_agent(command: AgentCommand) -> dict[str, Any]:
    """Control agent actions."""
    try:
        command.validate_action()

        # Mock agent control - replace with actual agent management
        if command.action == "start":
            agent_config["execution_status"] = "running"
            # Simulate agent execution events
            if command.agent_id:
                await sse_manager.broadcast_agent_event(
                    command.agent_id, "agent_started", {"status": "running"}
                )

        elif command.action == "stop":
            agent_config["execution_status"] = "stopped"
            if command.agent_id:
                await sse_manager.broadcast_agent_event(
                    command.agent_id, "agent_stopped", {"status": "stopped"}
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
    await sse_manager.broadcast(
        {"event": "internet_toggle", "enabled": agent_config["internet_enabled"]}
    )

    return {"status": "success", "internet_enabled": agent_config["internet_enabled"]}


@app.get("/agent-status")
async def get_agent_status() -> dict[str, Any]:
    """Get current agent status for polling fallback."""
    return {
        "execution_status": agent_config["execution_status"],
        "internet_enabled": agent_config["internet_enabled"],
        "active_agents": len(unified_state.list_agents()),
        "running_agents": unified_state.get_agent_count_by_status(
            UnifiedAgentStatus.RUNNING
        ),
        "completed_agents": unified_state.get_agent_count_by_status(
            UnifiedAgentStatus.COMPLETED
        ),
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
        "sse_connections": sse_manager.get_connection_count(),
        "active_agents": len(unified_state.list_agents()),
        "running_agents": unified_state.get_agent_count_by_status(
            UnifiedAgentStatus.RUNNING
        ),
        "completed_agents": unified_state.get_agent_count_by_status(
            UnifiedAgentStatus.COMPLETED
        ),
        "active_demos": unified_state.get_agent_count_by_status(
            UnifiedAgentStatus.RUNNING
        ),
    }


@app.get("/api/dashboard/metrics")
async def get_dashboard_metrics() -> dict[str, Any]:
    """Get dashboard metrics for integration with metrics dashboard."""
    agents = unified_state.list_agents()
    running_count = unified_state.get_agent_count_by_status(UnifiedAgentStatus.RUNNING)
    completed_count = unified_state.get_agent_count_by_status(
        UnifiedAgentStatus.COMPLETED
    )
    error_count = unified_state.get_agent_count_by_status(UnifiedAgentStatus.ERROR)

    # Calculate average execution time
    total_time = 0
    completed_agents = 0
    for agent in agents:
        if agent["status"] == "completed" and agent["execution_time"] != "00:00:00":
            try:
                # Parse execution time (format: HH:MM:SS)
                time_parts = agent["execution_time"].split(":")
                if len(time_parts) == 3:
                    hours, minutes, seconds = map(int, time_parts)
                    total_time += hours * 3600 + minutes * 60 + seconds
                    completed_agents += 1
            except (ValueError, IndexError):
                continue

    avg_execution_time = total_time / completed_agents if completed_agents > 0 else 0

    # Calculate success rate
    total_finished = completed_count + error_count
    success_rate = (completed_count / total_finished * 100) if total_finished > 0 else 0

    return {
        "active_agents": running_count,
        "completed_demos": completed_count,
        "error_count": error_count,
        "avg_execution_time_seconds": avg_execution_time,
        "success_rate": round(success_rate, 2),
        "total_agents": len(agents),
        "sse_connections": sse_manager.get_connection_count(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics", response_class=HTMLResponse)
def get_metrics_dashboard(request: Request) -> HTMLResponse:
    """Metrics dashboard page"""
    return templates.TemplateResponse(request, "metrics.html")


@app.get("/metrics-panel", response_class=HTMLResponse)
def get_metrics_panel(request: Request) -> HTMLResponse:
    """HTMX endpoint for metrics panel"""
    return templates.TemplateResponse(request, "metrics.html")


@app.post("/test/progress-update/{agent_id}")
async def test_progress_update(agent_id: str) -> dict[str, Any]:
    """Test endpoint to trigger a progress update for debugging."""
    try:
        # Get the agent
        agent = unified_state.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": f"Agent {agent_id} not found"}

        # Trigger a progress update
        state_manager.broadcast_progress_update(
            agent_id,
            {
                "progress": 75,
                "steps_completed": 2,
                "total_steps": 3,
                "current_step": "Test progress update",
                "latest_output": "Testing progress synchronization",
            },
        )

        return {
            "status": "success",
            "message": f"Progress update triggered for agent {agent_id}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
