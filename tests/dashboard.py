"""Smart Terminal Dashboard using Rich UI.

Provides:
  - Real-time colored test execution tables.
  - Section 14 HTTP Status Reports.
  - Summary metrics and failed-test callouts.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

STATUS_COLORS = {
    "PASS": "bold green",
    "FAIL": "bold red",
    "WARN": "bold yellow",
    "WARNING": "bold yellow",
    "SKIPPED": "bold cyan",
    "RUNNING": "bold blue",
    "INFO": "dim white",
}

STATUS_ICONS = {
    "PASS": "✓",
    "FAIL": "✗",
    "WARN": "⚠",
    "WARNING": "⚠",
    "SKIPPED": "○",
    "RUNNING": "►",
    "INFO": "ℹ",
}


class TerminalDashboard:
    """Renders smart terminal UI for test automation results."""

    def __init__(self):
        self.console = console

    def print_banner(self, title: str = "CAMPUSAI AUTOMATED TEST SYSTEM"):
        """Displays master testing header banner."""
        banner_text = Text()
        banner_text.append("═══════════════════════════════════════════════════════════════════════════════\n", style="bold cyan")
        banner_text.append(f"   {title}   \n", style="bold white on blue")
        banner_text.append("   FastAPI • Supabase PostgreSQL • Next.js • Playwright • Security & RBAC\n", style="dim white")
        banner_text.append("═══════════════════════════════════════════════════════════════════════════════", style="bold cyan")
        self.console.print(Panel(banner_text, box=box.ROUNDED, border_style="cyan"))

    def render_suite_table(self, suite_name: str, test_items: List[Dict[str, Any]]):
        """Renders results table for an individual test suite."""
        table = Table(
            title=f"[bold cyan]Suite: {suite_name}[/bold cyan] ({len(test_items)} tests)",
            box=box.SIMPLE_HEAVY,
            header_style="bold magenta",
            show_lines=False,
            expand=True,
        )

        table.add_column("Status", width=10, justify="center")
        table.add_column("Test Case", ratio=3)
        table.add_column("Target / Endpoint", ratio=2)
        table.add_column("Duration", width=12, justify="right")
        table.add_column("Details", ratio=3)

        for item in test_items:
            status = item.get("status", "INFO")
            color = STATUS_COLORS.get(status, "white")
            icon = STATUS_ICONS.get(status, "•")
            duration_ms = item.get("duration_ms", 0.0)
            duration_str = f"{duration_ms:.1f}ms" if duration_ms < 1000 else f"{duration_ms/1000:.2f}s"
            test_name = item.get("name") or item.get("test", "Unnamed Test")
            target = item.get("target") or item.get("url", "-")
            detail_msg = item.get("detail") or item.get("message", "")

            status_text = Text(f"{icon} {status}", style=color)
            table.add_row(
                status_text,
                str(test_name),
                str(target),
                duration_str,
                Text(str(detail_msg)[:80], style="dim" if status == "PASS" else "bold red"),
            )

        self.console.print(table)
        self.console.print()

    def render_http_status_report(self, http_results: List[Dict[str, Any]]):
        """Displays Section 14: HTTP Status Report table."""
        table = Table(
            title="[bold yellow]SECTION 14: HTTP STATUS & ROUTE AUDIT REPORT[/bold yellow]",
            box=box.DOUBLE_EDGE,
            header_style="bold white on blue",
            show_lines=False,
            expand=True,
        )

        table.add_column("Method", width=9, justify="center")
        table.add_column("Route URL", ratio=3)
        table.add_column("Expected Status", width=16, justify="center")
        table.add_column("Actual Status", width=16, justify="center")
        table.add_column("Latency", width=12, justify="right")
        table.add_column("Result", width=10, justify="center")

        for r in http_results:
            status = r.get("status", "PASS")
            color = STATUS_COLORS.get(status, "white")
            icon = STATUS_ICONS.get(status, "•")

            expected = str(r.get("expected_code", "-"))
            actual = str(r.get("actual_code", "-"))
            latency_ms = r.get("latency_ms", 0.0)
            latency_str = f"{latency_ms:.1f}ms"

            table.add_row(
                Text(r.get("method", "GET"), style="bold cyan"),
                r.get("url", "/"),
                expected,
                Text(actual, style="green" if status == "PASS" else "red"),
                latency_str,
                Text(f"{icon} {status}", style=color),
            )

        self.console.print(table)
        self.console.print()

    def render_summary_dashboard(self, summary: Dict[str, Any], suite_breakdown: List[Dict[str, Any]]):
        """Displays master summary dashboard with category breakdown."""
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        warned = summary.get("warned", 0)
        duration_s = summary.get("duration_s", 0.0)

        # Overview Table
        table = Table(
            title="[bold green]FULL APPLICATION TEST SUITE BREAKDOWN[/bold green]",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Test Category", ratio=3)
        table.add_column("Passed", width=10, justify="center", style="bold green")
        table.add_column("Failed", width=10, justify="center", style="bold red")
        table.add_column("Skipped", width=10, justify="center", style="cyan")
        table.add_column("Total", width=10, justify="center")
        table.add_column("Pass Rate", width=12, justify="right")

        for b in suite_breakdown:
            s_total = b.get("total", 0)
            s_pass = b.get("passed", 0)
            s_fail = b.get("failed", 0)
            s_skip = b.get("skipped", 0)
            rate = (s_pass / s_total * 100.0) if s_total > 0 else 100.0
            table.add_row(
                b.get("category", "General"),
                str(s_pass),
                str(s_fail),
                str(s_skip),
                str(s_total),
                f"{rate:.1f}%",
            )

        self.console.print(table)

        # Master status panel
        app_status = "ALL TESTS PASSED" if failed == 0 else f"{failed} TESTS FAILED"
        status_color = "bold green" if failed == 0 else "bold red"

        p_text = Text()
        p_text.append(f"\n   APPLICATION STATUS: {app_status}\n\n", style=status_color)
        p_text.append(f"   TOTAL TESTS:     {total}\n", style="bold white")
        p_text.append(f"   PASSED:          {passed}\n", style="bold green")
        p_text.append(f"   FAILED:          {failed}\n", style="bold red" if failed > 0 else "dim white")
        p_text.append(f"   WARNINGS:        {warned}\n", style="bold yellow" if warned > 0 else "dim white")
        p_text.append(f"   SKIPPED:         {skipped}\n", style="cyan")
        p_text.append(f"   TOTAL TIME:      {duration_s:.2f} seconds\n", style="dim white")

        border = "green" if failed == 0 else "red"
        self.console.print(Panel(p_text, title="[bold]Test Execution Summary[/bold]", border_style=border))

    # Aliases for flexible orchestrator consumption
    def render_header(self, title: str = "CAMPUSAI AUTOMATED TEST SYSTEM"):
        self.print_banner(title)

    def render_http_status_table(self, http_records: List[Dict[str, Any]]):
        # Normalize fields if necessary
        normalized = []
        for h in http_records:
            normalized.append({
                "method": h.get("method", "GET"),
                "url": h.get("url", "/"),
                "expected_code": h.get("expected", h.get("expected_code", "-")),
                "actual_code": h.get("actual", h.get("actual_code", "-")),
                "latency_ms": h.get("duration_ms", h.get("latency_ms", 0.0)),
                "status": h.get("status", "PASS")
            })
        self.render_http_status_report(normalized)

    def render_master_summary(self, summary: Dict[str, Any], breakdown: Optional[List[Dict[str, Any]]] = None):
        if breakdown is None:
            breakdown = [{
                "category": summary.get("command", "All Suites").upper(),
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0)
            }]
        # Map duration_s from duration_ms if duration_s not set
        if "duration_s" not in summary and "duration_ms" in summary:
            summary["duration_s"] = summary["duration_ms"] / 1000.0
        self.render_summary_dashboard(summary, breakdown)


TestDashboard = TerminalDashboard
dashboard = TerminalDashboard()
