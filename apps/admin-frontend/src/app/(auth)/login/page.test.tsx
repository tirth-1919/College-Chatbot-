import React from "react";
import { act } from "react-dom/test-utils";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockRouter } = vi.hoisted(() => ({
  mockRouter: { replace: vi.fn() },
}));
const mockFetch = vi.fn();
const storage = new Map<string, string>();
const mockStorage = {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => storage.set(key, value),
  removeItem: (key: string) => storage.delete(key),
  clear: () => storage.clear(),
};
vi.stubGlobal("localStorage", mockStorage);
vi.stubGlobal("fetch", mockFetch);

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

vi.mock("next/link", async () => {
  const { createElement } = await import("react");
  return {
    default: ({ children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) =>
      createElement("a", props, children),
  };
});

import AdminLoginPage from "./page";

describe("AdminLoginPage", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStorage.clear();
    window.history.replaceState({}, "", "/login");
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    if (root) act(() => root.unmount());
    container.remove();
  });

  it("shows college admin auto-login details for the query parameter", async () => {
    window.history.replaceState({}, "", "/login?autologin=collegeadmin");
    await act(async () => {
      root.render(<AdminLoginPage />);
    });

    expect(container.textContent).toContain("Automatic College Admin Login");
    expect(container.textContent).toContain("Automatic Super Admin Login");
    expect(container.textContent).toContain("Automatic ID Login Triggered");
    expect(container.textContent).toContain("admin@aitindia.in");
  });

  it("redirects a backend-verified super admin session", async () => {
    localStorage.setItem("admin_auth_token", "valid-access-token");
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        data: {
          id: "super-admin-id",
          email: "admin@example.edu",
          full_name: "Super Admin",
          role: "SUPER_ADMIN",
          is_verified: true,
          is_active: true,
        },
      }),
    });

    await act(async () => {
      root.render(<AdminLoginPage />);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch.mock.calls[0][0]).toContain("/auth/me");
    expect(mockRouter.replace).toHaveBeenCalledWith("/super-admin/dashboard");
  });

  it("redirects a verified college admin only with matching cached college context", async () => {
    localStorage.setItem("admin_auth_token", "valid-access-token");
    localStorage.setItem(
      "admin_user",
      JSON.stringify({
        id: "college-admin-id",
        role: "COLLEGE_ADMIN",
        college_id: "ait-college-id",
      })
    );
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        data: {
          id: "college-admin-id",
          email: "admin@ait.example.edu",
          full_name: "AIT Admin",
          role: "COLLEGE_ADMIN",
          is_verified: true,
          is_active: true,
        },
      }),
    });

    await act(async () => {
      root.render(<AdminLoginPage />);
    });

    expect(mockRouter.replace).toHaveBeenCalledWith("/college-admin/dashboard");
    expect(localStorage.getItem("admin_college_id")).toBe("ait-college-id");
  });
});
