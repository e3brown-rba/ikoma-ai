# GitHub Label Export & Analysis Guide

This guide helps you export existing GitHub labels and analyze them against our proposed Phase 1B label set.

## Quick Start

1. **Export your existing labels:**
   ```bash
   ./export_labels.sh
   ```

2. **Analyze the labels:**
   ```bash
   python analyze_labels.py
   ```

3. **Review the reports:**
   - `existing_labels.json` - Raw label data
   - `label_summary.md` - Categorized summary
   - `label_analysis_report.md` - Detailed analysis

## Prerequisites

### Required Tools
- `curl` - HTTP client
- `jq` - JSON processor

### Installation (macOS)
```bash
brew install curl jq
```

### Authentication (Optional but Recommended)
For better rate limits and access to private repos:

1. Create a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token (classic)
   - Select `repo` scope
   - Copy the token

2. Set environment variable:
   ```bash
   export GITHUB_TOKEN=your_token_here
   ```

## What the Scripts Do

### `export_labels.sh`
- Automatically detects your GitHub repository from git remote
- Fetches all labels via GitHub API
- Creates categorized summary
- Saves raw data for analysis

### `analyze_labels.py`
- Compares existing labels with proposed Phase 1B labels
- Finds exact and similar matches
- Categorizes labels by type
- Generates recommendations
- Creates detailed analysis report

## Output Files

### `existing_labels.json`
Raw JSON data from GitHub API containing all label information:
```json
[
  {
    "name": "bug",
    "color": "d73a4a",
    "description": "Something isn't working"
  }
]
```

### `label_summary.md`
Human-readable summary with labels organized by category:
- Priority/Severity
- Status/Workflow  
- Type/Category
- Platform
- Component/Area
- Other

### `label_analysis_report.md`
Comprehensive analysis including:
- Similarity matching between existing and proposed labels
- Recommendations for label reuse vs. creation
- Action plan for Phase 1B implementation

## Example Workflow

```bash
# 1. Export labels
./export_labels.sh

# 2. Analyze (if you have 50+ labels, this is much faster than manual review)
python analyze_labels.py

# 3. Review the analysis report
cat label_analysis_report.md

# 4. Make decisions on label strategy
# 5. Update issue templates with final label set
```

## Troubleshooting

### "Missing required tools"
Install missing dependencies:
```bash
brew install curl jq
```

### "Could not get git remote URL"
Make sure you're in a git repository with a GitHub remote:
```bash
git remote -v
```

### "Failed to fetch labels from GitHub API"
- Check your internet connection
- Verify repository exists and is accessible
- If private repo, ensure you have a valid `GITHUB_TOKEN`
- Check rate limits (try again later)

### "Invalid JSON response"
- Repository might not exist
- API endpoint might have changed
- Check GitHub status page

## Next Steps After Analysis

1. **Review the analysis report** to understand your current label landscape
2. **Decide on label strategy:**
   - Use existing labels for exact matches
   - Reuse similar labels where appropriate
   - Create new labels for missing essentials
3. **Update issue templates** with your final label set
4. **Test the labeling system** with sample issues
5. **Document your label conventions** for the team

## Integration with Existing Tools

This export/analysis workflow complements our existing tools:
- `check_labels.py` - Validates label format
- `label_comparison.py` - Compares proposed vs existing
- `LABEL_MANAGEMENT.md` - Overall strategy guide

The analysis results will help you make informed decisions about which labels to keep, modify, or create for Phase 1B. 