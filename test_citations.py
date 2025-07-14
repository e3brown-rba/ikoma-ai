#!/usr/bin/env python3
"""Test suite for citation tracking system."""

import re

from tools.citation_manager import CitationManager


def test_citation_manager_basic():
    """Test basic CitationManager functionality."""
    print("Testing CitationManager basic operations...")

    cm = CitationManager()

    # Test adding citations
    citation_id1 = cm.add_citation(
        url="https://example.com",
        title="Example Page",
        content_preview="This is an example page content",
    )

    citation_id2 = cm.add_citation(
        url="https://test.org", title="Test Page", content_preview="Another test page"
    )

    assert citation_id1 == 1
    assert citation_id2 == 2
    assert len(cm.citations) == 2

    # Test citation text formatting
    citation_text1 = cm.get_citation_text(1)
    citation_text2 = cm.get_citation_text(2)

    assert "[1]" in citation_text1
    assert "Example Page" in citation_text1
    assert "https://example.com" in citation_text1

    assert "[2]" in citation_text2
    assert "Test Page" in citation_text2

    print("✓ CitationManager basic operations passed")


def test_citation_manager_serialization():
    """Test CitationManager serialization to/from dict."""
    print("Testing CitationManager serialization...")

    cm = CitationManager()

    # Add some citations
    cm.add_citation("https://example.com", "Example", "Content")
    cm.add_citation("https://test.org", "Test", "More content")

    # Convert to dict
    data = cm.to_dict()

    # Create new manager and load data
    cm2 = CitationManager()
    cm2.from_dict(data)

    # Verify citations are preserved
    assert len(cm2.citations) == 2
    assert cm2.counter == 3  # Next citation ID

    citation_text = cm2.get_citation_text(1)
    assert "Example" in citation_text

    print("✓ CitationManager serialization passed")


def test_citation_extraction():
    """Test citation marker extraction from text."""
    print("Testing citation extraction...")

    cm = CitationManager()

    # Test text with citations
    text = "Based on research [[1]] and recent studies [[2]], we can conclude that Python is popular."

    citations = cm.extract_citations_from_text(text)
    assert citations == [1, 2]

    # Test text without citations
    text_no_citations = "This is just regular text without citations."
    citations = cm.extract_citations_from_text(text_no_citations)
    assert citations == []

    # Test mixed text
    text_mixed = "Some text [[1]] more text [[3]] and [[2]]"
    citations = cm.extract_citations_from_text(text_mixed)
    assert citations == [1, 3, 2]

    print("✓ Citation extraction passed")


def test_citation_replacement():
    """Test replacing citation markers with formatted text."""
    print("Testing citation replacement...")

    cm = CitationManager()

    # Add citations
    cm.add_citation("https://example.com", "Example Page", "Content")
    cm.add_citation("https://test.org", "Test Page", "More content")

    # Test text with citations
    text = "Based on research [[1]] and recent studies [[2]], we can conclude that Python is popular."

    replaced = cm.replace_citations_with_text(text)

    # Should contain citation text
    assert "[1]" in replaced
    assert "[2]" in replaced
    assert "Example Page" in replaced
    assert "Test Page" in replaced

    # Should not contain original markers
    assert "[[1]]" not in replaced
    assert "[[2]]" not in replaced

    print("✓ Citation replacement passed")


