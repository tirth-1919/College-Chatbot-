/**
 * College Administrator TypeScript Types & Schemas.
 */

export interface CollegeProfile {
  id: string;
  name: string;
  slug: string;
  official_domain: string;
  contact_email: string;
  contact_phone?: string | null;
  logo_url?: string | null;
  status: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;

  // 1. Institution Identity
  short_name?: string | null;
  cover_image_url?: string | null;
  institution_type?: string | null;
  established_year?: number | null;
  website_url?: string | null;

  // 2. Address & Location
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
  postal_code?: string | null;
  maps_url?: string | null;
  latitude?: number | null;
  longitude?: number | null;

  // 3. Official Contacts
  admission_email?: string | null;
  examination_email?: string | null;
  placement_email?: string | null;
  admission_helpline?: string | null;
  alternate_phone?: string | null;
  working_hours?: string | null;

  // 4. Recognition & Accreditation
  affiliated_university?: string | null;
  recognized_by?: string | null;
  aicte_approval?: string | null;
  ugc_recognition?: string | null;
  naac_grade?: string | null;
  nba_accreditation?: string | null;
  accreditation_validity?: string | null;
  approval_document_url?: string | null;

  // 5. About Institution & Leadership
  short_description?: string | null;
  about_text?: string | null;
  vision?: string | null;
  mission?: string | null;
  leader_name?: string | null;
  leader_designation?: string | null;

  // 6. Social Media
  linkedin_url?: string | null;
  instagram_url?: string | null;
  facebook_url?: string | null;
  youtube_url?: string | null;
  twitter_url?: string | null;

  // 7. Branding
  favicon_url?: string | null;
  primary_brand_color?: string | null;
  secondary_brand_color?: string | null;

  // 8. Draft State
  draft_profile?: Record<string, any> | null;
}

export interface ProfileHistoryItem {
  id: string;
  action_type: string;
  actor_id?: string | null;
  actor_name?: string | null;
  actor_email?: string | null;
  payload_diff?: Record<string, { old: any; new: any }> | null;
  created_at: string;
}

export interface ProfileAssetUploadResult {
  asset_url: string;
  asset_type: string;
  file_name: string;
  file_size_bytes: number;
}

export interface CollegeDashboardStats {
  total_website_sources: number;
  total_crawled_pages: number;
  total_documents: number;
  pending_reviews: number;
  published_chunks: number;
  total_queries: number;
  recent_crawls_count: number;
  recent_documents_count: number;
  satisfaction_score: number;
  open_tickets_count: number;
}

export interface WebsiteSource {
  id: string;
  college_id: string;
  base_url: string;
  allowed_subdomains?: string | null;
  max_depth: number;
  max_pages: number;
  crawl_frequency: string;
  is_active: boolean;
  last_crawled_at?: string | null;
  pages_count: number;
  created_at: string;
}

export interface CrawlJob {
  id: string;
  source_id: string;
  college_id: string;
  base_url?: string | null;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "PAUSED" | "CANCELLED";
  pages_discovered: number;
  pages_crawled: number;
  pages_failed: number;
  failure_reason?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
}

