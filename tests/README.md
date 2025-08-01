# Tests Directory

This directory contains all test files for the ikoma-ai project. The tests are organized by functionality and cover various aspects of the system.

## Test Files Overview

### Agent Tests
- `test_agent_citations.py` - Tests for agent citation functionality
- `test_agent_phase1b.py` - Comprehensive agent functionality tests

### Sandbox and Tool Tests
- `test_sandbox_tools.py` - Tests for sandbox tool creation and loading functionality
- `test_tui_demo.py` - TUI demo test script for simple sandbox operations

### Schema/Validation Tests
- `test_plan_schema.py` - Plan schema and validation contract tests (strictness, roundtrip, error handling)
- `test_plan_reflection.py` - Plan self-reflection repair loop and retry logic for invalid plans

### Citation System Tests
- `test_citations.py` - Core citation management tests
- `test_citation_performance.py` - Performance tests for citation system
- `test_citation_state_persistence.py` - Citation state persistence tests
- `test_citation_superscripts.py` - Unicode superscript rendering tests
- `test_citation_vector_store.py` - Vector store integration for citations

### Web Extraction Tests
- `test_web_extraction.py` - Core web content extraction tests
- `test_web_extraction_citation.py` - Web extraction with citation integration
- `test_web_extraction_security.py` - Security and quality filtering tests
- `test_simple_web_extraction.py` - Basic web extraction functionality
- `test_web_tools.py` - Web search and tool integration tests

### HTTP and Network Tests
- `test_http_client.py` - HTTP client with rate limiting tests
- `test_domain_filter.py` - Domain filtering functionality tests
- `test_domain_filter_simple.py` - Simplified domain filter tests

### Security Tests
- `test_security_sanitization.py` - Content sanitization and security tests

### Persistence Tests
- `test_persistence_vector_store.py` - Vector store persistence tests
- `test_checkpointer.py` - SQLite conversation-state backend tests for crash recovery and exact resumption
- `test_checkpointer_crud.py` - CRUD operations for checkpoint records with Pydantic models and service layer
- `test_memory_manager_integration.py` - LangGraph memory manager integration and round-trip tests
- `test_checkpointer_toggle.py` - Checkpointer environment variable toggle tests for CHECKPOINTER_ENABLED and legacy compatibility

### Performance Benchmark Tests
- `test_benchmarks.py` - Performance benchmarking system tests including regression detection, baseline management, and metric collection

### Instrumentation Tests
- `test_instrumentation.py` - Agent instrumentation system tests including metrics collection, session tracking, and performance monitoring hooks
- `test_metrics.py` - Comprehensive metrics collection system tests including StepMetric, SessionMetric, MetricsCollector, and MetricsAnalyzer
- `test_metrics_dashboard.py` - Metrics dashboard functionality tests including API endpoints, chart generation, and FastAPI integration

### CLI and Interface Tests
- `test_cli_continuous.py` - Command-line interface continuous mode tests
- `test_cli_checkpointer.py` - CLI interface tests for checkpoint management commands
- `test_dashboard_caching.py` - Dashboard caching functionality tests
- `test_dashboard_demo_integration.py` - Dashboard demo integration and subprocess management tests
- `test_dashboard_mvp.py` - Dashboard MVP functionality and FastAPI integration tests
- `test_tui_basic.py` - Basic TUI functionality and component tests

### Heuristics & Iteration Control Tests
- `test_iteration_limit.py` - Tests for the iteration-count termination heuristic, including CLI/env overrides and integration
- `test_goal_criterion.py` - Unit tests for the goal satisfaction termination criterion
- `test_time_limit_criterion.py` - Unit tests for the time limit termination criterion
- `test_human_checkpoint.py` - Unit and integration tests for the human checkpoint criterion and user prompt in continuous mode
- `test_reflect_termination.py` - Integration tests for reflect/termination logic
- `test_goal_satisfaction_integration.py` - Integration tests for goal satisfaction and agent termination

## Running Tests

To run all tests:
```bash
python -m pytest tests/ -v
```

To run specific test categories:
```bash
# Agent tests
python -m pytest tests/test_agent_*.py -v

# Sandbox and tool tests
python -m pytest tests/test_sandbox_tools.py -v
python -m pytest tests/test_tui_demo.py -v

# Schema/Validation tests
python -m pytest tests/test_plan_schema.py -v
python -m pytest tests/test_plan_reflection.py -v

# Citation tests
python -m pytest tests/test_citation_*.py -v

# Web extraction tests
python -m pytest tests/test_web_*.py -v

# HTTP and network tests
python -m pytest tests/test_http_*.py tests/test_domain_*.py -v

# Persistence tests
python -m pytest tests/test_persistence_*.py tests/test_checkpointer*.py -v

# Checkpointer tests (new)
python -m pytest tests/test_checkpointer*.py tests/test_memory_manager*.py -v

# CLI tests
python -m pytest tests/test_cli_*.py -v

# Dashboard tests
python -m pytest tests/test_dashboard*.py -v

# TUI tests
python -m pytest tests/test_tui_*.py -v

# Performance benchmark tests
python -m pytest tests/test_benchmarks.py -v

# Instrumentation tests
python -m pytest tests/test_instrumentation.py -v
python -m pytest tests/test_metrics.py -v
python -m pytest tests/test_metrics_dashboard.py -v

To run with coverage:
```bash
python -m pytest tests/ --cov=. --cov-report=html
```

## Test Organization Benefits

- **Centralized Location**: All tests are now in one place, making them easier to find and maintain
- **Clear Separation**: Tests are logically grouped by functionality
- **Easier CI/CD**: Simplified test discovery and execution for continuous integration
- **Better Documentation**: This README provides an overview of what each test file covers
- **Reduced Clutter**: The root directory is now cleaner without scattered test files

## Adding New Tests

When adding new test files:
1. Place them in the `tests/` directory
2. Follow the naming convention: `test_<module>_<functionality>.py`
3. Update this README if adding a new test category
4. Ensure tests can be run from the project root directory 