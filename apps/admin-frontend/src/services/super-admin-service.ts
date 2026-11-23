/**
 * Centralized Global Super Admin Service.
 * Connects frontend UI to FastAPI Super Admin governance endpoints.
 */

import { adminApiRequest } from "@/lib/api-client";
import {
  DashboardOverview,
  College,
  CollegeRegistration,
  CollegeAdminItem,
  PlatformUser,
  AIProviderConfig,
  AIProviderTestResult,
  UsageAnalytics,
  JobOverview,
  AuditLogItem,
  SupportTicket,
  PlatformHealth,
  SystemSettings,
} from "@/types/admin";

export const superAdminService = {
  // 1. Dashboard Aggregations
  async getDashboardOverview() {
    return adminApiRequest<DashboardOverview>("/super-admin/dashboard");
  },

  // 2. Colleges & Tenant Management
  async getColleges(allColleges: boolean = true) {
    return adminApiRequest<College[]>(`/colleges?all_colleges=${allColleges}`);
  },

  async getCollegeDetails(idOrSlug: string) {
    return adminApiRequest<College>(`/colleges/${idOrSlug}`);
  },

  async createCollege(data: {
    name: string;
    slug: string;
    official_domain: string;
    logo_url?: string;
    contact_email: string;
    contact_phone?: string;
  }) {
    return adminApiRequest<College>("/colleges", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateCollege(
    collegeId: string,
    data: {
      name?: string;
      official_domain?: string;
      logo_url?: string;
      contact_email?: string;
      contact_phone?: string;
      status?: string;
      is_active?: boolean;
    }
  ) {
    return adminApiRequest<College>(`/colleges/${collegeId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  // 3. College Registration & Approvals Queue (Phase 6)
  async getRegistrations(statusFilter: string = "ALL") {
    return adminApiRequest<CollegeRegistration[]>(
      `/super-admin/registrations?status_filter=${statusFilter}`
    );
  },

  async getRegistrationDetails(registrationId: string) {
    return adminApiRequest<CollegeRegistration>(
      `/super-admin/registrations/${registrationId}`
    );
  },

  async approveRegistration(registrationId: string, reason?: string) {
    return adminApiRequest<CollegeRegistration>(
      `/super-admin/registrations/${registrationId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ action: "APPROVE", comments: reason }),
      }
    );
  },

  async rejectRegistration(registrationId: string, reason?: string) {
    return adminApiRequest<CollegeRegistration>(
      `/super-admin/registrations/${registrationId}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ action: "REJECT", comments: reason }),
      }
    );
  },

  async requestRegistrationInfo(
    registrationId: string,
    prompt: string,
    comments?: string
  ) {
    return adminApiRequest<CollegeRegistration>(
      `/super-admin/registrations/${registrationId}/request-information`,
      {
        method: "POST",
        body: JSON.stringify({
          action: "REQUEST_INFO",
          additional_info_prompt: prompt,
          comments,
        }),
      }
    );
  },

  // 4. College Admin Directory & Invitations (Phase 6)
  async getCollegeAdmins() {
    return adminApiRequest<CollegeAdminItem[]>("/super-admin/admins");
  },

  async assignCollegeAdmin(data: {
    user_id: string;
    college_id: string;
    role_in_college?: string;
    is_primary?: boolean;
  }) {
    return adminApiRequest<{ membership_id: string; user_id: string; college_id: string }>(
      "/super-admin/admins/assign",
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  },

  async inviteCollegeAdmin(
    collegeId: string,
    data: { email: string; full_name: string; role_in_college?: string }
  ) {
    return adminApiRequest<any>(`/super-admin/colleges/${collegeId}/admins/invite`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getCollegeAdminsAndInvitations(collegeId: string) {
    return adminApiRequest<{
      assigned_admins: CollegeAdminItem[];
      pending_invitations: any[];
    }>(`/super-admin/colleges/${collegeId}/admins`);
  },

  async revokeAdminInvitation(collegeId: string, invitationId: string) {
    return adminApiRequest<boolean>(
      `/super-admin/colleges/${collegeId}/invitations/${invitationId}`,
      { method: "DELETE" }
    );
  },

  async resendAdminInvitation(collegeId: string, invitationId: string) {
    return adminApiRequest<any>(
      `/super-admin/colleges/${collegeId}/invitations/${invitationId}/resend`,
      { method: "POST" }
    );
  },

  async getNotificationLogs(limit: number = 50) {
    return adminApiRequest<any[]>(`/super-admin/notifications?limit=${limit}`);
  },

  // 5. User Directory
  async getUsers(limit: number = 50, offset: number = 0) {
    return adminApiRequest<PlatformUser[]>(`/users?limit=${limit}&offset=${offset}`);
  },

  async getUserDetails(userId: string) {
    return adminApiRequest<PlatformUser>(`/users/${userId}`);
  },

  async updateUser(
    userId: string,
    data: {
      full_name?: string;
      role?: string;
      is_active?: boolean;
    }
  ) {
    return adminApiRequest<PlatformUser>(`/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  // 6. AI Provider Orchestration
  async getAIProviders() {
    return adminApiRequest<AIProviderConfig[]>("/super-admin/ai-providers");
  },

  async createAIProvider(data: {
    provider_name: string;
    model_name: string;
    is_primary?: boolean;
    is_active?: boolean;
    timeout_seconds?: number;
    max_retries?: number;
    temperature?: number;
  }) {
    return adminApiRequest<AIProviderConfig>("/super-admin/ai-providers", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateAIProvider(
    configId: string,
    data: {
      is_primary?: boolean;
      is_active?: boolean;
      timeout_seconds?: number;
      max_retries?: number;
      temperature?: number;
    }
  ) {
    return adminApiRequest<AIProviderConfig>(`/super-admin/ai-providers/${configId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async testAIProvider(configId: string) {
    return adminApiRequest<AIProviderTestResult>(
      `/super-admin/ai-providers/${configId}/test`,
      {
        method: "POST",
      }
    );
  },

  // 7. Telemetry & Analytics
  // The platform endpoint (/analytics/platform) is preferred because it serves
  // real, database-backed AI telemetry. It returns a PlatformAnalyticsResponse,
  // though, where token/latency metrics live under `ai_metrics`, the user-question
  // total is `total_questions_asked`, and colleges are `top_active_colleges`
  // (which carry no per-college token counts). Normalize it into the flat
  // UsageAnalytics shape the analytics page and its type expect, so the page can
  // never receive a partially-shaped object that would crash a method call such
  // as `data.total_tokens.toLocaleString()`.
  async getUsageAnalytics(
    timeRange: string = "30D"
  ): Promise<{ success: boolean; message?: string; data?: UsageAnalytics; error?: string }> {
    const res = await adminApiRequest<any>(`/analytics/platform?time_range=${encodeURIComponent(timeRange)}`);
    if (!res.success || !res.data) return res;
    const p = res.data as Record<string, any>;
    const ai = (p.ai_metrics ?? {}) as Record<string, any>;
    const colleges = Array.isArray(p.top_active_colleges) ? p.top_active_colleges : [];
    const normalized: UsageAnalytics = {
      total_queries: p.total_questions_asked ?? 0,
      total_tokens: ai.total_tokens ?? 0,
      prompt_tokens: ai.prompt_tokens ?? 0,
      completion_tokens: ai.completion_tokens ?? 0,
      average_latency_ms: ai.average_latency_ms ?? 0,
      fallback_rate_percent: ai.fallback_rate_percent ?? 0,
      estimated_cost_usd: ai.estimated_cost_usd ?? 0,
      top_colleges: colleges.map((c: Record<string, any>) => ({
        name: c.name ?? "Unknown",
        queries: c.queries ?? 0,
        tokens: c.tokens ?? 0,
        percent: c.percent ?? 0,
      })),
    };
    return { success: true, message: res.message, data: normalized };
  },

  async getPlatformAnalytics(timeRange: string = "30D") {
    try {
      const res = await adminApiRequest<any>(`/analytics/platform?time_range=${timeRange}`);
      if (res.success && res.data) return res;
    } catch (e) {}
    return adminApiRequest<UsageAnalytics>("/super-admin/analytics");
  },

  // 8. Ingestion & Job Monitor
  async getBackgroundJobs() {
    return adminApiRequest<JobOverview[]>("/super-admin/jobs");
  },

  // 9. Compliance Audit Logs
  async getAuditLogs(params?: {
    college_id?: string;
    action_type?: string;
    limit?: number;
    offset?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.college_id) searchParams.append("college_id", params.college_id);
    if (params?.action_type) searchParams.append("action_type", params.action_type);
    if (params?.limit) searchParams.append("limit", params.limit.toString());
    if (params?.offset) searchParams.append("offset", params.offset.toString());

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return adminApiRequest<AuditLogItem[]>(`/super-admin/audit-logs${qs}`);
  },

  // 10. Student Support Tickets
  async getSupportTickets(params?: { status?: string; college_id?: string; category?: string; priority?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.status && params.status !== "ALL") searchParams.append("status", params.status);
    if (params?.college_id && params.college_id !== "ALL") searchParams.append("college_id", params.college_id);
    if (params?.category && params.category !== "ALL") searchParams.append("category", params.category);
    if (params?.priority && params.priority !== "ALL") searchParams.append("priority", params.priority);

    const qs = searchParams.toString() ? `?${searchParams.toString()}` : "";
    try {
      const res = await adminApiRequest<SupportTicket[]>(`/support/tickets${qs}`);
      if (res.success && res.data) return res;
    } catch (e) {}

    const oldParams = new URLSearchParams();
    if (params?.status) oldParams.append("status_filter", params.status);
    if (params?.college_id) oldParams.append("college_id", params.college_id);
    const oldQs = oldParams.toString() ? `?${oldParams.toString()}` : "";
    return adminApiRequest<SupportTicket[]>(`/super-admin/support-tickets${oldQs}`);
  },

  async getTicketDetail(ticketId: string): Promise<{ success: boolean; message?: string; data?: SupportTicket; error?: string }> {
    try {
      return await adminApiRequest<SupportTicket>(`/support/tickets/${ticketId}`);
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

  async updateSupportTicketStatus(ticketId: string, status: string, resolution_notes?: string) {
    try {
      const res = await adminApiRequest<{ id: string; status: string }>(
        `/support/tickets/${ticketId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status, resolution_notes }),
        }
      );
      if (res.success && res.data) return res;
    } catch (e) {}

    return adminApiRequest<{ id: string; status: string }>(
      `/super-admin/support-tickets/${ticketId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }
    );
  },

  // 11. Infrastructure Health
  async getHealthMetrics() {
    return adminApiRequest<PlatformHealth>("/super-admin/health-metrics");
  },

  // 12. Global Settings
  async getSystemSettings() {
    return adminApiRequest<SystemSettings>("/super-admin/settings");
  },

  async updateSystemSettings(data: Partial<SystemSettings>) {
    return adminApiRequest<SystemSettings>("/super-admin/settings", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },
};

