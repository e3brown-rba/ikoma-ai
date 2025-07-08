# Setup Issues for GitHub

## Issue 1: Python Version Detection in Setup Scripts

```markdown
---
name: Setup Script Python Version Detection
about: Fix Python version detection in setup scripts for cross-platform compatibility
title: '[SETUP] Fix Python version detection in setup scripts'
labels: ['setup', 'high', 'needs-triage', 'cross-platform']
assignees: ''
---

## Problem Description
The setup scripts (`setup_macos.sh`, `setup_windows.bat`) have hardcoded Python version detection that doesn't work reliably across different macOS configurations.

## Specific Issues
1. **macOS Setup Script**: Uses `python3 --version` which may not be available
2. **Version Parsing**: Assumes specific output format that varies by Python installation method
3. **Homebrew Detection**: Doesn't handle cases where Python is installed via Homebrew vs system Python
4. **Path Issues**: Doesn't account for different Python installation paths

## Steps to Reproduce
1. Fresh macOS installation
2. Install Python via Homebrew: `brew install python@3.11`
3. Run `./setup_macos.sh`
4. Script fails to detect correct Python version

## Expected Behavior
Script should detect Python 3.10+ regardless of installation method and provide clear guidance.

## Actual Behavior
Script fails with "Python 3.10+ required" even when Python 3.11 is installed.

## Environment
- **OS**: macOS 14.0+
- **Python Installation**: Homebrew
- **Python Version**: 3.11.x

## Proposed Solution
1. Use `python3 -c "import sys; print(sys.version_info)"` for reliable version detection
2. Add fallback detection methods for different installation types
3. Improve error messages with specific guidance
4. Add validation for virtual environment creation

## Priority
- [x] **High** - Blocks new developer onboarding

## Component
- [x] **Setup** - Installation/setup issues

## Platform
- [x] **macOS** - macOS-specific issues
- [x] **Cross-platform** - Affects all platforms
```

## Issue 2: Virtual Environment Path Issues

```markdown
---
name: Virtual Environment Path Resolution
about: Fix virtual environment path issues in run_agent.py
title: '[SETUP] Fix virtual environment path resolution in run_agent.py'
labels: ['setup', 'medium', 'needs-triage', 'agent']
assignees: ''
---

## Problem Description
The `run_agent.py` script has hardcoded virtual environment paths that don't work across different setups and platforms.

## Specific Issues
1. **Hardcoded Paths**: Script assumes specific venv location
2. **Platform Differences**: Windows vs macOS path handling
3. **PYTHONPATH Issues**: Module import failures due to incorrect path resolution
4. **Activation Scripts**: Different venv activation methods per platform

## Steps to Reproduce
1. Create virtual environment in non-standard location
2. Run `python run_agent.py`
3. Get import errors for local modules

## Expected Behavior
Script should automatically detect and use the correct virtual environment regardless of location.

## Actual Behavior
Script fails with module import errors due to incorrect PYTHONPATH.

## Environment
- **OS**: macOS 14.0+
- **Python**: 3.11.x
- **Virtual Environment**: Custom location

## Proposed Solution
1. Auto-detect virtual environment location
2. Use relative imports where possible
3. Add proper path resolution for different platforms
4. Improve error messages for path issues

## Priority
- [x] **Medium** - Affects development workflow

## Component
- [x] **Setup** - Installation/setup issues
- [x] **Agent** - Core agent functionality

## Platform
- [x] **Cross-platform** - Affects all platforms
```

## Issue 3: GitHub Token Authentication for Private Repos

