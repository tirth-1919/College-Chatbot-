/**
 * Frontend tests for college-admin-service.ts — Institutional Profile & Metadata methods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

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
  clear: () => { Object.keys(mockStorage).forEach(k => delete mockStorage[k]); },
});

import { collegeAdminService } from "./college-admin-service";

function makeFetchResponse(body: unknown, status: number = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: new Headers(),
  } as unknown as Response;
}

describe("collegeAdminService Institutional Profile Operations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("updates institutional profile with partial metadata payload via PATCH", async () => {
    const payload = {
      name: "Ahmedabad Institute of Technology",
      short_name: "AIT",
      established_year: 2004,
      city: "Ahmedabad",
      naac_grade: "A+",
      primary_brand_color: "#10B981",
    };

    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Profile updated successfully",
        data: {
          id: "11111111-1111-1111-1111-111111111111",
          ...payload,
        },
      })
    );

    const res = await collegeAdminService.updateProfile(payload);
    expect(res.success).toBe(true);
    expect(mockFetch).toHaveBeenCalledOnce();
    const [calledUrl, calledInit] = mockFetch.mock.calls[0];
    expect(calledUrl).toContain("/college-admin/profile");
    expect(calledInit.method).toBe("PATCH");
    expect(JSON.parse(calledInit.body)).toMatchObject(payload);
  });

  it("saves and retrieves profile drafts", async () => {
    const draftData = { short_name: "DRAFT-AIT", naac_grade: "A++" };

    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Draft saved",
        data: draftData,
      })
    );

    const saveRes = await collegeAdminService.saveDraft(draftData);
    expect(saveRes.success).toBe(true);

    const [saveUrl, saveInit] = mockFetch.mock.calls[0];
    expect(saveUrl).toContain("/college-admin/profile/draft");
    expect(saveInit.method).toBe("POST");

    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Draft retrieved",
        data: draftData,
      })
    );

    const getRes = await collegeAdminService.getDraft();
    expect(getRes.success).toBe(true);
    expect(getRes.data).toEqual(draftData);
  });

  it("discards saved profile draft via DELETE", async () => {
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Draft discarded",
        data: true,
      })
    );

    const delRes = await collegeAdminService.deleteDraft();
    expect(delRes.success).toBe(true);
    const [delUrl, delInit] = mockFetch.mock.calls[0];
    expect(delUrl).toContain("/college-admin/profile/draft");
    expect(delInit.method).toBe("DELETE");
  });

  it("fetches profile change audit history", async () => {
    const mockHistory = [
      {
        id: "hist-1",
        action_type: "COLLEGE_PROFILE_UPDATED",
        actor_name: "Super Admin",
        payload_diff: { short_name: { old: "AIT", new: "AIT-ENG" } },
        created_at: new Date().toISOString(),
      },
    ];

    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "History retrieved",
        data: mockHistory,
      })
    );

    const res = await collegeAdminService.getProfileHistory(15);
    expect(res.success).toBe(true);
    expect(res.data).toHaveLength(1);
    const [histUrl] = mockFetch.mock.calls[0];
    expect(histUrl).toContain("/college-admin/profile/history?limit=15");
  });

  it("uploads profile asset via multipart/form-data to /profile/upload-image", async () => {
    const pngBytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    const logoFile = new File([pngBytes], "logo.png", { type: "image/png" });

    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Asset uploaded",
        data: {
          asset_url: "/api/v1/colleges/assets/1111/logo_123.png",
          asset_type: "logo",
          file_name: "logo.png",
          file_size_bytes: pngBytes.length,
        },
      })
    );

    const res = await collegeAdminService.uploadProfileAsset(logoFile, "logo");
    expect(res.success).toBe(true);
    expect(res.data?.asset_type).toBe("logo");
    const [uploadUrl, uploadInit] = mockFetch.mock.calls[0];
    expect(uploadUrl).toContain("/college-admin/profile/upload-image");
    expect(uploadInit.method).toBe("POST");
    expect(uploadInit.body).toBeInstanceOf(FormData);
  });
});
