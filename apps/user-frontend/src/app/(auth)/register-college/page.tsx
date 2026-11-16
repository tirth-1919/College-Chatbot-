"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { registrationService, CollegeRegistrationPayload } from "@/services/registration-service";
import {
  Building2,
  MapPin,
  Award,
  UserCheck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  Shield,
  ExternalLink,
  Copy,
  Check,
  HelpCircle,
  Clock,
  Sparkles,
} from "lucide-react";

interface FormState extends CollegeRegistrationPayload {
  admin_password_confirm?: string;
}

const INITIAL_STATE: FormState = {
  college_name: "",
  college_code: "",
  slug: "",
  official_domain: "",
  official_email: "",
  contact_phone: "",
  contact_person_name: "",
  contact_person_email: "",
  address: "",
  city: "Ahmedabad",
  state: "Gujarat",
  country: "India",
  description: "",
  accreditation_details: "AICTE Approved, NAAC Accredited",
  website_url: "",
  logo_url: "",
  supporting_documents: [],
  initial_admin_name: "",
  initial_admin_email: "",
  initial_admin_password: "",
  initial_admin_designation: "College Administrator",
  admin_password_confirm: "",
};

export default function UserRegisterCollegePage() {
  const router = useRouter();
  const [step, setStep] = useState<number>(1);
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedData, setSubmittedData] = useState<{
    tracking_code: string;
    college_name: string;
    slug: string;
    domain: string;
    contact_person_email: string;
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Auto-slugify college name
  const handleNameChange = (val: string) => {
    const slugified = val
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");

    setForm((prev) => ({
      ...prev,
      college_name: val,
      slug: prev.slug === "" || prev.slug === prev.college_name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
        ? slugified
        : prev.slug,
    }));
  };

  const updateField = (field: keyof FormState, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const validateStep = (s: number): boolean => {
    setError(null);
    if (s === 1) {
      if (!form.college_name.trim() || form.college_name.length < 3) {
        setError("Please enter the full formal name of the institution (minimum 3 characters).");
        return false;
      }
      if (!form.slug.trim() || !/^[a-z0-9-]+$/.test(form.slug)) {
        setError("Institutional slug must contain only lowercase letters, numbers, and hyphens.");
        return false;
      }
      if (!form.official_domain.trim() || !form.official_domain.includes(".")) {
        setError("Please enter a valid official domain (e.g. college.edu.in or univ.ac.in).");
        return false;
      }
      const genericDomains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"];
      if (genericDomains.some((d) => form.official_domain.toLowerCase().includes(d))) {
        setError("The official domain must be an educational domain (e.g. .edu, .ac.in, .edu.in), not a public email provider.");
        return false;
      }
      if (!form.official_email.trim() || !form.official_email.includes("@")) {
        setError("Please enter a valid official institutional email address.");
        return false;
      }
    } else if (s === 2) {
      if (!form.city?.trim() || !form.state?.trim()) {
        setError("City and State are required fields.");
        return false;
      }
    } else if (s === 3) {
      if (form.website_url && !form.website_url.startsWith("http")) {
        setError("Website URL must start with http:// or https://");
        return false;
      }
    } else if (s === 4) {
      if (!form.contact_person_name.trim() || form.contact_person_name.length < 2) {
        setError("Please enter the contact person / registrar's full name.");
        return false;
      }
      if (!form.contact_person_email.trim() || !form.contact_person_email.includes("@")) {
        setError("Please enter a valid email address for the contact person.");
        return false;
      }
      if (form.initial_admin_password && form.initial_admin_password.length < 8) {
        setError("Administrator password must be at least 8 characters.");
        return false;
      }
      if (form.initial_admin_password && form.initial_admin_password !== form.admin_password_confirm) {
        setError("Password and confirmation password do not match.");
        return false;
      }
    }
    return true;
  };

  const nextStep = () => {
    if (validateStep(step)) {
      setStep((prev) => Math.min(prev + 1, 4));
    }
  };

  const prevStep = () => {
    setError(null);
    setStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(4)) return;

    setLoading(true);
    setError(null);

    // Sync admin fields with contact person if left empty
    const payload: CollegeRegistrationPayload = {
      college_name: form.college_name.trim(),
      college_code: form.college_code?.trim() || undefined,
      slug: form.slug.trim().toLowerCase(),
      official_domain: form.official_domain.trim().toLowerCase(),
      official_email: form.official_email.trim().toLowerCase(),
      contact_phone: form.contact_phone?.trim() || undefined,
      contact_person_name: form.contact_person_name.trim(),
      contact_person_email: form.contact_person_email.trim().toLowerCase(),
      address: form.address?.trim() || undefined,
      city: form.city?.trim() || undefined,
      state: form.state?.trim() || undefined,
      country: form.country || "India",
      description: form.description?.trim() || undefined,
      accreditation_details: form.accreditation_details?.trim() || undefined,
      website_url: form.website_url?.trim() || undefined,
      logo_url: form.logo_url?.trim() || undefined,
      supporting_documents: form.supporting_documents || [],
      initial_admin_name: form.initial_admin_name?.trim() || form.contact_person_name.trim(),
      initial_admin_email: form.initial_admin_email?.trim() || form.contact_person_email.trim(),
      initial_admin_password: form.initial_admin_password || undefined,
      initial_admin_designation: form.initial_admin_designation || "College Administrator",
    };

    const res = await registrationService.submitRegistration(payload);
    setLoading(false);

    if (res.success && res.data) {
      setSubmittedData({
        tracking_code: res.data.tracking_code,
        college_name: res.data.college_name,
        slug: res.data.slug,
        domain: res.data.official_domain,
        contact_person_email: res.data.contact_person_email,
      });
    } else {
      setError(res.error || "Failed to submit registration. Please check your inputs.");
    }
  };

  const copyCode = () => {
    if (submittedData?.tracking_code) {
      navigator.clipboard.writeText(submittedData.tracking_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] py-12 px-4 sm:px-6 lg:px-8 bg-[#0B0B0D]">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/30 text-[#818CF8] text-xs font-medium mb-3">
            <Shield className="h-3.5 w-3.5" />
            Institutional Partner Onboarding
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5] tracking-tight">
            Register Your College Institution
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-2 max-w-xl mx-auto">
            Provide official institutional details to set up your verified AI Campus Chatbot with domain-grounded knowledge.
          </p>
        </div>

        {/* Success Modal */}
        {submittedData && (
          <div className="p-8 rounded-2xl border border-[#10B981]/40 bg-[#111114] shadow-2xl space-y-6 text-center">
            <div className="h-14 w-14 rounded-2xl bg-[#10B981]/20 flex items-center justify-center text-[#10B981] mx-auto">
              <CheckCircle2 className="h-8 w-8" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-[#F5F5F5]">Application Submitted for Review</h2>
              <p className="text-xs text-[#A1A1AA] mt-1.5 max-w-md mx-auto">
                Your institution <span className="text-white font-medium">{submittedData.college_name}</span> is now entered into the Super Admin verification queue.
              </p>
            </div>

            {/* Tracking Code Box */}
            <div className="p-4 rounded-xl bg-[#1F1F23] border border-[#2A2A30] max-w-sm mx-auto flex items-center justify-between">
              <div className="text-left">
                <div className="text-[10px] text-[#A1A1AA] uppercase font-semibold">Your Tracking Code</div>
                <div className="text-base font-mono font-bold text-[#6366F1]">{submittedData.tracking_code}</div>
              </div>
              <button
                type="button"
                onClick={copyCode}
                className="p-2 rounded-lg bg-[#2A2A30] hover:bg-[#3F3F46] text-white transition flex items-center gap-1 text-xs"
                title="Copy code"
              >
                {copiedCode ? <Check className="h-4 w-4 text-[#10B981]" /> : <Copy className="h-4 w-4" />}
                <span>{copiedCode ? "Copied" : "Copy"}</span>
              </button>
            </div>

            <p className="text-xs text-[#A1A1AA]/80 max-w-md mx-auto">
              Save this tracking code to check your verification status, view reviewer comments, or provide additional documentation.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
              <Link
                href={`/registration-status?code=${submittedData.tracking_code}`}
                className="px-5 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition flex items-center justify-center gap-1.5 shadow-lg shadow-[#6366F1]/20"
              >
                <Clock className="h-4 w-4" />
                Track Application Status
              </Link>
              <Link
                href="/"
                className="px-5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] text-xs font-medium transition flex items-center justify-center"
              >
                Back to Homepage
              </Link>
            </div>
          </div>
        )}

        {/* Multi-step Registration Form */}
        {!submittedData && (
          <div className="rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-xl overflow-hidden">
            {/* Step Progress Bar */}
            <div className="grid grid-cols-4 border-b border-[#2A2A30] text-xs">
              {[
                { num: 1, label: "Institution Profile", icon: Building2 },
                { num: 2, label: "Campus Location", icon: MapPin },
                { num: 3, label: "Accreditation", icon: Award },
                { num: 4, label: "Administrator", icon: UserCheck },
              ].map(({ num, label, icon: Icon }) => (
                <div
                  key={num}
                  className={`p-3.5 flex items-center justify-center gap-2 border-r last:border-r-0 border-[#2A2A30] transition ${
                    step === num
                      ? "bg-[#1F1F23] text-[#818CF8] font-semibold border-b-2 border-b-[#6366F1]"
                      : step > num
                      ? "text-[#10B981] bg-[#111114]"
                      : "text-[#A1A1AA]/60 bg-[#111114]"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="hidden sm:inline">{label}</span>
                </div>
              ))}
            </div>

            {/* Error Message */}
            {error && (
              <div className="m-6 mb-0 p-3.5 rounded-xl bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6">
              {/* STEP 1: Institution Profile */}
              {step === 1 && (
                <div className="space-y-4">
                  <h3 className="text-base font-semibold text-[#F5F5F5] border-b border-[#2A2A30] pb-2">
                    Step 1: Institutional Profile
                  </h3>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Full Legal College Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={form.college_name}
                      onChange={(e) => handleNameChange(e.target.value)}
                      placeholder="e.g., Ahmedabad Institute of Technology"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        URL Slug Identifier *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.slug}
                        onChange={(e) => updateField("slug", e.target.value.toLowerCase())}
                        placeholder="e.g., ait-ahmedabad"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        College / AISHE Code
                      </label>
                      <input
                        type="text"
                        value={form.college_code}
                        onChange={(e) => updateField("college_code", e.target.value.toUpperCase())}
                        placeholder="e.g., C-12847 or GTU-002"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Official Campus Domain *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.official_domain}
                        onChange={(e) => updateField("official_domain", e.target.value.toLowerCase())}
                        placeholder="e.g., aitindia.in or univ.edu.in"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                      <p className="text-[11px] text-[#A1A1AA]/60 mt-1">Must be the institutional root domain.</p>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Institutional Contact Email *
                      </label>
                      <input
                        type="email"
                        required
                        value={form.official_email}
                        onChange={(e) => updateField("official_email", e.target.value)}
                        placeholder="e.g., info@aitindia.in"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Campus Telephone / Contact Phone
                    </label>
                    <input
                      type="tel"
                      value={form.contact_phone}
                      onChange={(e) => updateField("contact_phone", e.target.value)}
                      placeholder="e.g., +91 79 2630 1111"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Institution Overview / Description
                    </label>
                    <textarea
                      rows={3}
                      value={form.description}
                      onChange={(e) => updateField("description", e.target.value)}
                      placeholder="Brief summary of faculties, academic programs, and campus facilities..."
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1] resize-none"
                    />
                  </div>
                </div>
              )}

              {/* STEP 2: Location */}
              {step === 2 && (
                <div className="space-y-4">
                  <h3 className="text-base font-semibold text-[#F5F5F5] border-b border-[#2A2A30] pb-2">
                    Step 2: Campus Physical Location
                  </h3>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Street Address
                    </label>
                    <textarea
                      rows={2}
                      value={form.address}
                      onChange={(e) => updateField("address", e.target.value)}
                      placeholder="e.g., Near Vasantnagar Township, Gota-Ognaj Road"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1] resize-none"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        City *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.city}
                        onChange={(e) => updateField("city", e.target.value)}
                        placeholder="Ahmedabad"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        State / Province *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.state}
                        onChange={(e) => updateField("state", e.target.value)}
                        placeholder="Gujarat"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Country *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.country}
                        onChange={(e) => updateField("country", e.target.value)}
                        placeholder="India"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: Accreditation & Links */}
              {step === 3 && (
                <div className="space-y-4">
                  <h3 className="text-base font-semibold text-[#F5F5F5] border-b border-[#2A2A30] pb-2">
                    Step 3: Accreditation & Online Presence
                  </h3>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Official Website Homepage URL
                    </label>
                    <input
                      type="url"
                      value={form.website_url}
                      onChange={(e) => updateField("website_url", e.target.value)}
                      placeholder="https://www.aitindia.in"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                    <p className="text-[11px] text-[#A1A1AA]/60 mt-1">
                      Our automated crawler uses this homepage as the base source for public FAQ ingestion.
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Accreditation & Approvals
                    </label>
                    <input
                      type="text"
                      value={form.accreditation_details}
                      onChange={(e) => updateField("accreditation_details", e.target.value)}
                      placeholder="e.g., Approved by AICTE, Affiliated with Gujarat Technological University (GTU)"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Institution Crest / Logo URL
                    </label>
                    <input
                      type="url"
                      value={form.logo_url}
                      onChange={(e) => updateField("logo_url", e.target.value)}
                      placeholder="https://www.aitindia.in/assets/images/logo.png"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>
                </div>
              )}

              {/* STEP 4: Designated Administrator */}
              {step === 4 && (
                <div className="space-y-4">
                  <h3 className="text-base font-semibold text-[#F5F5F5] border-b border-[#2A2A30] pb-2">
                    Step 4: Designated College Administrator
                  </h3>
                  <p className="text-xs text-[#A1A1AA]">
                    These credentials will be activated once the Super Administrator verifies and approves your institution.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Administrator / Registrar Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={form.contact_person_name}
                        onChange={(e) => {
                          updateField("contact_person_name", e.target.value);
                          if (!form.initial_admin_name) updateField("initial_admin_name", e.target.value);
                        }}
                        placeholder="Dr. R. K. Patel"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Designation / Role
                      </label>
                      <input
                        type="text"
                        value={form.initial_admin_designation}
                        onChange={(e) => updateField("initial_admin_designation", e.target.value)}
                        placeholder="Head of Admissions / Registrar"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Administrator Institutional Email *
                    </label>
                    <input
                      type="email"
                      required
                      value={form.contact_person_email}
                      onChange={(e) => {
                        updateField("contact_person_email", e.target.value);
                        if (!form.initial_admin_email) updateField("initial_admin_email", e.target.value);
                      }}
                      placeholder="admin@aitindia.in"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Admin Account Password *
                      </label>
                      <input
                        type="password"
                        required
                        value={form.initial_admin_password}
                        onChange={(e) => updateField("initial_admin_password", e.target.value)}
                        placeholder="Min 8 characters"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Confirm Password *
                      </label>
                      <input
                        type="password"
                        required
                        value={form.admin_password_confirm}
                        onChange={(e) => updateField("admin_password_confirm", e.target.value)}
                        placeholder="Confirm password"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23] text-sm text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation Controls */}
              <div className="flex items-center justify-between pt-4 border-t border-[#2A2A30]">
                {step > 1 ? (
                  <button
                    type="button"
                    onClick={prevStep}
                    className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#111114] text-xs font-medium text-[#A1A1AA] hover:text-white transition flex items-center gap-1.5"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Previous Step
                  </button>
                ) : (
                  <div />
                )}

                {step < 4 ? (
                  <button
                    type="button"
                    onClick={nextStep}
                    className="px-5 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-medium text-white transition flex items-center gap-1.5 shadow-md shadow-[#6366F1]/20"
                  >
                    Next Step
                    <ArrowRight className="h-4 w-4" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-medium text-white transition flex items-center gap-2 shadow-lg shadow-[#6366F1]/30 disabled:opacity-50"
                  >
                    {loading ? (
                      <span>Submitting Application...</span>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        <span>Submit Registration</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </form>
          </div>
        )}

        {/* Existing applicant tracker reminder */}
        <div className="text-center mt-8 text-xs text-[#A1A1AA]">
          Already submitted a registration?{" "}
          <Link href="/registration-status" className="text-[#818CF8] hover:underline font-medium">
            Check your application review status &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}

