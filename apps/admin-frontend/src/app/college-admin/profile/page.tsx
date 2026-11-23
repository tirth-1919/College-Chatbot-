"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { CollegeProfile, ProfileHistoryItem } from "@/types/college-admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Building2,
  Shield,
  Globe,
  Mail,
  Phone,
  MapPin,
  Award,
  FileText,
  Users,
  Share2,
  Palette,
  Save,
  CheckCircle,
  AlertCircle,
  Eye,
  History,
  UploadCloud,
  X,
  ExternalLink,
  Lock,
  Clock,
  RefreshCw,
  Trash2,
  Calendar,
  Compass,
  FileCheck,
} from "lucide-react";

interface ProfileFormData {
  // 1. Identity
  name: string;
  short_name: string;
  institution_type: string;
  established_year: string;
  website_url: string;
  official_domain: string;
  logo_url: string;
  cover_image_url: string;

  // 2. Address & Location
  address_line1: string;
  address_line2: string;
  city: string;
  district: string;
  state: string;
  country: string;
  postal_code: string;
  maps_url: string;
  latitude: string;
  longitude: string;

  // 3. Official Contacts
  contact_email: string;
  contact_phone: string;
  admission_email: string;
  examination_email: string;
  placement_email: string;
  admission_helpline: string;
  alternate_phone: string;
  working_hours: string;

  // 4. Recognition & Accreditation
  affiliated_university: string;
  recognized_by: string;
  aicte_approval: string;
  ugc_recognition: string;
  naac_grade: string;
  nba_accreditation: string;
  accreditation_validity: string;
  approval_document_url: string;

  // 5. About Institution
  short_description: string;
  about_text: string;
  vision: string;
  mission: string;

  // 6. Leadership
  leader_name: string;
  leader_designation: string;

  // 7. Social Media
  linkedin_url: string;
  instagram_url: string;
  facebook_url: string;
  youtube_url: string;
  twitter_url: string;

  // 8. Branding
  favicon_url: string;
  primary_brand_color: string;
  secondary_brand_color: string;
}

const INITIAL_FORM: ProfileFormData = {
  name: "",
  short_name: "",
  institution_type: "Autonomous College",
  established_year: "",
  website_url: "",
  official_domain: "",
  logo_url: "",
  cover_image_url: "",

  address_line1: "",
  address_line2: "",
  city: "",
  district: "",
  state: "",
  country: "India",
  postal_code: "",
  maps_url: "",
  latitude: "",
  longitude: "",

  contact_email: "",
  contact_phone: "",
  admission_email: "",
  examination_email: "",
  placement_email: "",
  admission_helpline: "",
  alternate_phone: "",
  working_hours: "",

  affiliated_university: "",
  recognized_by: "",
  aicte_approval: "",
  ugc_recognition: "",
  naac_grade: "A+",
  nba_accreditation: "",
  accreditation_validity: "",
  approval_document_url: "",

  short_description: "",
  about_text: "",
  vision: "",
  mission: "",

  leader_name: "",
  leader_designation: "Principal / Director",

  linkedin_url: "",
  instagram_url: "",
  facebook_url: "",
  youtube_url: "",
  twitter_url: "",

  favicon_url: "",
  primary_brand_color: "#10B981",
  secondary_brand_color: "#6366F1",
};

const PROFILE_STEPS = [
  { title: "Institution", description: "Name, website, and profile photo" },
  { title: "Location & Contacts", description: "Address and contact details" },
  { title: "Recognition & About", description: "Accreditation and college overview" },
  { title: "Leadership & Social", description: "Leadership and social links" },
] as const;

