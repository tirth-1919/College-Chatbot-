export interface College {
  id: string;
  name: string;
  slug: string;
  official_domain: string;
  logo_url: string | null;
  contact_email: string;
  contact_phone: string | null;
  status: "PENDING" | "APPROVED" | "SUSPENDED" | "REJECTED";
  is_active: boolean;
}

