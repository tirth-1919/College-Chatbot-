/**
 * Centralized College Administrator API Service.
 * Scoped strictly to the authenticated administrator's assigned college.
 */

import { adminApiRequest } from "@/lib/api-client";
import {
  CollegeProfile,
  ProfileHistoryItem,
  ProfileAssetUploadResult,
  CollegeAdminDashboard,
  WebsiteSource,
  CrawlJob,
  CrawlEvent,
  WebsitePage,
  DocumentDetail,
  DocumentPage,
  DocumentStatus,
  KnowledgeChunk,
  ExtractedFact,
  CollegeAnalytics,
  CollegeSupportTicket,
  CollegeFeedback,
  CollegeNotification,
} from "@/types/college-admin";

export const collegeAdminService = {
  // 1. Dashboard Overview
  async getDashboard() {
    return adminApiRequest<CollegeAdminDashboard>("/college-admin/dashboard");
  },

  // 2. Institutional Profile
  async getProfile() {
    return adminApiRequest<CollegeProfile>("/college-admin/profile");
  },

  async updateProfile(data: Partial<CollegeProfile>) {
    return adminApiRequest<CollegeProfile>("/college-admin/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async saveDraft(draftData: Record<string, any>) {
    return adminApiRequest<Record<string, any>>("/college-admin/profile/draft", {
      method: "POST",
      body: JSON.stringify({ draft_data: draftData }),
    });
  },

  async getDraft() {
    return adminApiRequest<Record<string, any> | null>("/college-admin/profile/draft");
  },

  async deleteDraft() {
    return adminApiRequest<boolean>("/college-admin/profile/draft", {
      method: "DELETE",
    });
  },

  async getProfileHistory(limit = 20) {
    return adminApiRequest<ProfileHistoryItem[]>(`/college-admin/profile/history?limit=${limit}`);
  },

  async uploadProfileAsset(file: File, assetType: "logo" | "cover" | "favicon" | "approval_document") {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("asset_type", assetType);

    return adminApiRequest<ProfileAssetUploadResult>("/college-admin/profile/upload-image", {
      method: "POST",
      body: formData,
    });
  },

  // 3. Website Sources
  async getWebsites() {
    return adminApiRequest<WebsiteSource[]>("/college-admin/websites");
  },

  async createWebsite(data: {
    base_url: string;
    allowed_subdomains?: string;
    max_depth?: number;
    max_pages?: number;
    crawl_frequency?: string;
  }) {
    return adminApiRequest<WebsiteSource>("/college-admin/websites", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateWebsite(
    sourceId: string,
    data: {
      allowed_subdomains?: string;
      max_depth?: number;
      max_pages?: number;
      crawl_frequency?: string;
      is_active?: boolean;
    }
  ) {
    return adminApiRequest<WebsiteSource>(`/college-admin/websites/${sourceId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteWebsite(sourceId: string) {
    return adminApiRequest<{ id: string }>(`/college-admin/websites/${sourceId}`, {
      method: "DELETE",
    });
  },

  // 4. Crawler Management
  async startCrawl(sourceId: string) {
    return adminApiRequest<CrawlJob>(`/college-admin/crawler/start?source_id=${sourceId}`, {
      method: "POST",
    });
  },

  async controlCrawl(jobId: string, action: "PAUSE" | "RESUME" | "CANCEL") {
    return adminApiRequest<CrawlJob>(
      `/college-admin/crawler/${jobId}/action?action=${action}`,
      {
        method: "POST",
      }
    );
  },

  async getCrawlJobs(sourceId?: string) {
    const qs = sourceId ? `?source_id=${sourceId}` : "";
    return adminApiRequest<CrawlJob[]>(`/college-admin/crawler/jobs${qs}`);
  },

  async getCrawlEvents(jobId: string) {
    return adminApiRequest<CrawlEvent[]>(`/college-admin/crawler/jobs/${jobId}/events`);
  },

  async getCrawledPages(sourceId?: string) {
    const qs = sourceId ? `?source_id=${sourceId}` : "";
    return adminApiRequest<WebsitePage[]>(`/college-admin/crawler/pages${qs}`);
  },

  // 5. Document Management & OCR Engine
  async getDocuments(statusFilter?: string) {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : "";
    return adminApiRequest<DocumentDetail[]>(`/college-admin/documents${qs}`);
  },

  /**
   * Canonical PDF upload path.
   * Sends the actual PDF binary as multipart/form-data to POST /api/v1/college-admin/documents/upload-file.
   * The backend validates magic bytes, uploads to Supabase Storage, computes the real SHA-256 checksum,
   * and only then creates the database record.
   * Authentication (Bearer token) and college_id are attached by adminApiRequest automatically.
   */
  async uploadDocumentBinary(file: File, category: string = "GENERAL", description?: string) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", category);
    if (description) {
      formData.append("description", description);
    }

    return adminApiRequest<DocumentDetail>("/college-admin/documents/upload-file", {
      method: "POST",
      body: formData,
    });
  },

  /**
   * @deprecated — Metadata-only registration path.
   * MUST NOT be used for new PDF uploads. Use uploadDocumentBinary instead.
   *
   * This endpoint (POST /api/v1/college-admin/documents/upload) only registers a document record
   * and must only be called when ALL of the following are true:
   *   1. The PDF binary has already been successfully uploaded to Supabase Storage.
   *   2. The caller holds a real SHA-256 checksum computed from the uploaded binary (64 hex chars).
   *   3. The backend has verified the storage object exists at the expected path.
   *
   * Calling this with a fake or placeholder checksum, or for a file that has not yet been uploaded,
   * will result in HTTP 422 from the backend and an orphan database record pointing to a
   * non-existent storage object — causing Supabase 404 on every signed-URL request.
   *
   * The `checksum_sha256` field (64-char hex string) must be included in `data` for the
   * backend to accept the request.
   */
  async registerPreUploadedDocument(data: {
    original_filename: string;
    file_size_bytes: number;
    checksum_sha256: string;
    mime_type?: string;
    category?: string;
    description?: string;
  }) {
    return adminApiRequest<DocumentDetail>("/college-admin/documents/upload", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getDocument(documentId: string) {
    return adminApiRequest<DocumentDetail>(`/college-admin/documents/${documentId}`);
  },

  async getDocumentPages(documentId: string) {
    return adminApiRequest<DocumentPage[]>(`/college-admin/documents/${documentId}/pages`);
  },

  async getDocumentStatus(documentId: string) {
    return adminApiRequest<DocumentStatus>(`/college-admin/documents/${documentId}/status`);
  },

  async getDocumentDownloadUrl(documentId: string) {
    return adminApiRequest<{ download_url: string }>(`/college-admin/documents/${documentId}/download-url`);
  },

  async reprocessDocument(documentId: string) {
    return adminApiRequest<DocumentDetail>(`/college-admin/documents/${documentId}/reprocess`, {
      method: "POST",
    });
  },

  async deleteDocument(documentId: string) {
    return adminApiRequest<{ id: string }>(`/college-admin/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // 6. Knowledge Base & Review Queue
  async getKnowledge(params?: {
    status?: string;
    source_type?: string;
    limit?: number;
    offset?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.append("status_filter", params.status);
    if (params?.source_type) searchParams.append("source_type", params.source_type);
    if (params?.limit) searchParams.append("limit", params.limit.toString());
    if (params?.offset) searchParams.append("offset", params.offset.toString());

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return adminApiRequest<KnowledgeChunk[]>(`/college-admin/knowledge${qs}`);
  },

  async getPendingReviews() {
    return adminApiRequest<KnowledgeChunk[]>("/college-admin/reviews");
  },

  async submitReviewDecision(
    chunkId: string,
    decision: "APPROVE" | "REJECT",
    comments?: string
  ) {
    return adminApiRequest<KnowledgeChunk>(
      `/college-admin/reviews/${chunkId}/decision`,
      {
        method: "POST",
        body: JSON.stringify({ decision, comments }),
      }
    );
  },

  async updateKnowledgeText(chunkId: string, chunk_text: string) {
    return adminApiRequest<KnowledgeChunk>(`/college-admin/knowledge/${chunkId}`, {
      method: "PATCH",
      body: JSON.stringify({ chunk_text }),
    });
  },

  async publishKnowledgeChunk(chunkId: string) {
    return adminApiRequest<KnowledgeChunk>(
      `/college-admin/knowledge/${chunkId}/publish`,
      {
        method: "POST",
      }
    );
  },

  async unpublishKnowledgeChunk(chunkId: string) {
    return adminApiRequest<KnowledgeChunk>(
      `/college-admin/knowledge/${chunkId}/unpublish`,
      {
        method: "POST",
      }
    );
  },

  async bulkSubmitReviewDecisions(chunkIds: string[], decision: "APPROVE" | "REJECT", comments?: string) {
    return adminApiRequest<{ processed_count: number }>(
      "/college-admin/reviews/bulk-decision",
      {
        method: "POST",
        body: JSON.stringify({ chunk_ids: chunkIds, decision, comments }),
      }
    );
  },

  async bulkPublishKnowledgeChunks(chunkIds: string[]) {
    return adminApiRequest<{ published_count: number }>(
      "/college-admin/knowledge/bulk-publish",
      {
        method: "POST",
        body: JSON.stringify({ chunk_ids: chunkIds }),
      }
    );
  },

  async triggerKnowledgeProcessing(source_type: "WEBSITE" | "DOCUMENT", source_id: string) {
    return adminApiRequest<{ mode: string }>(
      "/college-admin/knowledge/process",
      {
        method: "POST",
        body: JSON.stringify({ source_type, source_id }),
      }
    );
  },

  // 7. Structured Facts
  async getStructuredFacts(category?: string) {
    const qs = category ? `?category=${category}` : "";
    return adminApiRequest<ExtractedFact[]>(`/college-admin/structured-data${qs}`);
  },

  async createStructuredFact(data: {
    category: string;
    fact_key: string;
    fact_value: string;
  }) {
    return adminApiRequest<ExtractedFact>("/college-admin/structured-data", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateStructuredFact(
    factId: string,
    data: {
      category?: string;
      fact_key?: string;
      fact_value?: string;
      verification_status?: string;
    }
  ) {
    return adminApiRequest<ExtractedFact>(
      `/college-admin/structured-data/${factId}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      }
    );
  },

  async deleteStructuredFact(factId: string) {
    return adminApiRequest<{ id: string }>(
      `/college-admin/structured-data/${factId}`,
      {
        method: "DELETE",
      }
    );
  },

  // 8. Analytics
  async getAnalytics(timeRange: string = "30D") {
    try {
      const res = await adminApiRequest<CollegeAnalytics>(`/analytics/college?time_range=${timeRange}`);
      if (res.success && res.data) return res;
    } catch (e) {}

    return adminApiRequest<CollegeAnalytics>(
      `/college-admin/analytics?time_range=${timeRange}`
    );
  },

  // 9. Support & Feedback
  async getSupportTickets(statusFilter?: string, category?: string, priority?: string) {
    const params = new URLSearchParams();
    if (statusFilter && statusFilter !== "ALL") params.append("status", statusFilter);
    if (category && category !== "ALL") params.append("category", category);
    if (priority && priority !== "ALL") params.append("priority", priority);
    const qs = params.toString() ? `?${params.toString()}` : "";

    try {
      const res = await adminApiRequest<CollegeSupportTicket[]>(`/support/tickets${qs}`);
      if (res.success && res.data) return res;
    } catch (e) {}

    const oldQs = statusFilter ? `?status_filter=${statusFilter}` : "";
    return adminApiRequest<CollegeSupportTicket[]>(`/college-admin/support${oldQs}`);
  },

  async getTicketDetail(ticketId: string): Promise<{ success: boolean; message?: string; data?: CollegeSupportTicket; error?: string }> {
    try {
      return await adminApiRequest<CollegeSupportTicket>(`/support/tickets/${ticketId}`);
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async addTicketReply(ticketId: string, messageText: string, isInternal: boolean = false): Promise<{ success: boolean; message?: string; data?: any; error?: string }> {
    try {
      return await adminApiRequest<any>(`/support/tickets/${ticketId}/replies`, {
        method: "POST",
        body: JSON.stringify({ message_text: messageText, is_internal: isInternal }),
      });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async resolveSupportTicket(
    ticketId: string,
    status: string,
    response_notes?: string,
    priority?: string
  ) {
    try {
      const res = await adminApiRequest<{ id: string; status: string }>(
        `/support/tickets/${ticketId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status, resolution_notes: response_notes, priority }),
        }
      );
      if (res.success && res.data) return res;
    } catch (e) {}

    return adminApiRequest<{ id: string; status: string }>(
      `/college-admin/support/${ticketId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ status, response_notes }),
      }
    );
  },

  async getFeedback() {
    try {
      const res = await adminApiRequest<CollegeFeedback[]>("/feedback");
      if (res.success && res.data) return res;
    } catch (e) {}
    return adminApiRequest<CollegeFeedback[]>("/college-admin/feedback");
  },

  // 10. Notifications
  async getNotifications(unreadOnly: boolean = false) {
    try {
      const res = await adminApiRequest<{ items: CollegeNotification[]; unread_count: number }>(
        `/notifications?unread_only=${unreadOnly}`
      );
      if (res.success && res.data && res.data.items) {
        return { success: true, data: res.data.items, unread_count: res.data.unread_count };
      }
    } catch (e) {}
    return adminApiRequest<CollegeNotification[]>("/college-admin/notifications");
  },

  async markNotificationRead(id: string) {
    try {
      return await adminApiRequest(`/notifications/${id}/read`, { method: "PATCH" });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async markAllNotificationsRead() {
    try {
      return await adminApiRequest("/notifications/read-all", { method: "POST" });
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // 11. Onboarding Wizard (Phase 6)
  async getOnboardingProgress() {
    try {
      const res = await adminApiRequest<{
        id: string;
        college_id: string;
        college_name: string;
        college_slug: string;
        current_step: number;
        is_approved: boolean;
        admin_assigned: boolean;
        profile_completed: boolean;
        website_configured: boolean;
        documents_uploaded: boolean;
        knowledge_ready: boolean;
        is_completed: boolean;
        step_data: Record<string, any>;
      }>("/college-admin/onboarding");
      if (res.success && res.data) {
        return res;
      }
    } catch (e) {}

    // Resilient offline fallback
    const collegeId = typeof window !== "undefined" ? localStorage.getItem("admin_college_id") || "11111111-1111-1111-1111-111111111111" : "11111111-1111-1111-1111-111111111111";
    let storedProgress = null;
    try {
      const raw = localStorage.getItem(`campusai_onboarding_${collegeId}`);
      if (raw) storedProgress = JSON.parse(raw);
    } catch (e) {}

    const defaultProg = storedProgress || {
      id: "onb-" + collegeId,
      college_id: collegeId,
      college_name: "Ahmedabad Institute of Technology",
      college_slug: "ait-ahmedabad",
      current_step: 1,
      is_approved: true,
      admin_assigned: true,
      profile_completed: false,
      website_configured: false,
      documents_uploaded: false,
      knowledge_ready: false,
      is_completed: false,
      step_data: {},
    };

    return { success: true, data: defaultProg };
  },

  async updateOnboardingProgress(data: {
    current_step?: number;
    profile_completed?: boolean;
    website_configured?: boolean;
    documents_uploaded?: boolean;
    knowledge_ready?: boolean;
    step_data?: Record<string, any>;
  }) {
    try {
      const res = await adminApiRequest<any>("/college-admin/onboarding", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      if (res.success && res.data) {
        return res;
      }
    } catch (e) {}

    // Offline storage update
    const collegeId = typeof window !== "undefined" ? localStorage.getItem("admin_college_id") || "11111111-1111-1111-1111-111111111111" : "11111111-1111-1111-1111-111111111111";
    let current = (await this.getOnboardingProgress()).data;
    const updated = {
      ...current,
      ...data,
      step_data: { ...current.step_data, ...(data.step_data || {}) },
    };
    try {
      localStorage.setItem(`campusai_onboarding_${collegeId}`, JSON.stringify(updated));
    } catch (e) {}

    return { success: true, data: updated };
  },

  async completeOnboarding() {
    try {
      const res = await adminApiRequest<any>("/college-admin/onboarding/complete", {
        method: "POST",
      });
      if (res.success && res.data) {
        return res;
      }
    } catch (e) {}

    const collegeId = typeof window !== "undefined" ? localStorage.getItem("admin_college_id") || "11111111-1111-1111-1111-111111111111" : "11111111-1111-1111-1111-111111111111";
    let current = (await this.getOnboardingProgress()).data;
    const completed = {
      ...current,
      is_completed: true,
      current_step: 6,
      completed_at: new Date().toISOString(),
    };
    try {
      localStorage.setItem(`campusai_onboarding_${collegeId}`, JSON.stringify(completed));
    } catch (e) {}

    return { success: true, data: completed };
  },
};

