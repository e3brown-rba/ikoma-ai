import argparse
import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, TypedDict, cast

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from rich.console import Console
from rich.panel import Panel

# Checkpoint functionality for conversation state persistence
from agent.checkpointer import IkomaCheckpointer
from agent.constants import MAX_ITER, MAX_MINS
from agent.instrumentation import get_instrumentation
from agent.metrics import metrics_collector
from ikoma.schemas.plan_models import MalformedPlanError, Plan
from planning.reflection import PlanRepairFailure, get_max_plan_retries, repair_plan
from tools.citation_manager import ProductionCitationManager
from tools.tool_loader import tool_loader

# Add import for TUI broadcaster
try:
    from agent.ui.state_broadcaster import broadcaster

    tui_broadcaster: Any = broadcaster
except ImportError:
    tui_broadcaster = None

# Add import for dashboard sender
dashboard_sender_global: Any = None
try:
    from agent.ui.dashboard_sender import get_dashboard_sender

    dashboard_sender_global = get_dashboard_sender()
except ImportError:
    pass

# Load environment variables from .env file
load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-dummy"


def signal_handler(sig: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    print("\n🛑 Received shutdown signal, cleaning up...")
    # Force close ChromaDB connections
    try:
        from tools.vector_store import cleanup_vector_store

        cleanup_vector_store()
    except ImportError:
        pass
    sys.exit(0)


# --- Enhanced State Definition ---
class AgentState(TypedDict):
    """Enhanced state schema for plan-execute-reflect architecture."""

    messages: Annotated[list[Any], add_messages]
    memory_context: str | None
    user_profile: dict[str, Any] | None
    session_summary: str | None
    current_plan: list[dict[str, Any]] | None
    execution_results: list[dict[str, Any]] | None
    reflection: str | None
    continue_planning: bool
    max_iterations: int
    current_iteration: int
    start_time: float | None  # New: for continuous mode time tracking
    time_limit_secs: int | None  # New: for continuous mode time limit
    citations: list[dict[str, Any]] | None  # New: citation tracking
    citation_counter: int | None  # New: tracks next citation ID
    reflection_json: dict[str, Any] | None  # New: raw reflection data for heuristics
    reflection_failures: (
        list[dict[str, Any]] | None
    )  # New: history of reflection failures
    checkpoint_every: int | None  # New: for human checkpoint intervals
    last_checkpoint_iter: int | None  # New: tracks last checkpoint iteration
    stats: dict[str, Any] | None  # New: for tracking repair attempts and metrics


# --- Continuous Mode Safety Functions ---
def should_abort_continuous(state: AgentState) -> bool:
    """Check if continuous mode should be aborted due to time or iteration limits.

    TODO remove in v0.4 - this is now a thin wrapper that delegates to criteria.
    """
    from agent.heuristics import DEFAULT_CRITERIA

    return any(c.should_stop(state) for c in DEFAULT_CRITERIA)


# --- File Tools moved to tools/fs_tools.py ---
# Tools are now loaded dynamically via tools/tool_loader.py


# --- Memory Management Functions ---
def retrieve_long_term_memory(
    state: AgentState, config: dict, *, store: Any
) -> AgentState:
    """Retrieve relevant long-term memories based on current context."""
    try:
        # Extract user ID from config
        user_id = config.get("configurable", {}).get("user_id", "default")

        # Get the last user message for context
        user_messages = [
            msg
            for msg in state["messages"]
            if hasattr(msg, "type") and msg.type == "human"
        ]
        if not user_messages:
            return state

        last_user_message = user_messages[-1].content

        # Search for relevant memories using semantic search
        namespace = ("memories", user_id)

        try:
            memories = store.search(namespace, query=last_user_message, limit=3)

            if memories:
                memory_context = "Previous relevant context:\n"
                for memory in memories:
                    # Handle different memory result structures
                    if hasattr(memory, "value"):
                        content = memory.value.get("content", "")
                        # Restore citation state from memory if available
                        if memory.value.get("citations") and not state.get("citations"):
                            state["citations"] = memory.value.get("citations")
                        if memory.value.get("citation_counter") and not state.get(
                            "citation_counter"
                        ):
                            state["citation_counter"] = memory.value.get(
                                "citation_counter"
                            )
                    elif isinstance(memory, dict):
                        content = memory.get("content", "")
                        # Restore citation state from memory if available
                        if memory.get("citations") and not state.get("citations"):
                            state["citations"] = memory.get("citations")
                        if memory.get("citation_counter") and not state.get(
                            "citation_counter"
                        ):
                            state["citation_counter"] = memory.get("citation_counter")
                    else:
                        content = str(memory)
                    memory_context += f"- {content}\n"

                state["memory_context"] = memory_context
        except Exception as e:
            print(f"Warning: Could not retrieve memories: {e}")

    except Exception as e:
        print(f"Error in retrieve_long_term_memory: {e}")

    return state


def store_long_term_memory(
    state: AgentState, config: dict, *, store: Any
) -> AgentState:
    """Store important information to long-term memory."""
    try:
        # Extract user ID from config
        user_id = config.get("configurable", {}).get("user_id", "default")

        # Get the last few messages for context
        recent_messages = (
            state["messages"][-4:] if len(state["messages"]) >= 4 else state["messages"]
        )

        # Extract memorable content (enhanced logic)
        memorable_content = []
        for msg in recent_messages:
            if hasattr(msg, "content") and msg.content:
                # Enhanced heuristic: store based on keywords, length, and execution results
                if any(
                    keyword in msg.content.lower()
                    for keyword in [
                        "prefer",
                        "like",
                        "remember",
                        "important",
                        "project",
                        "task",
                        "learn",
                    ]
                ):
                    memorable_content.append(msg.content)
                elif len(msg.content) > 100:  # Store longer interactions
                    memorable_content.append(msg.content)

        # Also store successful execution patterns
        if state.get("execution_results"):
            for result in state["execution_results"]:  # type: ignore
                if result.get("status") == "success":
                    memorable_content.append(
                        f"Successful execution: {result.get('tool_name')} with {result.get('args')}"
                    )

        # Store memories if we have content worth remembering
        if memorable_content:
            namespace = ("memories", user_id)
            memory_id = str(uuid.uuid4())

            memory_entry = {
                "content": " ".join(memorable_content),
                "timestamp": datetime.now().isoformat(),
                "context": "conversation",
                "plan_context": state.get("current_plan"),
                "reflection": state.get("reflection"),
                "citations": state.get("citations"),  # Include citation state
                "citation_counter": state.get(
                    "citation_counter"
                ),  # Include citation counter
            }

            try:
                store.put(namespace, memory_id, memory_entry)
            except Exception as e:
                print(f"Warning: Could not store memory: {e}")

    except Exception as e:
        print(f"Error in store_long_term_memory: {e}")

    return state


# --- Conditional Edge Functions ---
def should_continue_planning(state: AgentState) -> str:
    """Determine whether to continue planning or end the conversation."""
    return "plan" if state.get("continue_planning", False) else "store_memory"


# --- Plan-Execute-Reflect Nodes ---
def plan_node(state: AgentState, config: dict, *, store: Any, llm: Any) -> AgentState:
    """Optimized plan_node that uses shared LLM instance."""
    # Instrumentation: Record plan start
    instrumentation = get_instrumentation()
    instrumentation.record_plan_start()

    # Metrics: Record plan step start
    plan_start_time = time.perf_counter()

    try:
        # TUI Integration: planning_start
        if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
            print(
                f"[AGENT DEBUG] Broadcasting planning_start: {state['messages'][-1].content}"
            )
            tui_broadcaster.broadcast(
                "planning_start",
                {
                    "user_request": state["messages"][-1].content,
                    "memory_context": state.get("memory_context"),
                },
            )

        # Dashboard Integration: planning_start
        if dashboard_sender_global:
            dashboard_sender_global.send_event(
                "planning_start",
                {
                    "user_request": state["messages"][-1].content,
                    "memory_context": state.get("memory_context"),
                    "iteration": state.get("current_iteration", 0),
                },
            )
        # Get tool descriptions
        tool_descriptions = tool_loader.get_tool_descriptions()

        # Build planning prompt
        planning_prompt = f"""You are a planning assistant. Based on the user's request, create a detailed plan of tool calls.

Available tools:
{tool_descriptions}

Your task is to analyze the user's request and create a JSON plan that **conforms to the plan schema** (see below) and *nothing else*.

CRITICAL: Return ONLY the JSON plan. Do not include any explanatory text, comments, or other content before or after the JSON.

Important guidelines:
1. Break complex tasks into logical steps
2. Use exact tool names from the available tools
3. Provide proper arguments for each tool
4. Include clear descriptions for each step
5. Return ONLY the JSON plan, no other text or explanations
6. If the request cannot be handled with available tools, create a plan that explains this
7. For philosophical questions like "meaning of life", use create_text_file to provide a thoughtful response
8. Do NOT use Calculator tool for non-mathematical questions
9. Calculator tool is ONLY for numerical calculations and math problems

Citation Guidelines:
- When a step involves information from external sources or previous context, include citation markers [[n]] in the description
- Use [[1]], [[2]], etc. for different sources
- Place citations immediately after claims that need sourcing
- The execute phase will populate actual citation details
- For future web tools, include citations when referencing external information

Tool argument examples:
- list_sandbox_files: {{"query": ""}} or {{"query": "search_term"}}
- read_text_file: {{"filename": "file.txt"}}
- create_text_file: {{"filename_and_content": "file.txt|||content here"}}
- update_text_file: {{"filename_and_content": "file.txt|||new content"}}
- Calculator: {{"question": "2 + 2"}}

User's request: {state["messages"][-1].content}

Return ONLY the JSON that **conforms to the plan schema** and *nothing else*:

```json
{{
  "plan": [
    {{
      "step": 1,
      "tool_name": "tool_name",
      "args": {{"arg1": "value1"}},
      "description": "What this step accomplishes",
      "citations": [1, 2]
    }}
  ],
  "reasoning": "Why this plan will achieve the user's goal"
}}
```"""

        # Add memory context if available
        if state.get("memory_context"):
            planning_prompt += f"\n\nRelevant context from previous conversations:\n{state['memory_context']}"

        # Get plan from LLM
        response = llm.invoke([HumanMessage(content=planning_prompt)])

        # Guard against empty response
        if not response.content.strip():
            raise ValueError("Empty response from LLM")

        # Debug: Log the raw response for troubleshooting
        if os.getenv("IKOMA_TUI_DEBUG") == "true":
            print(
                f"[DEBUG] Raw LLM response (first 200 chars): {response.content[:200]}..."
            )

        # Parse the plan
        try:
            # Extract JSON from response with improved parsing
            plan_text = response.content.strip()

            # Try to find JSON in the response
            json_start = -1
            json_end = -1

            # Look for JSON code blocks first
            if "```json" in plan_text:
                json_start = plan_text.find("```json") + 7
                json_end = plan_text.find("```", json_start)
            elif "```" in plan_text:
                json_start = plan_text.find("```") + 3
                json_end = plan_text.find("```", json_start)

            # If no code blocks found, look for JSON object directly
            if json_start == -1:
                # Find the first occurrence of '{' and last occurrence of '}'
                brace_start = plan_text.find("{")
                brace_end = plan_text.rfind("}")

                if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                    json_start = brace_start
                    json_end = brace_end + 1

            # Extract the JSON text
            if json_start != -1 and json_end != -1:
                plan_text = plan_text[json_start:json_end].strip()
            else:
                # If no JSON found, try to extract any text that looks like JSON
                # Look for patterns that might be JSON
                import re

                json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
                json_matches = re.findall(json_pattern, plan_text)
                if json_matches:
                    plan_text = json_matches[0]
                else:
                    raise ValueError("No valid JSON found in response")

            # Validate plan using schema with self-reflection retry (Issue-18)
            try:
                validated_plan = Plan.model_validate_json(plan_text)
                # Convert PlanStep objects back to dictionaries for state compatibility
                state["current_plan"] = [
                    step.model_dump() for step in validated_plan.plan
                ]
                state["continue_planning"] = True

                # Instrumentation: Record successful plan end
                instrumentation.record_plan_end(
                    len(validated_plan.plan), state["current_plan"] or []
                )

                # Metrics: Record successful plan step
                plan_duration_ms = (time.perf_counter() - plan_start_time) * 1000
                metrics_collector.emit_step(
                    step_type="plan",
                    duration_ms=plan_duration_ms,
                    success=True,
                    metadata={"plan_steps": len(validated_plan.plan)},
                )

            except Exception as e:
                # Self-reflection retry (Issue-18)
                max_retries = (
                    get_max_plan_retries() - 1
                )  # -1 because first attempt already failed
                try:
                    repaired_plan = repair_plan(
                        llm=llm,
                        invalid_plan=plan_text,
                        validation_error=str(e),
                        retries=max_retries,
                    )
                    # Validate the repaired plan
                    validated_plan = Plan.model_validate_json(repaired_plan)
                    state["current_plan"] = [
                        step.model_dump() for step in validated_plan.plan
                    ]
                    state["continue_planning"] = True
                    # Track repair success in state stats
                    if state.get("stats") is None:
                        state["stats"] = {}
                    stats = cast(dict[str, Any], state["stats"])
                    stats["plan_retries"] = stats.get("plan_retries", 0) + 1
                except PlanRepairFailure:
                    # Repair failed, fall back to original error
                    raise MalformedPlanError(str(e)) from e

        except (json.JSONDecodeError, MalformedPlanError) as e:
            print(f"Error parsing plan: {e}")

            # Metrics: Record failed plan step
            plan_duration_ms = (time.perf_counter() - plan_start_time) * 1000
            metrics_collector.emit_step(
                step_type="plan",
                duration_ms=plan_duration_ms,
                success=False,
                error=str(e),
            )

            # Intelligent fallback based on request type
            user_request = state["messages"][-1].content.lower()

            if any(
                word in user_request
                for word in ["meaning", "life", "philosophy", "existential", "purpose"]
            ):
                # For philosophical questions, acknowledge the limitation
                # Check if the file already exists to make this idempotent
                sandbox_path = Path("agent/ikoma_sandbox")
                philosophical_file = sandbox_path / "philosophical_response.txt"

                if philosophical_file.exists():
                    # File exists, use update_text_file
                    tool_name = "update_text_file"
                    description = "Update existing philosophical response with additional thoughts"
                else:
                    # File doesn't exist, use create_text_file
                    tool_name = "create_text_file"
                    description = "Create a thoughtful response acknowledging the limitation of available tools for philosophical questions"

                state["current_plan"] = [
                    {
                        "step": 1,
                        "tool_name": tool_name,
                        "args": {
                            "filename_and_content": "philosophical_response.txt|||I understand you're asking about the meaning of life, which is a profound philosophical question that has been contemplated by thinkers throughout history. While I can help with practical tasks using available tools, I cannot provide definitive answers to such existential questions. I'd be happy to help you with concrete tasks, calculations, or file operations instead."
                        },
                        "description": description,
                    }
                ]
            else:
                # For other requests, try to list files as starting point
                state["current_plan"] = [
                    {
                        "step": 1,
                        "tool_name": "list_sandbox_files",
                        "args": {"query": ""},
                        "description": "List available files as a starting point",
                    }
                ]
            state["continue_planning"] = True

        # After plan is generated
        if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
            plan = state.get("current_plan") or []
            if os.getenv("IKOMA_TUI_DEBUG") == "true":
                print(f"[AGENT DEBUG] Broadcasting plan_generated: {len(plan)} steps")
            tui_broadcaster.broadcast(
                "plan_generated", {"plan": plan, "step_count": len(plan)}
            )

        # Dashboard Integration: plan_generated
        if dashboard_sender_global:
            plan = state.get("current_plan") or []
            dashboard_sender_global.send_event(
                "plan_generated",
                {
                    "plan": plan,
                    "step_count": len(plan),
                    "iteration": state.get("current_iteration", 0),
                },
            )

    except Exception as e:
        print(f"Error in plan_node: {e}")
        state["current_plan"] = []
        state["continue_planning"] = False

    return state


def execute_node(
    state: AgentState, config: dict, *, store: Any, tools: Any
) -> AgentState:
    """Optimized execute_node that uses shared tools with citation tracking."""
    # Instrumentation: Record execute start
    instrumentation = get_instrumentation()
    instrumentation.record_execute_start()

    # Metrics: Record execute step start
    execute_start_time = time.perf_counter()

    try:
        # Initialize citation manager
        from tools.citation_manager import CitationManager

        citation_manager = CitationManager()

        # Initialize citations if not present
        if state.get("citations") is None:
            state["citations"] = []
            state["citation_counter"] = 1
        else:
            # Load existing citations into manager
            citation_manager.from_dict(
                {
                    "citations": state["citations"],
                    "counter": state.get("citation_counter", 1),
                }
            )

        # Execute each step in the plan
        execution_results = []

        for step in state.get("current_plan", []):  # type: ignore
            tool_name = step["tool_name"]
            args = step["args"]
            description = step["description"]

            # TUI Integration: step_start
            if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
                if os.getenv("IKOMA_TUI_DEBUG") == "true":
                    print(f"[AGENT DEBUG] Broadcasting step_start: {tool_name}")
                tui_broadcaster.broadcast(
                    "step_start",
                    {
                        "step_index": step.get("step", 0),
                        "tool_name": tool_name,
                        "description": description,
                    },
                )

            # Dashboard Integration: step_start
            if dashboard_sender_global:
                dashboard_sender_global.send_event(
                    "step_start",
                    {
                        "step_index": step.get("step", 0),
                        "tool_name": tool_name,
                        "description": description,
                        "iteration": state.get("current_iteration", 0),
                    },
                )
            # Find the tool (handle name mapping for math tools)
            tool = None
            for t in tools:
                if t.name == tool_name:
                    tool = t
                    break
                # Handle llm-math -> Calculator mapping
                elif tool_name == "llm-math" and t.name == "Calculator":
                    tool = t
                    break

            if not tool:
                execution_results.append(
                    {
                        "step": step["step"],
                        "tool_name": tool_name,
                        "args": args,
                        "description": description,
                        "status": "error",
                        "result": f"Tool '{tool_name}' not found",
                    }
                )
                # Instrumentation: Record failed tool call
                instrumentation.record_tool_call(
                    tool_name, args, False, f"Tool '{tool_name}' not found"
                )
                continue

            # Execute the tool
            tool_start_time = time.perf_counter()
            try:
                # Handle different tool argument formats
                if tool_name == "Calculator" or (
                    tool_name == "llm-math" and t.name == "Calculator"
                ):
                    # Calculator expects a single string argument
                    if isinstance(args, dict) and "question" in args:
                        result = tool.invoke(args["question"])
                    elif isinstance(args, str):
                        result = tool.invoke(args)
                    else:
                        result = tool.invoke(str(args))
                elif tool_name in ["create_text_file", "update_text_file"]:
                    # File tools expect filename_and_content as single string with ||| separator
                    if isinstance(args, dict):
                        if "filename_and_content" in args:
                            result = tool.invoke(args["filename_and_content"])
                        elif "filename" in args and "content" in args:
                            # Convert separate fields to expected format
                            combined = f"{args['filename']}|||{args['content']}"
                            result = tool.invoke(combined)
                        else:
                            result = tool.invoke(args)
                    else:
                        result = tool.invoke(args)
                elif tool_name == "read_text_file":
                    # Read file tool expects filename as string
                    if isinstance(args, dict):
                        if "filename" in args:
                            result = tool.invoke(args["filename"])
                        else:
                            # If args is empty dict, we need to handle this case
                            result = "Error: filename parameter is required"
                    elif isinstance(args, str):
                        result = tool.invoke(args)
                    else:
                        result = tool.invoke(str(args))
                elif tool_name == "list_sandbox_files":
                    # List files tool expects query as string (can be empty)
                    if isinstance(args, dict):
                        if "query" in args:
                            result = tool.invoke(args["query"])
                        else:
                            result = tool.invoke("")
                    elif isinstance(args, str):
                        result = tool.invoke(args)
                    else:
                        result = tool.invoke("")
                else:
                    # Regular tool execution
                    result = tool.invoke(args)

                # Track execution result
                execution_result = {
                    "step": step["step"],
                    "tool_name": tool_name,
                    "args": args,
                    "description": description,
                    "status": "success",
                    "result": str(result),
                }

                # Metrics: Record successful tool execution
                tool_duration_ms = (time.perf_counter() - tool_start_time) * 1000
                metrics_collector.emit_step(
                    step_type="tool",
                    duration_ms=tool_duration_ms,
                    success=True,
                    tool_name=tool_name,
                    metadata={"args": args, "result_length": len(str(result))},
                )

                # Check for citation-worthy sources after successful execution
                if execution_result["status"] == "success":
                    # For future web tools, extract citation info
                    if tool_name in [
                        "web_search",
                        "web_fetch",
                        "search_web",
                    ]:  # Future tools
                        # Extract URL and title from result if available
                        # This will be implemented when web tools are added
                        pass

                    # For memory-based tools, track citations
                    elif tool_name in ["retrieve_memory", "search_memory"]:
                        # Extract memory source info if available
                        pass

                execution_results.append(execution_result)

            except Exception as e:
                execution_results.append(
                    {
                        "step": step["step"],
                        "tool_name": tool_name,
                        "args": args,
                        "description": description,
                        "status": "error",
                        "result": f"Error executing tool: {e}",
                    }
                )

                # Metrics: Record failed tool execution
                tool_duration_ms = (time.perf_counter() - tool_start_time) * 1000
                metrics_collector.emit_step(
                    step_type="tool",
                    duration_ms=tool_duration_ms,
                    success=False,
                    tool_name=tool_name,
                    error=str(e),
                    metadata={"args": args},
                )

        # Update citation state
        citation_data = citation_manager.to_dict()
        state["citations"] = citation_data["citations"]
        state["citation_counter"] = citation_data["counter"]

        state["execution_results"] = execution_results

        # Instrumentation: Record execute end
        instrumentation.record_execute_end(execution_results)

        # Metrics: Record successful execute step
        execute_duration_ms = (time.perf_counter() - execute_start_time) * 1000
        metrics_collector.emit_step(
            step_type="execute",
            duration_ms=execute_duration_ms,
            success=True,
            metadata={"tools_executed": len(execution_results)},
        )

        # After execution result
        if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
            print(
                f"[AGENT DEBUG] Broadcasting step_complete: {execution_results[-1]['status']}"
            )
            tui_broadcaster.broadcast(
                "step_complete",
                {
                    "step_index": step.get("step", 0),
                    "status": execution_results[-1]["status"],
                    "result": execution_results[-1]["result"],
                },
            )

        # Dashboard Integration: step_complete
        if dashboard_sender_global:
            dashboard_sender_global.send_event(
                "step_complete",
                {
                    "step_index": step.get("step", 0),
                    "status": execution_results[-1]["status"],
                    "result": execution_results[-1]["result"],
                    "iteration": state.get("current_iteration", 0),
                },
            )

    except Exception as e:
        print(f"Error in execute_node: {e}")
        state["execution_results"] = [
            {
                "step": 1,
                "tool_name": "unknown",
                "args": {},
                "description": "Execution failed",
                "status": "error",
                "result": f"Execution error: {e}",
            }
        ]
        # Instrumentation: Record error
        instrumentation.record_error(str(e), {"node": "execute_node"})

        # Metrics: Record failed execute step
        execute_duration_ms = (time.perf_counter() - execute_start_time) * 1000
        metrics_collector.emit_step(
            step_type="execute",
            duration_ms=execute_duration_ms,
            success=False,
            error=str(e),
        )

    return state


def reflect_node(
    state: AgentState, config: dict, *, store: Any, llm: Any
) -> AgentState:
    """Optimized reflect_node that uses shared LLM instance."""
    # Instrumentation: Record reflect start
    instrumentation = get_instrumentation()
    instrumentation.record_reflect_start()

    # Metrics: Record reflect step start
    reflect_start_time = time.perf_counter()

    try:
        # Increment iteration counter
        state["current_iteration"] = state.get("current_iteration", 0) + 1

        # Check for human checkpoint
        from agent.heuristics import CHECKPOINT_CRITERION

        if CHECKPOINT_CRITERION.should_checkpoint(state):
            from agent.ui import prompt_user_confirm

            if not prompt_user_confirm(state):
                state["continue_planning"] = False
                return state

        # Ensure reflection_failures is initialized
        if "reflection_failures" not in state or state["reflection_failures"] is None:
            state["reflection_failures"] = []

        # Termination criteria are now fully centralised

        # Format execution results for reflection
        results_summary = []
        for result in state.get("execution_results", []):  # type: ignore
            status = "✓" if result["status"] == "success" else "✗"
            results_summary.append(
                f"{status} Step {result['step']}: {result['description']} -> {result['result']}"
            )

        results_text = "\n".join(results_summary)

        # Create reflection prompt
        reflection_prompt = f"""Analyze the execution results and determine if the user's request has been satisfied.

Original request: {state["messages"][-1].content}

Execution results:
{results_text}

Provide your analysis in JSON format:
```json
{{
  "task_completed": true/false,
  "success_rate": "percentage of successful steps",
  "summary": "Brief summary of what was accomplished",
  "next_action": "continue" or "end",
  "reasoning": "Why you chose this next action"
}}
```

Return only the JSON, no other text."""

        # Get reflection from LLM
        response = llm.invoke([HumanMessage(content=reflection_prompt)])

        # Guard against empty response
        if not response.content.strip():
            if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
                tui_broadcaster.broadcast(
                    "reflection_error", {"error": "Empty response from LLM"}
                )
            raise ValueError("Empty response from LLM")

        # Parse reflection
        try:
            reflection_text = response.content.strip()
            if reflection_text.startswith("```json"):
                reflection_text = reflection_text[7:-3].strip()
            elif reflection_text.startswith("```"):
                reflection_text = reflection_text[3:-3].strip()

            reflection_data = json.loads(reflection_text)

            # Broadcast reflection reasoning and summary
            if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
                tui_broadcaster.broadcast(
                    "reflection",
                    {
                        "reasoning": reflection_data.get("reasoning", ""),
                        "summary": reflection_data.get("summary", ""),
                        "success_rate": reflection_data.get("success_rate", ""),
                        "task_completed": reflection_data.get("task_completed", None),
                    },
                )

            # Dashboard Integration: reflection
            if dashboard_sender_global:
                dashboard_sender_global.send_event(
                    "reflection",
                    {
                        "reasoning": reflection_data.get("reasoning", ""),
                        "summary": reflection_data.get("summary", ""),
                        "success_rate": reflection_data.get("success_rate", ""),
                        "task_completed": reflection_data.get("task_completed", None),
                        "iteration": state.get("current_iteration", 0),
                    },
                )

            # Persist reflection for downstream heuristics
            state["reflection_json"] = reflection_data

            # Unified stop-check using all criteria
            from agent.heuristics import DEFAULT_CRITERIA

            should_stop = any(c.should_stop(state) for c in DEFAULT_CRITERIA)

            if should_stop:
                state["continue_planning"] = False

                # Create final response with citation support
                final_response = f"""Task completed! Here's what I accomplished:

{reflection_data.get("summary", "Task execution completed.")}

Execution Details:
{results_text}

Success Rate: {reflection_data.get("success_rate", "N/A")}"""

                # Add citations to response if any exist
                if state.get("citations"):
                    citation_manager = ProductionCitationManager()
                    citation_manager.from_dict(
                        {
                            "citations": state["citations"],
                            "counter": state.get("citation_counter", 1),
                        }
                    )

                    # Extract citations from the response text
                    citation_ids = citation_manager.extract_citations_from_text(
                        final_response
                    )
                    if citation_ids:
                        final_response += "\n\n📚 Sources:\n"
                        for cid in citation_ids:
                            if citation := citation_manager.get_citation_details(cid):
                                final_response += (
                                    f"  [{cid}] {citation.title} - {citation.url}\n"
                                )

                state["messages"].append(AIMessage(content=final_response))
            else:
                state["continue_planning"] = True

            state["reflection"] = reflection_data.get(
                "reasoning", "Reflection completed"
            )

            # Instrumentation: Record reflect end
            next_action = reflection_data.get("next_action", "continue")
            instrumentation.record_reflect_end(
                reflection_data.get("reasoning", "Reflection completed"), next_action
            )

            # Metrics: Record successful reflect step
            reflect_duration_ms = (time.perf_counter() - reflect_start_time) * 1000
            metrics_collector.emit_step(
                step_type="reflect",
                duration_ms=reflect_duration_ms,
                success=True,
                metadata={"next_action": next_action},
            )

        except (json.JSONDecodeError, ValueError) as e:
            # Record failure
            failure_record = {
                "error": str(e),
                "raw_response": response.content,
                "prompt": reflection_prompt,
                "timestamp": time.time(),
            }
            if state["reflection_failures"] is None:
                state["reflection_failures"] = []
            failures = cast(list[dict[str, Any]], state["reflection_failures"])
            failures.append(failure_record)
            state["reflection_failures"] = failures
            state["continue_planning"] = False

            # Broadcast reflection error
            if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
                tui_broadcaster.broadcast(
                    "reflection_error",
                    {"error": str(e), "raw_response": response.content},
                )

            # Dashboard Integration: reflection_error
            if dashboard_sender_global:
                dashboard_sender_global.send_event(
                    "reflection_error",
                    {
                        "error": str(e),
                        "raw_response": response.content,
                        "iteration": state.get("current_iteration", 0),
                    },
                )

            # Create fallback response
            fallback_response = f"""I've completed the requested tasks. Here are the results:

{results_text}

Let me know if you need anything else!"""

            state["messages"].append(AIMessage(content=fallback_response))

            # Instrumentation: Record error
            instrumentation.record_error(
                str(e), {"node": "reflect_node", "type": "json_decode"}
            )

            # Metrics: Record failed reflect step
            reflect_duration_ms = (time.perf_counter() - reflect_start_time) * 1000
            metrics_collector.emit_step(
                step_type="reflect",
                duration_ms=reflect_duration_ms,
                success=False,
                error=str(e),
            )

    except Exception as e:
        print(f"Error in reflect_node: {e}")
        state["continue_planning"] = False
        state["messages"].append(
            AIMessage(content=f"I encountered an error while reflecting: {e}")
        )
        # Broadcast reflection error
        if os.getenv("IKOMA_TUI_MODE") == "true" and tui_broadcaster:
            tui_broadcaster.broadcast("reflection_error", {"error": str(e)})

        # Dashboard Integration: reflection_error
        if dashboard_sender_global:
            dashboard_sender_global.send_event(
                "reflection_error",
                {
                    "error": str(e),
                    "iteration": state.get("current_iteration", 0),
                },
            )

        # Instrumentation: Record error
        instrumentation.record_error(
            str(e), {"node": "reflect_node", "type": "exception"}
        )

        # Metrics: Record failed reflect step
        reflect_duration_ms = (time.perf_counter() - reflect_start_time) * 1000
        metrics_collector.emit_step(
            step_type="reflect",
            duration_ms=reflect_duration_ms,
            success=False,
            error=str(e),
        )

    return state


# --- Environment Sanity Check ---
def check_env() -> None:
    """Warn the user when critical environment variables are missing or invalid."""
    critical_vars = [
        "LMSTUDIO_BASE_URL",
        "LMSTUDIO_MODEL",
        "LMSTUDIO_EMBED_MODEL",
        "VECTOR_STORE_PATH",
    ]

    missing_vars = []
    for var in critical_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(
                f"⚠️  ENV WARNING: Required variable {var} is not set. Using default built-in fallback."
            )
        elif var == "VECTOR_STORE_PATH":
            # Warn if the vector store path does not exist (it will be created automatically, but notify the user)
            store_path = Path(value)
            if not store_path.exists():
                print(
                    f"ℹ️  INFO: VECTOR_STORE_PATH {store_path} does not exist yet – it will be created on first use."
                )

    # Validate CHECKPOINTER_ENABLED value
    cpe = os.getenv("CHECKPOINTER_ENABLED")
    if cpe and cpe.lower() not in {"0", "1", "true", "false", "yes", "no"}:
        print(
            f"⚠️  ENV WARNING: CHECKPOINTER_ENABLED value '{cpe}' is invalid – "
            "defaulting to 'true'. Valid values: true/false, yes/no, 1/0"
        )

    # Enhanced validation for GitHub-related variables
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        if len(github_token) < 10:
            print(
                "⚠️  ENV WARNING: GITHUB_TOKEN appears to be too short. Please verify your token."
            )
        elif not github_token.startswith(("ghp_", "github_pat_")):
            print(
                "⚠️  ENV WARNING: GITHUB_TOKEN format appears invalid. Expected format: ghp_... or github_pat_..."
            )

    # Validate search configuration
    search_enabled = os.getenv("SEARCH_ENABLED", "false").lower()
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if search_enabled in {"true", "1", "yes"} and not serpapi_key:
        print(
            "⚠️  ENV WARNING: SEARCH_ENABLED=true but SERPAPI_API_KEY is not set. Web search will be disabled."
        )

    # Validate domain filter configuration
    allow_list = os.getenv("DOMAIN_ALLOW_LIST_PATH", ".allow_domains.txt")
    deny_list = os.getenv("DOMAIN_DENY_LIST_PATH", ".deny_domains.txt")

    if not Path(allow_list).exists():
        print(
            f"ℹ️  INFO: Domain allow list not found at {allow_list} - using default allow list"
        )
    if not Path(deny_list).exists():
        print(
            f"ℹ️  INFO: Domain deny list not found at {deny_list} - using default deny list"
        )

    # Summary if there are issues
    if missing_vars:
        print(f"\n📋 SETUP SUMMARY: {len(missing_vars)} critical variables missing")
        print("   Run './setup.sh' to configure your environment automatically")
        print("   Or copy 'config.env.template' to '.env' and edit as needed")


# --- Agent Setup ---
def create_agent(disable_checkpoint: bool = False) -> Any:
    """Create and configure the enhanced plan-execute-reflect agent.

    Args:
        disable_checkpoint: If True, disable SQLite conversation state persistence
    """
    # Perform environment sanity check once at startup
    check_env()

    # Get environment variables
    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
    model_name = os.getenv("LMSTUDIO_MODEL", "meta-llama-3-8b-instruct")

    # Initialize LLM once for all nodes (Performance optimization)
    llm = ChatOpenAI(
        base_url=base_url,
        model=model_name,
        temperature=0.1,
    )

    # Pre-load tools once (Performance optimization)
    tools = tool_loader.load_tools(llm)

    # Import and initialize vector store for memory functions
    from tools.vector_store import get_vector_store

    store = get_vector_store()

    # --- Checkpointer feature gate ---
    # Prefer new positive flag but honour legacy var for now
    legacy_disabled = os.getenv("IKOMA_DISABLE_CHECKPOINTER")
    if legacy_disabled:
        print(
            "⚠️  DEPRECATION: IKOMA_DISABLE_CHECKPOINTER detected – "
            "use CHECKPOINTER_ENABLED=false instead (will be removed in Phase 3)."
        )

    enabled_env = os.getenv("CHECKPOINTER_ENABLED", "true").lower()
    env_allows = enabled_env not in {"0", "false", "no"}

    checkpointer = None
    if not disable_checkpoint and env_allows and not legacy_disabled:
        db_path = os.getenv("CONVERSATION_DB_PATH", "agent/memory/conversations.sqlite")
        checkpointer = IkomaCheckpointer(db_path)

    # Create closures that capture the shared instances
    def retrieve_memory_with_store(state, config):  # type: ignore[no-untyped-def]
        return retrieve_long_term_memory(state, config, store=store)

    def store_memory_with_store(state, config):  # type: ignore[no-untyped-def]
        return store_long_term_memory(state, config, store=store)

    def plan_node_with_shared_llm(state, config, *, store):  # type: ignore[no-untyped-def]
        return plan_node(state, config, store=store, llm=llm)

    def execute_node_with_shared_tools(state, config, *, store):  # type: ignore[no-untyped-def]
        return execute_node(state, config, store=store, tools=tools)

    def reflect_node_with_shared_llm(state, config, *, store):  # type: ignore[no-untyped-def]
        return reflect_node(state, config, store=store, llm=llm)

    # Create state graph
    workflow = StateGraph(AgentState)

    # Add nodes with shared resources
    workflow.add_node("retrieve_memory", retrieve_memory_with_store)
    workflow.add_node("plan", plan_node_with_shared_llm)
    workflow.add_node("execute", execute_node_with_shared_tools)
    workflow.add_node("reflect", reflect_node_with_shared_llm)
    workflow.add_node("store_memory", store_memory_with_store)

    # Add edges
    workflow.add_edge("retrieve_memory", "plan")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "reflect")
    workflow.add_conditional_edges(
        "reflect",
        should_continue_planning,
        {"plan": "plan", "store_memory": "store_memory"},
    )
    workflow.add_edge("store_memory", END)

    # Set entry point
    workflow.set_entry_point("retrieve_memory")

    # Compile the graph with checkpointer if enabled
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
    else:
        app = workflow.compile()

    return app


