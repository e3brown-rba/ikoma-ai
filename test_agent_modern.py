import os
import unittest
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path

# Set environment variables for testing
os.environ["OPENAI_API_KEY"] = "sk-dummy"
os.environ["LMSTUDIO_BASE_URL"] = "http://127.0.0.1:11434/v1"
os.environ["LMSTUDIO_MODEL"] = "test-model"
os.environ["SANDBOX_PATH"] = "agent/test_sandbox"

class TestModernAgent(unittest.TestCase):

    def setUp(self):
        """Set up a clean sandbox for each test."""
        self.sandbox = Path(os.getenv("SANDBOX_PATH"))
        # Ensure the directory exists and is empty
        shutil.rmtree(self.sandbox, ignore_errors=True)
        self.sandbox.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up the sandbox after each test."""
        shutil.rmtree(self.sandbox, ignore_errors=True)

    @patch('agent.agent.load_tools', return_value=[])
    @patch('agent.agent.ChatOpenAI')
    @patch('agent.agent.PatchedOpenAIEmbeddings')
    @patch('agent.agent.Chroma')
    def test_01_initialization_and_memory(self, MockChroma, MockEmbeddings, MockChatOpenAI, MockLoadTools):
        """Test that components initialize and that memory is saved."""
        print("\n1. Testing Initialization and Memory...")
        # Import the setup function from the agent module
        from agent.agent import setup_agent

        # Configure the mock for Chroma
        mock_vectorstore_instance = MagicMock()
        MockChroma.return_value = mock_vectorstore_instance

        # Call the setup function to create the agent components
        agent_executor, retriever, save_to_memory = setup_agent()

        # Assert that our main components were initialized
        MockChatOpenAI.assert_called_once()
        MockEmbeddings.assert_called_once()
        MockChroma.assert_called_once()
        self.assertIsNotNone(agent_executor)
        print("✓ Components initialized correctly.")

        # Test the save_to_memory function
        save_to_memory("hello", "world")
        mock_vectorstore_instance.add_texts.assert_called_once_with(["User: hello", "AI: world"])
        print("✓ Memory saving works correctly.")

    def test_02_file_operations(self):
        """Test the agent's file system tools directly."""
        print("\n2. Testing File Operations...")
        # Import the tools directly to test them in isolation
        from agent.agent import create_text_file, read_text_file, update_text_file, list_sandbox_files

        create_result = create_text_file.invoke({"filename_and_content": "test.txt|||hello from test"})
        self.assertIn("✓ Created file", create_result)
        self.assertTrue((self.sandbox / "test.txt").exists())
        print("✓ File creation works.")

        read_result = read_text_file.invoke({"filename": "test.txt"})
        self.assertIn("hello from test", read_result)
        print("✓ File reading works.")

        update_result = update_text_file.invoke({"filename_and_content": "test.txt|||new content"})
        self.assertIn("✓ Updated file", update_result)
        read_again_result = read_text_file.invoke({"filename": "test.txt"})
        self.assertIn("new content", read_again_result)
        print("✓ File updating works.")

        list_result = list_sandbox_files.invoke({})
        self.assertIn("test.txt", list_result)
        print("✓ File listing works.")

if __name__ == '__main__':
    print("🔬 Running tests for modern agent architecture...")
    print("=" * 50)
    unittest.main(verbosity=2)
    print("=" * 50)
    print("✅ All tests passed!") 