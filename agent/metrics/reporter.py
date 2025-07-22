"""Metrics reporter for CI integration and reporting."""

import argparse
import sys
from pathlib import Path

from .analyzer import MetricsAnalyzer


def main() -> None:
    """Main entry point for metrics reporter."""
    parser = argparse.ArgumentParser(description="Analyze and report metrics")
    parser.add_argument(
        "--analyze", action="store_true", help="Analyze metrics and generate report"
    )
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=Path("agent/logs/metrics.jsonl"),
        help="Path to metrics JSONL file",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with error code if performance regression detected",
    )
    parser.add_argument(
        "--fail-on-incidents",
        action="store_true",
        help="Exit with error code if safety incidents detected",
    )

    args = parser.parse_args()

    if not args.metrics_file.exists():
        print(
            "⚠️ No metrics file found. Run tests with IKOMA_METRICS_ENABLED=true to generate metrics."
        )
        sys.exit(0)

    analyzer = MetricsAnalyzer(args.metrics_file)

    if args.analyze:
        # Generate and print report
        report = analyzer.generate_ci_report()
        print(report)

        # Check for failures
        summary = analyzer.analyze_recent_performance()
        incidents = analyzer.check_safety_incidents()

        exit_code = 0

        if args.fail_on_regression and summary.performance_regression:
            print(
                f"❌ Performance regression detected: {summary.performance_regression:.1f}% slower"
            )
            exit_code = 1

        if args.fail_on_incidents and incidents:
            print(f"❌ Safety incidents detected: {len(incidents)} incidents")
            exit_code = 1

        sys.exit(exit_code)
    else:
        # Default behavior: just analyze and report
        summary = analyzer.analyze_recent_performance()
        print("📊 Metrics Summary:")
        print(f"  Sessions: {summary.total_sessions}")
        print(f"  Iterations: {summary.total_iterations}")
        print(f"  Success Rate: {summary.overall_success_rate:.1%}")
        print(f"  Safety Incidents: {summary.safety_incidents}")

        if summary.performance_regression:
            print(
                f"  ⚠️ Performance Regression: {summary.performance_regression:.1f}% slower"
            )


if __name__ == "__main__":
    main()
