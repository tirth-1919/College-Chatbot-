/**
 * Frontend tests for the Super Admin analytics page.
 *
 * Regression guard for the runtime crash:
 *   TypeError: Cannot read properties of undefined (reading 'toLocaleString')
 *   at src/app/super-admin/analytics/page.tsx — data.total_tokens.toLocaleString()
 *
 * The page must render without throwing when the analytics API returns:
 *   - a full platform response (token metrics nested under ai_metrics)
 *   - a partial platform response (some fields missing)
 *   - an empty data object
 *   - an outright API failure (network error)
 *
 * These states previously crashed because the service fed the page a
 * PlatformAnalyticsResponse (nested shape) while the page read a flat
 * UsageAnalytics shape. getUsageAnalytics now normalizes to the flat shape.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ---------------------------------------------------------------------------
// Mock the fetch global + localStorage BEFORE importing anything that
// depends on them (mirrors the existing college-admin-service.test.ts setup).
// ---------------------------------------------------------------------------
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

const mockStorage: Record<string, string> = {
  admin_auth_token: "test-bearer-token-abc123",
  admin_college_id: "11111111-1111-1111-1111-111111111111",
};
vi.stubGlobal("localStorage", {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value; },
  removeItem: (key: string) => { delete mockStorage[key]; },
  clear: () => { Object.keys(mockStorage).forEach((k) => delete mockStorage[k]); },
});

// next/link is a Next.js router component; stub it so the page module can be
// imported and rendered under vitest without a Next router context. The
// analytics page never passes `href` to DashboardCard, so this stub is never
// actually rendered — it only needs to resolve as a module.
vi.mock("next/link", async () => {
  const { createElement } = await import("react");
  return {
    default: ({ children, ...rest }: any) => createElement("a", rest, children),
  };
});

// ---------------------------------------------------------------------------
// Imports (after stubs are in place).
// ---------------------------------------------------------------------------
import React from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react-dom/test-utils";
import AnalyticsPage from "@/app/super-admin/analytics/page";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal Response-like object that fetch would return. */
function makeFetchResponse(body: unknown, status: number = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: new Headers(),
  } as unknown as Response;
}

/** Drain the microtask queue so the fetch -> service -> setState chain settles. */
async function flushMicrotasks(ticks = 30): Promise<void> {
  for (let i = 0; i < ticks; i++) {
    await Promise.resolve();
  }
}

/** Route fetch responses by endpoint path substring. */
function routeResponses(platformBody: unknown, fallbackBody: unknown): void {
  mockFetch.mockImplementation(async (url: string) => {
    if (typeof url === "string" && url.includes("/analytics/platform")) {
      return makeFetchResponse(platformBody);
    }
    if (typeof url === "string" && url.includes("/super-admin/analytics")) {
      return makeFetchResponse(fallbackBody, 404);
    }
    return makeFetchResponse({ success: false, error: "unexpected endpoint" }, 404);
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Super Admin AnalyticsPage — crash-safe rendering", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.clearAllMocks();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("renders without throwing when the API returns a full platform response", async () => {
    routeResponses(
      {
        success: true,
        message: "Platform analytics retrieved",
        data: {
          time_range: "30D",
          total_questions_asked: 200,
          ai_metrics: {
            total_requests: 200,
            total_tokens: 64900,
            prompt_tokens: 48500,
            completion_tokens: 16400,
            average_latency_ms: 174.5,
            fallback_rate_percent: 1.2,
            estimated_cost_usd: 0.0171,
          },
          top_active_colleges: [
            { name: "Ahmedabad Institute of Technology", queries: 84, percent: 65.6 },
          ],
        },
      },
      { success: false, error: "fallback should not be reached" }
    );

    await act(async () => {
      root.render(React.createElement(AnalyticsPage));
    });
    await act(async () => {
      await flushMicrotasks();
    });

    expect(container.textContent).toContain("AI Telemetry & Token Analytics");
    // Nested ai_metrics.total_tokens normalized to the top level and formatted.
    expect(container.textContent).toContain("64,900");
  });

  it("renders without throwing when the API returns a PARTIAL platform response", async () => {
    routeResponses(
      {
        success: true,
        data: {
          total_questions_asked: 5,
          ai_metrics: { total_tokens: 100 }, // most metrics absent
          // top_active_colleges missing entirely
        },
      },
      { success: false, error: "fallback should not be reached" }
    );

    await act(async () => {
      root.render(React.createElement(AnalyticsPage));
    });
    await act(async () => {
      await flushMicrotasks();
    });

    expect(container.textContent).toContain("AI Telemetry & Token Analytics");
    // The one present token value renders safely; missing values fall back to 0.
    expect(container.textContent).toContain("100");
    // Reaching these assertions proves the page did not throw on partial data.
  });

  it("renders without throwing when the API returns an EMPTY data object", async () => {
    routeResponses({ success: true, data: {} }, { success: false, error: "ignored" });

    await act(async () => {
      root.render(React.createElement(AnalyticsPage));
    });
    await act(async () => {
      await flushMicrotasks();
    });

    expect(container.textContent).toContain("AI Telemetry & Token Analytics");
    // Missing numeric fields render a safe "0" instead of crashing.
    expect(container.textContent).toContain("0");
  });

  it("renders without throwing when the API call fails (network error)", async () => {
    // Every fetch rejects — neither the platform nor the fallback endpoint is
    // reachable, so the service returns a non-success result.
    mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));

    await act(async () => {
      root.render(React.createElement(AnalyticsPage));
    });
    await act(async () => {
      await flushMicrotasks();
    });

    // Falls back to the in-page default analytics object and does not crash.
    expect(container.textContent).toContain("AI Telemetry & Token Analytics");
    // Default fallback total_tokens is 64900 -> "64,900".
    expect(container.textContent).toContain("64,900");
  });
});
