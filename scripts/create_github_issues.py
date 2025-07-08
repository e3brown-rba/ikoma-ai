#!/usr/bin/env python3
"""
General GitHub Issue Creator for iKOMA
This script helps create GitHub issues from markdown templates.
"""

import json
import os
import re
import sys
from pathlib import Path

def extract_issues_from_markdown(markdown_file):
    """Extract issue templates from markdown file."""
    with open(markdown_file, 'r') as f:
        content = f.read()
    
    # Split by issue sections (supports multiple formats)
    issue_sections = re.split(r'## Issue \d+:|## Issue:|## \d+\.', content)[1:]
    
    issues = []
    for i, section in enumerate(issue_sections, 1):
        # Extract the markdown template
        match = re.search(r'```markdown\s*(.*?)\s*```', section, re.DOTALL)
        if match:
            issue_template = match.group(1).strip()
            issues.append({
                'number': i,
                'template': issue_template,
                'title': extract_title(issue_template)
            })
    
    return issues

def extract_title(template):
    """Extract title from issue template."""
    # Look for the title field in the frontmatter (with quotes)
    match = re.search(r'title:\s*[\'"]([^\'"]+)[\'"]', template)
    if match:
        return match.group(1).strip()
    
    # Fallback: look for title without quotes
    match = re.search(r'title:\s*(.+)', template)
    if match:
        return match.group(1).strip()
    
    return "Untitled Issue"

def extract_labels(template):
    """Extract labels from template."""
    labels_match = re.search(r'labels:\s*\[(.*?)\]', template)
    if labels_match:
        labels_str = labels_match.group(1)
        return [label.strip().strip("'\"") for label in labels_str.split(',')]
    return []

def create_github_cli_commands(issues):
    """Create GitHub CLI commands to create issues."""
    commands = []
    
    for issue in issues:
        # Extract labels
        labels = extract_labels(issue['template'])
        
        # Extract body (everything after the frontmatter)
        body_match = re.search(r'---\s*\n(.*?)\n---\s*\n(.*)', issue['template'], re.DOTALL)
        if body_match:
            body = body_match.group(2).strip()
        else:
            body = issue['template']
        
        # Create gh command
        labels_str = ','.join(labels) if labels else ''
        command = f'gh issue create --title "{issue["title"]}" --body "{body}" --label "{labels_str}"'
        commands.append(command)
    
    return commands

def create_manual_instructions(issues):
    """Create manual instructions for creating issues."""
    instructions = []
    
    for issue in issues:
        instructions.append(f"""
## Issue {issue['number']}: {issue['title']}

**Labels:** {', '.join(extract_labels(issue['template']))}

**Steps to create:**
1. Go to https://github.com/e3brown-rba/ikoma-ai/issues/new
2. Copy the template below
3. Paste and submit

**Template:**
```markdown
{issue['template']}
```
""")
    
    return instructions

def create_summary_file(issues, output_file):
    """Create a summary file with all issue details and commands."""
    with open(output_file, 'w') as f:
        f.write("# GitHub Issue Creation Summary\n\n")
        f.write(f"Found {len(issues)} issues to create:\n\n")
        
        for issue in issues:
            f.write(f"## Issue {issue['number']}: {issue['title']}\n")
            f.write(f"**Labels:** {', '.join(extract_labels(issue['template']))}\n\n")
            
            # Add GitHub CLI command
            labels = extract_labels(issue['template'])
            labels_str = ','.join(labels) if labels else ''
            
            # Extract body (everything after the frontmatter)
            body_match = re.search(r'---\s*\n(.*?)\n---\s*\n(.*)', issue['template'], re.DOTALL)
            if body_match:
                body = body_match.group(2).strip()
            else:
                body = issue['template']
            
            # Escape quotes in body for shell command
            body_escaped = body.replace('"', '\\"').replace("'", "\\'")
            
            f.write(f"**GitHub CLI Command:**\n")
            f.write(f"```bash\n")
            f.write(f'gh issue create --title "{issue["title"]}" --body "{body_escaped}" --label "{labels_str}"\n')
            f.write(f"```\n\n")

def main():
    """Main function."""
    print("iKOMA GitHub Issue Creator")
    print("=" * 50)
    
    # Get input file from command line or use default
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = 'issues.md'  # Default filename
    
    # Check if input file exists
    if not Path(input_file).exists():
        print(f"❌ {input_file} not found!")
        print(f"Usage: python scripts/create_github_issues.py [input_file.md]")
        print(f"Default: looks for 'issues.md' in current directory")
        sys.exit(1)
    
    # Extract issues
    issues = extract_issues_from_markdown(input_file)
    
    if not issues:
        print(f"❌ No issues found in {input_file}")
        sys.exit(1)
    
    print(f"✅ Found {len(issues)} issues to create from {input_file}")
    print()
    
    # Check if GitHub CLI is available
    if os.system('gh --version > /dev/null 2>&1') == 0:
        print("🎉 GitHub CLI detected! Here are the commands to create issues:")
        print()
        
        commands = create_github_cli_commands(issues)
        for i, command in enumerate(commands, 1):
            print(f"# Issue {i}")
            print(command)
            print()
        
        print("To run all commands:")
        print("1. Make sure you're authenticated: gh auth login")
        print("2. Run each command above")
        print()
        
    else:
        print("⚠️  GitHub CLI not found. Here are manual instructions:")
        print()
        
        instructions = create_manual_instructions(issues)
        for instruction in instructions:
            print(instruction)
    
    # Create a summary file
    summary_file = f"{Path(input_file).stem}_creation_summary.md"
    create_summary_file(issues, summary_file)
    
    print(f"📝 Summary saved to: {summary_file}")
    print()
    print("🎯 Next steps:")
    print("1. Create the issues using the commands/instructions above")
    print("2. Verify all issues are created in your GitHub repository")
    print(f"3. Delete {input_file} once all issues are created")
    print()
    print("💡 Tip: You can also run this script on any markdown file:")
    print(f"   python scripts/create_github_issues.py your_issues_file.md")

if __name__ == "__main__":
    main() 