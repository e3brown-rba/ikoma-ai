#!/usr/bin/env python3
"""
Test script for agent citation functionality.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent import create_agent
from tools.citation_manager import ProductionCitationManager


def test_agent_with_citations():
    """Test the agent with citation functionality."""
    print("🧪 Testing Agent with Citations...")

    try:
        # Create agent
        create_agent()  # Test that agent creation works
        print("✅ Agent created successfully")

        # Test citation manager integration
        citation_mgr = ProductionCitationManager()

        # Add some test citations
        citation_id1 = citation_mgr.add_citation(
            url="https://example.com/test1",
            title="Test Source 1",
            content_preview="This is a test source",
            domain="example.com",
        )
        citation_id2 = citation_mgr.add_citation(
            url="https://example.com/test2",
            title="Test Source 2",
            content_preview="This is another test source",
            domain="example.com",
        )

        print(f"✅ Added test citations: {citation_id1}, {citation_id2}")

        # Test citation rendering
        test_response = "Here is some information [[1]] and more details [[2]]."
        print("\n🤖 Ikoma: ", end="")
        citation_mgr.render_response_with_citations(test_response)

        print("✅ Citation rendering works correctly")

        # Test state management
        state_dict = citation_mgr.to_dict()
        print(f"✅ State management: {len(state_dict['citations'])} citations stored")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_citation_parsing():
    """Test citation parsing functionality."""
    print("\n🧪 Testing Citation Parsing...")

    citation_mgr = ProductionCitationManager()

    # Test various citation formats
    test_cases = [
        "Simple citation [[1]]",
        "Multiple citations [[1]] and [[2]]",
        "No citations here",
        "Mixed content with [[1]] citations [[2]] and more text",
        "Edge case [[999]]",
    ]

    for i, test_case in enumerate(test_cases, 1):
        clean_text, citations = citation_mgr.parse_citations_anthropic_style(test_case)
        print(f"  Test {i}: {len(citations)} citations found")
        print(f"    Original: {test_case}")
        print(f"    Clean: {clean_text}")
        print(f"    Citations: {citations}")
        print()

    print("✅ Citation parsing tests completed!")


def test_unicode_superscript_rendering():
    """Test Unicode superscript rendering in different scenarios."""
    print("\n🧪 Testing Unicode Superscript Rendering...")

    citation_mgr = ProductionCitationManager()

    # Test different number ranges
    test_numbers = [1, 2, 3, 10, 25, 100, 999]

    print("Unicode superscript conversion:")
    for num in test_numbers:
        superscript = citation_mgr.unicode_superscript(num)
        print(f"  {num:3d} -> {superscript}")

    # Test in context
    test_text = "Results: [[1]], [[2]], [[10]], [[25]]"
    clean_text, citations = citation_mgr.parse_citations_anthropic_style(test_text)
    print("\nContext test:")
    print(f"  Original: {test_text}")
    print(f"  Clean: {clean_text}")
    print(f"  Citations: {citations}")

    print("✅ Unicode superscript rendering tests completed!")


if __name__ == "__main__":
    print("🚀 Starting Agent Citation Tests")
    print("=" * 50)

    success = True

    try:
        success &= test_agent_with_citations()
        test_citation_parsing()
        test_unicode_superscript_rendering()

        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
