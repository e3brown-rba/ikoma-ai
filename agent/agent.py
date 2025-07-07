import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
# Checkpoint functionality temporarily disabled due to langgraph version changes
# from langgraph_checkpoint.sqlite import SqliteSaver

from typing import List, Dict, Any, TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
import uuid
from datetime import datetime
from tools.tool_loader import tool_loader

# Load environment variables from .env file
load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-dummy"



# --- Enhanced State Definition ---
class AgentState(TypedDict):
    """Enhanced state schema for plan-execute-reflect architecture."""
    messages: Annotated[List[Any], add_messages]
    memory_context: Optional[str]
    user_profile: Optional[Dict[str, Any]]
    session_summary: Optional[str]
    current_plan: Optional[List[Dict[str, Any]]]
    execution_results: Optional[List[Dict[str, Any]]]
    reflection: Optional[str]
    continue_planning: bool
    max_iterations: int
    current_iteration: int

# --- File Tools moved to tools/fs_tools.py ---
# Tools are now loaded dynamically via tools/tool_loader.py

# --- Memory Management Functions ---
def retrieve_long_term_memory(state: AgentState, config: dict, *, store) -> AgentState:
    """Retrieve relevant long-term memories based on current context."""
    try:
        # Extract user ID from config
        user_id = config.get("configurable", {}).get("user_id", "default")
        
        # Get the last user message for context
        user_messages = [msg for msg in state["messages"] if hasattr(msg, 'type') and msg.type == "human"]
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
                    if hasattr(memory, 'value'):
                        content = memory.value.get('content', '')
                    elif isinstance(memory, dict):
                        content = memory.get('content', '')
                    else:
                        content = str(memory)
                    memory_context += f"- {content}\n"
                
                state["memory_context"] = memory_context
        except Exception as e:
            print(f"Warning: Could not retrieve memories: {e}")
            
    except Exception as e:
        print(f"Error in retrieve_long_term_memory: {e}")
    
    return state

