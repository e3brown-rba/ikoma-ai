# iKOMA Scripts

This directory contains utility scripts for the iKOMA project.

## Available Scripts

### `create_github_issues.py`

A general-purpose script to create GitHub issues from markdown templates.

#### Usage

```bash
# Create issues from default file (issues.md)
python scripts/create_github_issues.py

# Create issues from specific file
python scripts/create_github_issues.py my_issues.md

# Create issues from setup issues (if you have setup_issues.md)
python scripts/create_github_issues.py setup_issues.md
```

#### Input Format

Create a markdown file with issue templates in this format:

```markdown
## Issue 1: Brief Description

```markdown
---
name: Issue Name
about: Brief description
title: '[TYPE] Issue title'
labels: ['label1', 'label2', 'label3']
assignees: ''
---

## Problem Description
Detailed description of the problem...

## Steps to Reproduce
1. Step 1
2. Step 2

## Expected Behavior
What should happen...

## Actual Behavior
What actually happens...

## Proposed Solution
How to fix it...
```

## Issue 2: Another Issue

```markdown
---
name: Another Issue
about: Another description
title: '[TYPE] Another title'
labels: ['label1', 'label2']
assignees: ''
---

## Problem Description
...
```

#### Output

The script will:
1. Extract all issue templates from the markdown file
2. Generate GitHub CLI commands for each issue
3. Create a summary file with all commands
4. Provide manual instructions if GitHub CLI is not available

#### Requirements

- Python 3.6+
- GitHub CLI (optional, for automated creation)
- Valid GitHub authentication (if using GitHub CLI)

#### Example Workflow

1. **Create issue templates:**
   ```bash
   # Create issues.md with your issue templates
   vim issues.md
   ```

2. **Generate commands:**
   ```bash
   python scripts/create_github_issues.py issues.md
   ```

3. **Create issues:**
   ```bash
   # Copy and run the generated commands
   gh issue create --title "..." --body "..." --label "..."
   ```

4. **Clean up:**
   ```bash
   # Delete the template file once issues are created
   rm issues.md
   ```

## Future Scripts

This directory can be expanded with other utility scripts such as:
- Release automation
- Documentation generation
- Testing utilities
- Deployment scripts 