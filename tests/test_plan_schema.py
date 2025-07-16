#!/usr/bin/env python3
"""Tests for plan schema validation and generation."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ikoma.schemas.plan_models import (  # noqa: E402
    MalformedPlanError,
    Plan,
    PlanStep,
    generate_schema,
    validate_plan_json,
)


class TestPlanSchema:
    """Test suite for plan schema validation."""

    def test_valid_minimal_plan(self):
        """Test that a valid minimal plan passes validation."""
        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files in sandbox",
                }
            ],
            "reasoning": "Start by exploring available files",
        }

        plan = Plan.model_validate(plan_data)
        assert len(plan.plan) == 1
        assert plan.plan[0].step == 1
        assert plan.plan[0].tool_name == "list_sandbox_files"
        assert plan.reasoning == "Start by exploring available files"

    def test_valid_plan_with_citations(self):
        """Test that a plan with citations passes validation."""
        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "search_web",
                    "args": {"query": "Python best practices"},
                    "description": "Search for current Python best practices [[1]]",
                    "citations": [1],
                },
                {
                    "step": 2,
                    "tool_name": "create_text_file",
                    "args": {
                        "filename_and_content": "best_practices.txt|||Content here"
                    },
                    "description": "Create file with researched practices [[1]]",
                    "citations": [1],
                },
            ],
            "reasoning": "This plan searches for information and documents it",
        }

        plan = Plan.model_validate(plan_data)
        assert len(plan.plan) == 2
        assert plan.plan[0].citations == [1]
        assert plan.plan[1].citations == [1]

    def test_missing_field_fails(self):
        """Test that missing required fields cause validation errors."""
        # Missing step
        plan_data = {
            "plan": [
                {
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files",
                }
            ],
            "reasoning": "Start by exploring",
        }

        with pytest.raises(ValueError, match="Field required"):
            Plan.model_validate(plan_data)

        # Missing tool_name
        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "args": {"query": ""},
                    "description": "List files",
                }
            ],
            "reasoning": "Start by exploring",
        }

        with pytest.raises(ValueError, match="Field required"):
            Plan.model_validate(plan_data)

    def test_invalid_step_number_fails(self):
        """Test that step numbers must be positive integers."""
        plan_data = {
            "plan": [
                {
                    "step": 0,  # Invalid: must be >= 1
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files",
                }
            ],
            "reasoning": "Start by exploring",
        }

        with pytest.raises(ValueError, match="greater than or equal to 1"):
            Plan.model_validate(plan_data)

    def test_invalid_citations_fail(self):
        """Test that invalid citation IDs cause validation errors."""
        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files",
                    "citations": [0, -1],  # Invalid: must be positive
                }
            ],
            "reasoning": "Start by exploring",
        }

        with pytest.raises(ValueError, match="positive integer"):
            Plan.model_validate(plan_data)

    def test_empty_plan_fails(self):
        """Test that empty plan arrays are rejected."""
        plan_data = {
            "plan": [],
            "reasoning": "Empty plan",
        }

        with pytest.raises(ValueError, match="at least 1 item"):
            Plan.model_validate(plan_data)

    def test_additional_properties_rejected(self):
        """Test that additional properties are rejected."""
        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "list_sandbox_files",
                    "args": {"query": ""},
                    "description": "List files",
                    "extra_field": "should be rejected",
                }
            ],
            "reasoning": "Start by exploring",
            "extra_top_level": "should be rejected",
        }

        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            Plan.model_validate(plan_data)

    @patch("ikoma.schemas.plan_models.tool_loader")
    def test_unknown_tool_fails(self, mock_tool_loader):
        """Test that unknown tool names cause validation errors."""
        # Mock available tools
        mock_tool_loader.get_tool_names.return_value = [
            "list_sandbox_files",
            "Calculator",
        ]

        plan_data = {
            "plan": [
                {
                    "step": 1,
                    "tool_name": "nonexistent_tool",
                    "args": {"query": ""},
                    "description": "List files",
                }
            ],
            "reasoning": "Start by exploring",
        }

        with pytest.raises(ValueError, match="Tool 'nonexistent_tool' not found"):
            Plan.model_validate(plan_data)

    def test_validate_plan_json_function(self):
        """Test the validate_plan_json function."""
        plan_json = json.dumps(
            {
                "plan": [
                    {
                        "step": 1,
                        "tool_name": "list_sandbox_files",
                        "args": {"query": ""},
                        "description": "List files",
                    }
                ],
                "reasoning": "Start by exploring",
            }
        )

        plan = validate_plan_json(plan_json)
        assert isinstance(plan, Plan)
        assert len(plan.plan) == 1

    def test_validate_plan_json_invalid_json(self):
        """Test that invalid JSON raises MalformedPlanError."""
        with pytest.raises(MalformedPlanError, match="Plan validation failed"):
            validate_plan_json("invalid json")

    def test_malformed_plan_error(self):
        """Test MalformedPlanError exception."""
        error = MalformedPlanError("Test error", ["error1", "error2"])
        assert str(error) == "Test error"
        assert error.validation_errors == ["error1", "error2"]


class TestSchemaGeneration:
    """Test suite for schema generation."""

    def test_generate_schema(self):
        """Test that schema generation produces valid JSON Schema."""
        schema = generate_schema()

        # Check required metadata
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == "https://ikoma.ai/plan.schema.json"
        assert schema["version"] == "1.0.0"
        assert schema["title"] == "iKOMA Plan Schema"

        # Check structure
        assert "properties" in schema
        assert "plan" in schema["properties"]
        assert "reasoning" in schema["properties"]

        # Check that additionalProperties is false
        assert schema["additionalProperties"] is False

    def test_roundtrip_generate_schema(self):
        """Test that regenerated schema matches the checked-in file."""
        # Generate schema from models
        generated_schema = generate_schema()

        # Read the checked-in schema file
        schema_path = (
            Path(__file__).parent.parent / "ikoma" / "schemas" / "plan.schema.json"
        )
        with open(schema_path) as f:
            checked_in_schema = json.load(f)

        # Compare schemas (ignore order of properties)
        assert generated_schema["$schema"] == checked_in_schema["$schema"]
        assert generated_schema["$id"] == checked_in_schema["$id"]
        assert generated_schema["version"] == checked_in_schema["version"]
        assert generated_schema["title"] == checked_in_schema["title"]
        assert (
            generated_schema["additionalProperties"]
            == checked_in_schema["additionalProperties"]
        )

        # Check that required fields are the same
        assert set(generated_schema["required"]) == set(checked_in_schema["required"])


class TestPlanStep:
    """Test suite for PlanStep model."""

    def test_plan_step_validation(self):
        """Test PlanStep validation."""
        step_data = {
            "step": 1,
            "tool_name": "list_sandbox_files",
            "args": {"query": ""},
            "description": "List files",
        }

        step = PlanStep.model_validate(step_data)
        assert step.step == 1
        assert step.tool_name == "list_sandbox_files"
        assert step.citations is None

    def test_plan_step_with_citations(self):
        """Test PlanStep with citations."""
        step_data = {
            "step": 1,
            "tool_name": "list_sandbox_files",
            "args": {"query": ""},
            "description": "List files",
            "citations": [1, 2, 3],
        }

        step = PlanStep.model_validate(step_data)
        assert step.citations == [1, 2, 3]

    def test_plan_step_model_dump(self):
        """Test PlanStep model_dump method."""
        step = PlanStep(
            step=1,
            tool_name="list_sandbox_files",
            args={"query": ""},
            description="List files",
            citations=[1, 2],
        )

        dumped = step.model_dump()
        assert dumped["step"] == 1
        assert dumped["tool_name"] == "list_sandbox_files"
        assert dumped["citations"] == [1, 2]
