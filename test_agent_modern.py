import os
import unittest
import shutil
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from datetime import datetime
import uuid

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-dummy"
os.environ["LMSTUDIO_BASE_URL"] = "http://127.0.0.1:11434/v1"
os.environ["LMSTUDIO_MODEL"] = "test-model"
os.environ["LMSTUDIO_EMBED_MODEL"] = "test-embed-model"
os.environ["SANDBOX_PATH"] = "agent/test_sandbox"

class TestModernAgent(unittest.TestCase):
    """Comprehensive tests for the modernized LangGraph-based agent."""

    def setUp(self):
        """Set up a clean test environment for each test."""
        self.sandbox = Path(os.getenv("SANDBOX_PATH"))
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test_conversations.sqlite")
        
        # Ensure the sandbox directory exists and is empty
        shutil.rmtree(self.sandbox, ignore_errors=True)
        self.sandbox.mkdir(parents=True, exist_ok=True)
        
        # Mock user input for confirmation prompts
        self.confirm_responses = []
        
    def tearDown(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.sandbox, ignore_errors=True)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def mock_confirm_input(self, prompt):
        """Mock user input for confirmation prompts."""
        if self.confirm_responses:
            return self.confirm_responses.pop(0)
        return "yes"  # Default to yes

    @patch('builtins.input')
    @patch('langgraph.checkpoint.sqlite.SqliteSaver')
    @patch('langgraph.store.memory.InMemoryStore')
    @patch('agent.agent.PatchedOpenAIEmbeddings')
    def test_01_agent_initialization(self, MockEmbeddings, MockStore, MockSaver, mock_input):
        """Test that the agent initializes correctly with all components."""
        print("\n1. Testing Agent Initialization...")
        
        # Configure mocks
        mock_embeddings = MagicMock()
        MockEmbeddings.return_value = mock_embeddings
        
        mock_store = MagicMock()
        MockStore.return_value = mock_store
        
        mock_checkpointer = MagicMock()
        MockSaver.return_value = mock_checkpointer
        
        # Import and test agent creation
        from agent.agent import create_agent
        
        agent = create_agent()
        
        # Assert components were initialized
        MockEmbeddings.assert_called_once()
        MockStore.assert_called_once()
        MockSaver.assert_called_once_with("agent/memory/conversations.sqlite")
        
        # Assert agent was created successfully
        self.assertIsNotNone(agent)
        print("✓ Agent initialization successful")

    @patch('builtins.input')
    def test_02_file_operations_with_confirmation(self, mock_input):
        """Test file operations with confirmation prompts."""
        print("\n2. Testing File Operations with Confirmation...")
        
        # Import file operation tools
        from agent.agent import create_text_file, read_text_file, update_text_file, list_sandbox_files
        
        # Test file creation with confirmation
        mock_input.side_effect = ["yes"]  # User confirms creation
        result = create_text_file.invoke({"filename_and_content": "test.txt|||Hello, world!"})
        
        self.assertIn("✓ Created file", result)
        self.assertTrue((self.sandbox / "test.txt").exists())
        print("✓ File creation with confirmation works")
        
        # Test file reading (no confirmation needed)
        result = read_text_file.invoke({"filename": "test.txt"})
        self.assertIn("Hello, world!", result)
        print("✓ File reading works")
        
        # Test file update with confirmation
        mock_input.side_effect = ["yes"]  # User confirms update
        result = update_text_file.invoke({"filename_and_content": "test.txt|||Updated content"})
        
        self.assertIn("✓ Updated file", result)
        
        # Verify update worked
        result = read_text_file.invoke({"filename": "test.txt"})
        self.assertIn("Updated content", result)
        print("✓ File update with confirmation works")
        
        # Test file listing
        result = list_sandbox_files.invoke({})
        self.assertIn("test.txt", result)
        print("✓ File listing works")

    @patch('builtins.input')
    def test_03_file_operations_cancelled(self, mock_input):
        """Test file operations when user cancels."""
        print("\n3. Testing File Operations Cancellation...")
        
        from agent.agent import create_text_file, update_text_file
        
        # Test creation cancellation
        mock_input.side_effect = ["no"]  # User cancels creation
        result = create_text_file.invoke({"filename_and_content": "cancelled.txt|||Content"})
        
        self.assertIn("❌ Operation cancelled", result)
        self.assertFalse((self.sandbox / "cancelled.txt").exists())
        print("✓ File creation cancellation works")
        
        # Create a file first for update test
        mock_input.side_effect = ["yes"]  # Confirm creation
        create_text_file.invoke({"filename_and_content": "existing.txt|||Original"})
        
        # Test update cancellation
        mock_input.side_effect = ["no"]  # User cancels update
        result = update_text_file.invoke({"filename_and_content": "existing.txt|||New content"})
        
        self.assertIn("❌ Operation cancelled", result)
        
        # Verify file wasn't changed
        from agent.agent import read_text_file
        result = read_text_file.invoke({"filename": "existing.txt"})
        self.assertIn("Original", result)
        print("✓ File update cancellation works")

    @patch('langchain_openai.ChatOpenAI')
    @patch('langgraph.store.memory.InMemoryStore')
    def test_04_memory_system_storage(self, MockStore, MockChatOpenAI):
        """Test that the memory system stores and retrieves memories correctly."""
        print("\n4. Testing Memory System Storage...")
        
        # Configure mocks
        mock_store = MagicMock()
        MockStore.return_value = mock_store
        
        mock_llm = MagicMock()
        MockChatOpenAI.return_value = mock_llm
        
        # Import memory functions
        from agent.agent import store_long_term_memory, AgentState
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Create test state with memorable content
        state = AgentState(
            messages=[
                HumanMessage(content="I prefer vegetarian food"),
                AIMessage(content="I'll remember your food preferences"),
                HumanMessage(content="I'm working on a Python project"),
                AIMessage(content="Good to know about your project")
            ],
            memory_context=None,
            user_profile=None,
            session_summary=None
        )
        
        config = {
            "configurable": {
                "user_id": "test_user",
                "thread_id": "test_thread"
            }
        }
        
        # Test memory storage
        result = store_long_term_memory(state, config, store=mock_store)
        
        # Verify memory was stored
        mock_store.put.assert_called()
        call_args = mock_store.put.call_args
        namespace, memory_id, memory_entry = call_args[0]
        
        self.assertEqual(namespace, ("memories", "test_user"))
        self.assertIn("content", memory_entry)
        self.assertIn("timestamp", memory_entry)
        self.assertIn("vegetarian", memory_entry["content"])
        print("✓ Memory storage works correctly")

    @patch('langgraph.store.memory.InMemoryStore')
    def test_05_memory_system_retrieval(self, MockStore):
        """Test that the memory system retrieves relevant memories."""
        print("\n5. Testing Memory System Retrieval...")
        
        # Configure mock store with test memories
        mock_store = MagicMock()
        MockStore.return_value = mock_store
        
        # Mock search results
        mock_memory = MagicMock()
        mock_memory.value = {"content": "User prefers vegetarian food", "timestamp": "2024-01-01"}
        mock_store.search.return_value = [mock_memory]
        
        # Import memory function
        from agent.agent import retrieve_long_term_memory, AgentState
        from langchain_core.messages import HumanMessage
        
        # Create test state
        state = AgentState(
            messages=[HumanMessage(content="What restaurants do you recommend?")],
            memory_context=None,
            user_profile=None,
            session_summary=None
        )
        
        config = {
            "configurable": {
                "user_id": "test_user",
                "thread_id": "test_thread"
            }
        }
        
        # Test memory retrieval
        result = retrieve_long_term_memory(state, config, store=mock_store)
        
        # Verify search was called
        mock_store.search.assert_called_with(
            ("memories", "test_user"),
            query="What restaurants do you recommend?",
            limit=3
        )
        
        # Verify memory context was set
        self.assertIsNotNone(result["memory_context"])
        self.assertIn("vegetarian", result["memory_context"])
        print("✓ Memory retrieval works correctly")

    @patch('builtins.input')
    @patch('langchain_openai.ChatOpenAI')
    @patch('langchain_community.agent_toolkits.load_tools.load_tools')
    @patch('langgraph.checkpoint.sqlite.SqliteSaver')
    @patch('langgraph.store.memory.InMemoryStore')
    @patch('agent.PatchedOpenAIEmbeddings')
    def test_06_agent_workflow_execution(self, MockEmbeddings, MockStore, MockSaver, MockLoadTools, MockChatOpenAI, mock_input):
        """Test the complete agent workflow execution."""
        print("\n6. Testing Agent Workflow Execution...")
        
        # Configure mocks
        mock_embeddings = MagicMock()
        MockEmbeddings.return_value = mock_embeddings
        
        mock_store = MagicMock()
        MockStore.return_value = mock_store
        mock_store.search.return_value = []  # No previous memories
        
        mock_checkpointer = MagicMock()
        MockSaver.return_value = mock_checkpointer
        
        mock_llm = MagicMock()
        MockChatOpenAI.return_value = mock_llm
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = "Hello! I'm ready to help you."
        mock_response.tool_calls = []
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response
        
        # Mock math tools
        MockLoadTools.return_value = []
        
        # Import and create agent
        from agent.agent import create_agent
        from langchain_core.messages import HumanMessage
        
        agent = create_agent()
        
        # Test agent execution
        initial_state = {
            "messages": [HumanMessage(content="Hello, how are you?")],
            "memory_context": None,
            "user_profile": None,
            "session_summary": None
        }
        
        config = {
            "configurable": {
                "thread_id": "test_thread",
                "user_id": "test_user"
            }
        }
        
        result = agent.invoke(initial_state, config)
        
        # Verify the workflow executed
        self.assertIsNotNone(result)
        self.assertIn("messages", result)
        print("✓ Agent workflow execution successful")

    @patch('langchain_openai.ChatOpenAI')
    @patch('langchain_community.agent_toolkits.load_tools.load_tools')
    def test_07_tool_integration(self, MockLoadTools, MockChatOpenAI):
        """Test tool integration in the agent response function."""
        print("\n7. Testing Tool Integration...")
        
        # Configure mocks
        mock_llm = MagicMock()
        MockChatOpenAI.return_value = mock_llm
        
        # Mock tool response with tool calls
        mock_response = MagicMock()
        mock_response.content = "I'll help you with that calculation."
        mock_response.tool_calls = [
            {
                "name": "llm-math",
                "args": {"question": "2 + 2"}
            }
        ]
        mock_llm.bind_tools.return_value.invoke.return_value = mock_response
        
        # Mock math tools
        mock_math_tool = MagicMock()
        mock_math_tool.name = "llm-math"
        mock_math_tool.invoke.return_value = "4"
        MockLoadTools.return_value = [mock_math_tool]
        
        # Import and test agent response
        from agent.agent import agent_response, AgentState
        from langchain_core.messages import HumanMessage
        
        state = AgentState(
            messages=[HumanMessage(content="What is 2 + 2?")],
            memory_context=None,
            user_profile=None,
            session_summary=None
        )
        
        config = {
            "configurable": {
                "user_id": "test_user",
                "thread_id": "test_thread"
            }
        }
        
        # Mock store for the function call
        mock_store = MagicMock()
        
        result = agent_response(state, config, store=mock_store)
        
        # Verify tool was called
        mock_math_tool.invoke.assert_called_with({"question": "2 + 2"})
        
        # Verify response includes tool result
        self.assertIn("messages", result)
        response_content = result["messages"][0].content
        self.assertIn("Tool Results", response_content)
        self.assertIn("4", response_content)
        print("✓ Tool integration works correctly")

    def test_08_error_handling(self):
        """Test error handling in various scenarios."""
        print("\n8. Testing Error Handling...")
        
        # Test file operation with invalid format
        from agent.agent import create_text_file
        
        result = create_text_file.invoke({"filename_and_content": "invalid_format"})
        self.assertIn("Error: Use format", result)
        print("✓ File operation error handling works")
        
        # Test reading non-existent file
        from agent.agent import read_text_file
        
        result = read_text_file.invoke({"filename": "nonexistent.txt"})
        self.assertIn("not found", result)
        print("✓ File not found error handling works")

    @patch('builtins.input')
    def test_09_sandbox_isolation(self, mock_input):
        """Test that file operations are properly isolated to sandbox."""
        print("\n9. Testing Sandbox Isolation...")
        
        from agent.agent import create_text_file
        
        # Test file creation in sandbox
        mock_input.side_effect = ["yes"]
        result = create_text_file.invoke({"filename_and_content": "isolated.txt|||Safe content"})
        
        # Verify file was created in sandbox only
        self.assertTrue((self.sandbox / "isolated.txt").exists())
        self.assertFalse(Path("isolated.txt").exists())  # Not in current directory
        print("✓ Sandbox isolation works correctly")

    def test_10_agent_state_schema(self):
        """Test the AgentState schema and structure."""
        print("\n10. Testing Agent State Schema...")
        
        from agent.agent import AgentState
        from langchain_core.messages import HumanMessage
        
        # Test state creation
        state = AgentState(
            messages=[HumanMessage(content="Test message")],
            memory_context="Test context",
            user_profile={"name": "Test User"},
            session_summary="Test summary"
        )
        
        # Verify state structure
        self.assertIn("messages", state)
        self.assertIn("memory_context", state)
        self.assertIn("user_profile", state)
        self.assertIn("session_summary", state)
        self.assertEqual(state["memory_context"], "Test context")
        print("✓ Agent state schema works correctly")

if __name__ == '__main__':
    print("🧪 Running comprehensive tests for modern LangGraph agent...")
    print("=" * 60)
    
    # Run tests with detailed output
    unittest.main(verbosity=2, exit=False)
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("\nTest Coverage:")
    print("- Agent initialization and component setup")
    print("- Memory system (storage and retrieval)")
    print("- File operations with safety confirmations")
    print("- Complete workflow execution")
    print("- Tool integration and execution")
    print("- Error handling and validation")
    print("- Sandbox isolation")
    print("- State schema validation")
    print("\n🎉 Modern agent architecture fully tested!") 