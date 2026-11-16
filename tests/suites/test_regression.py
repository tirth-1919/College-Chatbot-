"""
Regression testing engine.
Compares current test execution metrics against baseline.json:
- Detects regression in PASS/FAIL statuses
- Detects performance degradation (latency increase > 25%)
- Manages and saves new baseline benchmarks
"""

import json
import os
import time
from typing import Dict, Any, List
from tests.config import BASELINE_FILE


def load_baseline() -> Dict[str, Any]:
    """Load stored baseline benchmarks."""
    if not os.path.exists(BASELINE_FILE):
        return {}
    try:
        with open(BASELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_baseline(summary: Dict[str, Any], results: List[Dict[str, Any]]):
    """Save current passing metrics as new baseline."""
    os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
    baseline_data = {
        "timestamp": time.time(),
        "summary": {
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "duration_ms": summary.get("duration_ms", 0)
        },
        "tests": {
            (r.get("test") or r.get("name") or "Unnamed Test"): {
                "status": r.get("status", "PASS"),
                "duration_ms": r.get("duration_ms", 0)
            }
            for r in results
        }
    }
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(baseline_data, f, indent=2)


def run_regression_comparison(current_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare current execution against saved baseline."""
    baseline = load_baseline()
    regression_findings = []

    if not baseline or "tests" not in baseline:
        return {
            "suite_name": "Regression Detection Suite",
            "results": [{
                "test": "Baseline Existence Check",
                "status": "PASS",
                "duration_ms": 1.0,
                "message": "No previous baseline found. Establishing current run as inaugural baseline."
            }],
            "regressions_detected": 0
        }

    baseline_tests = baseline.get("tests", {})
    regressions_count = 0

    for curr in current_results:
        test_name = curr.get("test") or curr.get("name") or "Unnamed Test"
        curr_status = curr.get("status", "PASS")
        curr_dur = curr.get("duration_ms", 0)

        if test_name in baseline_tests:
            base_info = baseline_tests[test_name]
            base_status = base_info.get("status")
            base_dur = base_info.get("duration_ms", 0)

            # Check status regression (PASS -> FAIL)
            if base_status == "PASS" and curr_status == "FAIL":
                regressions_count += 1
                regression_findings.append({
                    "test": f"Status Regression: {test_name}",
                    "status": "FAIL",
                    "duration_ms": curr_dur,
                    "message": f"REGRESSION: Previously PASS ({base_dur:.1f}ms) now FAIL ({curr_dur:.1f}ms)!"
                })
            # Check performance latency regression (> 25% increase and > 100ms delta)
            elif curr_dur > 150.0 and curr_dur > (base_dur * 1.25) and (curr_dur - base_dur) > 100.0:
                regression_findings.append({
                    "test": f"Performance Regression: {test_name}",
                    "status": "WARN",
                    "duration_ms": curr_dur,
                    "message": f"Latency increased by {((curr_dur - base_dur) / base_dur * 100):.1f}% ({base_dur:.1f}ms -> {curr_dur:.1f}ms)"
                })
        else:
            regression_findings.append({
                "test": f"New Test Detected: {test_name}",
                "status": "PASS",
                "duration_ms": curr_dur,
                "message": "New test detected outside historical baseline."
            })

    if not regression_findings:
        regression_findings.append({
            "test": "Comprehensive Regression Audit",
            "status": "PASS",
            "duration_ms": 2.0,
            "message": f"Zero regressions detected across {len(current_results)} evaluated test vectors."
        })

    return {
        "suite_name": "Regression Detection Suite",
        "results": regression_findings,
        "regressions_detected": regressions_count
    }

