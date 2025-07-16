#!/usr/bin/env python3
"""Generate JSON Schema from Pydantic models for CI validation.

This script ensures the schema file stays in sync with the Pydantic models.
Run this in CI to detect schema drift.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ikoma.schemas.plan_models import generate_schema  # noqa: E402


def main() -> int:
    """Generate schema and write to file."""
    try:
        # Generate schema from Pydantic models
        schema = generate_schema()

        # Write to schema file
        schema_path = Path(__file__).parent / "plan.schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)

        print(f"✅ Generated schema: {schema_path}")
        return 0

    except Exception as e:
        print(f"❌ Error generating schema: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