```markdown
---
name: GitHub API Authentication for Private Repositories
about: Improve GitHub token handling for private repository access
title: '[SETUP] Improve GitHub token authentication for private repos'
labels: ['setup', 'low', 'needs-triage', 'tools']
assignees: ''
---

## Problem Description
The label export script (`export_labels.sh`) doesn't handle GitHub token authentication reliably for private repositories.

## Specific Issues
1. **Token Validation**: No validation of token format or permissions
2. **Error Handling**: Poor error messages for authentication failures
3. **Environment Variables**: Token persistence issues across shell sessions
4. **Rate Limiting**: No handling of API rate limits

## Steps to Reproduce
1. Set invalid GitHub token
2. Run `./export_labels.sh`
3. Get unclear error messages

## Expected Behavior
Script should validate token, provide clear error messages, and handle authentication gracefully.

## Actual Behavior
Script fails with "Bad credentials" or "Not Found" errors without clear guidance.

## Environment
- **OS**: macOS 14.0+
- **Repository**: Private GitHub repository
- **Authentication**: Personal Access Token

## Proposed Solution
1. Add token validation and format checking
2. Improve error messages with specific guidance
3. Add rate limit handling
4. Support multiple authentication methods

## Priority
- [x] **Low** - Nice to have improvement

## Component
- [x] **Setup** - Installation/setup issues
- [x] **Tools** - Tool system issues

## Platform
- [x] **Cross-platform** - Affects all platforms
```

## Issue 4: Cross-Platform Setup Script Consistency

```markdown
---
name: Cross-Platform Setup Script Consistency
about: Standardize setup scripts across platforms for better maintainability
title: '[SETUP] Standardize cross-platform setup script consistency'
labels: ['setup', 'medium', 'needs-triage', 'cross-platform']
assignees: ''
---

## Problem Description
Setup scripts for different platforms have inconsistent behavior, error handling, and user experience.

## Specific Issues
1. **Different Scripts**: Separate scripts for each platform create maintenance overhead
2. **Inconsistent Error Messages**: Different error handling per platform
3. **Feature Parity**: Some platforms have features others don't
4. **Testing Complexity**: Hard to test across all platforms

## Steps to Reproduce
1. Compare `setup_macos.sh` vs `setup_windows.bat`
2. Notice different error messages and behaviors
3. Try to maintain both scripts

## Expected Behavior
Consistent setup experience across all platforms with unified error handling.

## Actual Behavior
Different scripts with different behaviors and maintenance requirements.

## Environment
- **Platforms**: macOS, Windows, Linux
- **Scripts**: setup_macos.sh, setup_windows.bat

## Proposed Solution
1. Create unified Python-based setup script
2. Standardize error messages and handling
3. Add platform-specific modules for differences
4. Improve testing and validation

## Priority
- [x] **Medium** - Improves maintainability

## Component
- [x] **Setup** - Installation/setup issues

## Platform
- [x] **Cross-platform** - Affects all platforms
```

## Issue 5: Environment Variable Management

```markdown
---
name: Environment Variable Management and Validation
about: Improve environment variable handling and validation across the project
title: '[SETUP] Improve environment variable management and validation'
labels: ['setup', 'medium', 'needs-triage', 'cross-platform']
assignees: ''
---

## Problem Description
Environment variable handling is inconsistent and lacks proper validation across different parts of the project.

## Specific Issues
1. **Missing Validation**: No validation of required environment variables
2. **Inconsistent Loading**: Different methods for loading .env files
3. **Error Messages**: Poor error messages for missing variables
4. **Documentation**: Incomplete documentation of required variables

## Steps to Reproduce
1. Run setup without setting required environment variables
2. Get unclear error messages
3. Struggle to understand what variables are needed

## Expected Behavior
Clear validation, error messages, and documentation for all environment variables.

## Actual Behavior
Inconsistent handling and poor error messages for missing variables.

## Environment
- **Platforms**: All platforms
- **Components**: Setup scripts, agent, tools

## Proposed Solution
1. Create centralized environment variable management
2. Add validation for all required variables
3. Improve error messages and documentation
4. Add environment variable testing

## Priority
- [x] **Medium** - Improves developer experience

## Component
- [x] **Setup** - Installation/setup issues

## Platform
- [x] **Cross-platform** - Affects all platforms
``` 