export interface CrawlEvent {
  id: string;
  crawl_job_id: string;
  log_level: "INFO" | "WARNING" | "ERROR" | "SUCCESS";
  message: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface WebsitePage {
  id: string;
  source_id: string;
  college_id: string;
  crawl_job_id?: string | null;
  url: string;
  title?: string | null;
  meta_description?: string | null;
  content_hash: string;
  cleaned_text: string;
  content_length?: number;
  http_status: number;
  fetched_at: string;
}

export interface DocumentDetail {
  id: string;
  college_id: string;
  original_filename: string;
  storage_path?: string;
  file_size_bytes: number;
  total_pages: number;
  checksum_sha256?: string;
  processing_status:
    | "UPLOADED"
    | "VALIDATING"
    | "QUEUED"
    | "PROCESSING"
    | "OCR_PROCESSING"
    | "EXTRACTED"
    | "PENDING_REVIEW"
    | "COMPLETED"
    | "FAILED"
    | "REPROCESSING"
    | "DELETED";
  mime_type: string;
  title?: string | null;
  category?: string;
  description?: string | null;
  failure_reason?: string | null;
  extraction_method?: string;
  ocr_applied?: boolean;
  download_url?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface DocumentPage {
  id: string;
  document_id: string;
  college_id?: string | null;
  page_number: number;
  extracted_text: string;
  is_scanned: boolean;
  ocr_applied: boolean;
  ocr_confidence?: number | null;
  extraction_method: string;
  tables_markdown?: string[];
  has_tables: boolean;
  word_count: number;
  char_count: number;
  processed_at: string;
}

export interface DocumentStatus {
  id: string;
  college_id: string;
  processing_status: string;
  total_pages: number;
  pages_extracted: number;
  ocr_applied: boolean;
  failure_reason?: string | null;
  updated_at: string;
}

export interface KnowledgeChunk {
  id: string;
  college_id: string;
  source_type: "WEBSITE" | "DOCUMENT" | "ADMIN_STRUCTURED" | "OFFICIAL_WEBSITE" | "PDF" | "FAQ";
  source_id: string;
  source_url?: string | null;
  page_number?: number | null;
  category?: string;
  heading?: string | null;
  content_hash?: string | null;
  chunk_text: string;
  chunk_metadata?: Record<string, any>;
  status: "PENDING_REVIEW" | "APPROVED" | "PUBLISHED" | "REJECTED" | "STALE" | "SUPERSEDED" | "FAILED";
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ExtractedFact {
  id: string;
  college_id: string;
  source_type: string;
  source_id: string;
  category: "ABOUT" | "COURSES" | "ADMISSIONS" | "DEPARTMENTS" | "FACILITIES" | "FAQS";
  fact_key: string;
  fact_value: string;
  verification_status: string;
  created_at: string;
}

export interface CollegeAnalytics {
  college_id?: string;
  college_name?: string;
  time_range?: string;
  total_queries: number;
  total_sessions?: number;
  total_feedback_count?: number;
  satisfaction_rate?: number;
  satisfaction_score?: number;
  average_confidence?: number;
  unanswered_queries_count?: number;
  active_knowledge_chunks?: number;
  daily_queries?: Array<{ date: string; queries: number; verified_queries?: number }>;
  daily_trends?: Array<{ date: string; queries: number; verified_queries: number }>;
  daily_query_trend?: Array<{ date: string; queries: number }>;
  popular_questions?: Array<{ query?: string; question?: string; count: number; percentage?: number }>;
  frequent_questions?: Array<{ query: string; count: number; category?: string; latest_asked_at?: string | null }>;
  top_questions?: Array<{ question: string; count: number; last_asked_at?: string; percentage?: number }>;
  unanswered_questions: Array<string | { query?: string; question?: string; count?: number; occurrence_count?: number; last_asked_at?: string; sample_session_id?: string }>;
  source_usage?: Record<string, number>;
  source_distribution?: Record<string, number>;
  badge_distribution?: Record<string, number>;
  category_distribution?: Record<string, number>;
  positive_feedback_count?: number;
  negative_feedback_count?: number;
  category_breakdown?: Record<string, number>;
}

export interface CollegeSupportTicketReply {
  id: string;
  ticket_id: string;
  sender_user_id: string;
  sender_name?: string;
  sender_role: string;
  message_text: string;
  is_internal: boolean;
  created_at: string;
}

export interface CollegeSupportTicket {
  id: string;
  college_id: string;
  user_id?: string;
  student_name?: string;
  user_name?: string;
  student_email?: string;
  user_email?: string;
  session_id?: string;
  subject: string;
  message: string;
  category?: string;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  status: "OPEN" | "IN_PROGRESS" | "WAITING_FOR_USER" | "RESOLVED" | "CLOSED";
  assigned_to_user_id?: string;
  assigned_to_name?: string;
  reply_count?: number;
  replies?: CollegeSupportTicketReply[];
  resolution_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface CollegeFeedback {
  id: string;
  message_id: string;
  session_id?: string;
  user_email?: string | null;
  rating: number;
  category?: string;
  comment?: string | null;
  comments?: string | null;
  created_at: string;
}

export interface CollegeNotification {
  id: string;
  user_id?: string;
  college_id?: string;
  title: string;
  message: string;
  notification_type?: "INFO" | "WARNING" | "SUCCESS" | "ERROR" | "SYSTEM" | "TICKET" | "CRAWL" | "INGESTION";
  type?: "INFO" | "WARNING" | "SUCCESS" | "ERROR";
  link?: string;
  is_read?: boolean;
  created_at: string;
}

export interface CollegeAdminDashboard {
  college: CollegeProfile;
  stats: CollegeDashboardStats;
  recent_crawl_jobs: CrawlJob[];
  recent_documents: DocumentDetail[];
  recent_pending_reviews: KnowledgeChunk[];
  recent_tickets: CollegeSupportTicket[];
}

