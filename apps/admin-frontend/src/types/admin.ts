export type UserRole = "STUDENT" | "COLLEGE_ADMIN" | "SUPER_ADMIN";

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  college_id?: string | null;
  is_verified: boolean;
  is_active: boolean;
}

export interface AdminAuthState {
  admin: AdminUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface DashboardStats {
  total_colleges: number;
  active_colleges: number;
  pending_approvals: number;
  total_users: number;
  total_college_admins: number;
  total_queries: number;
  total_documents: number;
  ai_success_rate: number;
  storage_used_mb: number;
  monthly_jobs: number;
}

export interface RecentCollege {
  id: string;
  name: string;
  slug: string;
  official_domain: string;
  status: string;
  is_active: boolean;
  created_at: string;
}

export interface DashboardOverview {
  stats: DashboardStats;
  recent_colleges: RecentCollege[];
  recent_audit_logs: AuditLogItem[];
  system_status: string;
}

export interface College {
  id: string;
  name: string;
  slug: string;
  official_domain: string;
  logo_url?: string | null;
  contact_email: string;
  contact_phone?: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";
  is_active: boolean;
  created_at: string;
}

export interface RegistrationReviewHistory {
  id: string;
  previous_status: string;
  new_status: string;
  comments?: string;
  action_type: string;
  created_at: string;
}

export interface CollegeRegistration {
  id: string;
  college_id?: string | null;
  college_name?: string;
  name?: string; // backward compat with name
  college_code?: string | null;
  slug: string;
  official_domain: string;
  contact_email: string;
  contact_phone?: string | null;
  contact_person_name?: string;
  contact_person_email?: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string;
  description?: string | null;
  accreditation_details?: string | null;
  website_url?: string | null;
  logo_url?: string | null;
  supporting_documents?: Array<any>;
  status: string;
  tracking_code?: string;
  initial_admin_name?: string | null;
  initial_admin_email?: string | null;
  reviewed_at?: string | null;
  review_comments?: string | null;
  additional_info_requested?: string | null;
  additional_info_submitted?: string | null;
  is_active?: boolean;
  created_at: string;
  updated_at?: string;
  review_history?: RegistrationReviewHistory[];
}

export interface CollegeAdminItem {
  membership_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  college_id: string;
  college_name: string;
  college_domain?: string;
  role_in_college: string;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
}

export interface PlatformUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AIProviderConfig {
  id: string;
  provider_name: string;
  model_name: string;
  is_primary: boolean;
  is_active: boolean;
  timeout_seconds: number;
  max_retries: number;
  temperature: number;
  created_at: string;
  updated_at: string;
}

export interface AIProviderTestResult {
  provider_name: string;
  model_name: string;
  status: "SUCCESS" | "FAILED";
  latency_ms: number;
  message: string;
  timestamp: string;
}

export interface UsageAnalytics {
  total_queries: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  average_latency_ms: number;
  fallback_rate_percent: number;
  estimated_cost_usd: number;
  top_colleges: Array<{
    name: string;
    queries: number;
    tokens: number;
    percent: number;
  }>;
}

export interface JobOverview {
  id: string;
  college_id: string;
  college_name: string;
  job_type: "CRAWLER" | "DOCUMENT_PROCESSING";
  target_name: string;
  status: string;
  progress_percent: number;
  error_message?: string | null;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  college_id?: string | null;
  college_name?: string | null;
  actor_user_id?: string | null;
  actor_email?: string | null;
  action_type: string;
  target_entity: string;
  target_id: string;
  payload_diff?: Record<string, any> | null;
  ip_address?: string | null;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  college_id: string;
  college_name: string;
  user_id?: string | null;
  student_name: string;
  student_email: string;
  subject: string;
  message: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";
  created_at: string;
}

export interface PlatformHealth {
  status: "HEALTHY" | "DEGRADED" | "CRITICAL";
  database: Record<string, any>;
  redis_broker: Record<string, any>;
  supabase_storage: Record<string, any>;
  celery_workers: Record<string, any>;
  timestamp: string;
}

export interface SystemSettings {
  allow_college_registration: boolean;
  default_language: string;
  max_pdf_upload_mb: number;
  rate_limit_per_minute: number;
  maintenance_mode: boolean;
  rag_similarity_threshold: number;
}
