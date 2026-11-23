import Link from "next/link";
import {
  CheckCircle2,
  ShieldCheck,
  Search,
  BookOpen,
  ArrowRight,
  Globe,
  Mic,
  FileText,
  Building2,
  Lock,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center pt-20 pb-16 px-4 text-center max-w-5xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#2A2A30] bg-[#111114] text-xs text-[#A1A1AA] mb-8">
          <ShieldCheck className="h-4 w-4 text-[#10B981]" />
          <span>Strictly Grounded in Official College Knowledge</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-center max-w-4xl mb-6">
          Ask Any College Question. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#F5F5F5] via-[#A1A1AA] to-[#6366F1]">
            Receive Verified Answers with Citations.
          </span>
        </h1>

        <p className="text-base sm:text-lg text-[#A1A1AA] text-center max-w-2xl mb-10 leading-relaxed">
          Instant, reliable answers on fees, admissions, courses, and hostel facilities directly cited from official college websites and admin-approved brochures. Zero AI hallucinations.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
          <Link
            href="/colleges"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-[#6366F1] hover:bg-[#4F46E5] text-white font-medium text-sm flex items-center justify-center gap-2 transition shadow-xl shadow-[#6366F1]/20"
          >
            Select Your College
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/chat"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-[#111114] hover:bg-[#1F1F23] border border-[#2A2A30] text-[#F5F5F5] font-medium text-sm flex items-center justify-center gap-2 transition"
          >
            Open Chat Interface
          </Link>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16 px-4 border-t border-[#2A2A30] bg-[#0E0E11]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-xl mx-auto mb-12">
            <span className="text-xs text-[#6366F1] font-mono uppercase tracking-wider block mb-1">
              Architecture
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5]">
              How AI FAQ Colleges Chatbot Delivers Zero Hallucinations
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <div className="h-10 w-10 rounded-xl bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1] font-bold text-sm mb-4">
                01
              </div>
              <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">1. Official Ingestion</h3>
              <p className="text-xs text-[#A1A1AA] leading-relaxed">
                College websites are crawled and PDF prospectuses parsed. College admins audit and approve every extracted fact before publishing.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <div className="h-10 w-10 rounded-xl bg-[#10B981]/10 flex items-center justify-center text-[#10B981] font-bold text-sm mb-4">
                02
              </div>
              <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">2. Hybrid Vector Retrieval</h3>
              <p className="text-xs text-[#A1A1AA] leading-relaxed">
                When you ask a question, our PostgreSQL pgvector engine searches only your selected college's published knowledge chunks.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
              <div className="h-10 w-10 rounded-xl bg-[#F59E0B]/10 flex items-center justify-center text-[#F59E0B] font-bold text-sm mb-4">
                03
              </div>
              <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">3. Grounded Citations</h3>
              <p className="text-xs text-[#A1A1AA] leading-relaxed">
                Answers are returned with green verification badges and clickable source links to the exact PDF page or webpage cited.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Main Features Grid */}
      <section className="py-20 px-4 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-xl mx-auto mb-14">
          <span className="text-xs text-[#10B981] font-mono uppercase tracking-wider block mb-1">
            Capabilities
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F5]">
            Engineered for Academic Accuracy
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
            <div className="h-10 w-10 rounded-xl bg-[#10B981]/10 flex items-center justify-center text-[#10B981] mb-4">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">Verified Badges</h3>
            <p className="text-xs text-[#A1A1AA] leading-relaxed">
              Every answer displays its verification status: Official Website, Admin Verified, or clearly marked Unverified AI Guidance.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
            <div className="h-10 w-10 rounded-xl bg-[#6366F1]/10 flex items-center justify-center text-[#6366F1] mb-4">
              <Globe className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">Multilingual Support</h3>
            <p className="text-xs text-[#A1A1AA] leading-relaxed">
              Full interface and conversational support in English, Hindi (हिन्दी), and Gujarati (ગુજરાતી) for maximum accessibility.
            </p>
          </div>

          <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114]">
            <div className="h-10 w-10 rounded-xl bg-[#F59E0B]/10 flex items-center justify-center text-[#F59E0B] mb-4">
              <Mic className="h-5 w-5" />
            </div>
            <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">Voice Input & Output</h3>
            <p className="text-xs text-[#A1A1AA] leading-relaxed">
              Speak your question directly using your microphone and listen to the assistant's answer with native text-to-speech.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-[#2A2A30] bg-[#111114] py-8 px-4">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#A1A1AA]">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-[#6366F1] flex items-center justify-center text-white font-bold text-xs">
              C
            </div>
            <span className="font-semibold text-[#F5F5F5]">AI FAQ Colleges Chatbot</span>
            <span>— Enterprise Multi-Tenant SaaS</span>
          </div>

          <div className="flex items-center gap-6">
            <Link href="/colleges" className="hover:text-[#F5F5F5] transition">
              Colleges Directory
            </Link>
            <Link href="/chat" className="hover:text-[#F5F5F5] transition">
              Chatbot
            </Link>
            <Link href="/login" className="hover:text-[#F5F5F5] transition">
              Student Sign In
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
