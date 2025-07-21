"""Performance benchmark runner for Ikoma agent."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from agent.agent import AgentState, create_agent
from benchmarks.metrics import BenchmarkMetrics, PerformanceResult
from benchmarks.scenarios import BENCHMARK_SCENARIOS


class IkomaBenchmark:
    """Performance benchmark runner with regression detection."""

    def __init__(self, baseline_path: Path = Path("benchmarks/baselines.json")):
        self.baseline_path = baseline_path
        self.metrics = BenchmarkMetrics()

    def measure_startup(self, iterations: int = 5, ci_mode: bool = False) -> float:
        """Measure agent initialization time."""
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            if ci_mode:
                # Use mocked agent for CI
                agent = self._create_mocked_agent()
            else:
                agent = create_agent(disable_checkpoint=True)
            end = time.perf_counter()
            times.append(end - start)
            del agent  # Clean up
            print(f"  Startup iteration {i + 1}/{iterations}: {times[-1]:.3f}s")
        return sum(times) / len(times)

    def _create_mocked_agent(self) -> Any:
        """Create a mocked agent for CI testing."""
        # Import here to avoid circular imports
        from langchain_core.messages import AIMessage
        from langgraph.graph import StateGraph, END
        from typing import TypedDict
        
        # Define a simple state type for the mocked agent
        class MockState(TypedDict):
            messages: list
            current_plan: list
            execution_results: list
            reflection: str
            continue_planning: bool
        
        # Create a simple mocked agent that just returns a response
        def mock_plan_node(state: MockState) -> MockState:
            return {
                **state,
                "current_plan": [{"step": 1, "tool_name": "create_text_file", "args": {"filename_and_content": "test.txt|||test"}, "description": "Create test file"}],
                "reflection": "Plan created successfully"
            }
        
        def mock_execute_node(state: MockState) -> MockState:
            return {
                **state,
                "execution_results": [{"step": 1, "result": "File created successfully"}],
                "reflection": "Task completed"
            }
        
        def mock_reflect_node(state: MockState) -> MockState:
            return {
                **state,
                "continue_planning": False,
                "reflection": "Task completed successfully"
            }
        
        # Create simple workflow
        workflow = StateGraph(MockState)
        workflow.add_node("plan", mock_plan_node)
        workflow.add_node("execute", mock_execute_node)
        workflow.add_node("reflect", mock_reflect_node)
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "reflect")
        workflow.add_edge("reflect", END)
        workflow.set_entry_point("plan")
        
        return workflow.compile()

    def measure_turn_latency(
        self, scenario: dict[str, Any], iterations: int = 3, ci_mode: bool = False
    ) -> float:
        """Measure single plan-execute-reflect cycle time."""
        if ci_mode:
            agent = self._create_mocked_agent()
        else:
            agent = create_agent(disable_checkpoint=True)
        times = []

        for i in range(iterations):
            if ci_mode:
                # Use simplified state for mocked agent
                initial_state: dict[str, Any] = {
                    "messages": [HumanMessage(content=scenario["goal"])],
                    "current_plan": None,
                    "execution_results": None,
                    "reflection": None,
                    "continue_planning": False,
                }
            else:
                initial_state: AgentState = {
                    "messages": [HumanMessage(content=scenario["goal"])],
                    "memory_context": None,
                    "user_profile": None,
                    "session_summary": None,
                    "current_plan": None,
                    "execution_results": None,
                    "reflection": None,
                    "continue_planning": False,
                    "max_iterations": 1,  # Single turn only
                    "current_iteration": 0,
                    "start_time": None,
                    "time_limit_secs": None,
                    "citations": None,
                    "citation_counter": None,
                    "reflection_json": None,
                    "reflection_failures": None,
                    "checkpoint_every": None,
                    "last_checkpoint_iter": None,
                    "stats": None,
                }

            start = time.perf_counter()
            try:
                agent.invoke(initial_state, scenario.get("config", {}))
                end = time.perf_counter()
                times.append(end - start)
                print(
                    f"  {scenario['name']} iteration {i + 1}/{iterations}: {times[-1]:.3f}s"
                )
            except Exception as e:
                print(f"  Error in {scenario['name']} iteration {i + 1}: {e}")
                # Use a high value for failed iterations to indicate problems
                times.append(10.0)

        return sum(times) / len(times)

    def run_benchmarks(self, ci_mode: bool = False) -> list[PerformanceResult]:
        """Run all benchmark scenarios."""
        results = []

        print("🚀 Running startup benchmark...")
        startup_time = self.measure_startup(ci_mode=ci_mode)
        results.append(
            PerformanceResult(name="agent_startup", value=startup_time, unit="seconds")
        )
        print(f"✅ Average startup time: {startup_time:.3f}s")

        print("\n⏱️ Running turn latency benchmarks...")
        for scenario in BENCHMARK_SCENARIOS:
            print(f"\n📋 Testing scenario: {scenario['name']}")
            latency = self.measure_turn_latency(scenario, ci_mode=ci_mode)
            results.append(
                PerformanceResult(
                    name=f"turn_latency_{scenario['name']}",
                    value=latency,
                    unit="seconds",
                )
            )
            print(f"✅ Average latency: {latency:.3f}s")

        return results

    def check_regression(self, results: list[PerformanceResult]) -> bool:
        """Check if any metric regressed >20% from baseline."""
        if not self.baseline_path.exists():
            print("📊 No baseline found - establishing new baseline")
            self.save_baseline(results)
            return False

        with open(self.baseline_path) as f:
            baseline_data = json.load(f)

        baselines = baseline_data.get("baselines", {})
        has_regression = False
        print("\n📊 Checking for performance regressions...")

        for result in results:
            if result.name in baselines:
                baseline = baselines[result.name]["value"]
                regression = (result.value - baseline) / baseline

                if regression > 0.20:  # >20% slower
                    print(f"❌ REGRESSION: {result.name} is {regression:.1%} slower")
                    print(f"   Baseline: {baseline:.3f}s, Current: {result.value:.3f}s")
                    has_regression = True
                elif regression < -0.10:  # >10% faster (notable improvement)
                    print(f"✅ IMPROVEMENT: {result.name} is {-regression:.1%} faster")
                    print(f"   Baseline: {baseline:.3f}s, Current: {result.value:.3f}s")
                else:
                    print(
                        f"✅ {result.name}: {regression:+.1%} change (within acceptable range)"
                    )
            else:
                print(f"📝 New metric: {result.name} = {result.value:.3f}s")

        return has_regression

    def save_baseline(self, results: list[PerformanceResult]) -> None:
        """Save current results as new baseline."""
        baseline_data = {
            "timestamp": time.time(),
            "baselines": {r.name: r.to_dict() for r in results},
        }

        self.baseline_path.parent.mkdir(exist_ok=True)
        with open(self.baseline_path, "w") as f:
            json.dump(baseline_data, f, indent=2)
        print(f"💾 Saved new baseline to {self.baseline_path}")


def main() -> None:
    """Main benchmark runner."""
    parser = argparse.ArgumentParser(description="Run Ikoma performance benchmarks")
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current results as new baseline",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for regressions, don't run benchmarks",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results.json"),
        help="Output file for results",
    )
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Run in CI mode with mocked components (no external dependencies)",
    )

    args = parser.parse_args()

    benchmark = IkomaBenchmark()

    if args.check_only:
        # Load existing results and check against baseline
        if not args.output.exists():
            print("❌ No results file found for check-only mode")
            sys.exit(1)

        with open(args.output) as f:
            data = json.load(f)
            results = [PerformanceResult(**r) for r in data["results"]]

        has_regression = benchmark.check_regression(results)
        sys.exit(1 if has_regression else 0)

    # Run benchmarks
    print("🎯 Starting Ikoma Performance Benchmarks")
    if args.ci_mode:
        print("🔧 Running in CI mode with mocked components")
    print("=" * 50)

    results = benchmark.run_benchmarks(ci_mode=args.ci_mode)

    # Save results
    benchmark.metrics.save_artifacts(results, args.output)
    print(f"\n💾 Results saved to {args.output}")

    # Check for regressions
    has_regression = benchmark.check_regression(results)

    # Output GitHub-friendly format
    print("\n" + benchmark.metrics.format_github_output(results))

    if args.save_baseline:
        benchmark.save_baseline(results)

    # Exit with error code if regression detected
    if has_regression:
        print("\n❌ Performance regression detected!")
        sys.exit(1)
    else:
        print("\n✅ All performance checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
