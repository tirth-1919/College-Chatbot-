"""Multi-Format Test Report Generator.

Exports:
  - Interactive HTML report (`reports/test_report.html`)
  - Machine-readable JSON report (`reports/test_report.json`)
  - Failed-tests report (`reports/failed_tests.json`)
  - Regression comparison baseline (`reports/baseline.json`)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from tests.config import (
    HTML_REPORT_FILE,
    JSON_REPORT_FILE,
    FAILED_REPORT_FILE,
    BASELINE_FILE,
)


class TestReporter:
    """Generates structured HTML and JSON reports."""

    def __init__(self, summary: Dict[str, Any], results: List[Dict[str, Any]], http_results: List[Dict[str, Any]]):
        self.summary = summary
        self.results = results
        self.http_results = http_results

    def generate_all(self):
        """Builds and writes all report formats to disk."""
        self.write_json_report()
        self.write_failed_report()
        self.write_html_report()
        self.update_baseline()

    def write_json_report(self):
        """Writes complete results to JSON."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": self.summary,
            "results": self.results,
            "http_status_report": self.http_results,
        }
        JSON_REPORT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def write_failed_report(self):
        """Extracts only failed tests into a dedicated JSON file for quick re-run."""
        failed = [r for r in self.results if r.get("status") == "FAIL"]
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failed_count": len(failed),
            "failed_tests": failed,
        }
        FAILED_REPORT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update_baseline(self):
        """Updates baseline record for regression comparisons."""
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": self.summary.get("total", 0),
            "passed": self.summary.get("passed", 0),
            "failed": self.summary.get("failed", 0),
            "test_names_passed": [r.get("name") for r in self.results if r.get("status") == "PASS"],
            "test_names_failed": [r.get("name") for r in self.results if r.get("status") == "FAIL"],
        }
        BASELINE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def write_html_report(self):
        """Generates self-contained, responsive HTML report."""
        total = self.summary.get("total", 0)
        passed = self.summary.get("passed", 0)
        failed = self.summary.get("failed", 0)
        skipped = self.summary.get("skipped", 0)
        duration_s = self.summary.get("duration_s", 0.0)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        pass_rate = (passed / total * 100.0) if total > 0 else 100.0
        status_badge_color = "#10B981" if failed == 0 else "#EF4444"
        status_text = "ALL TESTS PASSED" if failed == 0 else f"{failed} FAILED"

        # Build table rows
        rows_html = []
        for r in self.results:
            st = r.get("status", "PASS")
            color = "#10B981" if st == "PASS" else ("#EF4444" if st == "FAIL" else "#F59E0B")
            dur = f"{r.get('duration_ms', 0):.1f}ms"
            detail = str(r.get("detail", ""))
            rows_html.append(f"""
            <tr class="test-row status-{st.lower()}">
              <td><span class="badge" style="background-color: {color}22; color: {color}; border: 1px solid {color}44;">{st}</span></td>
              <td><strong>{r.get('category', 'General')}</strong></td>
              <td>{r.get('name', 'Test')}</td>
              <td><code>{r.get('target', '-')}</code></td>
              <td>{dur}</td>
              <td class="detail-cell">{detail}</td>
            </tr>
            """)

        # Build HTTP report rows
        http_rows_html = []
        for h in self.http_results:
            st = h.get("status", "PASS")
            color = "#10B981" if st == "PASS" else "#EF4444"
            lat = f"{h.get('latency_ms', 0):.1f}ms"
            http_rows_html.append(f"""
            <tr>
              <td><span class="method-badge">{h.get('method', 'GET')}</span></td>
              <td><code>{h.get('url', '/')}</code></td>
              <td>{h.get('expected_code', '-')}</td>
              <td style="color: {color}; font-weight: bold;">{h.get('actual_code', '-')}</td>
              <td>{lat}</td>
              <td><span class="badge" style="background-color: {color}22; color: {color};">{st}</span></td>
            </tr>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CampusAI — Full Application Automated Test Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0B0B0D; color: #F5F5F5; padding: 32px; }}
    .container {{ max-width: 1400px; margin: 0 auto; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 24px; border-bottom: 1px solid #2A2A30; margin-bottom: 32px; }}
    .title h1 {{ font-size: 26px; font-weight: 700; color: #FFFFFF; margin-bottom: 6px; }}
    .title p {{ font-size: 13px; color: #A1A1AA; }}
    .status-pill {{ padding: 8px 18px; border-radius: 9999px; font-weight: 700; font-size: 14px; background: {status_badge_color}22; color: {status_badge_color}; border: 1px solid {status_badge_color}55; }}
    
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
    .card {{ background: #111114; border: 1px solid #2A2A30; border-radius: 12px; padding: 20px; text-align: center; }}
    .card .num {{ font-size: 32px; font-weight: 800; margin-bottom: 4px; }}
    .card .label {{ font-size: 12px; color: #A1A1AA; text-transform: uppercase; letter-spacing: 0.5px; }}

    .section-title {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; margin-top: 32px; color: #FFFFFF; display: flex; justify-content: space-between; align-items: center; }}
    table {{ width: 100%; border-collapse: collapse; background: #111114; border: 1px solid #2A2A30; border-radius: 12px; overflow: hidden; margin-bottom: 32px; }}
    th {{ background: #18181B; padding: 12px 16px; text-align: left; font-size: 12px; font-weight: 600; color: #A1A1AA; text-transform: uppercase; border-bottom: 1px solid #2A2A30; }}
    td {{ padding: 12px 16px; font-size: 13px; border-bottom: 1px solid #1F1F23; color: #E4E4E7; }}
    tr:hover {{ background: #18181D; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }}
    .method-badge {{ background: #27272A; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 700; color: #60A5FA; }}
    code {{ background: #18181B; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #A78BFA; }}
    .detail-cell {{ max-width: 400px; word-break: break-word; color: #A1A1AA; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">
        <h1>CampusAI Full Application Automated Test Report</h1>
        <p>Executed on: {timestamp} • Elapsed Time: {duration_s:.2f}s</p>
      </div>
      <div class="status-pill">{status_text} ({pass_rate:.1f}%)</div>
    </div>

    <div class="grid">
      <div class="card"><div class="num" style="color: #6366F1;">{total}</div><div class="label">Total Tests</div></div>
      <div class="card"><div class="num" style="color: #10B981;">{passed}</div><div class="label">Passed</div></div>
      <div class="card"><div class="num" style="color: #EF4444;">{failed}</div><div class="label">Failed</div></div>
      <div class="card"><div class="num" style="color: #38BDF8;">{skipped}</div><div class="label">Skipped</div></div>
      <div class="card"><div class="num" style="color: #F59E0B;">{duration_s:.2f}s</div><div class="label">Execution Time</div></div>
    </div>

    <div class="section-title">
      <span>Section 14: HTTP Route & Status Code Audit Report</span>
      <span style="font-size: 12px; color: #A1A1AA;">{len(self.http_results)} endpoints tested</span>
    </div>
    <table>
      <thead>
        <tr><th>Method</th><th>Route URL</th><th>Expected Status</th><th>Actual Status</th><th>Latency</th><th>Result</th></tr>
      </thead>
      <tbody>
        {"".join(http_rows_html)}
      </tbody>
    </table>

    <div class="section-title">
      <span>Full Application Test Execution Details</span>
      <span style="font-size: 12px; color: #A1A1AA;">{len(self.results)} total assertions</span>
    </div>
    <table>
      <thead>
        <tr><th>Status</th><th>Category</th><th>Test Name</th><th>Target</th><th>Latency</th><th>Details</th></tr>
      </thead>
      <tbody>
        {"".join(rows_html)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""
        HTML_REPORT_FILE.write_text(html_content, encoding="utf-8")
        return str(HTML_REPORT_FILE)


def generate_html_report(summary: Dict[str, Any], results: List[Dict[str, Any]], http_results: List[Dict[str, Any]]) -> str:
    # Normalize result items
    normalized_results = []
    for r in results:
        normalized_results.append({
            "status": r.get("status", "PASS"),
            "category": r.get("category", r.get("suite", "Suite")),
            "name": r.get("name", r.get("test", "Test")),
            "target": r.get("target", "-"),
            "duration_ms": r.get("duration_ms", 0.0),
            "detail": r.get("detail", r.get("message", ""))
        })

    normalized_http = []
    for h in http_results:
        normalized_http.append({
            "method": h.get("method", "GET"),
            "url": h.get("url", "/"),
            "expected_code": h.get("expected_code", h.get("expected", "-")),
            "actual_code": h.get("actual_code", h.get("actual", "-")),
            "latency_ms": h.get("latency_ms", h.get("duration_ms", 0.0)),
            "status": h.get("status", "PASS")
        })

    reporter = TestReporter(summary, normalized_results, normalized_http)
    reporter.write_html_report()
    return str(HTML_REPORT_FILE)


def save_json_report(summary: Dict[str, Any], results: List[Dict[str, Any]], http_results: List[Dict[str, Any]]) -> str:
    reporter = TestReporter(summary, results, http_results)
    reporter.write_json_report()
    return str(JSON_REPORT_FILE)


def save_failed_report(summary: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    reporter = TestReporter(summary, results, [])
    reporter.write_failed_report()
    return str(FAILED_REPORT_FILE)

