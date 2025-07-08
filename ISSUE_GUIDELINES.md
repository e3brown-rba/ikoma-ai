# Issue Filing Guidelines

## Issue Types and Templates

### 1. Bug Reports (`bug_report.md`)
Use for:
- Unexpected behavior or crashes
- Incorrect functionality
- Performance issues
- Security vulnerabilities

**Labels**: `bug`, `needs-triage`

### 2. Enhancement Requests (`enhancement_request.md`)
Use for:
- New features
- Improvements to existing functionality
- UX/UI improvements
- Performance optimizations

**Labels**: `enhancement`, `needs-triage`

### 3. Platform Issues (`platform_issue.md`)
Use for:
- macOS-specific problems
- Windows-specific problems
- Cross-platform compatibility issues
- Setup/installation problems on specific platforms

**Labels**: `platform`, `needs-triage`

## Label System

### Priority Labels
- `critical` - System-breaking issues
- `high` - Major functionality affected
- `medium` - Moderate impact
- `low` - Minor issues or improvements

### Platform Labels
- `platform:windows` - Windows-specific
- `platform:macos` - macOS-specific
- `platform:linux` - Linux-specific
- `cross-platform` - Affects all platforms

### Status Labels
- `needs-triage` - New issue, needs review
- `in-progress` - Being worked on
- `blocked` - Waiting for dependencies
- `ready-for-review` - Ready for PR review
- `wont-fix` - Issue will not be addressed

### Component Labels
- `agent` - Core agent functionality
- `memory` - Memory/vector store issues
- `tools` - Tool system issues
- `setup` - Installation/setup issues
- `ui/ux` - User interface issues

## Filing Issues for Phase 1B

### Current Known Issues to File

1. **Telemetry Errors**
   - Template: Bug Report
   - Labels: `bug`, `low`, `agent`
   - Description: Repeated telemetry capture errors in agent startup

2. **Confirmation Prompt UX**
   - Template: Enhancement Request
   - Labels: `enhancement`, `medium`, `ui/ux`
   - Description: Improve confirmation prompt flow for file operations

3. **Platform-Specific Setup**
   - Template: Platform Issue
   - Labels: `platform`, `platform:macos`, `setup`
   - Description: macOS setup requires different steps than Windows

4. **Memory Import Issues**
   - Template: Bug Report
   - Labels: `bug`, `medium`, `memory`
   - Description: Module import issues with tools package

## Issue Quality Checklist

Before submitting an issue, ensure:

- [ ] You've searched for existing issues
- [ ] You've provided clear reproduction steps
- [ ] You've included relevant environment details
- [ ] You've specified the impact on main branch
- [ ] You've used the appropriate template
- [ ] You've added relevant labels

## Impact on Main Branch

When filing issues, consider:

1. **Does this affect the Windows Phase 1B freeze?**
   - If yes, mark as `critical` or `high`
   - Include in issue description

2. **Is this macOS-specific?**
   - Use `platform:macos` label
   - Note if it doesn't affect main branch

3. **Does this require cross-platform changes?**
   - Use `cross-platform` label
   - Consider impact on both branches

## Example Issue Titles

```
[BUG] Telemetry capture errors during agent startup
[ENHANCEMENT] Improve file operation confirmation UX
[PLATFORM] macOS setup requires Homebrew installation
[BUG] Module import error with tools package on macOS
``` 