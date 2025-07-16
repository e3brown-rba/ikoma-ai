"""Self-reflection repair hooks for invalid plans.

This module implements the reflection hook to repair invalid plans as specified
in Issue #18. It provides a retry mechanism that prompts the LLM to self-correct
malformed JSON plans using the exact schema and validation errors.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class PlanRepairFailure(Exception):
    """Raised when plan repair attempts are exhausted.

    This exception is raised when the LLM fails to produce valid JSON
    after the maximum number of retry attempts.
    """

    def __init__(self, message: str, attempts: int = 0):
        super().__init__(message)
        self.attempts = attempts


def build_reflection_prompt(
    invalid_plan: str,
    validation_error: str,
    schema_snippet: str | None = None
) -> str:
    """Build a reflection prompt to help the LLM self-correct invalid plans.

    Args:
        invalid_plan: The malformed JSON plan that failed validation
        validation_error: The Pydantic validation error message
        schema_snippet: Optional schema excerpt (first 60 lines of plan.schema.json)

    Returns:
        A formatted prompt asking the LLM to correct the invalid JSON
    """
    # Load schema snippet if not provided
    if schema_snippet is None:
        schema_path = Path("ikoma/schemas/plan.schema.json")
        if schema_path.exists():
            with open(schema_path) as f:
                schema_content = f.read()
                # Take first 60 lines for prompt efficiency
                schema_lines = schema_content.split("\n")[:60]
                schema_snippet = "\n".join(schema_lines)
        else:
            schema_snippet = "Schema file not found - using basic structure"

    prompt = f"""You generated an invalid plan JSON that failed validation. Please correct it.

INVALID JSON:
{invalid_plan}

VALIDATION ERROR:
{validation_error}

SCHEMA REQUIREMENTS:
{schema_snippet}

Return ONLY the corrected JSON that conforms to the schema above. No explanations or prose - just valid JSON."""

    return prompt


def repair_plan(
    llm: Any,
    invalid_plan: str,
    validation_error: str,
    retries: int = 1,
    schema_snippet: str | None = None
) -> str:
    """Prompt the LLM to self-correct an invalid plan JSON.

    Args:
        llm: The language model instance to use for repair
        invalid_plan: The malformed JSON plan that failed validation
        validation_error: The Pydantic validation error message
        retries: Maximum number of repair attempts (default: 1)
        schema_snippet: Optional schema excerpt for the prompt

    Returns:
        The corrected JSON plan string

    Raises:
        PlanRepairFailure: If all repair attempts fail validation
    """
    for attempt in range(1, retries + 1):
        logger.info(f"Plan repair attempt {attempt}/{retries}")

        # Build reflection prompt
        prompt = build_reflection_prompt(invalid_plan, validation_error, schema_snippet)

        # Get repair response from LLM
        response = llm.invoke([HumanMessage(content=prompt)])
        repaired_json = str(response.content).strip()

        # Clean up response if it contains markdown code blocks
        if repaired_json.startswith("```json"):
            repaired_json = repaired_json[7:-3].strip()
        elif repaired_json.startswith("```"):
            repaired_json = repaired_json[3:-3].strip()

        # Quick validation that it looks like JSON
        if repaired_json.startswith("{") and repaired_json.endswith("}"):
            try:
                # Test JSON parsing
                json.loads(repaired_json)
                logger.info(f"Plan repair attempt {attempt} succeeded")
                return repaired_json
            except json.JSONDecodeError:
                logger.warning(f"Plan repair attempt {attempt} produced invalid JSON")
                continue
        else:
            logger.warning(f"Plan repair attempt {attempt} did not produce JSON")
            continue

    # All attempts failed
    raise PlanRepairFailure(
        f"Exceeded plan repair retries ({retries} attempts)",
        attempts=retries
    )


def get_max_plan_retries() -> int:
    """Get the maximum number of plan repair retries from environment.

    Returns:
        Maximum retry attempts (default: 2)
    """
    return int(os.getenv("IKOMA_MAX_PLAN_RETRIES", "2"))
