"""Standardized benchmark scenarios for consistent testing."""

BENCHMARK_SCENARIOS = [
    {
        "name": "simple_math",
        "goal": "Calculate 23*7+11",
        "expected_tools": ["Calculator"],
        "config": {"configurable": {"user_id": "benchmark"}}
    },
    {
        "name": "file_operation",
        "goal": "Create a file called test.txt with content 'benchmark'",
        "expected_tools": ["create_text_file"],
        "config": {"configurable": {"user_id": "benchmark"}}
    },
    {
        "name": "multi_step",
        "goal": "List files, then create summary.txt with the count",
        "expected_tools": ["list_sandbox_files", "create_text_file"],
        "config": {"configurable": {"user_id": "benchmark"}}
    },
    {
        "name": "text_processing",
        "goal": "Create a file with the text 'Hello World' and then read it back",
        "expected_tools": ["create_text_file", "read_text_file"],
        "config": {"configurable": {"user_id": "benchmark"}}
    },
    {
        "name": "simple_planning",
        "goal": "What is 2+2?",
        "expected_tools": [],
        "config": {"configurable": {"user_id": "benchmark"}}
    }
]
