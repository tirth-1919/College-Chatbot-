/**
 * Frontend tests for college-admin-service.ts — document upload methods.
 *
 * Tests verify:
 *  1. uploadDocumentBinary sends multipart/form-data to /upload-file, response contains document_id.
 *  2. uploadDocumentBinary surfaces error state on network error or non-200 response.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ---------------------------------------------------------------------------
// Mock the fetch global before any module is imported that depends on it.
// ---------------------------------------------------------------------------
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Stub localStorage so adminApiRequest can read the auth token.
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

// ---------------------------------------------------------------------------
// Import the service AFTER stubs are in place.
// ---------------------------------------------------------------------------
import { collegeAdminService } from "./college-admin-service";

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

/** Create a minimal PDF File object (magic bytes "%PDF-" at start). */
function makePdfFile(name: string = "test.pdf"): File {
  const pdfBytes = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]); // %PDF-
  return new File([pdfBytes], name, { type: "application/pdf" });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("collegeAdminService.uploadDocumentBinary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("sends a multipart/form-data POST to /upload-file and returns document_id on success", async () => {
    // Arrange
    const fakeDocumentId = "doc-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx";
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse({
        success: true,
        message: "Document uploaded successfully.",
        data: {
          id: fakeDocumentId,
          original_filename: "test.pdf",
          processing_status: "QUEUED",
          storage_path: "11111111-1111-1111-1111-111111111111/abc.pdf",
          file_size_bytes: 5,
          checksum_sha256: "a".repeat(64),
          category: "GENERAL",
          created_at: new Date().toISOString(),
          download_url: null,
          total_pages: 0,
          ocr_applied: false,
          extraction_method: null,
          failure_reason: null,
        },
      })
    );

    const pdfFile = makePdfFile("annual-report.pdf");

    // Act
    const result = await collegeAdminService.uploadDocumentBinary(pdfFile, "PROSPECTUS", "Annual report 2026");

    // Assert — the call was made
    expect(mockFetch).toHaveBeenCalledOnce();
    const [calledUrl, calledInit] = mockFetch.mock.calls[0];

    // Must target the binary upload endpoint (full URL contains /upload-file)
    expect(calledUrl).toContain("/college-admin/documents/upload-file");

    // Body must be FormData — not a JSON string
    expect(calledInit.body).toBeInstanceOf(FormData);
    const form = calledInit.body as FormData;
    expect(form.get("file")).toBeInstanceOf(File);
    expect((form.get("file") as File).name).toBe("annual-report.pdf");
    expect(form.get("category")).toBe("PROSPECTUS");
    expect(form.get("description")).toBe("Annual report 2026");

    // Must carry the Authorization header with the Bearer token
    const headers = calledInit.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-bearer-token-abc123");

    // Must carry the X-College-ID header
    expect(headers.get("X-College-ID")).toBe("11111111-1111-1111-1111-111111111111");

    // Content-Type must NOT be manually set (browser sets multipart boundary automatically)
    expect(headers.get("Content-Type")).toBeNull();

    // Response must report success and expose document_id
    expect(result.success).toBe(true);
    expect(result.data?.id).toBe(fakeDocumentId);
  });

  it("surfaces error state when the server returns a non-200 response — no silent failure", async () => {
    // Arrange: backend returns 422 (e.g. magic-byte validation failure)
    mockFetch.mockResolvedValueOnce(
      makeFetchResponse(
        { detail: "PDF validation failed: magic bytes not found." },
        422
      )
    );

    const pdfFile = makePdfFile("bad-file.pdf");

    // Act
    const result = await collegeAdminService.uploadDocumentBinary(pdfFile);

    // Assert — error must be exposed, success must be false
    expect(result.success).toBe(false);
    expect(result.error).toBeTruthy();
    expect(result.error).toContain("PDF validation failed");
    expect(result.data).toBeUndefined();
  });

  it("surfaces error state on network failure — no silent failure", async () => {
    // Arrange: fetch throws a network error (no connectivity)
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const pdfFile = makePdfFile("network-fail.pdf");

    // Act
    const result = await collegeAdminService.uploadDocumentBinary(pdfFile);

    // Assert — error must be surfaced
    expect(result.success).toBe(false);
    expect(result.error).toBeTruthy();
    expect(result.data).toBeUndefined();
  });
});