def store_long_term_memory(state: AgentState, config: dict, *, store) -> AgentState:
    """Store important information to long-term memory."""
    try:
        # Extract user ID from config
        user_id = config.get("configurable", {}).get("user_id", "default")
        
        # Get the last few messages for context
        recent_messages = state["messages"][-4:] if len(state["messages"]) >= 4 else state["messages"]
        
        # Extract memorable content (enhanced logic)
        memorable_content = []
        for msg in recent_messages:
            if hasattr(msg, 'content') and msg.content:
                # Enhanced heuristic: store based on keywords, length, and execution results
                if any(keyword in msg.content.lower() for keyword in ['prefer', 'like', 'remember', 'important', 'project', 'task', 'learn']):
                    memorable_content.append(msg.content)
                elif len(msg.content) > 100:  # Store longer interactions
                    memorable_content.append(msg.content)
        
        # Also store successful execution patterns
        if state.get("execution_results"):
            for result in state["execution_results"]:
                if result.get("status") == "success":
                    memorable_content.append(f"Successful execution: {result.get('tool_name')} with {result.get('args')}")
        
        # Store memories if we have content worth remembering
        if memorable_content:
            namespace = ("memories", user_id)
            memory_id = str(uuid.uuid4())
            
            memory_entry = {
                "content": " ".join(memorable_content),
                "timestamp": datetime.now().isoformat(),
                "context": "conversation",
                "plan_context": state.get("current_plan"),
                "reflection": state.get("reflection")
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
def plan_node(state: AgentState, config: dict, *, store, llm) -> AgentState:
    """Optimized plan_node that uses shared LLM instance."""
    try:
        # Get tool descriptions
        tool_descriptions = tool_loader.get_tool_descriptions()
        
        # Build planning prompt
        planning_prompt = f"""You are a planning assistant. Based on the user's request, create a detailed plan of tool calls.

Available tools:
{tool_descriptions}

Your task is to analyze the user's request and create a JSON plan with the following structure:
```json
{{
  "plan": [
    {{
      "step": 1,
      "tool_name": "tool_name",
      "args": {{"arg1": "value1", "arg2": "value2"}},
      "description": "What this step accomplishes"
    }}
  ],
  "reasoning": "Why this plan will achieve the user's goal"
}}
```

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

Tool argument examples:
- list_sandbox_files: {{"query": ""}} or {{"query": "search_term"}}
- read_text_file: {{"filename": "file.txt"}}
- create_text_file: {{"filename_and_content": "file.txt|||content here"}}
- update_text_file: {{"filename_and_content": "file.txt|||new content"}}
- Calculator: {{"question": "2 + 2"}}

User's request: {state["messages"][-1].content}

Remember: Return ONLY valid JSON, no other text."""
        
        # Add memory context if available
        if state.get("memory_context"):
            planning_prompt += f"\n\nRelevant context from previous conversations:\n{state['memory_context']}"
        
        # Get plan from LLM
        response = llm.invoke([HumanMessage(content=planning_prompt)])
        
        # Guard against empty response
        if not response.content.strip():
            raise ValueError("Empty response from LLM")
        
        # Parse the plan
        try:
            # Extract JSON from response
            plan_text = response.content.strip()
            if plan_text.startswith("```json"):
                plan_text = plan_text[7:-3].strip()
            elif plan_text.startswith("```"):
                plan_text = plan_text[3:-3].strip()
            
            plan_data = json.loads(plan_text)
            plan = plan_data.get("plan", [])
            
            # Validate plan structure
            for step in plan:
                if not all(key in step for key in ["step", "tool_name", "args", "description"]):
                    raise ValueError("Invalid plan structure")
            
            state["current_plan"] = plan
            state["continue_planning"] = True
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing plan: {e}")
            # Intelligent fallback based on request type
            user_request = state["messages"][-1].content.lower()
            
            if any(word in user_request for word in ["meaning", "life", "philosophy", "existential", "purpose"]):
                # For philosophical questions, acknowledge the limitation
                # Check if the file already exists to make this idempotent
                import os
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
                
                state["current_plan"] = [{
                    "step": 1,
                    "tool_name": tool_name,
                    "args": {"filename_and_content": "philosophical_response.txt|||I understand you're asking about the meaning of life, which is a profound philosophical question that has been contemplated by thinkers throughout history. While I can help with practical tasks using available tools, I cannot provide definitive answers to such existential questions. I'd be happy to help you with concrete tasks, calculations, or file operations instead."},
                    "description": description
                }]
            else:
                # For other requests, try to list files as starting point
                state["current_plan"] = [{
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List available files as a starting point"
                }]
            state["continue_planning"] = True
        
    except Exception as e:
        print(f"Error in plan_node: {e}")
        state["current_plan"] = []
        state["continue_planning"] = False
    
    return state

def execute_node(state: AgentState, config: dict, *, store, tools) -> AgentState:
    """Optimized execute_node that uses shared tools."""
    try:
        # Execute each step in the plan
        execution_results = []
        
        for step in state.get("current_plan", []):
            tool_name = step["tool_name"]
            args = step["args"]
            description = step["description"]
            
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
                execution_results.append({
                    "step": step["step"],
                    "tool_name": tool_name,
                    "args": args,
                    "description": description,
                    "status": "error",
                    "result": f"Tool '{tool_name}' not found"
                })
                continue
            
            # Execute the tool
            try:
                # Handle different tool argument formats
                if tool_name == "Calculator" or (tool_name == "llm-math" and t.name == "Calculator"):
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
                
                execution_results.append({
                    "step": step["step"],
                    "tool_name": tool_name,
                    "args": args,
                    "description": description,
                    "status": "success",
                    "result": str(result)
                })
                
            except Exception as e:
                execution_results.append({
                    "step": step["step"],
                    "tool_name": tool_name,
                    "args": args,
                    "description": description,
                    "status": "error",
                    "result": f"Error executing tool: {e}"
                })
        
        state["execution_results"] = execution_results
        
    except Exception as e:
        print(f"Error in execute_node: {e}")
        state["execution_results"] = [{
            "step": 1,
            "tool_name": "unknown",
            "args": {},
            "description": "Execution failed",
            "status": "error",
            "result": f"Execution error: {e}"
        }]
    
    return state

def reflect_node(state: AgentState, config: dict, *, store, llm) -> AgentState:
    """Optimized reflect_node that uses shared LLM instance."""
    try:
        # Increment iteration counter
        state["current_iteration"] = state.get("current_iteration", 0) + 1
        
        # Format execution results for reflection
        results_summary = []
        for result in state.get("execution_results", []):
            status = "✓" if result["status"] == "success" else "✗"
            results_summary.append(f"{status} Step {result['step']}: {result['description']} -> {result['result']}")
        
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
            raise ValueError("Empty response from LLM")
        
        # Parse reflection
        try:
            reflection_text = response.content.strip()
            if reflection_text.startswith("```json"):
                reflection_text = reflection_text[7:-3].strip()
            elif reflection_text.startswith("```"):
                reflection_text = reflection_text[3:-3].strip()
            
            reflection_data = json.loads(reflection_text)
            
            # Determine next action
            task_completed = reflection_data.get("task_completed", False)
            next_action = reflection_data.get("next_action", "end")
            max_iterations = state.get("max_iterations", 3)
            current_iteration = state.get("current_iteration", 1)
            
            # Decision logic
            if task_completed or next_action == "end" or current_iteration >= max_iterations:
                state["continue_planning"] = False
                
                # Create final response
                final_response = f"""Task completed! Here's what I accomplished:

{reflection_data.get('summary', 'Task execution completed.')}

Execution Details:
{results_text}

Success Rate: {reflection_data.get('success_rate', 'N/A')}"""
                
                state["messages"].append(AIMessage(content=final_response))
            else:
                state["continue_planning"] = True
            
            state["reflection"] = reflection_data.get("reasoning", "Reflection completed")
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing reflection: {e}")
            # Fallback decision
            state["continue_planning"] = False
            
            # Create fallback response
            fallback_response = f"""I've completed the requested tasks. Here are the results:

{results_text}

Let me know if you need anything else!"""
            
            state["messages"].append(AIMessage(content=fallback_response))
        
    except Exception as e:
        print(f"Error in reflect_node: {e}")
        state["continue_planning"] = False
        state["messages"].append(AIMessage(content=f"I encountered an error while reflecting: {e}"))
    
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
    for var in critical_vars:
        value = os.getenv(var)
        if not value:
            print(f"⚠️  ENV WARNING: Required variable {var} is not set. Using default built-in fallback.")
        elif var == "VECTOR_STORE_PATH":
            # Warn if the vector store path does not exist (it will be created automatically, but notify the user)
            store_path = Path(value)
            if not store_path.exists():
                print(f"ℹ️  INFO: VECTOR_STORE_PATH {store_path} does not exist yet – it will be created on first use.")

# --- Agent Setup ---
def create_agent():
    """Create and configure the enhanced plan-execute-reflect agent."""
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
    
    # Initialize checkpointer for short-term memory (conversation state)
    # checkpointer = SqliteSaver("agent/memory/conversations.sqlite")  # Temporarily disabled
    
    # Create closures that capture the shared instances
    def retrieve_memory_with_store(state, config):
        return retrieve_long_term_memory(state, config, store=store)
    
    def store_memory_with_store(state, config):
        return store_long_term_memory(state, config, store=store)
    
    def plan_node_with_shared_llm(state, config, *, store):
        return plan_node(state, config, store=store, llm=llm)
    
    def execute_node_with_shared_tools(state, config, *, store):
        return execute_node(state, config, store=store, tools=tools)
    
    def reflect_node_with_shared_llm(state, config, *, store):
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
        {
            "plan": "plan",
            "store_memory": "store_memory"
        }
    )
    workflow.add_edge("store_memory", END)
    
    # Set entry point
    workflow.set_entry_point("retrieve_memory")
    
    # Compile the graph
    app = workflow.compile()  # LangGraph 0.5.1+ doesn't need store parameter
    
    return app

