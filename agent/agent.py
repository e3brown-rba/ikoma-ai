import os
import re
from pathlib import Path
import openai
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.tools import tool
from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.memory import ConversationBufferMemory
from typing import List

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

# --- File Tools ---
SANDBOX = Path(os.getenv("SANDBOX_PATH", "agent/ikoma_sandbox")).expanduser()

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

def setup_agent():
    """Initializes and returns all the core components of the agent."""
    base_url   = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
    chat_model = os.getenv("LMSTUDIO_MODEL", "meta-llama-3-8b-instruct")
    embed_model = os.getenv(
        "LMSTUDIO_EMBED_MODEL",
        "nomic-ai/nomic-embed-text-v1.5-GGUF",  # safe default embedding model
    )

    llm = ChatOpenAI(
        base_url=base_url,
        model=chat_model,
        temperature=0.1,
    )

    embeddings = PatchedOpenAIEmbeddings(
        openai_api_key="sk-dummy",
        openai_api_base=base_url,
        model=embed_model,
    )

    vectorstore = Chroma(
        persist_directory="agent/memory",
        embedding_function=embeddings,
        collection_name="ikoma_mem"
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})

    math_tools = load_tools(["llm-math"], llm=llm)
    file_tools = [list_sandbox_files, create_text_file, update_text_file, read_text_file]
    tools = math_tools + file_tools

    template = """You are Ikoma, a helpful AI assistant.

TOOLS:
------
You have access to the following tools:
{tools}

CONVERSATION HISTORY (for short-term memory):
----------------------------------------------
{chat_history}

INSTRUCTIONS:
-------------
The user's new input is below. It may include relevant context from your long-term memory. Use this information to inform your response.

To use a tool, you MUST use the following format:
```
Thought: Do I need to use a tool? Yes
Action: The name of the tool to use, chosen from [{tool_names}]
Action Input: The input to the tool
Observation: The result of the tool
```

When you have a response for the user, or if you don't need to use a tool, you MUST use the format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response to the user]
```

Begin!

New input: {input}
{agent_scratchpad}
"""
    prompt = PromptTemplate.from_template(template)

    agent = create_react_agent(llm, tools, prompt)
    # TODO: ConversationBufferMemory is deprecated (LangChain warning).  
    #       Migrate to the new LangGraph memory per
    #       https://python.langchain.com/docs/versions/migrating_memory/
    memory = ConversationBufferMemory(memory_key="chat_history")
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=3,
        memory=memory
    )

    def save_to_memory(input_str, output_str):
        """Saves the conversation to the vector store."""
        vectorstore.add_texts([f"User: {input_str}", f"AI: {output_str}"])

    return agent_executor, retriever, save_to_memory

# --- Main Loop ---
if __name__ == "__main__":
    agent_executor, retriever, save_to_memory = setup_agent()
    
    print("🤖 Ikoma: Hello! I can help with conversations, math, and file management.")
    print("🤖 Ikoma: File operations are limited to the sandbox directory for safety.")
    print("🤖 Ikoma: Type 'quit' or 'exit' to end.")
    print("-" * 50)

    while True:
        user_input = input("🧑‍💻 You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("🤖 Ikoma: Goodbye!")
            break
        
        if not user_input:
            continue

        try:
            print("🤖 Ikoma: Let me think about that...")
            
            retrieved_docs = retriever.invoke(user_input)
            retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])
            
            combined_input = (
                "CONTEXT FROM LONG-TERM MEMORY:\n"
                f"{retrieved_context}\n\n"
                "---\n\n"
                f"USER'S QUESTION:\n{user_input}"
            )
            
            response = agent_executor.invoke({"input": combined_input})
            output = response.get('output', 'I apologize, but I had trouble processing that request.')
            print(f"🤖 Ikoma: {output}")

            save_to_memory(user_input, output)
            
        except Exception as e:
            print(f"🤖 Ikoma: I encountered an issue: {e}")
            try:
                fallback_response = llm.invoke(f"You are Ikoma, a helpful AI assistant. Respond to: {user_input}")
                print(f"🤖 Ikoma: {fallback_response.content}")
            except:
                print("🤖 Ikoma: I'm having connection issues. Please check your LM Studio server.")
        
        print("-" * 50) 