export default function CollegeProfilePage() {
  const [profile, setProfile] = useState<CollegeProfile | null>(null);
  const [formData, setFormData] = useState<ProfileFormData>(INITIAL_FORM);
  const [originalData, setOriginalData] = useState<ProfileFormData>(INITIAL_FORM);
  const [hasDraft, setHasDraft] = useState(false);
  const [draftTimestamp, setDraftTimestamp] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDraftSaving, setIsDraftSaving] = useState(false);
  const [uploadingField, setUploadingField] = useState<string | null>(null);

  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modals
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyItems, setHistoryItems] = useState<ProfileHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // File input refs for image upload
  const logoInputRef = useRef<HTMLInputElement>(null);
  const coverInputRef = useRef<HTMLInputElement>(null);
  const faviconInputRef = useRef<HTMLInputElement>(null);
  const approvalDocInputRef = useRef<HTMLInputElement>(null);

  const profileToFormData = (data: CollegeProfile): ProfileFormData => ({
    name: data.name || "",
    short_name: data.short_name || "",
    institution_type: data.institution_type || "Autonomous College",
    established_year: data.established_year ? String(data.established_year) : "",
    website_url: data.website_url || "",
    official_domain: data.official_domain || "",
    logo_url: data.logo_url || "",
    cover_image_url: data.cover_image_url || "",

    address_line1: data.address_line1 || "",
    address_line2: data.address_line2 || "",
    city: data.city || "",
    district: data.district || "",
    state: data.state || "",
    country: data.country || "India",
    postal_code: data.postal_code || "",
    maps_url: data.maps_url || "",
    latitude: data.latitude !== null && data.latitude !== undefined ? String(data.latitude) : "",
    longitude: data.longitude !== null && data.longitude !== undefined ? String(data.longitude) : "",

    contact_email: data.contact_email || "",
    contact_phone: data.contact_phone || "",
    admission_email: data.admission_email || "",
    examination_email: data.examination_email || "",
    placement_email: data.placement_email || "",
    admission_helpline: data.admission_helpline || "",
    alternate_phone: data.alternate_phone || "",
    working_hours: data.working_hours || "",

    affiliated_university: data.affiliated_university || "",
    recognized_by: data.recognized_by || "",
    aicte_approval: data.aicte_approval || "",
    ugc_recognition: data.ugc_recognition || "",
    naac_grade: data.naac_grade || "A+",
    nba_accreditation: data.nba_accreditation || "",
    accreditation_validity: data.accreditation_validity || "",
    approval_document_url: data.approval_document_url || "",

    short_description: data.short_description || "",
    about_text: data.about_text || "",
    vision: data.vision || "",
    mission: data.mission || "",

    leader_name: data.leader_name || "",
    leader_designation: data.leader_designation || "Principal / Director",

    linkedin_url: data.linkedin_url || "",
    instagram_url: data.instagram_url || "",
    facebook_url: data.facebook_url || "",
    youtube_url: data.youtube_url || "",
    twitter_url: data.twitter_url || "",

    favicon_url: data.favicon_url || "",
    primary_brand_color: data.primary_brand_color || "#10B981",
    secondary_brand_color: data.secondary_brand_color || "#6366F1",
  });

  const fetchProfile = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getProfile();
      if (res.success && res.data) {
        setProfile(res.data);
        const parsed = profileToFormData(res.data);
        setFormData(parsed);
        setOriginalData(parsed);

        // Check if draft exists
        if (res.data.draft_profile && Object.keys(res.data.draft_profile).length > 0) {
          setHasDraft(true);
          setDraftTimestamp(res.data.draft_profile._saved_at || null);
        } else {
          setHasDraft(false);
        }
      }
    } catch (err) {
      console.error("Failed to load profile:", err);
      setErrorMsg("Failed to load institutional profile. Please check network connectivity.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  // Completion calculation
  const completion = useMemo(() => {
    const fields = [
      { key: "name", label: "Institution Name", weight: 8, filled: !!formData.name.trim() },
      { key: "official_domain", label: "Official Domain", weight: 8, filled: !!formData.official_domain.trim() },
      { key: "contact_email", label: "Contact Email", weight: 8, filled: !!formData.contact_email.trim() },
      { key: "contact_phone", label: "Official Phone", weight: 5, filled: !!formData.contact_phone.trim() },
      { key: "logo_url", label: "College Profile Photo", weight: 6, filled: !!formData.logo_url.trim() },
      { key: "cover_image_url", label: "Cover Image", weight: 5, filled: !!formData.cover_image_url.trim() },
      { key: "institution_type", label: "Institution Type", weight: 4, filled: !!formData.institution_type.trim() },
      { key: "established_year", label: "Established Year", weight: 4, filled: !!formData.established_year.trim() },
      { key: "website_url", label: "Official Website", weight: 4, filled: !!formData.website_url.trim() },
      { key: "city", label: "City", weight: 5, filled: !!formData.city.trim() },
      { key: "state", label: "State", weight: 5, filled: !!formData.state.trim() },
      { key: "postal_code", label: "Postal PIN Code", weight: 4, filled: !!formData.postal_code.trim() },
      { key: "maps_url", label: "Google Maps URL", weight: 3, filled: !!formData.maps_url.trim() },
      { key: "admission_email", label: "Admission Email", weight: 4, filled: !!formData.admission_email.trim() },
      { key: "working_hours", label: "Office Hours", weight: 3, filled: !!formData.working_hours.trim() },
      { key: "affiliated_university", label: "Affiliated University", weight: 4, filled: !!formData.affiliated_university.trim() },
      { key: "naac_grade", label: "NAAC Grade", weight: 4, filled: !!formData.naac_grade.trim() },
      { key: "short_description", label: "Short Description", weight: 4, filled: !!formData.short_description.trim() },
      { key: "about_text", label: "About Text", weight: 4, filled: !!formData.about_text.trim() },
      { key: "vision", label: "Vision", weight: 3, filled: !!formData.vision.trim() },
      { key: "mission", label: "Mission", weight: 3, filled: !!formData.mission.trim() },
      { key: "leader_name", label: "Principal/Director", weight: 4, filled: !!formData.leader_name.trim() },
    ];

    const totalWeight = fields.reduce((sum, f) => sum + f.weight, 0);
    const completedWeight = fields.filter((f) => f.filled).reduce((sum, f) => sum + f.weight, 0);
    const percentage = Math.round((completedWeight / totalWeight) * 100);

    return { percentage, fields };
  }, [formData]);

  // Form field updater helper
  const handleChange = (field: keyof ProfileFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleNextStep = () => {
    setErrorMsg(null);
    setSuccessMsg(null);

    if (activeStep === 0 && !formData.name.trim()) {
      setErrorMsg("Institution Legal Name is required before continuing.");
      return;
    }
    if (activeStep === 0 && !formData.official_domain.trim()) {
      setErrorMsg("Official Institutional Domain is required before continuing.");
      return;
    }
    if (activeStep === 1 && !formData.contact_email.trim()) {
      setErrorMsg("Official Contact Email is required before continuing.");
      return;
    }
    if (activeStep === 1 && !/^\S+@\S+\.\S+$/.test(formData.contact_email.trim())) {
      setErrorMsg("Enter a valid Official Contact Email before continuing.");
      return;
    }

    setActiveStep((current) => Math.min(current + 1, PROFILE_STEPS.length - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handlePreviousStep = () => {
    setErrorMsg(null);
    setActiveStep((current) => Math.max(current - 1, 0));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleWizardSubmit = (e: React.FormEvent) => {
    if (activeStep < PROFILE_STEPS.length - 1) {
      e.preventDefault();
      handleNextStep();
      return;
    }
    void handleSubmit(e);
  };

  // Secure Image / Asset Upload Handler
  const handleFileUpload = async (
    e: React.ChangeEvent<HTMLInputElement>,
    assetType: "logo" | "cover" | "favicon" | "approval_document",
    targetField: keyof ProfileFormData
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side quick check
    const isDoc = assetType === "approval_document";
    const maxMb = isDoc ? 10 : 5;
    if (file.size > maxMb * 1024 * 1024) {
      setErrorMsg(`File size exceeds the ${maxMb} MB limit.`);
      return;
    }

    setUploadingField(targetField);
    setErrorMsg(null);

    try {
      const res = await collegeAdminService.uploadProfileAsset(file, assetType);
      const uploadedData = res.data;
      if (res.success && uploadedData) {
        setFormData((prev) => ({ ...prev, [targetField]: uploadedData.asset_url }));
        setSuccessMsg(assetType === "logo" ? "College profile photo uploaded and preview updated." : `${assetType.replace("_", " ").toUpperCase()} uploaded successfully.`);
        setTimeout(() => setSuccessMsg(null), 3500);
      } else {
        setErrorMsg(res.error || "Upload failed. Please verify the file format.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Upload failed.");
    } finally {
      setUploadingField(null);
      e.target.value = "";
    }
  };

  // Form Save (Publish Changes)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Required Field Validation
    if (!formData.name.trim()) {
      setErrorMsg("Institution Legal Name is required.");
      return;
    }
    if (!formData.official_domain.trim()) {
      setErrorMsg("Official Institutional Domain is required.");
      return;
    }
    if (!formData.contact_email.trim()) {
      setErrorMsg("Official Contact Email is required.");
      return;
    }

    setIsSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const payload: Partial<CollegeProfile> = {
        name: formData.name.trim(),
        short_name: formData.short_name.trim() || null,
        institution_type: formData.institution_type.trim() || null,
        established_year: formData.established_year ? parseInt(formData.established_year, 10) : null,
        website_url: formData.website_url.trim() || null,
        official_domain: formData.official_domain.trim(),
        logo_url: formData.logo_url.trim() || null,
        cover_image_url: formData.cover_image_url.trim() || null,

        address_line1: formData.address_line1.trim() || null,
        address_line2: formData.address_line2.trim() || null,
        city: formData.city.trim() || null,
        district: formData.district.trim() || null,
        state: formData.state.trim() || null,
        country: formData.country.trim() || "India",
        postal_code: formData.postal_code.trim() || null,
        maps_url: formData.maps_url.trim() || null,
        latitude: formData.latitude ? parseFloat(formData.latitude) : null,
        longitude: formData.longitude ? parseFloat(formData.longitude) : null,

        contact_email: formData.contact_email.trim(),
        contact_phone: formData.contact_phone.trim() || null,
        admission_email: formData.admission_email.trim() || null,
        examination_email: formData.examination_email.trim() || null,
        placement_email: formData.placement_email.trim() || null,
        admission_helpline: formData.admission_helpline.trim() || null,
        alternate_phone: formData.alternate_phone.trim() || null,
        working_hours: formData.working_hours.trim() || null,

        affiliated_university: formData.affiliated_university.trim() || null,
        recognized_by: formData.recognized_by.trim() || null,
        aicte_approval: formData.aicte_approval.trim() || null,
        ugc_recognition: formData.ugc_recognition.trim() || null,
        naac_grade: formData.naac_grade.trim() || null,
        nba_accreditation: formData.nba_accreditation.trim() || null,
        accreditation_validity: formData.accreditation_validity.trim() || null,
        approval_document_url: formData.approval_document_url.trim() || null,

        short_description: formData.short_description.trim() || null,
        about_text: formData.about_text.trim() || null,
        vision: formData.vision.trim() || null,
        mission: formData.mission.trim() || null,

        leader_name: formData.leader_name.trim() || null,
        leader_designation: formData.leader_designation.trim() || null,

        linkedin_url: formData.linkedin_url.trim() || null,
        instagram_url: formData.instagram_url.trim() || null,
        facebook_url: formData.facebook_url.trim() || null,
        youtube_url: formData.youtube_url.trim() || null,
        twitter_url: formData.twitter_url.trim() || null,

        favicon_url: formData.favicon_url.trim() || null,
        primary_brand_color: formData.primary_brand_color.trim() || null,
        secondary_brand_color: formData.secondary_brand_color.trim() || null,
      };

      const res = await collegeAdminService.updateProfile(payload);
      if (res.success && res.data) {
        setProfile(res.data);
        const parsed = profileToFormData(res.data);
        setFormData(parsed);
        setOriginalData(parsed);

        // If a draft was saved, discard it since changes are now live
        if (hasDraft) {
          await collegeAdminService.deleteDraft();
          setHasDraft(false);
          setDraftTimestamp(null);
        }

        setSuccessMsg("Institutional Profile successfully updated and published to live knowledge scope!");
        setTimeout(() => setSuccessMsg(null), 5000);
      } else {
        setErrorMsg(res.error || "Failed to save profile changes.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected error occurred while saving profile.");
    } finally {
      setIsSaving(false);
    }
  };

  // Save Draft
  const handleSaveDraft = async () => {
    setIsDraftSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const draftPayload = {
        ...formData,
        _saved_at: new Date().toISOString(),
      };
      const res = await collegeAdminService.saveDraft(draftPayload);
      if (res.success) {
        setHasDraft(true);
        setDraftTimestamp(draftPayload._saved_at);
        setSuccessMsg("Profile draft saved successfully! Changes are held private until you click 'Save Changes'.");
        setTimeout(() => setSuccessMsg(null), 4000);
      } else {
        setErrorMsg(res.error || "Failed to save draft.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save draft.");
    } finally {
      setIsDraftSaving(false);
    }
  };

  // Restore Draft
  const handleRestoreDraft = () => {
    if (profile?.draft_profile) {
      const draft = profile.draft_profile;
      setFormData((prev) => ({
        ...prev,
        ...draft,
      }));
      setSuccessMsg("Draft values restored into editing form.");
      setTimeout(() => setSuccessMsg(null), 3000);
    }
  };

  // Discard Draft
  const handleDiscardDraft = async () => {
    if (!confirm("Are you sure you want to discard your uncommitted draft? This cannot be undone.")) {
      return;
    }
    try {
      await collegeAdminService.deleteDraft();
      setHasDraft(false);
      setDraftTimestamp(null);
      setFormData(originalData);
      setSuccessMsg("Draft discarded. Restored published profile data.");
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to discard draft.");
    }
  };

  // Reset Changes (Cancel)
  const handleCancel = () => {
    setFormData(originalData);
    setActiveStep(0);
    setSuccessMsg("Changes cancelled. Restored published values.");
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  // Fetch History
  const handleOpenHistory = async () => {
    setShowHistoryModal(true);
    setHistoryLoading(true);
    try {
      const res = await collegeAdminService.getProfileHistory(25);
      if (res.success && res.data) {
        setHistoryItems(res.data);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-xs text-[#A1A1AA] dark:text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-[#10B981] border-t-transparent rounded-full animate-spin" />
          <span className="font-medium">Loading Institutional Profile Management System...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-16 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[#2A2A30] dark:border-[#2A2A30] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-[#10B981]/10 text-[#10B981]">
              <Building2 className="h-5 w-5" />
            </span>
            <h1 className="text-xl font-bold text-[#F5F5F5] dark:text-[#F5F5F5] tracking-tight">
              College Profile & Institutional Metadata
            </h1>
          </div>
          <p className="text-xs text-[#A1A1AA] dark:text-[#A1A1AA] mt-1">
            Enterprise institutional management: official identity, accredited rankings, contacts, and public branding.
          </p>
        </div>

        {/* Global Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={handleOpenHistory}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#2A2A30] bg-[#111114] hover:bg-[#1F1F23] text-xs font-medium text-[#F5F5F5] transition"
          >
            <History className="h-3.5 w-3.5 text-[#A1A1AA]" />
            Change History
          </button>

          <button
            type="button"
            onClick={() => setShowPreviewModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#2A2A30] bg-[#111114] hover:bg-[#1F1F23] text-xs font-medium text-[#F5F5F5] transition"
          >
            <Eye className="h-3.5 w-3.5 text-[#10B981]" />
            Preview Public Profile
          </button>

          <button
            type="button"
            onClick={handleSaveDraft}
            disabled={isDraftSaving}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#F5F5F5] transition disabled:opacity-50"
          >
            {isDraftSaving ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5 text-[#6366F1]" />}
            Save Draft
          </button>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-xs font-semibold text-white shadow-lg shadow-[#10B981]/20 transition disabled:opacity-50"
          >
            {isSaving ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
            Save Changes
          </button>
        </div>
      </div>

      {/* Completion & Draft Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Profile Completion Indicator */}
        <div className="md:col-span-2 p-4 rounded-2xl border border-[#2A2A30] bg-[#111114] flex flex-col justify-between gap-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-[#F5F5F5]">Profile Completion</span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#10B981]/10 text-[#10B981] font-bold">
                {completion.percentage}% Completed
              </span>
            </div>
            {profile?.updated_at && (
              <span className="text-[11px] text-[#A1A1AA] flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Last updated {new Date(profile.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-[#1F1F23] h-2 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-[#10B981] to-[#6366F1] h-full rounded-full transition-all duration-500"
              style={{ width: `${completion.percentage}%` }}
            />
          </div>

          <div className="flex flex-wrap gap-2 text-[11px] text-[#A1A1AA]">
            <span>Missing:</span>
            {completion.fields
              .filter((f) => !f.filled)
              .slice(0, 4)
              .map((f) => (
                <span key={f.key} className="px-1.5 py-0.5 rounded bg-[#1F1F23] text-[#71717A]">
                  {f.label}
                </span>
              ))}
            {completion.fields.filter((f) => !f.filled).length > 4 && (
              <span className="text-[#71717A]">
                +{completion.fields.filter((f) => !f.filled).length - 4} more
              </span>
            )}
          </div>
        </div>

        {/* Quick Identity Status Card */}
        <div className="p-4 rounded-2xl border border-[#2A2A30] bg-[#111114] flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-[#F5F5F5]">Status & Verification</span>
            <StatusBadge status={profile?.status || "APPROVED"} />
          </div>
          <div className="text-[11px] text-[#A1A1AA] space-y-1 mt-2">
            <div>
              <span className="text-[#71717A]">Slug:</span>{" "}
              <code className="text-[#10B981]">{profile?.slug}</code>
            </div>
            <div>
              <span className="text-[#71717A]">Domain:</span>{" "}
              <span>{profile?.official_domain}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Draft Notification Alert */}
      {hasDraft && (
        <div className="p-3.5 rounded-2xl bg-[#6366F1]/10 border border-[#6366F1]/30 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs text-[#6366F1] animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>
              You have an active uncommitted draft
              {draftTimestamp ? ` saved on ${new Date(draftTimestamp).toLocaleString()}` : ""}.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRestoreDraft}
              className="px-2.5 py-1 rounded-lg bg-[#6366F1] text-white text-[11px] font-medium hover:bg-[#4F46E5] transition"
            >
              Restore Draft
            </button>
            <button
              type="button"
              onClick={handleDiscardDraft}
              className="px-2.5 py-1 rounded-lg border border-[#6366F1]/40 text-[#A1A1AA] hover:text-[#EF4444] text-[11px] transition"
            >
              Discard Draft
            </button>
          </div>
        </div>
      )}

      {/* Success Notification */}
      {successMsg && (
        <div className="p-4 rounded-2xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center gap-3 text-xs text-[#10B981] animate-in fade-in">
          <CheckCircle className="h-4 w-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Error Notification */}
      {errorMsg && (
        <div className="p-4 rounded-2xl bg-[#EF4444]/10 border border-[#EF4444]/30 flex items-center gap-3 text-xs text-[#EF4444] animate-in fade-in">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="p-5 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-[#F5F5F5]">Step {activeStep + 1} of {PROFILE_STEPS.length}: {PROFILE_STEPS[activeStep].title}</p>
            <p className="text-[11px] text-[#A1A1AA] mt-1">{PROFILE_STEPS[activeStep].description}</p>
          </div>
          <span className="text-[11px] text-[#A1A1AA]">{Math.round(((activeStep + 1) / PROFILE_STEPS.length) * 100)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-[#1F1F23] overflow-hidden" role="progressbar" aria-valuemin={0} aria-valuemax={PROFILE_STEPS.length} aria-valuenow={activeStep + 1}>
          <div className="h-full rounded-full bg-gradient-to-r from-[#10B981] to-[#6366F1] transition-all" style={{ width: `${((activeStep + 1) / PROFILE_STEPS.length) * 100}%` }} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {PROFILE_STEPS.map((step, index) => (
            <div key={step.title} className={`rounded-lg px-3 py-2 text-[11px] ${index === activeStep ? "bg-[#10B981]/10 text-[#10B981]" : index < activeStep ? "text-[#A1A1AA]" : "text-[#71717A]"}`}>
              <span className="font-semibold">{index + 1}. {step.title}</span>
            </div>
          ))}
        </div>
      </div>

      <form onSubmit={handleWizardSubmit} className="space-y-6">
        {activeStep === 0 && (
          <div className="grid grid-cols-1 gap-6 items-start">
          {/* ================================================================= */}
          {/* CARD 1: INSTITUTION IDENTITY */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Shield className="h-4 w-4 text-[#10B981]" />
                Institution Identity
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Primary Legal Registry</span>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Full Institution Name <span className="text-[#EF4444]">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  placeholder="e.g. Ahmedabad Institute of Technology"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Short Name / Abbreviation
                  </label>
                  <input
                    type="text"
                    value={formData.short_name}
                    onChange={(e) => handleChange("short_name", e.target.value)}
                    placeholder="e.g. AIT"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Year Established
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                    <input
                      type="number"
                      min={1800}
                      max={2099}
                      value={formData.established_year}
                      onChange={(e) => handleChange("established_year", e.target.value)}
                      placeholder="e.g. 2004"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Institution Type
                  </label>
                  <select
                    value={formData.institution_type}
                    onChange={(e) => handleChange("institution_type", e.target.value)}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  >
                    <option value="Autonomous College">Autonomous College</option>
                    <option value="Affiliated Engineering College">Affiliated Engineering College</option>
                    <option value="State University">State University</option>
                    <option value="Central University">Central University</option>
                    <option value="Private University">Private University</option>
                    <option value="Institute of National Importance">Institute of National Importance</option>
                    <option value="Polytechnic & Diploma Institute">Polytechnic & Diploma Institute</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Registration / Approval Status
                  </label>
                  <div className="h-9 px-3 py-1.5 bg-[#18181B] border border-[#2A2A30] rounded-lg flex items-center justify-between">
                    <StatusBadge status={profile?.status || "APPROVED"} />
                    <span className="text-[10px] text-[#71717A]">(Super Admin)</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1 flex items-center justify-between">
                  <span>Permanent Slug Identifier (Immutable)</span>
                  <Lock className="h-3 w-3 text-[#71717A]" />
                </label>
                <input
                  type="text"
                  disabled
                  value={profile?.slug || ""}
                  className="w-full bg-[#18181B] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#71717A] font-mono cursor-not-allowed text-xs"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Official Institutional Domain <span className="text-[#EF4444]">*</span>
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                    <input
                      type="text"
                      required
                      value={formData.official_domain}
                      onChange={(e) => handleChange("official_domain", e.target.value)}
                      placeholder="e.g. aitindia.in"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#10B981]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Official Website Portal URL
                  </label>
                  <div className="relative">
                    <ExternalLink className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                    <input
                      type="url"
                      value={formData.website_url}
                      onChange={(e) => handleChange("website_url", e.target.value)}
                      placeholder="https://aitindia.in"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* CARD 2: BRANDING & VISUAL IDENTITY */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Palette className="h-4 w-4 text-[#10B981]" />
                Branding & Visual Identity
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Crest, Banner & Colors</span>
            </div>

            {/* Hidden File Inputs */}
            <input
              type="file"
              ref={logoInputRef}
              accept="image/png,image/jpeg,image/webp,image/svg+xml"
              className="hidden"
              onChange={(e) => handleFileUpload(e, "logo", "logo_url")}
            />
            <input
              type="file"
              ref={coverInputRef}
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => handleFileUpload(e, "cover", "cover_image_url")}
            />
            <input
              type="file"
              ref={faviconInputRef}
              accept="image/x-icon,image/png,image/svg+xml"
              className="hidden"
              onChange={(e) => handleFileUpload(e, "favicon", "favicon_url")}
            />

            <div className="space-y-4 text-xs">
              {/* Wide Cover Image Preview */}
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Wide Cover Image Preview (16:9 or Banner)
                </label>
                <div className="relative w-full h-32 rounded-xl border border-[#2A2A30] bg-[#1F1F23] overflow-hidden flex items-center justify-center group">
                  {formData.cover_image_url ? (
                    <img
                      src={formData.cover_image_url}
                      alt="Cover Preview"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="flex flex-col items-center text-[#71717A] text-[11px] gap-1">
                      <UploadCloud className="h-6 w-6 text-[#A1A1AA]" />
                      <span>No cover image uploaded</span>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => coverInputRef.current?.click()}
                      disabled={uploadingField === "cover_image_url"}
                      className="px-3 py-1.5 rounded-lg bg-[#10B981] text-white text-xs font-medium hover:bg-[#059669] transition"
                    >
                      {uploadingField === "cover_image_url" ? "Uploading..." : "Replace Cover"}
                    </button>
                    {formData.cover_image_url && (
                      <button
                        type="button"
                        onClick={() => handleChange("cover_image_url", "")}
                        className="p-1.5 rounded-lg bg-[#EF4444] text-white text-xs hover:bg-[#DC2626] transition"
                        title="Remove cover"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Logo & Favicon row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* College Profile Photo / Logo Preview */}
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    College Profile Photo
                  </label>
                  <div className="flex items-center gap-3">
                    <div className="relative w-20 h-20 rounded-full border-2 border-[#10B981]/50 bg-[#1F1F23] overflow-hidden flex items-center justify-center shrink-0">
                      {formData.logo_url ? (
                        <img
                          src={formData.logo_url}
                          alt="College profile photo preview"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Building2 className="h-8 w-8 text-[#71717A]" />
                      )}
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        onClick={() => logoInputRef.current?.click()}
                        disabled={uploadingField === "logo_url"}
                        className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[11px] font-medium text-[#F5F5F5] transition text-left"
                      >
                        {uploadingField === "logo_url" ? "Uploading..." : formData.logo_url ? "Change Photo" : "Upload Photo"}
                      </button>
                      <span className="text-[10px] text-[#71717A]">PNG, JPG, SVG or WebP (&lt;5MB)</span>
                    </div>
                  </div>
                </div>

                {/* Favicon Preview */}
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Favicon
                  </label>
                  <div className="flex items-center gap-3">
                    <div className="relative w-12 h-12 rounded-lg border border-[#2A2A30] bg-[#1F1F23] overflow-hidden flex items-center justify-center shrink-0">
                      {formData.favicon_url ? (
                        <img
                          src={formData.favicon_url}
                          alt="Favicon"
                          className="w-6 h-6 object-contain"
                        />
                      ) : (
                        <Globe className="h-5 w-5 text-[#71717A]" />
                      )}
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        onClick={() => faviconInputRef.current?.click()}
                        disabled={uploadingField === "favicon_url"}
                        className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-[11px] font-medium text-[#F5F5F5] transition text-left"
                      >
                        {uploadingField === "favicon_url" ? "Uploading..." : "Upload Favicon"}
                      </button>
                      <span className="text-[10px] text-[#71717A]">.ico, .png, or .svg</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Brand Colors */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Primary Brand Color
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={formData.primary_brand_color}
                      onChange={(e) => handleChange("primary_brand_color", e.target.value)}
                      className="w-9 h-9 rounded-lg border border-[#2A2A30] bg-[#1F1F23] cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={formData.primary_brand_color}
                      onChange={(e) => handleChange("primary_brand_color", e.target.value)}
                      placeholder="#10B981"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono uppercase text-xs"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Secondary Brand Color
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={formData.secondary_brand_color}
                      onChange={(e) => handleChange("secondary_brand_color", e.target.value)}
                      className="w-9 h-9 rounded-lg border border-[#2A2A30] bg-[#1F1F23] cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={formData.secondary_brand_color}
                      onChange={(e) => handleChange("secondary_brand_color", e.target.value)}
                      placeholder="#6366F1"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] font-mono uppercase text-xs"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
        )}

        {activeStep === 1 && (
          <div className="grid grid-cols-1 gap-6 items-start">
          {/* ================================================================= */}
          {/* CARD 3: ADDRESS & LOCATION */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <MapPin className="h-4 w-4 text-[#10B981]" />
                Address & Campus Location
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Physical Geography</span>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Address Line 1
                </label>
                <input
                  type="text"
                  value={formData.address_line1}
                  onChange={(e) => handleChange("address_line1", e.target.value)}
                  placeholder="Near Gota Cross Road, Sarkhej-Gandhinagar Highway"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Address Line 2 (Optional)
                </label>
                <input
                  type="text"
                  value={formData.address_line2}
                  onChange={(e) => handleChange("address_line2", e.target.value)}
                  placeholder="Jagatpur, Ognaj"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => handleChange("city", e.target.value)}
                    placeholder="Ahmedabad"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    District
                  </label>
                  <input
                    type="text"
                    value={formData.district}
                    onChange={(e) => handleChange("district", e.target.value)}
                    placeholder="Ahmedabad"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => handleChange("state", e.target.value)}
                    placeholder="Gujarat"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Country
                  </label>
                  <input
                    type="text"
                    value={formData.country}
                    onChange={(e) => handleChange("country", e.target.value)}
                    placeholder="India"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    PIN / Postal Code
                  </label>
                  <input
                    type="text"
                    value={formData.postal_code}
                    onChange={(e) => handleChange("postal_code", e.target.value)}
                    placeholder="382481"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Google Maps URL
                </label>
                <div className="relative">
                  <Compass className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                  <input
                    type="url"
                    value={formData.maps_url}
                    onChange={(e) => handleChange("maps_url", e.target.value)}
                    placeholder="https://maps.google.com/?q=..."
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Latitude (Optional)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.latitude}
                    onChange={(e) => handleChange("latitude", e.target.value)}
                    placeholder="23.0984"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Longitude (Optional)
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={formData.longitude}
                    onChange={(e) => handleChange("longitude", e.target.value)}
                    placeholder="72.5312"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* CARD 4: OFFICIAL CONTACTS */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Mail className="h-4 w-4 text-[#10B981]" />
                Official Contacts & Departmental Helplines
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Inquiry Channels</span>
            </div>

            <div className="space-y-3.5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Official Contact Email <span className="text-[#EF4444]">*</span>
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                    <input
                      type="email"
                      required
                      value={formData.contact_email}
                      onChange={(e) => handleChange("contact_email", e.target.value)}
                      placeholder="info@aitindia.in"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Official Phone Number
                  </label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#71717A]" />
                    <input
                      type="text"
                      value={formData.contact_phone}
                      onChange={(e) => handleChange("contact_phone", e.target.value)}
                      placeholder="+91-79-27663244"
                      className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-8 pr-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Admission Department Email
                  </label>
                  <input
                    type="email"
                    value={formData.admission_email}
                    onChange={(e) => handleChange("admission_email", e.target.value)}
                    placeholder="admission@aitindia.in"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Admission Helpline
                  </label>
                  <input
                    type="text"
                    value={formData.admission_helpline}
                    onChange={(e) => handleChange("admission_helpline", e.target.value)}
                    placeholder="+91-9978900000"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Examination Department Email
                  </label>
                  <input
                    type="email"
                    value={formData.examination_email}
                    onChange={(e) => handleChange("examination_email", e.target.value)}
                    placeholder="exam@aitindia.in"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Placement Department Email
                  </label>
                  <input
                    type="email"
                    value={formData.placement_email}
                    onChange={(e) => handleChange("placement_email", e.target.value)}
                    placeholder="placements@aitindia.in"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Alternate Phone Number
                  </label>
                  <input
                    type="text"
                    value={formData.alternate_phone}
                    onChange={(e) => handleChange("alternate_phone", e.target.value)}
                    placeholder="+91-79-27663245"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Office Working Hours
                  </label>
                  <input
                    type="text"
                    value={formData.working_hours}
                    onChange={(e) => handleChange("working_hours", e.target.value)}
                    placeholder="Mon - Fri: 9:00 AM - 5:00 PM, Sat: 9:00 AM - 1:00 PM"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>
            </div>
          </div>
          </div>
        )}

        {activeStep === 2 && (
          <div className="grid grid-cols-1 gap-6 items-start">
          {/* ================================================================= */}
          {/* CARD 5: RECOGNITION & ACCREDITATION */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Award className="h-4 w-4 text-[#10B981]" />
                Recognition & Accreditation
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Statutory Bodies & Rankings</span>
            </div>

            {/* Hidden Input for Approval Document */}
            <input
              type="file"
              ref={approvalDocInputRef}
              accept="application/pdf,image/png,image/jpeg"
              className="hidden"
              onChange={(e) => handleFileUpload(e, "approval_document", "approval_document_url")}
            />

            <div className="space-y-3.5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Affiliated University
                  </label>
                  <input
                    type="text"
                    value={formData.affiliated_university}
                    onChange={(e) => handleChange("affiliated_university", e.target.value)}
                    placeholder="e.g. Gujarat Technological University (GTU)"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Recognized By
                  </label>
                  <input
                    type="text"
                    value={formData.recognized_by}
                    onChange={(e) => handleChange("recognized_by", e.target.value)}
                    placeholder="e.g. Government of Gujarat / DTE"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    AICTE Approval Status / Number
                  </label>
                  <input
                    type="text"
                    value={formData.aicte_approval}
                    onChange={(e) => handleChange("aicte_approval", e.target.value)}
                    placeholder="Approved (F.No. Western/1-3323...)"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    UGC Recognition
                  </label>
                  <input
                    type="text"
                    value={formData.ugc_recognition}
                    onChange={(e) => handleChange("ugc_recognition", e.target.value)}
                    placeholder="Recognized under Section 2(f)"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    NAAC Grade
                  </label>
                  <select
                    value={formData.naac_grade}
                    onChange={(e) => handleChange("naac_grade", e.target.value)}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  >
                    <option value="A++">A++ (CGPA &gt; 3.5)</option>
                    <option value="A+">A+ (CGPA 3.26 - 3.5)</option>
                    <option value="A">A (CGPA 3.01 - 3.25)</option>
                    <option value="B++">B++</option>
                    <option value="B+">B+</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="In Progress">Application In Progress</option>
                    <option value="Not Applicable">Not Applicable</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    NBA Accreditation
                  </label>
                  <input
                    type="text"
                    value={formData.nba_accreditation}
                    onChange={(e) => handleChange("nba_accreditation", e.target.value)}
                    placeholder="Accredited for CSE, IT, ME"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">
                    Accreditation Validity
                  </label>
                  <input
                    type="text"
                    value={formData.accreditation_validity}
                    onChange={(e) => handleChange("accreditation_validity", e.target.value)}
                    placeholder="Valid through 2028"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              {/* Approval Document Upload */}
              <div className="pt-1">
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Official Statutory Approval Document
                </label>
                <div className="flex items-center gap-3 p-3 rounded-xl border border-[#2A2A30] bg-[#1F1F23]">
                  <FileCheck className="h-5 w-5 text-[#10B981] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[#F5F5F5] truncate">
                      {formData.approval_document_url
                        ? formData.approval_document_url.split("/").pop()
                        : "No approval document attached"}
                    </p>
                    <span className="text-[10px] text-[#71717A]">PDF or Scanned Certificate (&lt;10MB)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => approvalDocInputRef.current?.click()}
                    disabled={uploadingField === "approval_document_url"}
                    className="px-3 py-1.5 rounded-lg border border-[#2A2A30] bg-[#111114] hover:bg-[#2A2A30] text-xs font-medium text-[#F5F5F5] transition shrink-0"
                  >
                    {uploadingField === "approval_document_url" ? "Uploading..." : "Upload PDF"}
                  </button>
                  {formData.approval_document_url && (
                    <a
                      href={formData.approval_document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#10B981] transition"
                      title="Open Document"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* CARD 6: ABOUT INSTITUTION */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <FileText className="h-4 w-4 text-[#10B981]" />
                About Institution & Philosophy
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Public Narrative</span>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[#A1A1AA] font-medium">Short Summary / Tagline</label>
                  <span className="text-[10px] text-[#71717A]">
                    {formData.short_description.length}/500 chars
                  </span>
                </div>
                <textarea
                  rows={2}
                  maxLength={500}
                  value={formData.short_description}
                  onChange={(e) => handleChange("short_description", e.target.value)}
                  placeholder="Premier engineering institute committed to technical excellence and industry-ready graduates."
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Comprehensive About Institution
                </label>
                <textarea
                  rows={4}
                  value={formData.about_text}
                  onChange={(e) => handleChange("about_text", e.target.value)}
                  placeholder="Detailed background, campus infrastructure, faculties, laboratories, and research milestones..."
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Vision Statement</label>
                  <textarea
                    rows={3}
                    value={formData.vision}
                    onChange={(e) => handleChange("vision", e.target.value)}
                    placeholder="To emerge as a center of excellence in engineering education..."
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Mission Statement</label>
                  <textarea
                    rows={3}
                    value={formData.mission}
                    onChange={(e) => handleChange("mission", e.target.value)}
                    placeholder="Provide state-of-the-art infrastructure, foster research and ethical values..."
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>
            </div>
          </div>
          </div>
        )}

        {activeStep === 3 && (
          <div className="grid grid-cols-1 gap-6 items-start">
          {/* ================================================================= */}
          {/* CARD 7: LEADERSHIP */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Users className="h-4 w-4 text-[#10B981]" />
                Institutional Leadership
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Head of Institution</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Principal / Director Name
                </label>
                <input
                  type="text"
                  value={formData.leader_name}
                  onChange={(e) => handleChange("leader_name", e.target.value)}
                  placeholder="Dr. Rajesh K. Patel"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">
                  Designation / Role
                </label>
                <input
                  type="text"
                  value={formData.leader_designation}
                  onChange={(e) => handleChange("leader_designation", e.target.value)}
                  placeholder="Principal & Professor, Ph.D. (IIT Delhi)"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                />
              </div>
            </div>
          </div>

          {/* ================================================================= */}
          {/* CARD 8: SOCIAL MEDIA CHANNELS */}
          {/* ================================================================= */}
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#2A2A30] pb-3">
              <h2 className="text-sm font-semibold text-[#F5F5F5] flex items-center gap-2">
                <Share2 className="h-4 w-4 text-[#10B981]" />
                Official Social Media Handles
              </h2>
              <span className="text-[11px] text-[#A1A1AA]">Student Community Outreach</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">LinkedIn Profile</label>
                  <input
                    type="url"
                    value={formData.linkedin_url}
                    onChange={(e) => handleChange("linkedin_url", e.target.value)}
                    placeholder="https://linkedin.com/school/ait"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Instagram Handle</label>
                  <input
                    type="url"
                    value={formData.instagram_url}
                    onChange={(e) => handleChange("instagram_url", e.target.value)}
                    placeholder="https://instagram.com/ait_ahmedabad"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Facebook Page</label>
                  <input
                    type="url"
                    value={formData.facebook_url}
                    onChange={(e) => handleChange("facebook_url", e.target.value)}
                    placeholder="https://facebook.com/ait"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">YouTube Channel</label>
                  <input
                    type="url"
                    value={formData.youtube_url}
                    onChange={(e) => handleChange("youtube_url", e.target.value)}
                    placeholder="https://youtube.com/@ait"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">X / Twitter</label>
                  <input
                    type="url"
                    value={formData.twitter_url}
                    onChange={(e) => handleChange("twitter_url", e.target.value)}
                    placeholder="https://x.com/ait_campus"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Bottom Actions Bar */}
        <div className="p-4 rounded-2xl border border-[#2A2A30] bg-[#111114] flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-[#A1A1AA]">
            Make sure all mandatory fields (<span className="text-[#EF4444]">*</span>) are verified before saving.
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            >
              Cancel / Reset
            </button>

            <button
              type="button"
              onClick={handleSaveDraft}
              disabled={isDraftSaving}
              className="px-4 py-2 rounded-xl border border-[#6366F1]/30 bg-[#6366F1]/10 hover:bg-[#6366F1]/20 text-xs font-medium text-[#6366F1] transition disabled:opacity-50"
            >
              {isDraftSaving ? "Saving..." : "Save Draft"}
            </button>

            {activeStep > 0 && (
              <button
                type="button"
                onClick={handlePreviousStep}
                className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#F5F5F5] transition"
              >
                Back
              </button>
            )}

            {activeStep < PROFILE_STEPS.length - 1 ? (
              <button
                type="button"
                onClick={handleNextStep}
                disabled={Boolean(uploadingField)}
                className="px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-xs font-semibold text-white shadow-lg shadow-[#10B981]/25 transition disabled:opacity-50"
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSaving || Boolean(uploadingField)}
                className="px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-xs font-semibold text-white shadow-lg shadow-[#10B981]/25 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {isSaving ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save Changes
              </button>
            )}
          </div>
        </div>
      </form>

      {/* ===================================================================== */}
      {/* PREVIEW PUBLIC PROFILE MODAL */}
      {/* ===================================================================== */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="relative w-full max-w-3xl rounded-3xl border border-[#2A2A30] bg-[#111114] overflow-hidden shadow-2xl my-8">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-[#2A2A30] bg-[#18181B]">
              <div className="flex items-center gap-2">
                <Eye className="h-4 w-4 text-[#10B981]" />
                <h3 className="text-sm font-semibold text-[#F5F5F5]">
                  Public Student View Preview
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPreviewModal(false)}
                className="p-1 rounded-lg text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#2A2A30] transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Public Profile Card */}
            <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
              {/* Cover Banner */}
              <div className="relative h-44 rounded-2xl bg-gradient-to-r from-[#18181B] to-[#1F1F23] border border-[#2A2A30] overflow-hidden">
                {formData.cover_image_url ? (
                  <img
                    src={formData.cover_image_url}
                    alt="Cover"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#71717A] text-xs">
                    Campus Banner Cover
                  </div>
                )}

                {/* Overlaid Logo */}
                <div className="absolute -bottom-2 left-6 transform translate-y-1/4">
                  <div className="w-20 h-20 rounded-2xl border-4 border-[#111114] bg-[#1F1F23] overflow-hidden shadow-lg flex items-center justify-center">
                    {formData.logo_url ? (
                      <img src={formData.logo_url} alt="Logo" className="w-full h-full object-contain p-1" />
                    ) : (
                      <Building2 className="h-8 w-8 text-[#10B981]" />
                    )}
                  </div>
                </div>
              </div>

              {/* Identity Header */}
              <div className="pt-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-[#F5F5F5]">
                      {formData.name || "Institution Legal Name"}
                    </h2>
                    {formData.short_name && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-[#10B981]/15 text-[#10B981] font-semibold">
                        {formData.short_name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#A1A1AA] mt-1 flex items-center gap-2">
                    <span>{formData.institution_type}</span>
                    {formData.established_year && (
                      <>
                        <span>•</span>
                        <span>Est. {formData.established_year}</span>
                      </>
                    )}
                    <span>•</span>
                    <span className="font-mono text-[#10B981]">{formData.official_domain}</span>
                  </p>
                </div>

                {/* Accreditations Badges */}
                <div className="flex flex-wrap items-center gap-2">
                  {formData.naac_grade && formData.naac_grade !== "Not Applicable" && (
                    <span className="px-2.5 py-1 rounded-lg bg-[#6366F1]/15 text-[#6366F1] font-bold text-xs border border-[#6366F1]/30">
                      NAAC {formData.naac_grade}
                    </span>
                  )}
                  {formData.aicte_approval && (
                    <span className="px-2.5 py-1 rounded-lg bg-[#10B981]/15 text-[#10B981] font-medium text-xs border border-[#10B981]/30">
                      AICTE
                    </span>
                  )}
                  <StatusBadge status={profile?.status || "APPROVED"} />
                </div>
              </div>

              {/* Short Description */}
              {formData.short_description && (
                <div className="p-4 rounded-xl bg-[#18181B] border border-[#2A2A30] text-xs text-[#E4E4E7] leading-relaxed">
                  {formData.short_description}
                </div>
              )}

              {/* Leadership & Affiliation Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                {formData.leader_name && (
                  <div className="p-3.5 rounded-xl border border-[#2A2A30] bg-[#18181B]">
                    <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-semibold">
                      Leadership
                    </span>
                    <p className="font-semibold text-[#F5F5F5] mt-0.5">{formData.leader_name}</p>
                    <p className="text-[#A1A1AA] text-[11px]">{formData.leader_designation}</p>
                  </div>
                )}

                {formData.affiliated_university && (
                  <div className="p-3.5 rounded-xl border border-[#2A2A30] bg-[#18181B]">
                    <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-semibold">
                      Affiliation
                    </span>
                    <p className="font-semibold text-[#F5F5F5] mt-0.5">{formData.affiliated_university}</p>
                    <p className="text-[#A1A1AA] text-[11px]">{formData.recognized_by}</p>
                  </div>
                )}
              </div>

              {/* Location & Contacts */}
              <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#18181B] space-y-3 text-xs">
                <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-semibold">
                  Campus Address & Official Contacts
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[#A1A1AA]">
                  <div className="flex items-start gap-2">
                    <MapPin className="h-4 w-4 text-[#10B981] shrink-0 mt-0.5" />
                    <span>
                      {[formData.address_line1, formData.city, formData.state, formData.postal_code]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    {formData.contact_email && (
                      <div className="flex items-center gap-2">
                        <Mail className="h-3.5 w-3.5 text-[#10B981] shrink-0" />
                        <span>{formData.contact_email}</span>
                      </div>
                    )}
                    {formData.contact_phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-[#10B981] shrink-0" />
                        <span>{formData.contact_phone}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-[#2A2A30] bg-[#18181B] flex justify-end">
              <button
                type="button"
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-2 rounded-xl bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#F5F5F5] transition"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* CHANGE HISTORY MODAL */}
      {/* ===================================================================== */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="relative w-full max-w-2xl rounded-3xl border border-[#2A2A30] bg-[#111114] overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-[#2A2A30] bg-[#18181B]">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-[#10B981]" />
                <h3 className="text-sm font-semibold text-[#F5F5F5]">Profile Change Audit History</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="p-1 rounded-lg text-[#A1A1AA] hover:text-[#F5F5F5] hover:bg-[#2A2A30] transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 max-h-[70vh] overflow-y-auto space-y-4 text-xs">
              {historyLoading ? (
                <div className="flex items-center justify-center py-12 text-[#A1A1AA]">
                  <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                  <span>Loading change records...</span>
                </div>
              ) : historyItems.length === 0 ? (
                <div className="text-center py-12 text-[#71717A]">
                  No profile modification events recorded yet.
                </div>
              ) : (
                historyItems.map((item) => (
                  <div key={item.id} className="p-4 rounded-xl border border-[#2A2A30] bg-[#18181B] space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-[#10B981]">{item.action_type}</span>
                      <span className="text-[#71717A]">{new Date(item.created_at).toLocaleString()}</span>
                    </div>
                    <div className="text-[11px] text-[#A1A1AA]">
                      Modified by: <span className="text-[#F5F5F5] font-medium">{item.actor_name || "Admin"}</span>
                      {item.actor_email && ` (${item.actor_email})`}
                    </div>

                    {item.payload_diff && (
                      <div className="mt-2 pt-2 border-t border-[#2A2A30]/60 space-y-1">
                        <span className="text-[10px] text-[#71717A] uppercase font-bold">Changed Fields:</span>
                        <div className="space-y-1 font-mono text-[11px]">
                          {Object.entries(item.payload_diff).map(([field, diff]) => (
                            <div key={field} className="flex items-baseline gap-2">
                              <span className="text-[#A1A1AA]">{field}:</span>
                              <span className="text-[#EF4444] line-through">
                                {diff?.old !== null && diff?.old !== undefined ? String(diff.old) : "empty"}
                              </span>
                              <span className="text-[#71717A]">→</span>
                              <span className="text-[#10B981]">
                                {diff?.new !== null && diff?.new !== undefined ? String(diff.new) : "empty"}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="p-4 border-t border-[#2A2A30] bg-[#18181B] flex justify-end">
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-2 rounded-xl bg-[#1F1F23] hover:bg-[#2A2A30] text-xs font-medium text-[#F5F5F5] transition"
              >
                Close History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