# --- Main Loop ---
if __name__ == "__main__":
    agent = create_agent()
    
    print("🤖 Ikoma: Hello! I'm your AI assistant with enhanced plan-execute-reflect capabilities.")
    print("🤖 Ikoma: I can break down complex tasks, execute them systematically, and learn from the results.")
    print("🤖 Ikoma: I can help with math calculations and file operations in your sandbox.")
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
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": user_id
                }
            }
            
            # Invoke agent with plan-execute-reflect capabilities
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "memory_context": None,
                "user_profile": None,
                "session_summary": None,
                "current_plan": None,
                "execution_results": None,
                "reflection": None,
                "continue_planning": False,
                "max_iterations": 3,
                "current_iteration": 0
            }
            
            result = agent.invoke(initial_state, config)
            
            # Get the last AI message
            ai_messages = [msg for msg in result["messages"] if hasattr(msg, 'type') and msg.type == "ai"]
            if ai_messages:
                output = ai_messages[-1].content
                print(f"🤖 Ikoma: {output}")
            else:
                print("🤖 Ikoma: I apologize, but I had trouble processing that request.")
            
        except Exception as e:
            print(f"🤖 Ikoma: I encountered an issue: {e}")
            print("🤖 Ikoma: Please check that your LM Studio server is running on the configured port.")
        
        print("-" * 70)

