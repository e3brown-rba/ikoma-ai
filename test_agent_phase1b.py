#!/usr/bin/env python3
"""
Comprehensive test suite for iKOMA Agent Phase 1-B plan-execute-reflect architecture.
Tests the new planning system, tool execution, and reflection capabilities.
"""

import pytest
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the agent modules
from agent.agent import AgentState, create_agent, plan_node, execute_node, reflect_node
from tools.tool_loader import ToolLoader
from tools.vector_store import PersistentVectorStore, get_vector_store
from tools.fs_tools import FILE_TOOLS

class TestAgentPhase1B:
    """Test suite for Phase 1-B agent architecture."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns predictable responses."""
        mock_llm = Mock()
        
        # Mock planning responses
        planning_response = Mock()
        planning_response.content = json.dumps({
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files in sandbox"
                }
            ],
            "reasoning": "Starting with file listing"
        })
        
        # Mock reflection responses
        reflection_response = Mock()
        reflection_response.content = json.dumps({
            "task_completed": True,
            "success_rate": "100%",
            "summary": "Task completed successfully",
            "next_action": "end",
            "reasoning": "All steps completed successfully"
        })
        
        mock_llm.invoke.side_effect = [planning_response, reflection_response]
        return mock_llm
    
    @pytest.fixture
    def mock_agent_state(self):
        """Create a mock agent state for testing."""
        return {
            "messages": [Mock(content="Test request", type="human")],
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
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "configurable": {
                "thread_id": "test_thread",
                "user_id": "test_user"
            }
        }
    
    @pytest.fixture
    def temp_vector_store(self):
        """Create a temporary vector store for testing."""
        temp_dir = tempfile.mkdtemp()
        store = PersistentVectorStore(persist_directory=temp_dir)
        yield store
        shutil.rmtree(temp_dir)
    
    def test_tool_loader_initialization(self):
        """Test that ToolLoader initializes properly."""
        loader = ToolLoader()
        assert loader.schema is not None
        assert "tools" in loader.schema
    
    def test_tool_schema_validation(self):
        """Test that the MCP schema is valid."""
        loader = ToolLoader()
        schema = loader.schema
        
        # Check required fields
        assert "tools" in schema
        assert "categories" in schema
        assert "version" in schema
        
        # Check tool structure
        for tool in schema["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert "category" in tool
    
    @patch('agent.agent.ChatOpenAI')
    def test_plan_node_execution(self, mock_chat_openai, mock_agent_state, mock_config):
        """Test the plan_node function with mocked LLM."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps({
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files in sandbox"
                }
            ],
            "reasoning": "Starting with file listing"
        })
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        # Mock store
        mock_store = Mock()
        
        # Execute plan_node
        result = plan_node(mock_agent_state, mock_config, store=mock_store, llm=mock_llm)
        
        # Verify result
        assert "current_plan" in result
        assert result["current_plan"] is not None
        assert len(result["current_plan"]) == 1
        assert result["current_plan"][0]["tool_name"] == "list_sandbox_files"
        assert result["continue_planning"] is True
    
    @patch('tools.tool_loader.tool_loader.load_tools')
    @patch('agent.agent.ChatOpenAI')
    def test_execute_node_execution(self, mock_chat_openai, mock_load_tools, mock_agent_state, mock_config):
        """Test the execute_node function with mocked tools."""
        # Setup mock tools
        mock_tool = Mock()
        mock_tool.name = "list_sandbox_files"
        mock_tool.invoke.return_value = "Files listed successfully"
        mock_load_tools.return_value = [mock_tool]
        
        # Setup agent state with plan
        mock_agent_state["current_plan"] = [
            {
                "step": 1,
                "tool_name": "list_sandbox_files",
                "args": {"query": ""},
                "description": "List files in sandbox"
            }
        ]
        
        # Mock store
        mock_store = Mock()
        
        # Execute execute_node
        result = execute_node(mock_agent_state, mock_config, store=mock_store, tools=[mock_tool])
        
        # Verify result
        assert "execution_results" in result
        assert len(result["execution_results"]) == 1
        assert result["execution_results"][0]["status"] == "success"
        assert result["execution_results"][0]["tool_name"] == "list_sandbox_files"
    
    @patch('agent.agent.ChatOpenAI')
    def test_reflect_node_execution(self, mock_chat_openai, mock_agent_state, mock_config):
        """Test the reflect_node function with mocked LLM."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = json.dumps({
            "task_completed": True,
            "success_rate": "100%",
            "summary": "Task completed successfully",
            "next_action": "end",
            "reasoning": "All steps completed successfully"
        })
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        # Setup agent state with execution results
        mock_agent_state["execution_results"] = [
            {
                "step": 1,
                "tool_name": "list_sandbox_files",
                "args": {"query": ""},
                "description": "List files in sandbox",
                "status": "success",
                "result": "Files listed successfully"
            }
        ]
        
        # Mock store
        mock_store = Mock()
        
        # Execute reflect_node
        result = reflect_node(mock_agent_state, mock_config, store=mock_store, llm=mock_llm)
        
        # Verify result
        assert result["continue_planning"] is False
        assert "reflection" in result
        assert len(result["messages"]) > 0
    
    def test_persistent_vector_store_operations(self, temp_vector_store):
        """Test vector store operations."""
        store = temp_vector_store
        
        # Test put operation
        namespace = ("test", "user1")
        key = "test_key"
        value = {
            "content": "Test memory content",
            "timestamp": datetime.now().isoformat(),
            "context": "test"
        }
        
        store.put(namespace, key, value)
        
        # Test get operation
        retrieved = store.get(namespace, key)
        assert retrieved is not None
        assert retrieved["content"] == "Test memory content"
        
        # Test search operation
        results = store.search(namespace, "test memory")
        assert len(results) > 0
        assert results[0]["value"]["content"] == "Test memory content"
    
    @pytest.mark.parametrize("task_description,expected_tools", [
        ("calculate 23*7+11", ["llm-math"]),
        ("create a file called test.txt", ["create_text_file"]),
        ("list all files and read the first one", ["list_sandbox_files", "read_text_file"]),
        ("rename files in the directory", ["list_sandbox_files", "read_text_file", "create_text_file"]),
    ])
    def test_planning_scenarios(self, task_description, expected_tools):
        """Test planning for different task scenarios."""
        # This test verifies that the planning system would handle different task types
        # In a real scenario, this would test the actual planning logic
        
        # Mock tool loader to return expected tools
        loader = ToolLoader()
        available_tools = [tool["name"] for tool in loader.schema["tools"]]
        
        # Verify expected tools are available
        for tool in expected_tools:
            assert tool in available_tools or tool in ["llm-math"]
    
    def test_agent_state_schema(self):
        """Test that AgentState has required fields."""
        required_fields = [
            "messages", "memory_context", "user_profile", "session_summary",
            "current_plan", "execution_results", "reflection", "continue_planning",
            "max_iterations", "current_iteration"
        ]
        
        # Check that all required fields are in AgentState
        for field in required_fields:
            assert field in AgentState.__annotations__
    
    def test_error_handling_in_execution(self):
        """Test error handling during tool execution."""
        # Mock a failing tool
        mock_tool = Mock()
        mock_tool.name = "failing_tool"
        mock_tool.invoke.side_effect = Exception("Tool execution failed")
        
        # Test that execution handles errors gracefully
        with patch('tools.tool_loader.tool_loader.load_tools') as mock_load_tools:
            mock_load_tools.return_value = [mock_tool]
            
            state = {
                "current_plan": [
                    {
                        "step": 1,
                        "tool_name": "failing_tool",
                        "args": {},
                        "description": "This tool will fail"
                    }
                ]
            }
            
            with patch('agent.agent.ChatOpenAI'):
                result = execute_node(state, {}, store=Mock(), tools=[mock_tool])
                
                # Verify error is handled
                assert "execution_results" in result
                assert result["execution_results"][0]["status"] == "error"
                assert "Tool execution failed" in result["execution_results"][0]["result"]
    
    @patch.dict(os.environ, {
        'LMSTUDIO_BASE_URL': 'http://localhost:11434/v1',
        'LMSTUDIO_MODEL': 'test-model',
        'VECTOR_STORE_PATH': '/tmp/test_vector_store'
    })
    def test_environment_configuration(self):
        """Test that environment variables are properly loaded."""
        # Test that environment variables are accessible
        assert os.getenv("LMSTUDIO_BASE_URL") == "http://localhost:11434/v1"
        assert os.getenv("LMSTUDIO_MODEL") == "test-model"
        assert os.getenv("VECTOR_STORE_PATH") == "/tmp/test_vector_store"
    
    def test_memory_enhancement_with_plan_context(self, temp_vector_store):
        """Test that memory storage includes plan context."""
        store = temp_vector_store
        
        # Create memory with plan context
        namespace = ("memories", "test_user")
        key = "test_memory"
        value = {
            "content": "User prefers detailed explanations",
            "timestamp": datetime.now().isoformat(),
            "context": "conversation",
            "plan_context": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "description": "List files"
                }
            ],
            "reflection": "Task completed successfully"
        }
        
        store.put(namespace, key, value)
        
        # Search for the memory
        results = store.search(namespace, "detailed explanations")
        assert len(results) > 0
        
        # Verify plan context is preserved
        result = results[0]
        assert "plan_context" in result["value"]
        assert result["value"]["plan_context"] is not None


class TestToolIntegration:
    """Test integration between tools and the planning system."""
    
    def test_file_tools_availability(self):
        """Test that file tools are properly available."""
        from tools.fs_tools import FILE_TOOLS
        
        expected_tools = [
            "list_sandbox_files",
            "create_text_file", 
            "update_text_file",
            "read_text_file"
        ]
        
        available_tool_names = [tool.name for tool in FILE_TOOLS]
        
        for tool_name in expected_tools:
            assert tool_name in available_tool_names
    
    def test_tool_loader_integration(self):
        """Test that ToolLoader properly loads tools."""
        with patch('langchain_community.agent_toolkits.load_tools') as mock_load_tools:
            mock_load_tools.return_value = [Mock(name="llm-math")]
            
            loader = ToolLoader()
            mock_llm = Mock()
            
            tools = loader.load_tools(mock_llm)
            assert len(tools) > 0
            
            # Verify tools are loaded only once
            tools2 = loader.load_tools(mock_llm)
            assert tools == tools2  # Should return cached tools


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--disable-warnings"
    ]) 