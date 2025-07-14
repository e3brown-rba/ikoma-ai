#!/usr/bin/env python3
"""
Test script for citation superscript functionality.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.citation_manager import ProductionCitationManager


def test_citation_manager():
    """Test the citation manager functionality."""
    print("🧪 Testing Citation Manager...")

    # Initialize citation manager
    citation_mgr = ProductionCitationManager()

    # Test Unicode superscript conversion
    print("Unicode superscript test:")
    for i in range(1, 6):
        superscript = citation_mgr.unicode_superscript(i)
        print(f"  {i} -> {superscript}")

    # Test citation parsing
    test_text = "The sky is blue [[1]] and water freezes at 0°C [[2]]."
    print("\nCitation parsing test:")
    print(f"  Input: {test_text}")
    clean_text, citations = citation_mgr.parse_citations_anthropic_style(test_text)
    print(f"  Clean text: {clean_text}")
    print(f"  Citations: {citations}")

    # Test adding citations
    print("\nAdding citations:")
    citation_id1 = citation_mgr.add_citation(
        url="https://example.com/sky",
        title="Sky Color Research",
        content_preview="Research on why the sky appears blue",
        domain="example.com"
    )
    citation_id2 = citation_mgr.add_citation(
        url="https://example.com/water",
        title="Water Properties",
        content_preview="Information about water freezing point",
        domain="example.com"
    )
    citation1 = citation_mgr.get_citation_details(citation_id1)
    citation2 = citation_mgr.get_citation_details(citation_id2)
    print(f"  Added citation {citation_id1}: {citation1.title if citation1 else 'Not found'}")
    print(f"  Added citation {citation_id2}: {citation2.title if citation2 else 'Not found'}")

    # Test Rich rendering
    print("\nRich rendering test:")
    test_response = "The sky is blue [[1]] and water freezes at 0°C [[2]]. This is a test response with citations."
    print("🤖 Ikoma: ", end="")
    citation_mgr.render_response_with_citations(test_response)

    # Test state persistence
    print("\nState persistence test:")
    state_dict = citation_mgr.to_dict()
    print(f"  State dict keys: {list(state_dict.keys())}")
    print(f"  Citation count: {len(state_dict['citations'])}")

    # Create new manager and load state
    new_mgr = ProductionCitationManager()
    new_mgr.from_dict(state_dict)
    print(f"  Loaded citations: {len(new_mgr.get_all_citations())}")

    print("\n✅ Citation manager tests completed successfully!")


def test_unicode_support():
    """Test Unicode superscript support across different terminals."""
    print("\n🧪 Testing Unicode Support...")

    citation_mgr = ProductionCitationManager()

    # Test various numbers
    test_numbers = [1, 2, 3, 10, 25, 100]

    print("Unicode superscript conversion:")
    for num in test_numbers:
        superscript = citation_mgr.unicode_superscript(num)
        print(f"  {num:3d} -> {superscript}")

    # Test fallback behavior
    print("\nTesting fallback behavior with invalid input:")
    try:
        # This should trigger the fallback
        result = citation_mgr.unicode_superscript(-1)  # Negative numbers might cause issues
        print(f"  Fallback result: {result}")
    except Exception as e:
        print(f"  Exception caught: {e}")

    print("✅ Unicode support tests completed!")


if __name__ == "__main__":
    print("🚀 Starting Citation Superscript Tests")
    print("=" * 50)

    try:
        test_citation_manager()
        test_unicode_support()
        print("\n🎉 All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
