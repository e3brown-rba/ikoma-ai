import os
import re
from pathlib import Path
import openai
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any, TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
import uuid
from datetime import datetime

# Load environment variables from .env file
load_dotenv()
os.environ["OPENAI_API_KEY"] = "sk-dummy"

# --- Patched Embeddings Class ---
class PatchedOpenAIEmbeddings(OpenAIEmbeddings):
    """
    A patch to handle local servers that do not support batching. This patch
    iterates through all documents and embeds them one by one.
    """
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        temp_client = openai.OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base
        )
        response = temp_client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

# --- State Definition ---
class AgentState(TypedDict):
    """State schema for the agent with unified memory capabilities."""
    messages: Annotated[List[Any], add_messages]
    memory_context: Optional[str]
    user_profile: Optional[Dict[str, Any]]
    session_summary: Optional[str]

# --- File Tools ---
SANDBOX = Path(os.getenv("SANDBOX_PATH", "agent/ikoma_sandbox")).expanduser()

def confirm_destructive_action(action_description: str, filename: str) -> bool:
    """Ask user for confirmation before performing destructive file operations."""
    print(f"\n⚠️  CONFIRMATION REQUIRED:")
    print(f"   Action: {action_description}")
    print(f"   File: {filename}")
    
    while True:
        response = input("   Continue? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("   Please enter 'yes' or 'no'")

@tool
def list_sandbox_files(query: str = "") -> str:
    """List all files in the sandbox directory. No input needed."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        files = os.listdir(SANDBOX)
        if not files:
            return "📁 Sandbox directory is empty. Create some files to get started!"
        file_list = [f"📄 {file} ({os.path.getsize(os.path.join(SANDBOX, file))} bytes)" for file in files]
        return "Files in sandbox:\n" + "\n".join(file_list)
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def update_text_file(filename_and_content: str) -> str:
    """Update/modify an existing text file in the sandbox. Format: filename|||new_content"""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||new_content'"
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(SANDBOX, filename)
        if not os.path.exists(filepath):
            return f"File '{filename}' not found. Use create_text_file to create new files."
        
        # Request confirmation before overwriting
        if not confirm_destructive_action("Overwrite existing file", filename):
            return f"❌ Operation cancelled: File '{filename}' was not modified."
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✓ Updated file: {filename} with new content."
    except Exception as e:
        return f"Error updating file: {e}"

@tool
def create_text_file(filename_and_content: str) -> str:
    """Create a NEW text file in the sandbox. Format: filename|||content"""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||content'"
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(SANDBOX, filename)
        if os.path.exists(filepath):
            return f"File '{filename}' already exists. Use update_text_file."
        
        # Request confirmation before creating new file
        if not confirm_destructive_action("Create new file", filename):
            return f"❌ Operation cancelled: File '{filename}' was not created."
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✓ Created file: {filename} with content."
    except Exception as e:
        return f"Error creating file: {e}"

@tool
def read_text_file(filename: str) -> str:
    """Read a text file from the sandbox. If no filename provided, list available files."""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    try:
        filename = filename.strip()
        if not filename:
            files = os.listdir(SANDBOX)
            return f"Available files: {', '.join(files)}" if files else "No files in sandbox."
        if not filename.endswith('.txt'):
            filename += '.txt'
        filepath = os.path.join(SANDBOX, filename)
        if not os.path.exists(filepath):
            files = os.listdir(SANDBOX)
            return f"File '{filename}' not found. Available: {', '.join(files) if files else 'none'}"
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

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
                    memory_context += f"- {memory.value.get('content', '')}\n"
                
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
        
        # Extract memorable content (simplified logic)
        memorable_content = []
        for msg in recent_messages:
            if hasattr(msg, 'content') and msg.content:
                # Simple heuristic: store if it contains certain keywords or is sufficiently long
                if any(keyword in msg.content.lower() for keyword in ['prefer', 'like', 'remember', 'important', 'project', 'task']):
                    memorable_content.append(msg.content)
        
        # Store memories if we have content worth remembering
        if memorable_content:
            namespace = ("memories", user_id)
            memory_id = str(uuid.uuid4())
            
            memory_entry = {
                "content": " ".join(memorable_content),
                "timestamp": datetime.now().isoformat(),
                "context": "conversation"
            }
            
            try:
                store.put(namespace, memory_id, memory_entry)
            except Exception as e:
                print(f"Warning: Could not store memory: {e}")
                
    except Exception as e:
        print(f"Error in store_long_term_memory: {e}")
    
    return state

def agent_response(state: AgentState, config: dict, *, store) -> AgentState:
    """Generate agent response using LLM with memory context."""
    try:
        # Get environment variables
        base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
        model_name = os.getenv("LMSTUDIO_MODEL", "meta-llama-3-8b-instruct")
        
        # Initialize LLM
        llm = ChatOpenAI(
            base_url=base_url,
            model=model_name,
            temperature=0.1,
        )
        
        # Prepare tools
        math_tools = load_tools(["llm-math"], llm=llm)
        file_tools = [list_sandbox_files, create_text_file, update_text_file, read_text_file]
        tools = math_tools + file_tools
        
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)
        
        # Build system message with memory context
        system_content = """You are Ikoma, a helpful AI assistant with memory capabilities.

You have access to the following tools:
- Math calculations (llm-math)
- File operations (create, read, update, list files in sandbox)

For file operations, always use the exact format specified in the tool descriptions.

If you have relevant context from previous conversations, use it to provide more personalized responses."""
        
        # Add memory context if available
        if state.get("memory_context"):
            system_content += f"\n\n{state['memory_context']}"
        
        # Prepare messages
        messages = [SystemMessage(content=system_content)] + state["messages"]
        
        # Get response
        response = llm_with_tools.invoke(messages)
        
        # Handle tool calls if present
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Execute tools and get results
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                
                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            result = tool.invoke(tool_args)
                            tool_results.append(f"{tool_name}: {result}")
                        except Exception as e:
                            tool_results.append(f"{tool_name}: Error - {e}")
                        break
            
            # Create final response with tool results
            if tool_results:
                final_content = response.content + "\n\nTool Results:\n" + "\n".join(tool_results)
                response = AIMessage(content=final_content)
        
        return {"messages": [response]}
        
    except Exception as e:
        error_msg = f"I encountered an error: {e}"
        return {"messages": [AIMessage(content=error_msg)]}

# --- Agent Setup ---
def create_agent():
    """Create and configure the memory-enhanced agent."""
    # Get environment variables
    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
    embed_model = os.getenv("LMSTUDIO_EMBED_MODEL", "nomic-ai/nomic-embed-text-v1.5-GGUF")
    
    # Initialize embeddings for semantic search
    embeddings = PatchedOpenAIEmbeddings(
        openai_api_key="sk-dummy",
        openai_api_base=base_url,
        model=embed_model,
    )
    
    # Initialize memory store for long-term memory
    store = InMemoryStore()
    
    # Initialize checkpointer for short-term memory (conversation state)
    checkpointer = SqliteSaver("agent/memory/conversations.sqlite")
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve_memory", retrieve_long_term_memory)
    workflow.add_node("agent_response", agent_response)
    workflow.add_node("store_memory", store_long_term_memory)
    
    # Add edges
    workflow.add_edge("retrieve_memory", "agent_response")
    workflow.add_edge("agent_response", "store_memory")
    workflow.add_edge("store_memory", END)
    
    # Set entry point
    workflow.set_entry_point("retrieve_memory")
    
    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer, store=store)
    
    return app

# --- Main Loop ---
if __name__ == "__main__":
    agent = create_agent()
    
    print("🤖 Ikoma: Hello! I'm your AI assistant with enhanced memory capabilities.")
    print("🤖 Ikoma: I can remember our conversations and help with math and file operations.")
    print("🤖 Ikoma: Type 'quit' or 'exit' to end.")
    print("-" * 50)
    
    # Default user ID - in production, this would come from authentication
    user_id = "default_user"
    thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
    
    while True:
        user_input = input("🧑‍💻 You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("🤖 Ikoma: Goodbye!")
            break
        
        if not user_input:
            continue

        try:
            print("🤖 Ikoma: Let me think about that...")
            
            # Prepare config with user and thread identification
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": user_id
                }
            }
            
            # Invoke agent with memory capabilities
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "memory_context": None,
                "user_profile": None,
                "session_summary": None
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
            print("🤖 Ikoma: Please check that your LM Studio server is running.")
        
        print("-" * 50)

# TODO: Add a cronable reflection job (reflect.py)
#   Each night, summarise the day's (User, AI) pairs into "lessons learned"
#   and append those summaries to long-term memory for improved responses. 