def _render_final_response(result: dict) -> None:
    """Render the final response with citations using Rich."""
    # Get the last AI message
    ai_messages = [
        msg for msg in result["messages"] if hasattr(msg, "type") and msg.type == "ai"
    ]
    if ai_messages:
        output = ai_messages[-1].content

        # Initialize citation manager for this conversation
        citation_mgr = ProductionCitationManager()

        # Load citation state from result if available
        if result.get("citations"):
            citation_mgr.from_dict(
                {
                    "citations": result["citations"],
                    "counter": result.get("citation_counter", 1),
                }
            )

        # Render response with citations using Rich
        print("🤖 Ikoma: ", end="")
        citation_mgr.render_response_with_citations(output)
    else:
        print("🤖 Ikoma: I apologize, but I had trouble processing that request.")


def interactive_chat(agent: Any) -> None:
    """Run interactive chat mode."""
    print(
        "🤖 Ikoma: Hello! I'm your AI assistant with enhanced plan-execute-reflect capabilities."
    )
    print(
        "🤖 Ikoma: I can break down complex tasks, execute them systematically, and learn from the results."
    )
    print(
        "🤖 Ikoma: I can help with math calculations and file operations in your sandbox."
    )
    print("🤖 Ikoma: Type 'quit' or 'exit' to end.")
    print("-" * 70)

    # Default user ID - in production, this would come from authentication
    user_id = "default_user"
    thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"

    while True:
        user_input = input("🧑‍💻 You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("🤖 Ikoma: Goodbye! Thanks for using the enhanced planning system.")
            break

        if not user_input:
            continue

        try:
            print("🤖 Ikoma: Planning your request...")

            # Prepare config with user and thread identification
            config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

            # Start metrics session tracking for this interaction
            session_id = f"session_{thread_id}_{int(time.time())}"
            metrics_collector.start_session(session_id)

            # Invoke agent with plan-execute-reflect capabilities
            initial_state: AgentState = {
                "messages": [HumanMessage(content=user_input)],
                "memory_context": None,
                "user_profile": None,
                "session_summary": None,
                "current_plan": None,
                "execution_results": None,
                "reflection": None,
                "continue_planning": False,
                "max_iterations": MAX_ITER,
                "current_iteration": 0,
                "start_time": None,
                "time_limit_secs": None,
                "citations": [],  # Initialize citation tracking
                "citation_counter": 1,  # Initialize citation counter
                "checkpoint_every": None,  # No checkpoints in interactive mode
                "last_checkpoint_iter": 0,
                "stats": {},  # Ensure stats is always present
                "reflection_json": None,
                "reflection_failures": [],
            }

            result = agent.invoke(initial_state, config)
            _render_final_response(result)

            # End metrics session tracking
            final_metrics = metrics_collector.end_session(session_id)
            if final_metrics:
                print(
                    f"📊 Interaction completed: {final_metrics.total_duration_ms:.1f}ms, {final_metrics.iterations} iterations"
                )

        except Exception as e:
            print(f"🤖 Ikoma: I encountered an issue: {e}")
            print(
                "🤖 Ikoma: Please check that your LM Studio server is running on the configured port."
            )

        print("-" * 70)


def main() -> None:
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        prog="ikoma",
        description="Ikoma – local autonomous AI assistant",
    )

    # Add checkpoint subcommand
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Checkpoint subcommand
    from agent.cli.checkpoint_cli import create_checkpoint_parser

    checkpoint_parser = create_checkpoint_parser()
    subparsers.add_parser(
        "checkpoint", parents=[checkpoint_parser], help="Manage checkpoints"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run unattended plan-execute-reflect loop",
    )
    parser.add_argument(
        "--goal",
        type=str,
        help="High-level goal for continuous mode (required with --continuous)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=25,
        help="Iteration cap in continuous mode (default: 25)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        help="Override iteration cap (overrides --max-iterations and environment)",
    )
    parser.add_argument(
        "--time-limit",
        type=int,
        default=MAX_MINS,
        metavar="MIN",
        help=f"Time cap in minutes (default: {MAX_MINS})",
    )
    parser.add_argument(
        "--checkpoint-every",
        "-c",
        type=int,
        default=5,
        help="Human checkpoint every N iterations (default: 5, use --auto to disable)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Disable all human prompts (auto-continue mode)",
    )
    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Disable SQLite conversation state persistence",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Enable rich TUI interface for real-time monitoring",
    )
    parser.add_argument(
        "--demo",
        nargs="?",
        const="online",
        choices=["online", "offline", "continuous"],
        help="Run demo mode with pre-loaded task and TUI enabled (online/offline/continuous)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch dashboard server alongside agent",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8000,
        help="Dashboard server port (default: 8000)",
    )
    args = parser.parse_args()

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Handle demo mode - pre-loads specific tasks and enables TUI
    if getattr(args, "demo", False):
        os.environ["IKOMA_TUI_MODE"] = "true"
        args.tui = True
        args.continuous = True
        args.auto = True

        demo_script = args.demo if args.demo else "online"
        if demo_script == "online":
            args.goal = (
                "Fetch the current weather for New York City and create a simple summary "
                "with the temperature, conditions, and a brief description."
            )
            args.max_iterations = 5
            print("🎬 Demo mode: Simple Weather Fetch")

        elif demo_script == "offline":
            args.goal = (
                "Create a simple text file called 'demo_output.txt' with the content 'Hello from Ikoma demo!' "
                "and then read it back to verify the content."
            )
            args.max_iterations = 3
            os.environ["IKOMA_DISABLE_INTERNET"] = "true"
            print("🎬 Demo mode: Simple File Operations")

        elif demo_script == "continuous":
            args.goal = (
                "Create a memory entry about 'Python best practices', then create another entry about "
                "'Web development tips', and finally read both files and create a summary combining both topics."
            )
            args.max_iterations = 8
            args.time_limit = 10
            os.environ["IKOMA_DISABLE_INTERNET"] = "true"
            print("🎬 Demo mode: Memory Operations & Retrieval")

        print(f"Goal: {args.goal}")
        print("TUI enabled for real-time monitoring")
        print("-" * 70)

    # Set TUI mode environment variable and launch TUI if requested
    if getattr(args, "tui", False):
        os.environ["IKOMA_TUI_MODE"] = "true"
        try:
            import threading

            from agent.ui.tui import IkomaTUI

            tui = IkomaTUI()
            tui_thread = threading.Thread(target=tui.start_monitoring, daemon=True)
            tui_thread.start()
        except ImportError:
            print("[TUI] IkomaTUI could not be imported. TUI will not be shown.")

    # Launch dashboard if requested
    if getattr(args, "dashboard", False):
        try:
            import threading

            import uvicorn

            from dashboard.app import app

            def run_dashboard() -> None:
                host = os.getenv("IKOMA_DASHBOARD_HOST", "127.0.0.1")
                port = args.dashboard_port
                uvicorn.run(app, host=host, port=port, log_level="info")

            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            print(
                f"🌐 Dashboard running at http://{os.getenv('IKOMA_DASHBOARD_HOST', '127.0.0.1')}:{args.dashboard_port}"
            )

            # Enable dashboard events
            if dashboard_sender_global:
                # The original code had a function enable_dashboard_events() here,
                # but it was not defined in the provided file.
                # Assuming it's a placeholder or will be added elsewhere.
                # For now, we'll just print a message if the function is not found.
                print(
                    "[Dashboard] Dashboard events are not enabled as enable_dashboard_events() is not defined."
                )
        except ImportError as e:
            print(f"[Dashboard] Dashboard could not be imported: {e}")
            print("[Dashboard] Make sure FastAPI and uvicorn are installed")
        except Exception as e:
            print(f"[Dashboard] Failed to start dashboard: {e}")

    # Handle checkpoint subcommand
    if args.command == "checkpoint":
        from agent.cli.checkpoint_cli import main as checkpoint_main

        checkpoint_main()
        return

    agent = create_agent(disable_checkpoint=args.no_checkpoint)

    # ---------- Continuous mode ----------
    if args.continuous:
        if not args.goal:
            parser.error("--goal is required when --continuous is set")

        console = Console()
        # Determine checkpoint configuration
        checkpoint_info = ""
        if args.auto:
            checkpoint_info = "Auto-continue mode (no checkpoints)"
        else:
            checkpoint_info = (
                f"Human checkpoints every {args.checkpoint_every} iterations"
            )

        console.print(
            Panel(
                f"[bold yellow]⚠  Continuous mode activated[/bold yellow]\n"
                f"Ikoma will pursue the goal:\n\n[italic]{args.goal}[/italic]\n\n"
                f"Max iterations: {args.max_iterations} · "
                f"Time limit: {args.time_limit} min · "
                f"{checkpoint_info}\n"
                "Press [red]Ctrl-C[/red] to abort at any time.",
                title="Ikoma Autonomy",
                border_style="yellow",
            )
        )

        initial_state = {
            "messages": [HumanMessage(content=args.goal)],
            "memory_context": None,
            "user_profile": None,
            "session_summary": None,
            "current_plan": None,
            "execution_results": None,
            "reflection": None,
            "continue_planning": False,
            "max_iterations": args.max_iter or args.max_iterations,
            "current_iteration": 0,
            "start_time": time.time(),
            "time_limit_secs": args.time_limit * 60,
            "citations": [],
            "citation_counter": 1,
            "checkpoint_every": None if args.auto else args.checkpoint_every,
            "last_checkpoint_iter": 0,
            "stats": {},  # Ensure stats is always present
            "reflection_json": None,
            "reflection_failures": [],
        }

        # Prepare config with user and thread identification
        user_id = "default_user"
        thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

        # Start metrics session tracking
        session_id = f"session_{thread_id}"
        metrics_collector.start_session(session_id)

        try:
            result = agent.invoke(initial_state, config)
            _render_final_response(result)

            # End metrics session tracking
            final_metrics = metrics_collector.end_session(session_id)
            if final_metrics:
                print(
                    f"📊 Session completed: {final_metrics.total_duration_ms:.1f}ms, {final_metrics.iterations} iterations"
                )
        except KeyboardInterrupt:
            console.print("[red]⏹  Aborted by user[/red]")
            # End session even on interruption
            metrics_collector.end_session(session_id)
            sys.exit(1)
        sys.exit(0)

    # ---------- Interactive chat ----------
    interactive_chat(agent)


# --- Main Loop ---
if __name__ == "__main__":
    main()
