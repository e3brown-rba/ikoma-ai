#!/usr/bin/env python3
"""
iKOMA Setup Verification Script
Checks the current state of your iKOMA installation and provides guidance.
"""

import importlib.util
import sys
from pathlib import Path


def print_header(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
    }
    color = colors.get(status, "\033[0m")
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {message}")


def check_python_version():
    """Check if Python version meets requirements."""
    print_header("Python Version Check")

    version = sys.version_info
    print(f"Current Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 11:
        print_status("✅ Python version meets requirements (3.11+)", "SUCCESS")
        return True
    elif version.major == 3 and version.minor >= 10:
        print_status("⚠️  Python version acceptable but 3.11+ recommended", "WARNING")
        print_status("Upgrade to Python 3.11+ for best performance", "INFO")
        return True
    else:
        print_status("❌ Python version too old. Need 3.10+", "ERROR")
        print_status(
            "Install Python 3.11+ using Homebrew: brew install python@3.11", "WARNING"
        )
        return False


def check_virtual_environment():
    """Check if virtual environment is active."""
    print_header("Virtual Environment Check")

    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print_status("✅ Virtual environment is active", "SUCCESS")
        print(f"Environment: {sys.prefix}")
        return True
    else:
        print_status("❌ Virtual environment not active", "WARNING")
        print_status("Activate with: source venv/bin/activate", "INFO")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print_header("Dependencies Check")

    required_packages = [
        "langchain",
        "langchain-core",
        "langchain-openai",
        "langchain-community",
        "langgraph",
        "chromadb",
        "openai",
        "dotenv",
        "pydantic",
        "fastapi",
        "uvicorn",
        "rich",
        "jinja2",
        "sse_starlette",
        "websockets",
    ]

    missing_packages = []
    installed_packages = []

    for package in required_packages:
        try:
            importlib.import_module(package.replace("-", "_"))
            installed_packages.append(package)
            print_status(f"✅ {package}", "SUCCESS")
        except ImportError:
            missing_packages.append(package)
            print_status(f"❌ {package}", "ERROR")

    if missing_packages:
        print_status(f"Missing packages: {', '.join(missing_packages)}", "WARNING")
        print_status("Install with: pip install -r requirements.txt", "INFO")
        return False
    else:
        print_status("✅ All required dependencies installed", "SUCCESS")
        return True


def check_environment_file():
    """Check if .env file exists and is configured."""
    print_header("Environment Configuration")

    env_file = Path(".env")
    if env_file.exists():
        print_status("✅ .env file exists", "SUCCESS")

        # Check key configurations
        with open(env_file) as f:
            content = f.read()

        key_configs = [
            "LMSTUDIO_BASE_URL",
            "LMSTUDIO_MODEL",
            "VECTOR_STORE_PATH",
            "SANDBOX_PATH",
        ]

        for config in key_configs:
            if config in content:
                print_status(f"✅ {config} configured", "SUCCESS")
            else:
                print_status(f"⚠️  {config} not found", "WARNING")

        return True
    else:
        print_status("❌ .env file missing", "ERROR")
        print_status("Create with: cp config.env.template .env", "INFO")
        return False


def check_directories():
    """Check if required directories exist."""
    print_header("Directory Structure")

    required_dirs = ["agent/memory/vector_store", "agent/ikoma_sandbox", "tools"]

    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print_status(f"✅ {dir_path}", "SUCCESS")
        else:
            print_status(f"❌ {dir_path}", "ERROR")
            all_exist = False

    if not all_exist:
        print_status(
            "Create missing directories with: mkdir -p agent/memory/vector_store agent/ikoma_sandbox",
            "INFO",
        )

    return all_exist


def check_lm_studio():
    """Check if LM Studio is accessible."""
    print_header("LM Studio Check")

    try:
        import requests

        response = requests.get("http://127.0.0.1:11434/v1/models", timeout=5)
        if response.status_code == 200:
            print_status("✅ LM Studio server is running", "SUCCESS")
            models = response.json()
            if models.get("data"):
                print_status(f"✅ {len(models['data'])} model(s) available", "SUCCESS")
                for model in models["data"]:
                    print(f"   - {model.get('id', 'Unknown')}")
            else:
                print_status("⚠️  No models loaded in LM Studio", "WARNING")
            return True
        else:
            print_status("❌ LM Studio server responded with error", "ERROR")
            return False
    except requests.exceptions.ConnectionError:
        print_status("❌ Cannot connect to LM Studio server", "ERROR")
        print_status("Ensure LM Studio is running on port 11434", "INFO")
        return False
    except ImportError:
        print_status("⚠️  requests library not available for LM Studio check", "WARNING")
        return False


def check_tui_and_dashboard():
    """Check if TUI and dashboard components can be imported."""
    print_header("TUI and Dashboard Check")

    # Check TUI imports
    try:
        from agent.ui.tui import IkomaTUI  # noqa: F401

        print_status("✅ TUI imports working", "SUCCESS")
        tui_ok = True
    except ImportError as e:
        print_status(f"❌ TUI import failed: {e}", "ERROR")
        tui_ok = False

    # Check dashboard imports
    try:
        from dashboard.app import app  # noqa: F401

        print_status("✅ Dashboard imports working", "SUCCESS")
        dashboard_ok = True
    except ImportError as e:
        print_status(f"❌ Dashboard import failed: {e}", "ERROR")
        dashboard_ok = False

    # Check modern Python syntax
    try:
        # Test modern union syntax
        _: dict[str, str] | None = None  # noqa: F841
        print_status("✅ Modern union syntax supported", "SUCCESS")
        syntax_ok = True
    except SyntaxError as e:
        print_status(f"❌ Modern syntax not supported: {e}", "ERROR")
        syntax_ok = False

    return tui_ok and dashboard_ok and syntax_ok


def check_tests():
    """Check if tests can run."""
    print_header("Test Availability")

    test_files = [
        "tests/test_agent_phase1b.py",
        "tests/test_persistence_vector_store.py",
        "tests/test_tui_basic.py",
        "tests/test_dashboard_mvp.py",
        "tests/test_dashboard_demo_integration.py",
    ]

    for test_file in test_files:
        if Path(test_file).exists():
            print_status(f"✅ {test_file} available", "SUCCESS")
        else:
            print_status(f"❌ {test_file} missing", "ERROR")

    return all(Path(f).exists() for f in test_files)


def main():
    """Main verification function."""
    print_header("iKOMA Setup Verification")
    print("Checking your iKOMA installation...")

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("Environment File", check_environment_file),
        ("Directories", check_directories),
        ("TUI and Dashboard", check_tui_and_dashboard),
        ("LM Studio", check_lm_studio),
        ("Tests", check_tests),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_status(f"Error checking {name}: {e}", "ERROR")
            results.append((name, False))

    # Summary
    print_header("Setup Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Passed: {passed}/{total} checks")

    if passed == total:
        print_status("🎉 All checks passed! Your iKOMA setup is ready.", "SUCCESS")
        print_status("Run the agent with: python run_agent.py", "INFO")
    else:
        print_status("⚠️  Some checks failed. Review the issues above.", "WARNING")
        print_status("Run the setup script: ./setup.sh", "INFO")
        print_status("Or follow the manual setup guide: QUICK_SETUP.md", "INFO")

    # Next steps
    print_header("Next Steps")
    print("1. If all checks passed: python run_agent.py")
    print("2. If some failed: ./setup.sh")
    print("3. For detailed help: QUICK_SETUP.md")
    print("4. For technical details: README.md")


if __name__ == "__main__":
    main()
