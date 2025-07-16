#!/usr/bin/env python3
"""Tests for plan reflection repair functionality.

This module tests the self-reflection retry loop for repairing invalid plans
as specified in Issue #18.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from planning.reflection import (  # noqa: E402
    PlanRepairFailure,
    build_reflection_prompt,
    get_max_plan_retries,
    repair_plan,
)


class TestPlanReflection:
    """Test suite for plan reflection repair functionality."""

    def test_build_reflection_prompt_basic(self):
        """Test that reflection prompt includes all required components."""
        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        prompt = build_reflection_prompt(invalid_plan, validation_error)

        assert "INVALID JSON:" in prompt
        assert invalid_plan in prompt
        assert "VALIDATION ERROR:" in prompt
        assert validation_error in prompt
        assert "SCHEMA REQUIREMENTS:" in prompt
        assert "Return ONLY the corrected JSON" in prompt

    def test_build_reflection_prompt_with_schema_snippet(self):
        """Test that custom schema snippet is used when provided."""
        invalid_plan = '{"plan": []}'
        validation_error = "Array should have at least 1 item"
        custom_schema = '{"type": "object", "properties": {"plan": {"type": "array"}}}'

        prompt = build_reflection_prompt(invalid_plan, validation_error, custom_schema)

        assert custom_schema in prompt
        assert "SCHEMA REQUIREMENTS:" in prompt

    @patch("planning.reflection.Path")
    def test_build_reflection_prompt_schema_file_not_found(self, mock_path):
        """Test that prompt handles missing schema file gracefully."""
        mock_path.return_value.exists.return_value = False

        invalid_plan = '{"plan": []}'
        validation_error = "Array should have at least 1 item"

        prompt = build_reflection_prompt(invalid_plan, validation_error)

        assert "Schema file not found" in prompt
        assert "INVALID JSON:" in prompt
        assert "VALIDATION ERROR:" in prompt

    def test_repair_plan_success_first_attempt(self):
        """Test successful plan repair on first attempt."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        result = repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        assert result == '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        mock_llm.invoke.assert_called_once()

    def test_repair_plan_success_second_attempt(self):
        """Test successful plan repair on second attempt."""
        mock_llm = Mock()

        # First attempt fails, second succeeds
        mock_response1 = Mock()
        mock_response1.content = '{"invalid": "json"'  # Missing closing brace
        mock_response2 = Mock()
        mock_response2.content = '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        mock_llm.invoke.side_effect = [mock_response1, mock_response2]

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        result = repair_plan(mock_llm, invalid_plan, validation_error, retries=2)

        assert result == '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        assert mock_llm.invoke.call_count == 2

    def test_repair_plan_handles_markdown_code_blocks(self):
        """Test that repair handles markdown code blocks in LLM response."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '```json\n{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}\n```'
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        result = repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        expected = '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        assert result == expected

    def test_repair_plan_handles_regular_code_blocks(self):
        """Test that repair handles regular code blocks in LLM response."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '```\n{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}\n```'
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        result = repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        expected = '{"plan": [{"step": 1, "tool_name": "test", "args": {}, "description": "test"}], "reasoning": "test"}'
        assert result == expected

    def test_repair_plan_failure_all_attempts(self):
        """Test that PlanRepairFailure is raised when all attempts fail."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '{"invalid": "json"'  # Missing closing brace
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        with pytest.raises(PlanRepairFailure) as exc_info:
            repair_plan(mock_llm, invalid_plan, validation_error, retries=2)

        assert "Exceeded plan repair retries (2 attempts)" in str(exc_info.value)
        assert exc_info.value.attempts == 2
        assert mock_llm.invoke.call_count == 2

    def test_repair_plan_failure_non_json_response(self):
        """Test that repair fails when LLM returns non-JSON response."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "I cannot fix this JSON"
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        with pytest.raises(PlanRepairFailure) as exc_info:
            repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        assert "Exceeded plan repair retries (1 attempts)" in str(exc_info.value)

    def test_repair_plan_failure_invalid_json(self):
        """Test that repair fails when LLM returns invalid JSON."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '{"plan": [{"step": 1, "tool_name": "test"}]'  # Missing closing brace
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        with pytest.raises(PlanRepairFailure) as exc_info:
            repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        assert "Exceeded plan repair retries (1 attempts)" in str(exc_info.value)

    def test_get_max_plan_retries_default(self):
        """Test that get_max_plan_retries returns default value when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_max_plan_retries()
            assert result == 2

    def test_get_max_plan_retries_environment_override(self):
        """Test that get_max_plan_retries respects environment variable."""
        with patch.dict(os.environ, {"IKOMA_MAX_PLAN_RETRIES": "3"}):
            result = get_max_plan_retries()
            assert result == 3

    def test_get_max_plan_retries_invalid_environment(self):
        """Test that get_max_plan_retries handles invalid environment values."""
        with patch.dict(os.environ, {"IKOMA_MAX_PLAN_RETRIES": "invalid"}):
            with pytest.raises(ValueError):
                get_max_plan_retries()

    def test_plan_repair_failure_exception(self):
        """Test PlanRepairFailure exception with attempts tracking."""
        error = PlanRepairFailure("Test error", attempts=5)
        assert str(error) == "Test error"
        assert error.attempts == 5

    def test_plan_repair_failure_default_attempts(self):
        """Test PlanRepairFailure exception with default attempts."""
        error = PlanRepairFailure("Test error")
        assert str(error) == "Test error"
        assert error.attempts == 0


class TestPlanReflectionIntegration:
    """Integration tests for plan reflection with actual schema validation."""

    def test_repair_plan_with_real_schema_validation(self):
        """Test that repaired plan passes actual schema validation."""
        from ikoma.schemas.plan_models import Plan

        mock_llm = Mock()
        mock_response = Mock()
        # Valid plan structure
        valid_plan = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List available files"
                }
            ],
            "reasoning": "Start by exploring what files are available"
        }
        mock_response.content = json.dumps(valid_plan)
        mock_llm.invoke.return_value = mock_response

        invalid_plan = '{"plan": [{"step": 1}]}'
        validation_error = "Field required: tool_name"

        result = repair_plan(mock_llm, invalid_plan, validation_error, retries=1)

        # Verify the repaired plan is valid
        parsed_plan = Plan.model_validate_json(result)
        assert len(parsed_plan.plan) == 1
        assert parsed_plan.plan[0].tool_name == "list_sandbox_files"
        assert parsed_plan.reasoning == "Start by exploring what files are available"
