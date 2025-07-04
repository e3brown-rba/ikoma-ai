import os
import re
os.environ["OPENAI_API_KEY"] = "sk-dummy"

from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.tools import tool

# --- 1. Setup LLM and Tools ---
llm = ChatOpenAI(
    base_url="http://127.0.0.1:11434/v1",
    model="meta-llama-3-8b-instruct",
    temperature=0.1,
)

# Define sandbox directory
SANDBOX = os.path.join(os.getcwd(), "ikoma_sandbox")

# Ensure sandbox directory exists
os.makedirs(SANDBOX, exist_ok=True)

# --- 2. Simplified File Tools ---
@tool
def list_sandbox_files(query: str = "") -> str:
    """List all files in the sandbox directory. No input needed."""
    try:
        files = os.listdir(SANDBOX)
        if not files:
            return "📁 Sandbox directory is empty. Create some files to get started!"
        
        file_list = []
        for file in files:
            filepath = os.path.join(SANDBOX, file)
            size = os.path.getsize(filepath)
            file_list.append(f"📄 {file} ({size} bytes)")
        
        return "Files in sandbox:\n" + "\n".join(file_list)
    except Exception as e:
        return f"Error listing files: {e}"

@tool
def update_text_file(filename_and_content: str) -> str:
    """Update/modify an existing text file in the sandbox. Format: filename|||new_content"""
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||new_content'"
        
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        content = content.strip()
        
        # Auto-add .txt extension if not present
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        filepath = os.path.join(SANDBOX, filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            return f"File '{filename}' not found. Use create_text_file to create new files."
        
        # Update the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✓ Updated file: {filename} with new content: '{content}'"
    except Exception as e:
        return f"Error updating file: {e}"

@tool
def create_text_file(filename_and_content: str) -> str:
    """Create a NEW text file in the sandbox. Format: filename|||content"""
    try:
        if "|||" not in filename_and_content:
            return "Error: Use format 'filename|||content'"
        
        filename, content = filename_and_content.split("|||", 1)
        filename = filename.strip()
        content = content.strip()
        
        # Safety check - only allow .txt files for now
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        filepath = os.path.join(SANDBOX, filename)
        
        # Check if file already exists
        if os.path.exists(filepath):
            return f"File '{filename}' already exists. Use update_text_file to modify existing files."
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✓ Created file: {filename} with content: '{content}'"
    except Exception as e:
        return f"Error creating file: {e}"

@tool
def read_text_file(filename: str) -> str:
    """Read a text file from the sandbox. If no filename provided, list available files."""
    try:
        filename = filename.strip()
        
        # If no meaningful filename provided, list available files
        if not filename or filename.lower() in ['', 'no input needed', 'just execute the action']:
            files = os.listdir(SANDBOX)
            if not files:
                return "No files in sandbox. Please create a file first."
            return f"Available files in sandbox: {', '.join(files)}. Please specify which file to read."
        
        # Auto-add .txt extension if not present
        if not filename.endswith('.txt'):
            filename += '.txt'
        
        filepath = os.path.join(SANDBOX, filename)
        if not os.path.exists(filepath):
            # List available files to help user
            files = os.listdir(SANDBOX)
            available = ', '.join(files) if files else 'none'
            return f"File '{filename}' not found in sandbox. Available files: {available}"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Contents of {filename}:\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"

# Load tools
math_tools = load_tools(["llm-math"], llm=llm)
file_tools = [list_sandbox_files, create_text_file, update_text_file, read_text_file]
tools = math_tools + file_tools

# --- 3. Simplified Prompt ---
template = """You are Ikoma, a helpful AI assistant with access to tools for file management and calculations.

Available tools:
{tools}

To use a tool, you MUST follow this exact format:

Question: {input}
Thought: I need to analyze what the user is asking for
Action: [tool name]
Action Input: [input for the tool]
Observation: [result will appear here]
Thought: I can now respond based on the result
Final Answer: [your response to the user]

Available tool names: {tool_names}

Remember:
- Use create_text_file for NEW files
- Use update_text_file for EXISTING files (modify/change content)
- Use read_text_file to read file contents
- Use list_sandbox_files to see all files
- For calculations, use Calculator
- Be specific with filenames

Rules:
- After you receive a valid Observation from a tool, IMMEDIATELY provide a Final Answer and stop.
- Do NOT repeat the same action or tool call if you already have the information.

{agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

# --- 4. Create Agent ---
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,  # Clean output
    handle_parsing_errors=True,
    max_iterations=3,  # Increase back to 3
    return_intermediate_steps=False
)

# --- 5. Memory ---
chat_history_store = {}

agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    lambda session_id: chat_history_store.get(session_id, ChatMessageHistory()),
    input_messages_key="input",
    history_messages_key="chat_history",
)

# --- 6. Main Loop ---
print("🤖 Ikoma: Hello! I can help with conversations, math, and file management.")
print("🤖 Ikoma: File operations are limited to the sandbox directory for safety.")
print("🤖 Ikoma: Type 'quit' or 'exit' to end.")
print("-" * 50)

while True:
    user_input = input("🧑‍💻 You: ").strip()
    if user_input.lower() in {"quit", "exit", "q"}:
        print("🤖 Ikoma: Goodbye!")
        break
    
    if not user_input:  # Skip empty inputs
        continue

    try:
        # Simplified call without memory for debugging
        print("🤖 Ikoma: Let me think about that...")
        
        response = agent_executor.invoke({"input": user_input})
        
        # Clean output - just show the final answer
        output = response.get('output', 'I apologize, but I had trouble processing that request.')
        print(f"🤖 Ikoma: {output}")
        
    except Exception as e:
        print(f"🤖 Ikoma: I encountered an issue. Let me try a different approach...")
        # Simple fallback without showing technical errors
        try:
            fallback_response = llm.invoke(f"You are Ikoma, a helpful AI assistant. Respond to: {user_input}")
            print(f"🤖 Ikoma: {fallback_response.content}")
        except:
            print("🤖 Ikoma: I'm having connection issues. Please check your LM Studio server.")
    
    print("-" * 50) 