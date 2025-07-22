"""Pydantic models for plan validation and schema generation.

This module defines the data models used for validating LLM-generated plans
and generating the corresponding JSON Schema. The models ensure type safety
and provide a single source of truth for plan structure validation.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tools.tool_loader import tool_loader


class PlanStep(BaseModel):
    """A single step in a plan with tool execution details."""

    step: int = Field(..., ge=1, description="Step number (1-based)")
    tool_name: str = Field(..., description="Name of the tool to execute")
    args: dict[str, Any] = Field(..., description="Arguments for the tool")
    description: str = Field(
        ..., description="Human-readable description of what this step accomplishes"
    )
    citations: list[int] | None = Field(
        default=None, description="Optional citation IDs for this step"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate that the tool name exists in the available tools."""
        available_tools = tool_loader.get_tool_names()
        if v not in available_tools:
            raise ValueError(
                f"Tool '{v}' not found. Available tools: {', '.join(available_tools)}"
            )
        return v

    @field_validator("citations")
    @classmethod
    def validate_citations(cls, v: list[int] | None) -> list[int] | None:
        """Validate citation IDs are positive integers."""
        if v is not None:
            for citation_id in v:
                if not isinstance(citation_id, int) or citation_id < 1:
                    raise ValueError(
                        f"Citation ID must be a positive integer, got {citation_id}"
                    )
        return v


class Plan(BaseModel):
    """Complete plan structure with steps and reasoning."""

    plan: list[PlanStep] = Field(..., min_length=1, description="List of plan steps")
    reasoning: str = Field(
        ..., description="Explanation of why this plan will achieve the goal"
    )

    model_config = ConfigDict(
        extra="forbid",  # Reject any additional properties
        json_schema_extra={
            "examples": [
                {
                    "plan": [
                        {
                            "step": 1,
                            "tool_name": "list_sandbox_files",
                            "args": {"query": ""},
                            "description": "List available files in sandbox",
                        }
                    ],
                    "reasoning": "Start by exploring what files are available",
                }
            ]
        },
    )


class MalformedPlanError(Exception):
    """Raised when a plan fails validation."""

    def __init__(self, message: str, validation_errors: list[str] | None = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


def generate_schema() -> dict[str, Any]:
    """Generate JSON Schema from Pydantic models for CI validation."""
    schema = Plan.model_json_schema()

    # Add metadata for Draft-2020-12 compliance
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://ikoma.ai/plan.schema.json",
            "version": "1.0.0",
            "title": "iKOMA Plan Schema",
            "description": "Schema for validating LLM-generated execution plans",
        }
    )

    return schema


def validate_plan_json(plan_text: str) -> Plan:
    """Validate plan JSON and return parsed Plan object.

    Args:
        plan_text: JSON string containing the plan

    Returns:
        Parsed and validated Plan object

    Raises:
        MalformedPlanError: If validation fails
    """
    try:
        return Plan.model_validate_json(plan_text)
    except Exception as e:
        raise MalformedPlanError(f"Plan validation failed: {str(e)}") from e
