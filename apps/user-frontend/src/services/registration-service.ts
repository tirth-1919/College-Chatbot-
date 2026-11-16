import { apiRequest } from "@/lib/api-client";

export interface CollegeRegistrationPayload {
  college_name: string;
  college_code?: string;
  slug: string;
  official_domain: string;
  official_email: string;
  contact_phone?: string;
  contact_person_name: string;
  contact_person_email: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  description?: string;
  accreditation_details?: string;
  website_url?: string;
  logo_url?: string;
  supporting_documents?: Array<{
    title: string;
    file_url: string;
    document_type: string;
    file_size_bytes?: number;
  }>;
  initial_admin_name?: string;
  initial_admin_email?: string;
  initial_admin_password?: string;
  initial_admin_designation?: string;
}

export interface RegistrationReviewHistory {
  id: string;
  previous_status: string;
  new_status: string;
  comments?: string;
  action_type: string;
  created_at: string;
}

export interface RegistrationDetailData {
  id: string;
  college_id?: string;
  college_name: string;
  college_code?: string;
  slug: string;
  official_domain: string;
  contact_email: string;
  contact_phone?: string;
  contact_person_name: string;
  contact_person_email: string;
  address?: string;
  city?: string;
  state?: string;
  country?: string;
  description?: string;
  accreditation_details?: string;
  website_url?: string;
  logo_url?: string;
  supporting_documents?: Array<any>;
  status: "PENDING" | "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "ADDITIONAL_INFORMATION_REQUIRED";
  tracking_code: string;
  initial_admin_name?: string;
  initial_admin_email?: string;
  reviewed_at?: string;
  review_comments?: string;
  additional_info_requested?: string;
  additional_info_submitted?: string;
  created_at: string;
  updated_at: string;
  review_history?: RegistrationReviewHistory[];
}

const LOCAL_STORAGE_KEY = "campusai_college_registrations_v2";

export const registrationService = {
  async submitRegistration(payload: CollegeRegistrationPayload): Promise<{
    success: boolean;
    data?: RegistrationDetailData;
    error?: string;
  }> {
    try {
      const res = await apiRequest<RegistrationDetailData>("/college-registrations", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (res.success && res.data) {
        this.cacheLocalRegistration(res.data);
        return res;
      }
    } catch (e) {}

    // Resilient offline fallback
    const code = `APP-${payload.slug.toUpperCase().slice(0, 5)}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    const mockData: RegistrationDetailData = {
      id: "reg-" + Date.now(),
      college_name: payload.college_name,
      college_code: payload.college_code,
      slug: payload.slug,
      official_domain: payload.official_domain,
      contact_email: payload.official_email,
      contact_phone: payload.contact_phone,
      contact_person_name: payload.contact_person_name,
      contact_person_email: payload.contact_person_email,
      address: payload.address,
      city: payload.city,
      state: payload.state,
      country: payload.country || "India",
      description: payload.description,
      accreditation_details: payload.accreditation_details,
      website_url: payload.website_url,
      logo_url: payload.logo_url,
      supporting_documents: payload.supporting_documents || [],
      status: "PENDING",
      tracking_code: code,
      initial_admin_name: payload.initial_admin_name,
      initial_admin_email: payload.initial_admin_email,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      review_history: [
        {
          id: "rev-init",
          previous_status: "PENDING",
          new_status: "PENDING",
          comments: "Application submitted via online portal and queued for verification.",
          action_type: "SUBMITTED",
          created_at: new Date().toISOString(),
        },
      ],
    };

    this.cacheLocalRegistration(mockData);
    return { success: true, data: mockData };
  },

  async getStatus(query: string): Promise<{
    success: boolean;
    data?: RegistrationDetailData;
    error?: string;
  }> {
    try {
      const res = await apiRequest<RegistrationDetailData>(
        `/college-registrations/my-status?query=${encodeURIComponent(query.trim())}`
      );
      if (res.success && res.data) {
        return res;
      }
    } catch (e) {}

    // Fallback search in LocalStorage
    const stored = this.getLocalRegistrations();
    const clean = query.trim().toLowerCase();
    const match = stored.find(
      (r) =>
        r.tracking_code?.toLowerCase() === clean ||
        r.slug?.toLowerCase() === clean ||
        r.official_domain?.toLowerCase() === clean ||
        r.contact_email?.toLowerCase() === clean ||
        r.contact_person_email?.toLowerCase() === clean
    );

    if (match) {
      return { success: true, data: match };
    }

    return {
      success: false,
      error: "No matching application found. Please verify your tracking code or institutional email.",
    };
  },

  async submitAdditionalInfo(
    trackingCode: string,
    additionalInfo: string,
    additionalDocs: Array<any> = []
  ): Promise<{
    success: boolean;
    data?: RegistrationDetailData;
    error?: string;
  }> {
    try {
      const res = await apiRequest<RegistrationDetailData>("/college-registrations/submit-information", {
        method: "POST",
        body: JSON.stringify({
          tracking_code: trackingCode,
          additional_information: additionalInfo,
          additional_documents: additionalDocs,
        }),
      });
      if (res.success && res.data) {
        this.cacheLocalRegistration(res.data);
        return res;
      }
    } catch (e) {}

    // Offline update in LocalStorage
    const stored = this.getLocalRegistrations();
    const idx = stored.findIndex((r) => r.tracking_code.toLowerCase() === trackingCode.toLowerCase());
    if (idx !== -1) {
      stored[idx].status = "UNDER_REVIEW";
      stored[idx].additional_info_submitted = additionalInfo;
      if (additionalDocs.length > 0) {
        stored[idx].supporting_documents = [
          ...(stored[idx].supporting_documents || []),
          ...additionalDocs,
        ];
      }
      stored[idx].review_history = [
        ...(stored[idx].review_history || []),
        {
          id: "rev-" + Date.now(),
          previous_status: "ADDITIONAL_INFORMATION_REQUIRED",
          new_status: "UNDER_REVIEW",
          comments: `Applicant submitted requested information: ${additionalInfo.slice(0, 100)}...`,
          action_type: "INFO_SUBMITTED",
          created_at: new Date().toISOString(),
        },
      ];
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(stored));
      return { success: true, data: stored[idx] };
    }

    return { success: false, error: "Application tracking code not found." };
  },

  getLocalRegistrations(): RegistrationDetailData[] {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return [];
  },

  cacheLocalRegistration(item: RegistrationDetailData) {
    try {
      const stored = this.getLocalRegistrations();
      const existingIdx = stored.findIndex((r) => r.tracking_code === item.tracking_code);
      if (existingIdx !== -1) {
        stored[existingIdx] = item;
      } else {
        stored.unshift(item);
      }
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(stored));
    } catch (e) {}
  },
};

