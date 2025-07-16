# iKOMA Planning System

The iKOMA agent uses a machine-readable contract system for validating LLM-generated execution plans. This ensures deterministic validation and prevents field drift in plan structures.

## Overview

The planning system consists of:

- **JSON Schema**: `ikoma/schemas/plan.schema.json` - Draft-2020-12 compliant schema
- **Pydantic Models**: `ikoma/schemas/plan_models.py` - Type-safe validation models
- **Validation Hook**: Integrated into `agent.py` for automatic plan validation

## Schema Structure

### Plan Object
```json
{
  "plan": [
    {
      "step": 1,
      "tool_name": "list_sandbox_files",
      "args": {"query": ""},
      "description": "List available files in sandbox",
      "citations": [1, 2]
    }
  ],
  "reasoning": "Why this plan will achieve the user's goal"
}
```

### Validation Rules

- **Plan Array**: Must contain at least 1 step
- **Step Numbers**: Must be positive integers (≥1)
- **Tool Names**: Must exist in available tools (validated against `tool_loader.get_tool_names()`)
- **Citations**: Optional array of positive integers
- **Additional Properties**: Rejected (`additionalProperties: false`)

## Error Handling

When plan validation fails, the system:

1. Raises `MalformedPlanError` with detailed error message
2. Falls back to intelligent error recovery based on request type
3. For philosophical questions: Creates a thoughtful response file
4. For other requests: Lists available files as starting point

## Example Usage

### Valid Plan
```json
{
  "plan": [
    {
      "step": 1,
      "tool_name": "search_web",
      "args": {"query": "Python best practices 2025"},
      "description": "Search for current Python best practices [[1]]",
      "citations": [1]
    },
    {
      "step": 2,
      "tool_name": "create_text_file",
      "args": {"filename_and_content": "best_practices.txt|||Content here"},
      "description": "Create file with researched practices [[1]]",
      "citations": [1]
    }
  ],
  "reasoning": "This plan searches for current information and documents it properly"
}
```

### Invalid Plan (Missing Required Field)
```json
{
  "plan": [
    {
      "step": 1,
      "args": {"query": ""},
      "description": "List files"
      // Missing tool_name - will fail validation
    }
  ],
  "reasoning": "Start by exploring"
}
```

## Integration with Agent

The validation is integrated into the `plan_node` function in `agent.py`:

```python
# Validate plan using schema
try:
    validated_plan = Plan.model_validate_json(plan_text)
    # Convert PlanStep objects back to dictionaries for state compatibility
    state["current_plan"] = [step.model_dump() for step in validated_plan.plan]
    state["continue_planning"] = True
except Exception as e:
    raise MalformedPlanError(str(e)) from e
```

## Schema Generation

The JSON schema is auto-generated from Pydantic models to ensure consistency:

```bash
python -m ikoma.schemas.generate
```

This command:
1. Reads the Pydantic models from `plan_models.py`
2. Generates Draft-2020-12 compliant JSON Schema
3. Writes to `plan.schema.json`
4. Used in CI to detect schema drift

## Testing

Comprehensive tests are available in `tests/test_plan_schema.py`:

- Valid plan validation
- Invalid field rejection
- Tool name validation
- Citation validation
- Schema generation roundtrip
- Error handling

Run tests with:
```bash
pytest tests/test_plan_schema.py -v
```

## Benefits

1. **Deterministic Validation**: Schema ensures consistent plan structure
2. **Type Safety**: Pydantic models provide compile-time validation
3. **Error Recovery**: Intelligent fallbacks for malformed plans
4. **Documentation**: Self-documenting schema with examples
5. **CI Integration**: Automated schema drift detection
6. **Future-Proof**: Foundation for Issue 18's self-reflection auto-rewrite

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAN_SCHEMA_VERSION` | Override schema version | `1.0.0` |

## Troubleshooting

### Common Validation Errors

1. **Unknown Tool**: Check that tool name exists in `tools/mcp_schema.json`
2. **Missing Field**: Ensure all required fields are present
3. **Invalid Step Number**: Step numbers must be ≥1
4. **Invalid Citations**: Citation IDs must be positive integers

### Debugging

Enable verbose planning with:
```bash
export VERBOSE_PLANNING=true
```

This will show detailed validation errors in the agent output. 