"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { College } from "@/types/college";
import { collegeService } from "@/services/college-service";
import { Building2, Globe, Mail, Phone, CheckCircle2, ArrowRight, Search, Shield } from "lucide-react";

export default function CollegesPage() {
  const router = useRouter();
  const [colleges, setColleges] = useState<College[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const currentSelected = localStorage.getItem("selected_college_id");
    if (currentSelected) setSelectedId(currentSelected);

    collegeService
      .getColleges(true)
      .then((res) => {
        if (res.success && res.data) {
          setColleges(res.data);
        } else {
          // Development seed fallback if database is empty locally
          setColleges([
            {
              id: "11111111-1111-1111-1111-111111111111",
              name: "Ahmedabad Institute of Technology",
              slug: "ait-college",
              official_domain: "aitindia.in",
              logo_url: null,
              contact_email: "admissions@aitindia.in",
              contact_phone: "+91-79-27663244",
              status: "APPROVED",
              is_active: true,
            },
            {
              id: "22222222-2222-2222-2222-222222222222",
              name: "RC Technical Institute",
              slug: "rcti-college",
              official_domain: "rcti.cteguj.org",
              logo_url: null,
              contact_email: "info@rcti.cteguj.org",
              contact_phone: "+91-79-27664785",
              status: "APPROVED",
              is_active: true,
            },
          ]);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSelectCollege = (college: College) => {
    localStorage.setItem("selected_college_id", college.id);
    localStorage.setItem("selected_college_name", college.name);
    setSelectedId(college.id);
    router.push("/chat");
  };

  const filteredColleges = colleges.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.official_domain.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="text-center max-w-2xl mx-auto mb-10">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#2A2A30] bg-[#111114] text-xs text-[#10B981] mb-3">
          <Shield className="h-3.5 w-3.5" />
          Multi-Tenant Institutional Scope
        </span>
        <h1 className="text-3xl font-bold tracking-tight text-[#F5F5F5] mb-2">
          Select Your College Institution
        </h1>
        <p className="text-xs sm:text-sm text-[#A1A1AA]">
          Questions you ask will be strictly grounded in the official knowledge base of your selected institution.
        </p>
      </div>

      {/* Search Input Bar */}
      <div className="max-w-md mx-auto mb-10">
        <div className="relative">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-[#A1A1AA]" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by college name or domain (e.g., aitindia.in)..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-xs text-[#F5F5F5] placeholder-[#A1A1AA]/50 focus:outline-none focus:border-[#6366F1] transition shadow-md"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-44 rounded-2xl border border-[#2A2A30] bg-[#111114] animate-pulse"></div>
          ))}
        </div>
      ) : filteredColleges.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-[#2A2A30] rounded-2xl bg-[#111114]">
          <Building2 className="h-10 w-10 text-[#A1A1AA] mx-auto mb-3 opacity-50" />
          <h3 className="text-sm font-semibold text-[#F5F5F5] mb-1">No Institutions Found</h3>
          <p className="text-xs text-[#A1A1AA]">
            No verified college matches your query "{search}". Try searching for another name or domain.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredColleges.map((college) => {
            const isSelected = selectedId === college.id;
            return (
              <div
                key={college.id}
                onClick={() => handleSelectCollege(college)}
                className={`p-6 rounded-2xl border cursor-pointer transition flex flex-col justify-between ${
                  isSelected
                    ? "border-[#6366F1] bg-[#111114] shadow-xl shadow-[#6366F1]/10"
                    : "border-[#2A2A30] bg-[#111114] hover:border-[#6366F1]/50"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-11 w-11 rounded-xl bg-[#1F1F23] flex items-center justify-center text-[#6366F1]">
                      <Building2 className="h-6 w-6" />
                    </div>
                    {isSelected && (
                      <span className="inline-flex items-center gap-1 text-[11px] text-[#10B981] bg-[#10B981]/10 px-2.5 py-1 rounded-full border border-[#10B981]/20 font-medium">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Selected Institution
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-semibold text-[#F5F5F5] mb-2">{college.name}</h3>

                  <div className="space-y-1.5 text-xs text-[#A1A1AA] mb-6">
                    <div className="flex items-center gap-2">
                      <Globe className="h-3.5 w-3.5 text-[#6366F1]" />
                      <span className="font-mono">{college.official_domain}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="h-3.5 w-3.5 text-[#6366F1]" />
                      <span>{college.contact_email}</span>
                    </div>
                    {college.contact_phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-[#6366F1]" />
                        <span>{college.contact_phone}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-4 border-t border-[#2A2A30] flex items-center justify-between text-xs font-medium text-[#6366F1]">
                  <span>{isSelected ? "Open Chat Interface" : "Select this institution"}</span>
                  <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
