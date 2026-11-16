"use client";

import { useState } from "react";
import Link from "next/link";
import { adminApiRequest } from "@/lib/api-client";
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
} from "lucide-react";

interface OnboardingFormData {
  // Step 1: Institution Profile
  name: string;
  slug: string;
  official_domain: string;
  contact_email: string;
  contact_phone: string;

  // Step 2: Location
  address: string;
  city: string;
  state: string;
  country: string;

  // Step 3: Accreditation & Links
  accreditation_details: string;
  website_url: string;
  logo_url: string;

  // Step 4: Designated Administrator
  admin_name: string;
  admin_email: string;
  admin_designation: string;
}

const INITIAL_FORM: OnboardingFormData = {
  name: "",
  slug: "",
  official_domain: "",
  contact_email: "",
  contact_phone: "",
  address: "",
  city: "Ahmedabad",
  state: "Gujarat",
  country: "India",
  accreditation_details: "AICTE Approved, NAAC Accredited",
  website_url: "",
  logo_url: "",
  admin_name: "",
  admin_email: "",
  admin_designation: "College Administrator",
};

export default function RegisterCollegePage() {
  const [step, setStep] = useState<number>(1);
  const [formData, setFormData] = useState<OnboardingFormData>(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedData, setSubmittedData] = useState<{
    tracking_code: string;
    college_name: string;
    slug: string;
    domain: string;
    admin_email: string;
    submitted_at: string;
  } | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);

  // Auto-generate slug and website suggestions from name
  const handleNameChange = (val: string) => {
    const slugified = val
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    setFormData((prev) => ({
      ...prev,
      name: val,
      slug: prev.slug === "" || prev.slug === prev.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")
        ? slugified
        : prev.slug,
    }));
  };

  const updateField = (field: keyof OnboardingFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const validateStep = (s: number): boolean => {
    setError(null);
    if (s === 1) {
      if (!formData.name.trim() || formData.name.length < 3) {
        setError("Please enter the full formal name of the institution (min 3 characters).");
        return false;
      }
      if (!formData.slug.trim() || !/^[a-z0-9-]+$/.test(formData.slug)) {
        setError("Institution slug must contain only lowercase letters, numbers, and hyphens.");
        return false;
      }
      if (!formData.official_domain.trim() || !formData.official_domain.includes(".")) {
        setError("Please provide a valid official domain (e.g., college.edu.in or univ.ac.in).");
        return false;
      }
      const genericDomains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"];
      if (genericDomains.some((d) => formData.official_domain.toLowerCase().includes(d))) {
        setError("The official domain must be an institutional domain, not a public email provider.");
        return false;
      }
      if (!formData.contact_email.trim() || !formData.contact_email.includes("@")) {
        setError("Please enter a valid official contact email address.");
        return false;
      }
    } else if (s === 2) {
      if (!formData.city.trim() || !formData.state.trim()) {
        setError("City and State are required fields.");
        return false;
      }
    } else if (s === 4) {
      if (!formData.admin_name.trim() || formData.admin_name.length < 2) {
        setError("Please enter the administrator's full name.");
        return false;
      }
      if (!formData.admin_email.trim() || !formData.admin_email.includes("@")) {
        setError("Please enter a valid administrator email address.");
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

    const payload = {
      name: formData.name.trim(),
      slug: formData.slug.trim().toLowerCase(),
      official_domain: formData.official_domain.trim().toLowerCase(),
      contact_email: formData.contact_email.trim().toLowerCase(),
      contact_phone: formData.contact_phone.trim() || null,
      address: formData.address.trim() || null,
      city: formData.city.trim() || null,
      state: formData.state.trim() || null,
      country: formData.country.trim() || "India",
      accreditation_details: formData.accreditation_details.trim() || null,
      website_url: formData.website_url.trim() || null,
      logo_url: formData.logo_url.trim() || null,
      admin_name: formData.admin_name.trim(),
      admin_email: formData.admin_email.trim().toLowerCase(),
      admin_designation: formData.admin_designation.trim() || "College Administrator",
    };

    try {
      const res = await adminApiRequest<{
        college_id: string;
        college_name: string;
        college_slug: string;
        official_domain: string;
        admin_email: string;
        status: string;
        tracking_code: string;
        submitted_at: string;
      }>("/colleges/onboarding/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.success || !res.data) {
        setError(res.error || "The registration could not be submitted. Please try again.");
        return;
      }

      setSubmittedData({
        tracking_code: res.data.tracking_code,
        college_name: res.data.college_name,
        slug: res.data.college_slug,
        domain: res.data.official_domain,
        admin_email: res.data.admin_email,
        submitted_at: res.data.submitted_at,
      });
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "The registration could not be submitted. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const copyTrackingCode = () => {
    if (submittedData) {
      navigator.clipboard.writeText(submittedData.tracking_code);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0B0D] py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
      <div className="w-full max-w-2xl">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-2xl bg-[#6366F1]/10 border border-[#6366F1]/30 items-center justify-center text-[#6366F1] mb-3">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#F5F5F5]">
            College Institutional Onboarding
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1 max-w-md mx-auto">
            Apply to integrate your college with CampusAI for verified student assistance, official website crawling, and human-in-the-loop knowledge review.
          </p>
        </div>

        {/* Confirmation Screen */}
        {submittedData ? (
          <div className="p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl text-center">
            <div className="h-16 w-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-4">
              <CheckCircle2 className="h-8 w-8" />
            </div>

            <h2 className="text-xl font-bold text-[#F5F5F5] mb-2">
              Application Submitted Successfully!
            </h2>
            <p className="text-xs text-[#A1A1AA] max-w-md mx-auto mb-6">
              Your onboarding request for <span className="text-[#F5F5F5] font-semibold">{submittedData.college_name}</span> has been received and is queued for verification by platform administrators.
            </p>

            {/* Tracking Code Box */}
            <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23] max-w-md mx-auto mb-6 flex items-center justify-between">
              <div className="text-left">
                <div className="text-[10px] text-[#A1A1AA] uppercase tracking-wider font-semibold">
                  Application Tracking Code
                </div>
                <div className="text-sm font-mono font-bold text-[#6366F1]">
                  {submittedData.tracking_code}
                </div>
              </div>
              <button
                type="button"
                onClick={copyTrackingCode}
                className="p-2 rounded-lg bg-[#2A2A30] hover:bg-[#3F3F46] text-[#F5F5F5] text-xs flex items-center gap-1.5 transition cursor-pointer"
                title="Copy tracking code"
              >
                {copiedCode ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copiedCode ? "Copied" : "Copy"}</span>
              </button>
            </div>

            {/* Summary Details */}
            <div className="grid grid-cols-2 gap-3 text-left max-w-md mx-auto p-4 rounded-xl bg-[#1F1F23]/40 border border-[#2A2A30]/50 text-xs mb-6">
              <div>
                <span className="text-[#A1A1AA] text-[11px]">Domain:</span>
                <p className="text-[#F5F5F5] font-medium">{submittedData.domain}</p>
              </div>
              <div>
                <span className="text-[#A1A1AA] text-[11px]">Status:</span>
                <p className="text-amber-400 font-semibold">PENDING REVIEW</p>
              </div>
              <div className="col-span-2">
                <span className="text-[#A1A1AA] text-[11px]">Designated Admin Email:</span>
                <p className="text-[#F5F5F5] font-medium">{submittedData.admin_email}</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
              <Link
                href={`/registration-status?query=${submittedData.tracking_code}`}
                className="py-2.5 px-4 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-semibold flex items-center justify-center gap-2 transition shadow-lg shadow-[#6366F1]/20"
              >
                <span>Track Application Status</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </Link>
              <Link
                href="/login"
                className="py-2.5 px-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#F5F5F5] text-xs font-medium flex items-center justify-center transition"
              >
                Return to Admin Login
              </Link>
            </div>
          </div>
        ) : (
          <div className="p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-2xl">
            {/* Step Progress Indicator */}
            <div className="flex items-center justify-between mb-8 pb-6 border-b border-[#2A2A30]">
              {[
                { s: 1, label: "Institution", icon: Building2 },
                { s: 2, label: "Location", icon: MapPin },
                { s: 3, label: "Accreditation", icon: Award },
                { s: 4, label: "Administrator", icon: UserCheck },
              ].map(({ s, label, icon: Icon }) => (
                <div key={s} className="flex flex-col items-center">
                  <div
                    className={`h-9 w-9 rounded-full flex items-center justify-center text-xs font-semibold transition ${
                      step === s
                        ? "bg-[#6366F1] text-white ring-4 ring-[#6366F1]/20 shadow-lg shadow-[#6366F1]/30"
                        : step > s
                        ? "bg-emerald-500 text-white"
                        : "bg-[#1F1F23] text-[#A1A1AA] border border-[#2A2A30]"
                    }`}
                  >
                    {step > s ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                  </div>
                  <span
                    className={`text-[11px] mt-1.5 font-medium ${
                      step === s ? "text-[#F5F5F5]" : "text-[#A1A1AA]"
                    }`}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </div>

            {/* Error Notification */}
            {error && (
              <div className="flex items-center gap-2 p-3 mb-6 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-[#EF4444] text-xs">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {/* STEP 1: Institution Profile */}
              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Formal Institution Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => handleNameChange(e.target.value)}
                      placeholder="e.g. Gujarat Technological University"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        URL Slug / Code *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.slug}
                        onChange={(e) => updateField("slug", e.target.value)}
                        placeholder="gtu-ahmedabad"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs font-mono focus:outline-none focus:border-[#6366F1] transition"
                      />
                      <span className="text-[10px] text-[#A1A1AA]/70 mt-1 block">
                        Unique URL: campusai.edu/{formData.slug || "slug"}
                      </span>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Official Domain *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.official_domain}
                        onChange={(e) => updateField("official_domain", e.target.value)}
                        placeholder="gtu.ac.in"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs font-mono focus:outline-none focus:border-[#6366F1] transition"
                      />
                      <span className="text-[10px] text-[#A1A1AA]/70 mt-1 block">
                        Must match institutional domain
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Official Contact Email *
                      </label>
                      <input
                        type="email"
                        required
                        value={formData.contact_email}
                        onChange={(e) => updateField("contact_email", e.target.value)}
                        placeholder="admissions@gtu.ac.in"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Contact Telephone
                      </label>
                      <input
                        type="tel"
                        value={formData.contact_phone}
                        onChange={(e) => updateField("contact_phone", e.target.value)}
                        placeholder="+91-79-23267521"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: Campus Location */}
              {step === 2 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Campus Physical Address
                    </label>
                    <textarea
                      rows={2}
                      value={formData.address}
                      onChange={(e) => updateField("address", e.target.value)}
                      placeholder="Nr. Vishwakarma Government Engineering College, Chandkheda"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition resize-none"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">City *</label>
                      <input
                        type="text"
                        required
                        value={formData.city}
                        onChange={(e) => updateField("city", e.target.value)}
                        placeholder="Ahmedabad"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">State *</label>
                      <input
                        type="text"
                        required
                        value={formData.state}
                        onChange={(e) => updateField("state", e.target.value)}
                        placeholder="Gujarat"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">Country</label>
                      <input
                        type="text"
                        value={formData.country}
                        onChange={(e) => updateField("country", e.target.value)}
                        placeholder="India"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: Accreditation & Online Presence */}
              {step === 3 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Accreditation & Approvals
                    </label>
                    <input
                      type="text"
                      value={formData.accreditation_details}
                      onChange={(e) => updateField("accreditation_details", e.target.value)}
                      placeholder="e.g. NAAC A++, NBA Accredited, AICTE Approved, NIRF Top 100"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Primary Website Homepage URL
                    </label>
                    <input
                      type="url"
                      value={formData.website_url}
                      onChange={(e) => updateField("website_url", e.target.value)}
                      placeholder="https://www.gtu.ac.in"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                      Institution Logo or Crest URL (Optional)
                    </label>
                    <input
                      type="url"
                      value={formData.logo_url}
                      onChange={(e) => updateField("logo_url", e.target.value)}
                      placeholder="https://www.gtu.ac.in/images/logo.png"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                    />
                  </div>
                </div>
              )}

              {/* STEP 4: Designated Administrator */}
              {step === 4 && (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-[#6366F1]/10 border border-[#6366F1]/20 text-[11px] text-[#A1A1AA] leading-relaxed">
                    This designated administrator will manage the college website crawler, upload brochures, and approve AI answers once the institution is verified.
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Administrator Full Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={formData.admin_name}
                        onChange={(e) => updateField("admin_name", e.target.value)}
                        placeholder="Dr. Rajesh Patel"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Designation
                      </label>
                      <input
                        type="text"
                        value={formData.admin_designation}
                        onChange={(e) => updateField("admin_designation", e.target.value)}
                        placeholder="Dean of Academics / IT Director"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                        Official Work Email *
                      </label>
                      <input
                        type="email"
                        required
                        value={formData.admin_email}
                        onChange={(e) => updateField("admin_email", e.target.value)}
                        placeholder="admin@gtu.ac.in"
                        className="w-full px-3.5 py-2.5 rounded-lg bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] placeholder-[#A1A1AA]/50 text-xs focus:outline-none focus:border-[#6366F1] transition"
                      />
                    </div>

                  </div>
                  <p className="text-xs text-[#A1A1AA] mt-3">
                    The designated administrator will receive a one-time activation invitation only after the college is approved.
                  </p>
                </div>
              )}

              {/* Navigation Controls */}
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-[#2A2A30]">
                {step > 1 ? (
                  <button
                    type="button"
                    onClick={prevStep}
                    className="py-2.5 px-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[#F5F5F5] text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    <span>Previous</span>
                  </button>
                ) : (
                  <Link
                    href="/login"
                    className="text-xs text-[#A1A1AA] hover:text-[#F5F5F5] transition"
                  >
                    Back to Admin Sign In
                  </Link>
                )}

                {step < 4 ? (
                  <button
                    type="button"
                    onClick={nextStep}
                    className="py-2.5 px-5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-[#6366F1]/20 cursor-pointer ml-auto"
                  >
                    <span>Continue</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={loading}
                    className="py-2.5 px-6 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-emerald-600/20 disabled:opacity-50 cursor-pointer ml-auto"
                  >
                    {loading ? "Submitting Application..." : "Submit Onboarding Application"}
                    <CheckCircle2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </form>
          </div>
        )}

        {/* Footer Tracker Link */}
        <div className="mt-6 text-center text-xs text-[#A1A1AA]">
          Already submitted an application?{" "}
          <Link href="/registration-status" className="text-[#6366F1] hover:underline font-medium">
            Check Application Status
          </Link>
        </div>
      </div>
    </div>
  );
}

