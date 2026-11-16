"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { collegeAdminService } from "@/services/college-admin-service";
import {
  GraduationCap,
  Building2,
  Globe,
  FileText,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  Upload,
  Info,
  Check,
  ExternalLink,
  BookOpen,
  Eye,
  CheckSquare,
  Clock,
} from "lucide-react";

export default function CollegeOnboardingWizardPage() {
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [collegeData, setCollegeData] = useState<{
    id: string;
    name: string;
    slug: string;
    official_domain: string;
    contact_email: string;
    contact_phone: string;
    logo_url: string;
  }>({
    id: "11111111-1111-1111-1111-111111111111",
    name: "Ahmedabad Institute of Technology",
    slug: "ait-ahmedabad",
    official_domain: "aitindia.in",
    contact_email: "admin@aitindia.in",
    contact_phone: "+91 79 2630 1111",
    logo_url: "",
  });

  // Step 2 Profile State
  const [motto, setMotto] = useState("Empowering Engineering & Innovative Minds");

  // Step 3 Website State
  const [websiteUrl, setWebsiteUrl] = useState("https://www.aitindia.in");
  const [crawlDepth, setCrawlDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(50);
  const [allowedSubdomains, setAllowedSubdomains] = useState("admissions,academics");

  // Step 4 Documents State
  const [documents, setDocuments] = useState<Array<{ name: string; category: string; size: string }>>([
    { name: "AIT_Fee_Structure_2024_25.pdf", category: "FEES", size: "1.2 MB" },
    { name: "ACPC_Engineering_Admission_Brochure.pdf", category: "ADMISSIONS", size: "3.4 MB" },
  ]);
  const [newDocName, setNewDocName] = useState("");
  const [newDocCategory, setNewDocCategory] = useState("GENERAL");

  // Load existing onboarding progress on mount
  useEffect(() => {
    async function loadProgress() {
      setLoading(true);
      try {
        const [progRes, profRes] = await Promise.all([
          collegeAdminService.getOnboardingProgress(),
          collegeAdminService.getProfile(),
        ]);

        if (progRes.success && progRes.data) {
          if (progRes.data.current_step) {
            setCurrentStep(progRes.data.current_step);
          }
        }

        if (profRes.success && profRes.data) {
          const prof = profRes.data;
          setCollegeData((prev) => ({
            ...prev,
            id: prof.id || prev.id,
            name: prof.name || prev.name,
            slug: prof.slug || prev.slug,
            official_domain: prof.official_domain || prev.official_domain,
            contact_email: prof.contact_email || prev.contact_email,
            contact_phone: prof.contact_phone || prev.contact_phone,
            logo_url: prof.logo_url || prev.logo_url,
          }));
          if (prof.official_domain) {
            setWebsiteUrl(`https://${prof.official_domain}`);
          }
        }
      } catch (err) {
        console.error("Failed to load onboarding status:", err);
      } finally {
        setLoading(false);
      }
    }
    loadProgress();
  }, []);

  const saveProgressStep = async (nextStepNum: number, extraData: Record<string, any> = {}) => {
    setSaving(true);
    try {
      await collegeAdminService.updateOnboardingProgress({
        current_step: nextStepNum,
        step_data: extraData,
        profile_completed: nextStepNum > 2,
        website_configured: nextStepNum > 3,
        documents_uploaded: nextStepNum > 4,
        knowledge_ready: nextStepNum > 5,
      });
      setCurrentStep(nextStepNum);
    } catch (e) {
      setCurrentStep(nextStepNum);
    } finally {
      setSaving(false);
    }
  };

  const handleFinishOnboarding = async () => {
    setSaving(true);
    try {
      await collegeAdminService.completeOnboarding();
      router.push("/college-admin/dashboard");
    } catch (e) {
      router.push("/college-admin/dashboard");
    } finally {
      setSaving(false);
    }
  };

  const handleAddDocument = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocName.trim()) return;
    setDocuments((prev) => [
      ...prev,
      {
        name: newDocName.trim().endsWith(".pdf") ? newDocName.trim() : `${newDocName.trim()}.pdf`,
        category: newDocCategory,
        size: "2.1 MB",
      },
    ]);
    setNewDocName("");
  };

  const stepsList = [
    { num: 1, title: "Welcome & Tenant Intro", icon: GraduationCap },
    { num: 2, title: "College Profile", icon: Building2 },
    { num: 3, title: "Official Website", icon: Globe },
    { num: 4, title: "College Documents", icon: FileText },
    { num: 5, title: "Knowledge Review", icon: BookOpen },
    { num: 6, title: "Completion", icon: CheckCircle2 },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-xs text-[#A1A1AA]">
        <div className="flex flex-col items-center gap-2">
          <div className="w-5 h-5 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
          <span>Loading College Onboarding Wizard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#2A2A30] pb-5">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#6366F1]/10 border border-[#6366F1]/30 text-[#818CF8] text-[11px] font-medium mb-1.5">
            <ShieldCheck className="h-3.5 w-3.5" />
            Verified Institutional Tenant
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#F5F5F5] tracking-tight">
            Institutional Onboarding Wizard
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-0.5">
            Complete the 6 guided setup milestones to configure your domain crawler, upload official brochures, and publish grounded facts.
          </p>
        </div>

        <div className="text-right hidden sm:block">
          <div className="text-xs font-semibold text-[#F5F5F5]">{collegeData.name}</div>
          <div className="text-[11px] text-[#A1A1AA] font-mono">domain: {collegeData.official_domain}</div>
        </div>
      </div>

      {/* Stepper Progress Bar */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        {stepsList.map(({ num, title, icon: Icon }) => {
          const isDone = currentStep > num;
          const isCurrent = currentStep === num;
          return (
            <button
              key={num}
              type="button"
              onClick={() => setCurrentStep(num)}
              className={`p-2.5 rounded-xl border text-left transition flex flex-col justify-between ${
                isCurrent
                  ? "border-[#6366F1] bg-[#6366F1]/10 text-white"
                  : isDone
                  ? "border-[#10B981]/30 bg-[#10B981]/5 text-[#10B981]"
                  : "border-[#2A2A30] bg-[#111114] text-[#A1A1AA]/60 hover:text-[#A1A1AA]"
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="text-[10px] font-mono font-bold">Step {num}</span>
                {isDone ? (
                  <Check className="h-3 w-3 text-[#10B981]" />
                ) : (
                  <Icon className="h-3 w-3" />
                )}
              </div>
              <span className="text-[11px] font-medium truncate block">{title}</span>
            </button>
          );
        })}
      </div>

      {/* Step Content Card */}
      <div className="p-6 sm:p-8 rounded-2xl border border-[#2A2A30] bg-[#111114] shadow-xl space-y-6">
        {/* STEP 1: Welcome & Roadmap */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-2xl bg-[#6366F1]/20 border border-[#6366F1]/40 flex items-center justify-center text-[#6366F1] shrink-0">
                <GraduationCap className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-[#F5F5F5]">
                  Welcome to CampusAI, {collegeData.name}!
                </h2>
                <p className="text-xs text-[#A1A1AA] mt-1 leading-relaxed">
                  Your college registration has been officially approved by the Global Super Administrator.
                  Your tenant space is strictly isolated using PostgreSQL Row Level Security (RLS) and cryptographic tenant keys.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/60 space-y-1">
                <div className="font-semibold text-[#F5F5F5]">Tenant Identifier</div>
                <div className="font-mono text-[#818CF8] text-[11px] truncate">{collegeData.id}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/60 space-y-1">
                <div className="font-semibold text-[#F5F5F5]">Institutional Domain</div>
                <div className="font-mono text-[#10B981] text-[11px]">{collegeData.official_domain}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/60 space-y-1">
                <div className="font-semibold text-[#F5F5F5]">Assigned Administrator</div>
                <div className="text-[#A1A1AA] text-[11px]">{collegeData.contact_email}</div>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/30 space-y-2 text-xs">
              <h3 className="font-semibold text-[#F5F5F5] flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-[#6366F1]" />
                What happens during onboarding?
              </h3>
              <ul className="space-y-1.5 text-[#A1A1AA] list-disc list-inside">
                <li>Verify your official institutional profile, motto, and contact phone.</li>
                <li>Register your campus website domain for bounded, polite crawling.</li>
                <li>Upload official fee structures, admission brochures, and syllabus documents.</li>
                <li>Understand the human-in-the-loop review workflow to approve AI facts before publication.</li>
              </ul>
            </div>
          </div>
        )}

        {/* STEP 2: College Profile */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#F5F5F5] flex items-center gap-2">
                <Building2 className="h-5 w-5 text-[#6366F1]" />
                Step 2: Confirm Institutional Profile
              </h2>
              <p className="text-xs text-[#A1A1AA] mt-0.5">
                Review and update permitted fields. These details are cited when answering student inquiries.
              </p>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">College Name</label>
                <input
                  type="text"
                  value={collegeData.name}
                  onChange={(e) => setCollegeData({ ...collegeData, name: e.target.value })}
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Institutional Motto / Subtitle</label>
                <input
                  type="text"
                  value={motto}
                  onChange={(e) => setMotto(e.target.value)}
                  placeholder="e.g. Empowering Technical Innovation"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Contact Phone</label>
                  <input
                    type="text"
                    value={collegeData.contact_phone}
                    onChange={(e) => setCollegeData({ ...collegeData, contact_phone: e.target.value })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Contact Email</label>
                  <input
                    type="email"
                    value={collegeData.contact_email}
                    onChange={(e) => setCollegeData({ ...collegeData, contact_email: e.target.value })}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Logo / Crest URL</label>
                <input
                  type="url"
                  value={collegeData.logo_url}
                  onChange={(e) => setCollegeData({ ...collegeData, logo_url: e.target.value })}
                  placeholder="https://aitindia.in/logo.png"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Official Website */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#F5F5F5] flex items-center gap-2">
                <Globe className="h-5 w-5 text-[#6366F1]" />
                Step 3: Official Website Source Setup
              </h2>
              <p className="text-xs text-[#A1A1AA] mt-0.5">
                Register your primary campus web URL. Note: Unrestricted crawling is prevented by default; all crawling follows robots.txt.
              </p>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1">Primary Website URL *</label>
                <input
                  type="url"
                  required
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://www.aitindia.in"
                  className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Allowed Subdomains</label>
                  <input
                    type="text"
                    value={allowedSubdomains}
                    onChange={(e) => setAllowedSubdomains(e.target.value)}
                    placeholder="e.g. admissions,academics"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Max Crawl Depth</label>
                  <select
                    value={crawlDepth}
                    onChange={(e) => setCrawlDepth(Number(e.target.value))}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-xl px-3.5 py-2.5 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  >
                    <option value={1}>1 (Homepage only)</option>
                    <option value={2}>2 (Recommended - Direct links)</option>
                    <option value={3}>3 (Deep crawl - 3 levels)</option>
                  </select>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#6366F1]/10 border border-[#6366F1]/30 text-[#818CF8] text-[11px] flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  The crawler will extract textual notifications, fee notices, and contact tables.
                  Web pages are parsed and staged for your review before going live.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: College Documents Upload */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#F5F5F5] flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#6366F1]" />
                Step 4: Initial Institutional PDF Documents
              </h2>
              <p className="text-xs text-[#A1A1AA] mt-0.5">
                Upload official PDF circulars (such as FRC fee orders, admission checklists, or hostel guidelines).
              </p>
            </div>

            {/* Document Upload Simulation Form */}
            <form onSubmit={handleAddDocument} className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/60 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <div className="sm:col-span-2">
                  <label className="block text-[#A1A1AA] font-medium mb-1">Document Title / Filename</label>
                  <input
                    type="text"
                    value={newDocName}
                    onChange={(e) => setNewDocName(e.target.value)}
                    placeholder="e.g. AIT_Campus_Hostel_Rules_2024.pdf"
                    className="w-full bg-[#111114] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  />
                </div>
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Category</label>
                  <select
                    value={newDocCategory}
                    onChange={(e) => setNewDocCategory(e.target.value)}
                    className="w-full bg-[#111114] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#6366F1]"
                  >
                    <option value="FEES">Fees &amp; Scholarships</option>
                    <option value="ADMISSIONS">Admissions &amp; Cutoffs</option>
                    <option value="HOSTEL">Hostel &amp; Amenities</option>
                    <option value="EXAMS">Examinations &amp; Syllabus</option>
                    <option value="GENERAL">General Circular</option>
                  </select>
                </div>
              </div>
              <button
                type="submit"
                disabled={!newDocName.trim()}
                className="px-4 py-2 rounded-lg bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-medium transition flex items-center gap-1.5 disabled:opacity-40"
              >
                <Upload className="h-3.5 w-3.5" />
                <span>Upload Document</span>
              </button>
            </form>

            {/* Uploaded Documents List */}
            <div className="space-y-2 pt-2">
              <h4 className="text-xs font-semibold text-[#A1A1AA] uppercase">Staged Documents ({documents.length})</h4>
              {documents.map((doc, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/40 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2.5">
                    <FileText className="h-4 w-4 text-[#818CF8]" />
                    <div>
                      <span className="font-semibold text-[#F5F5F5] block">{doc.name}</span>
                      <span className="text-[10px] text-[#A1A1AA]">
                        Category: {doc.category} &bull; {doc.size}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 font-medium">
                    Ready for OCR
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 5: Knowledge Review Introduction */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-[#F5F5F5] flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-[#6366F1]" />
                Step 5: Human-in-the-Loop Review Architecture
              </h2>
              <p className="text-xs text-[#A1A1AA] mt-0.5">
                Understand how extracted website paragraphs and PDF circulars are authenticated before reaching students.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-4 rounded-xl border border-[#F59E0B]/30 bg-[#F59E0B]/5 space-y-2">
                <div className="font-bold text-[#F59E0B] flex items-center gap-1.5">
                  <Clock className="h-4 w-4" />
                  Staged / Draft Knowledge
                </div>
                <p className="text-[#A1A1AA] text-[11px] leading-relaxed">
                  When pages or documents are parsed, facts are placed into the <strong>Pending Review</strong> queue.
                  They are never exposed to students until you verify their accuracy.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-[#10B981]/30 bg-[#10B981]/5 space-y-2">
                <div className="font-bold text-[#10B981] flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  Published Verified Grounding
                </div>
                <p className="text-[#A1A1AA] text-[11px] leading-relaxed">
                  Once you click <strong>Approve Fact</strong> in your Review Dashboard, vector embeddings are generated
                  and the chatbot grounds its responses with official citations.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/40 text-xs text-[#D4D4D8] space-y-2">
              <div className="font-semibold text-[#F5F5F5]">Review Workspace Shortcut:</div>
              <p className="text-[11px] text-[#A1A1AA]">
                You can access the dedicated Human Review station anytime at{" "}
                <Link href="/college-admin/reviews" className="text-[#818CF8] hover:underline font-mono">
                  /college-admin/reviews
                </Link>
                .
              </p>
            </div>
          </div>
        )}

        {/* STEP 6: Completion */}
        {currentStep === 6 && (
          <div className="space-y-6 text-center py-4">
            <div className="h-16 w-16 rounded-2xl bg-[#10B981]/20 border border-[#10B981]/40 flex items-center justify-center text-[#10B981] mx-auto shadow-lg shadow-[#10B981]/10">
              <CheckCircle2 className="h-10 w-10" />
            </div>

            <div>
              <h2 className="text-xl font-bold text-[#F5F5F5]">
                {collegeData.name} is Ready!
              </h2>
              <p className="text-xs text-[#A1A1AA] mt-1.5 max-w-md mx-auto">
                All 6 institutional onboarding milestones have been recorded. Your college administration workspace is fully operational.
              </p>
            </div>

            {/* Checklist */}
            <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#1F1F23]/40 max-w-md mx-auto text-left text-xs space-y-2">
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Super Admin Institutional Approval</span>
              </div>
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Designated College Administrator Assigned</span>
              </div>
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Campus Profile &amp; Contact Information Confirmed</span>
              </div>
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Official Domain &amp; Crawler Sources Registered</span>
              </div>
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Initial Institutional PDF Circulars Staged</span>
              </div>
              <div className="flex items-center gap-2 text-[#10B981]">
                <Check className="h-4 w-4" />
                <span>Knowledge Base Review Workflow Enabled</span>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={handleFinishOnboarding}
                disabled={saving}
                className="px-6 py-3 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white text-xs font-semibold transition shadow-lg shadow-[#6366F1]/20 inline-flex items-center gap-2"
              >
                <Building2 className="h-4 w-4" />
                <span>{saving ? "Entering Workspace..." : "Enter College Admin Dashboard"}</span>
              </button>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        {currentStep < 6 && (
          <div className="flex items-center justify-between pt-4 border-t border-[#2A2A30]">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={() => saveProgressStep(currentStep - 1)}
                className="px-4 py-2 rounded-xl border border-[#2A2A30] bg-[#111114] text-xs font-medium text-[#A1A1AA] hover:text-white transition flex items-center gap-1.5"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Previous</span>
              </button>
            ) : (
              <div />
            )}

            <button
              type="button"
              onClick={() => saveProgressStep(currentStep + 1)}
              disabled={saving}
              className="px-5 py-2.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-xs font-medium text-white transition flex items-center gap-1.5 shadow-md shadow-[#6366F1]/20"
            >
              <span>{currentStep === 5 ? "Proceed to Final Review" : "Save & Continue"}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
