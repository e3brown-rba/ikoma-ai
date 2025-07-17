#!/usr/bin/env python3
"""
Comprehensive Phase 2 update for repo_structure.jsonl
Captures all missing Phase 2 progress including Epics E-01 through E-04
Aligned with TODO.md epic structure and status
"""

import json
from datetime import datetime
from pathlib import Path


def get_file_info(file_path):
    """Get file information for repo structure entry"""
    stat = file_path.stat()
    return {
        "size_kb": round(stat.st_size / 1024, 1),
        "lines": len(file_path.read_text().splitlines()) if file_path.is_file() else 0,
    }


def update_repo_structure():
    """Comprehensive Phase 2 update for repo structure - aligned with TODO.md"""

    # Read existing structure
    repo_structure_file = Path("repo_structure.jsonl")
    with open(repo_structure_file) as f:
        existing_entries = [json.loads(line) for line in f if line.strip()]

    # Create a map of existing entries by path
    existing_map = {}
    for entry in existing_entries:
        if "path" in entry:
            existing_map[entry["path"]] = entry

    # ===== PHASE 2 TOOLS UPDATES =====

    # Update tools directory with Phase 2 additions
    tools_dir = Path("tools")
    if tools_dir.exists():
        tool_files = list(tools_dir.glob("*.py")) + list(tools_dir.glob("*.json"))
        tool_contents = [f.name for f in tool_files]

        # Update tools directory entry
        tools_entry = {
            "type": "tools_package",
            "path": "tools/",
            "purpose": "phase_2_comprehensive_tool_system",
            "status": "phase_2_complete",
            "description": "Comprehensive Phase 2 tool system with internet capabilities, security, and citation management",
            "contents": tool_contents,
            "features": [
                "dynamic_loading",
                "mcp_schema",
                "performance_optimization",
                "internet_tools",
                "security_validation",
                "citation_system",
                "http_client",
                "web_extraction",
            ],
            "phase_2_additions": [
                "web_tools.py",
                "web_extraction.py",
                "content_extractor.py",
                "domain_filter.py",
                "security.py",
                "web_security.py",
                "http_client.py",
                "http_tools.py",
                "citation_manager.py",
            ],
            "last_updated": "phase_2_comprehensive_update",
        }

        # Add/update individual tool files
        for tool_file in tool_files:
            file_info = get_file_info(tool_file)

            if tool_file.name == "web_tools.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "web_search_and_extraction",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Web search and content extraction tools with SerpAPI integration and security validation",
                    "features": [
                        "web_search",
                        "content_extraction",
                        "security_validation",
                        "quality_filtering",
                        "chromadb_storage",
                    ],
                    "api_integration": "serpapi",
                    "security_features": ["domain_filtering", "content_sanitization"],
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "web_extraction.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "content_extraction_engine",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Advanced web content extraction with trafilatura, quality scoring, and fallback strategies",
                    "features": [
                        "trafilatura_parsing",
                        "quality_assessment",
                        "speed_optimization",
                        "fallback_methods",
                        "content_cleaning",
                    ],
                    "extraction_methods": ["wikipedia", "blog", "news"],
                    "quality_scoring": "textstat_integration",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "content_extractor.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "content_processing",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Content extraction and processing with quality assessment and text chunking",
                    "features": [
                        "quality_scoring",
                        "text_chunking",
                        "metadata_extraction",
                        "complexity_detection",
                    ],
                    "quality_metrics": ["readability", "complexity", "content_length"],
                    "chunking_strategy": "semantic_splitting",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "domain_filter.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "security_filtering",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Domain filtering system with allowlist/denylist support and wildcard matching",
                    "features": [
                        "domain_validation",
                        "wildcard_matching",
                        "cache_functionality",
                        "config_reload",
                    ],
                    "config_files": [".allow_domains.txt", ".deny_domains.txt"],
                    "matching_strategy": "exact_and_wildcard",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "security.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "content_security",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Content security and sanitization with OWASP-compliant validation",
                    "features": [
                        "url_sanitization",
                        "title_sanitization",
                        "metadata_validation",
                        "content_safety",
                    ],
                    "security_standards": [
                        "owasp_compliant",
                        "xss_prevention",
                        "injection_protection",
                    ],
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "web_security.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "web_security_filter",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Web security filter with content quality assessment and ChromaDB storage",
                    "features": [
                        "quality_filtering",
                        "content_storage",
                        "rate_limiting",
                        "security_validation",
                    ],
                    "storage_backend": "chromadb",
                    "quality_threshold": "configurable",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "http_client.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "rate_limited_http",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Rate-limited HTTP client with token bucket algorithm and comprehensive error handling",
                    "features": [
                        "rate_limiting",
                        "token_bucket",
                        "backoff_strategy",
                        "user_agent_rotation",
                        "domain_filtering",
                    ],
                    "algorithm": "token_bucket",
                    "error_handling": "comprehensive",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "http_tools.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "http_utilities",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "HTTP utility tools with request/response handling and connection testing",
                    "features": [
                        "make_http_request",
                        "get_http_client_stats",
                        "test_http_connection",
                    ],
                    "request_methods": ["GET", "POST"],
                    "response_formatting": "structured",
                    "last_updated": "epic_01_completion",
                }
            elif tool_file.name == "citation_manager.py":
                tool_entry = {
                    "type": "tool_file",
                    "path": f"tools/{tool_file.name}",
                    "purpose": "citation_system",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "epic_01_complete",
                    "description": "Citation management system with Unicode superscript support and Rich integration",
                    "features": [
                        "citation_storage",
                        "unicode_superscript",
                        "rich_integration",
                        "citation_extraction",
                    ],
                    "citation_format": "[[n]]",
                    "unicode_support": "superscript_rendering",
                    "last_updated": "epic_01_completion",
                }
            else:
                # Keep existing tool entries for legacy tools
                continue

            existing_map[f"tools/{tool_file.name}"] = tool_entry

        existing_map["tools/"] = tools_entry

    # ===== PLANNING MODULE (ISSUE #18) =====

    planning_dir = Path("planning")
    if planning_dir.exists():
        planning_files = list(planning_dir.glob("*.py"))
        planning_contents = [f.name for f in planning_files]

        planning_directory_entry = {
            "type": "planning_directory",
            "path": "planning/",
            "purpose": "planning_system",
            "status": "epic_e04_complete",
            "description": "Planning system with self-reflection repair hooks for invalid plans",
            "contents": planning_contents,
            "features": ["reflection_hooks", "plan_repair", "schema_validation"],
            "last_updated": "issue_18_completion",
        }

        for planning_file in planning_files:
            file_info = get_file_info(planning_file)

            if planning_file.name == "__init__.py":
                planning_entry = {
                    "type": "planning_module_init",
                    "path": f"planning/{planning_file.name}",
                    "purpose": "planning_package_init",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "issue_18_complete",
                    "description": "Planning package initialization with reflection hook exports",
                    "exports": [
                        "PlanRepairFailure",
                        "repair_plan",
                        "build_reflection_prompt",
                    ],
                    "last_updated": "issue_18_completion",
                }
            elif planning_file.name == "reflection.py":
                planning_entry = {
                    "type": "planning_reflection_module",
                    "path": f"planning/{planning_file.name}",
                    "purpose": "plan_repair_system",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "issue_18_complete",
                    "description": "Self-reflection retry loop for repairing invalid plans (Issue #18)",
                    "features": [
                        "retry_loop",
                        "prompt_builder",
                        "error_handling",
                        "metrics_tracking",
                        "environment_config",
                    ],
                    "key_functions": [
                        "repair_plan",
                        "build_reflection_prompt",
                        "get_max_plan_retries",
                    ],
                    "environment_variable": "IKOMA_MAX_PLAN_RETRIES",
                    "last_updated": "issue_18_completion",
                }

            existing_map[f"planning/{planning_file.name}"] = planning_entry

        existing_map["planning/"] = planning_directory_entry

    # ===== TESTS DIRECTORY UPDATES =====

    tests_dir = Path("tests")
    if tests_dir.exists():
        test_files = list(tests_dir.glob("*.py"))
        test_contents = [f.name for f in test_files]

        # Update tests directory entry
        tests_entry = {
            "type": "test_directory",
            "path": "tests/",
            "purpose": "comprehensive_test_suite",
            "status": "phase_2_complete",
            "description": "Comprehensive Phase 2 test suite with internet tools, security, citation, and planning tests",
            "total_tests": len(test_files),
            "test_categories": [
                "agent_tests",
                "citation_tests",
                "web_extraction_tests",
                "http_network_tests",
                "security_tests",
                "persistence_tests",
                "cli_interface_tests",
                "planning_tests",
            ],
            "contents": test_contents,
            "documentation": "tests/README.md",
            "package_structure": "tests/__init__.py",
            "last_updated": "phase_2_comprehensive_update",
        }

        # Add new test files
        for test_file in test_files:
            file_info = get_file_info(test_file)

            if test_file.name == "test_plan_reflection.py":
                test_entry = {
                    "type": "test_file",
                    "path": f"tests/{test_file.name}",
                    "purpose": "planning_reflection_tests",
                    "language": "python",
                    "lines": file_info["lines"],
                    "size_kb": file_info["size_kb"],
                    "status": "issue_18_complete",
                    "description": "Comprehensive test suite for plan reflection repair functionality",
                    "test_coverage": [
                        "prompt_building",
                        "retry_logic",
                        "environment_overrides",
                        "error_handling",
                        "integration_tests",
                    ],
                    "total_tests": 16,
                    "test_categories": [
                        "reflection_prompt",
                        "repair_success",
                        "repair_failure",
                        "environment_config",
                        "integration",
                    ],
                    "last_updated": "issue_18_completion",
                }
                existing_map[f"tests/{test_file.name}"] = test_entry

        existing_map["tests/"] = tests_entry

    # ===== AGENT UPDATES =====

    agent_file = Path("agent/agent.py")
    if agent_file.exists():
        file_info = get_file_info(agent_file)
        # Update agent.py entry
        for entry in existing_entries:
            if entry.get("path") == "agent/agent.py":
                entry.update(
                    {
                        "lines": file_info["lines"],
                        "size_kb": file_info["size_kb"],
                        "status": "phase_2_complete",
                        "description": "Phase 2 plan-execute-reflect agent with comprehensive internet tools, security, and planning enhancements",
                        "key_components": [
                            "AgentState",
                            "plan_node",
                            "execute_node",
                            "reflect_node",
                            "PersistentVectorStore",
                            "check_env",
                            "shared_resource_optimization",
                            "argument_format_conversion",
                            "plan_repair_integration",
                            "continuous_mode",
                            "termination_heuristics",
                            "human_checkpoints",
                        ],
                        "phase_2_features": [
                            "internet_tools",
                            "security_validation",
                            "citation_system",
                            "continuous_mode",
                            "termination_heuristics",
                            "human_checkpoints",
                            "plan_repair",
                        ],
                        "last_updated": "phase_2_comprehensive_update",
                    }
                )
                break

    # ===== CONFIG UPDATES =====

    config_file = Path("config.env.template")
    if config_file.exists():
        file_info = get_file_info(config_file)
        # Update config template entry
        for entry in existing_entries:
            if entry.get("path") == "config.env.template":
                entry.update(
                    {
                        "lines": file_info["lines"],
                        "size_kb": file_info["size_kb"],
                        "status": "phase_2_complete",
                        "description": "Environment configuration template with comprehensive Phase 2 settings",
                        "sections": [
                            "lm_studio_config",
                            "vector_store_config",
                            "agent_config",
                            "performance_config",
                            "debug_config",
                            "security_config",
                            "planning_config",
                            "continuous_mode_config",
                            "checkpointer_config",
                        ],
                        "phase_2_additions": [
                            "SERPAPI_API_KEY",
                            "IKOMA_MAX_PLAN_RETRIES",
                            "IKOMA_MAX_ITER",
                            "IKOMA_MAX_MINS",
                            "IKOMA_CHECKPOINT_EVERY",
                            "CHECKPOINTER_ENABLED",
                        ],
                        "last_updated": "phase_2_comprehensive_update",
                    }
                )
                break

    # ===== PHASE 2 COMPLETION ENTRIES (ALIGNED WITH TODO.md) =====

    # Epic E-01: Internet Tooling (COMPLETED per TODO.md)
    epic_e01_entry = {
        "type": "epic_e01_completion",
        "epic": "E-01",
        "title": "Internet Tooling",
        "status": "complete",
        "description": "Comprehensive internet tooling with security validation, domain filtering, and citation management",
        "completion_date": "2025-07-16",
        "key_achievements": [
            "domain_filtering",
            "rate_limited_http_client",
            "serpapi_search",
            "html_text_extractor",
            "security_first_web_extraction",
            "citation_tokens",
            "citation_superscripts",
        ],
        "issues_completed": [
            "Issue #4: Domain allow/deny filter",
            "Issue #5: Rate-limited HTTP client wrapper",
            "Issue #2: SerpAPI search tool",
            "Issue #3: HTML→Text extractor utility",
            "Issue #6: Security-first HTML→Text extractor",
            "Issue #7: Prompt template — add citation tokens",
            "Issue #8: Render citation superscripts in TUI/dashboard",
        ],
        "total_issues": 7,
        "completion_rate": "100%",
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e01_entry)

    # Epic E-02: Continuous Mode (COMPLETED per TODO.md)
    epic_e02_entry = {
        "type": "epic_e02_completion",
        "epic": "E-02",
        "title": "Continuous Mode",
        "status": "complete",
        "description": "Unattended execution capabilities with safety guardrails and termination heuristics",
        "completion_date": "2025-07-16",
        "key_achievements": [
            "continuous_mode_cli",
            "iteration_termination",
            "time_limit_termination",
            "goal_satisfaction_termination",
            "human_checkpoints",
        ],
        "issues_completed": [
            "Issue #9: Add --continuous CLI flag",
            "Issue #10: Termination heuristic — iteration-count",
            "Issue #11: Termination heuristic — wall-clock time limit",
            "Issue #12: Termination heuristic — goal-satisfaction",
            "Issue #13: Human checkpoint — confirm continuation",
        ],
        "total_issues": 5,
        "completion_rate": "100%",
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e02_entry)

    # Epic E-03: Short-term Checkpointer (COMPLETED per TODO.md)
    epic_e03_entry = {
        "type": "epic_e03_completion",
        "epic": "E-03",
        "title": "Short-term Checkpointer",
        "status": "complete",
        "description": "SQLite conversation-state backend for crash recovery and exact resumption",
        "completion_date": "2025-07-16",
        "key_achievements": [
            "sqlite_backend",
            "crud_api",
            "langgraph_integration",
            "environment_configuration",
            "cli_management",
        ],
        "issues_completed": [
            "Issue #14: Schema & backend (memory)",
            "Issue #15: Short-term Checkpointer CRUD API and LangGraph integration",
            "Issue #16: .env toggle & docs (configuration)",
        ],
        "total_issues": 3,
        "completion_rate": "100%",
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e03_entry)

    # Epic E-04: Planner Enhancements (COMPLETED per TODO.md)
    epic_e04_entry = {
        "type": "epic_e04_completion",
        "epic": "E-04",
        "title": "Planner Enhancements",
        "status": "complete",
        "description": "JSON schema validation and self-reflection repair hooks for enhanced planning",
        "completion_date": "2025-07-16",
        "key_achievements": [
            "json_schema_validation",
            "reflection_repair_hooks",
            "environment_configuration",
            "comprehensive_testing",
        ],
        "issues_completed": [
            "Issue #17: JSON schema + validator",
            "Issue #18: Reflection hook to repair invalid plans",
        ],
        "total_issues": 2,
        "completion_rate": "100%",
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e04_entry)

    # Epic E-05: UI/UX (PLANNED per TODO.md)
    epic_e05_entry = {
        "type": "epic_e05_planned",
        "epic": "E-05",
        "title": "UI/UX",
        "status": "planned",
        "description": "TUI refactor and Dashboard PoC for enhanced user experience",
        "planned_issues": [
            "Issue #19: TUI refactor (ux)",
            "Issue #20: Dashboard PoC (ux)",
        ],
        "total_issues": 2,
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e05_entry)

    # Epic E-06: Dev & Safety Hardening (PLANNED per TODO.md)
    epic_e06_entry = {
        "type": "epic_e06_planned",
        "epic": "E-06",
        "title": "Dev & Safety Hardening",
        "status": "planned",
        "description": "Performance benchmarks, test coverage, and security scanners",
        "planned_issues": [
            "Issue #21: Perf bench CI (metrics)",
            "Issue #22: Coverage ≥ 50% (testing)",
            "Issue #23: Security scanners (safety)",
        ],
        "total_issues": 3,
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(epic_e06_entry)

    # Issue #18 specific entry
    issue_18_entry = {
        "type": "issue_18_completion",
        "issue": "18",
        "title": "Reflection Hook to Repair Invalid Plans",
        "status": "complete",
        "description": "Self-reflection retry loop for repairing invalid plans with configurable retry attempts",
        "completion_date": "2025-07-16",
        "key_achievements": [
            "planning_reflection_module",
            "retry_loop_implementation",
            "environment_configuration",
            "comprehensive_testing",
            "agent_integration",
        ],
        "files_created": [
            "planning/__init__.py",
            "planning/reflection.py",
            "tests/test_plan_reflection.py",
        ],
        "files_modified": [
            "agent/agent.py",
            "config.env.template",
            "tests/README.md",
        ],
        "test_coverage": "16_tests",
        "environment_variable": "IKOMA_MAX_PLAN_RETRIES",
        "retry_config": "default_2_attempts",
        "last_updated": "issue_18_completion",
    }
    existing_entries.append(issue_18_entry)

    # ===== PHASE 2 SUMMARY (ALIGNED WITH TODO.md) =====

    phase_2_summary_entry = {
        "type": "phase_2_completion_summary",
        "phase": "2_active",
        "description": "Enhanced autonomy and internet integration capabilities with comprehensive tooling",
        "completion_date": "2025-07-16",
        "epics_completed": [
            "Epic E-01: Internet Tooling (complete)",
            "Epic E-02: Continuous Mode (complete)",
            "Epic E-03: Short-term Checkpointer (complete)",
            "Epic E-04: Planner Enhancements (complete)",
        ],
        "epics_planned": [
            "Epic E-05: UI/UX (planned)",
            "Epic E-06: Dev & Safety Hardening (planned)",
        ],
        "total_issues_completed": 17,
        "total_issues_planned": 5,
        "completion_rate": "77%",
        "key_achievements": [
            "internet_safety_layer",
            "continuous_operation",
            "enhanced_memory",
            "improved_planning",
            "comprehensive_testing",
        ],
        "architecture_evolution": "plan_execute_reflect_with_internet_tools",
        "quality_targets": {
            "test_coverage": "≥ 50% (currently 99 tests)",
            "performance": "Benchmarks in CI",
            "security": "Rate limiting and domain filtering",
            "reliability": "Structured logging and error handling",
        },
        "last_updated": "phase_2_comprehensive_update",
    }
    existing_entries.append(phase_2_summary_entry)

    # ===== CURRENT STRUCTURE UPDATE =====

    def count_lines_safe(file_path):
        """Safely count lines in a file, handling binary files"""
        try:
            return len(
                file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            )
        except Exception:
            return 0

    # Update current structure entry
    for entry in existing_entries:
        if entry.get("type") == "current_structure":
            entry.update(
                {
                    "total_files": len(list(Path(".").rglob("*"))),
                    "total_lines": sum(
                        count_lines_safe(f)
                        for f in Path(".").rglob("*.py")
                        if f.is_file()
                    ),
                    "python_files": len(list(Path(".").rglob("*.py"))),
                    "markdown_files": len(list(Path(".").rglob("*.md"))),
                    "config_files": len(
                        list(Path(".").rglob("*.{yaml,yml,toml,json,txt}"))
                    ),
                    "data_files": len(list(Path(".").rglob("*.{sqlite3,txt}"))),
                    "system_files": len(list(Path(".").rglob("*.{DS_Store,ini}"))),
                    "directories": len([d for d in Path(".").iterdir() if d.is_dir()]),
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "structure_version": "3.1",
                    "phase": "phase_2_active",
                    "next_phase": "epic_e05_ui_ux",
                    "update_note": "todo_aligned_phase_2_update",
                }
            )
            break

    # ===== WRITE UPDATED STRUCTURE =====

    with open(repo_structure_file, "w") as f:
        for entry in existing_entries:
            f.write(json.dumps(entry) + "\n")

    print(
        f"Updated {repo_structure_file} with comprehensive Phase 2 progress (TODO.md aligned)"
    )
    print(
        f"Added {len([e for e in existing_entries if 'phase_2' in str(e)])} Phase 2 entries"
    )
    print("Epic structure now matches TODO.md organization")


if __name__ == "__main__":
    update_repo_structure()