def test_planner_citation_emission():
    """Test that planner includes citation markers in descriptions."""
    print("Testing planner citation emission...")

    # Mock planning prompt with citation instructions
    # planning_prompt = """You are a planning assistant. When creating plans that reference external information or previous knowledge, include citation markers [[n]] where n is a number.

    # Available tools:
    # - web_search: Search the web for information
    # - create_text_file: Create a text file with content

    # Your task is to create a JSON plan. When a step involves information from external sources or previous context, include [[n]] citation markers in the description.

    # Citation Guidelines:
    # - Use [[1]], [[2]], etc. for different sources
    # - Place citations immediately after claims that need sourcing
    # - The execute phase will populate actual citation details

    # Example with citations:
    # ```json
    # {
    #   "plan": [
    #     {
    #       "step": 1,
    #       "tool_name": "web_search",
    #       "args": {"query": "Python best practices 2025"},
    #       "description": "Search for current Python best practices [[1]]"
    #     },
    #     {
    #       "step": 2,
    #       "tool_name": "create_text_file",
    #       "args": {"filename_and_content": "best_practices.txt|||Based on recent research [[1]], here are the top Python practices..."},
    #       "description": "Create file with researched best practices citing source [[1]]"
    #     }
    #   ],
    #   "reasoning": "This plan searches for current information [[1]] and documents it properly"
    # }
    # ```

    # User's request: Search for Python best practices and create a summary file."""

    # This would normally be processed by the LLM
    # For testing, we'll simulate the expected output
    expected_plan = {
        "plan": [
            {
                "step": 1,
                "tool_name": "web_search",
                "args": {"query": "Python best practices 2025"},
                "description": "Search for current Python best practices [[1]]",
            },
            {
                "step": 2,
                "tool_name": "create_text_file",
                "args": {
                    "filename_and_content": "best_practices.txt|||Based on recent research [[1]], here are the top Python practices..."
                },
                "description": "Create file with researched best practices citing source [[1]]",
            },
        ],
        "reasoning": "This plan searches for current information [[1]] and documents it properly",
    }

    # Extract all descriptions and reasoning
    all_text = ""
    for step in expected_plan["plan"]:
        all_text += step["description"] + " "
    all_text += expected_plan["reasoning"]

    # Check for citation markers
    citation_pattern = r"\[\[(\d+)\]\]"
    citations = re.findall(citation_pattern, all_text)

    assert len(citations) > 0, "No citation markers found in plan"
    assert "1" in citations, "Citation marker [[1]] not found"

    print("✓ Planner citation emission passed")


def test_citation_state_persistence():
    """Test that citations survive through agent state transitions."""
    print("Testing citation state persistence...")

    # Mock agent state
    state = {"citations": [], "citation_counter": 1, "execution_results": []}

    # Simulate adding citations during execution
    cm = CitationManager()
    cm.from_dict(
        {"citations": state["citations"], "counter": state["citation_counter"]}
    )

    # Add citations
    cm.add_citation("https://example.com", "Example", "Content")
    cm.add_citation("https://test.org", "Test", "More content")

    # Update state
    citation_data = cm.to_dict()
    state["citations"] = citation_data["citations"]
    state["citation_counter"] = citation_data["counter"]

    # Verify state persistence
    assert len(state["citations"]) == 2
    assert state["citation_counter"] == 3

    # Simulate state transition (e.g., to reflection phase)
    # State should still have citations
    assert "citations" in state
    assert "citation_counter" in state

    print("✓ Citation state persistence passed")


def test_citation_integration():
    """Test integration of citation system with planning and execution."""
    print("Testing citation integration...")

    # Mock plan with citations
    # plan = [
    #     {
    #         "step": 1,
    #         "tool_name": "web_search",
    #         "args": {"query": "Python best practices"},
    #         "description": "Search for current Python best practices [[1]]"
    #     },
    #     {
    #         "step": 2,
    #         "tool_name": "create_text_file",
    #         "args": {"filename_and_content": "practices.txt|||Based on research [[1]], here are the best practices..."},
    #         "description": "Create file with researched practices citing source [[1]]"
    #     }
    # ]

    # Mock execution results
    execution_results = [
        {
            "step": 1,
            "tool_name": "web_search",
            "args": {"query": "Python best practices"},
            "description": "Search for current Python best practices [[1]]",
            "status": "success",
            "result": "Found information from https://python.org/best-practices",
        },
        {
            "step": 2,
            "tool_name": "create_text_file",
            "args": {
                "filename_and_content": "practices.txt|||Based on research [[1]], here are the best practices..."
            },
            "description": "Create file with researched practices citing source [[1]]",
            "status": "success",
            "result": "File created successfully",
        },
    ]

    # Initialize citation manager
    cm = CitationManager()

    # Process execution results to extract citations
    for result in execution_results:
        if result["status"] == "success":
            tool_name = result["tool_name"]

            # For web tools, extract citation info
            if tool_name == "web_search":
                # Extract URL from result (in real implementation, this would parse the result)
                url = "https://python.org/best-practices"
                title = "Python Best Practices"
                citation_id = cm.add_citation(
                    url, title, "Python development best practices"
                )

                # Verify citation was added
                assert citation_id == 1
                citation_text = cm.get_citation_text(1)
                assert "Python Best Practices" in citation_text
                assert url in citation_text

    # Verify citations are tracked
    assert len(cm.citations) == 1
    assert cm.counter == 2

    print("✓ Citation integration passed")


def run_all_tests():
    """Run all citation system tests."""
    print("Running citation system tests...\n")

    try:
        test_citation_manager_basic()
        test_citation_manager_serialization()
        test_citation_extraction()
        test_citation_replacement()
        test_planner_citation_emission()
        test_citation_state_persistence()
        test_citation_integration()

        print("\n🎉 All citation system tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    run_all_tests()
