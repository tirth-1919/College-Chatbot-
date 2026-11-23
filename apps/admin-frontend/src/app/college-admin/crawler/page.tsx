"use client";

import React, { useEffect, useState, useRef } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { CrawlJob, CrawlEvent, WebsiteSource, WebsitePage } from "@/types/college-admin";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Activity,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  Globe,
  Terminal,
  FileCode,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  Eye,
  X,
  Hash,
  Clock,
  Layers,
} from "lucide-react";

export default function CrawlerManagementPage() {
  const [sources, setSources] = useState<WebsiteSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("");
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [activeJob, setActiveJob] = useState<CrawlJob | null>(null);
  const [events, setEvents] = useState<CrawlEvent[]>([]);
  const [pages, setPages] = useState<WebsitePage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [selectedPage, setSelectedPage] = useState<WebsitePage | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const hasLiveJobs = jobs.some((job) => job.status === "PENDING" || job.status === "RUNNING");

  const getJobProgress = (job: CrawlJob) => {
    if (job.status === "COMPLETED") return 100;
    const total = Math.max(0, job.pages_discovered);
    if (total === 0) return 0;
    const processed = Math.max(0, job.pages_crawled) + Math.max(0, job.pages_failed);
    const percent = Math.min(100, Math.round((processed / total) * 100));
    return job.status === "RUNNING" ? Math.min(95, percent) : percent;
  };

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [sourcesRes, jobsRes, pagesRes] = await Promise.all([
        collegeAdminService.getWebsites(),
        collegeAdminService.getCrawlJobs(),
        collegeAdminService.getCrawledPages(),
      ]);

      if (sourcesRes.success && sourcesRes.data) {
        setSources(sourcesRes.data);
        if (sourcesRes.data.length > 0 && !selectedSourceId) {
          setSelectedSourceId(sourcesRes.data[0].id);
        }
      }

      if (jobsRes.success && jobsRes.data) {
        setJobs(jobsRes.data);
        const runningOrFirst = jobsRes.data.find((j) => j.status === "RUNNING") || jobsRes.data[0];
        if (runningOrFirst) {
          setActiveJob(runningOrFirst);
          loadEvents(runningOrFirst.id);
        }
      }

      if (pagesRes.success && pagesRes.data) {
        setPages(pagesRes.data);
      }
    } catch (err) {
      console.error("Failed to load crawler console:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadEvents = async (jobId: string) => {
    try {
      const res = await collegeAdminService.getCrawlEvents(jobId);
      if (res.success && res.data) {
        setEvents(res.data);
      }
    } catch (err) {
      console.error("Failed to load crawl events:", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Keep the full job list and selected job telemetry fresh while any crawl is queued or running.
  useEffect(() => {
    if (!hasLiveJobs) return;

    const timer = setInterval(async () => {
      try {
        const [jobsRes, pagesRes] = await Promise.all([
          collegeAdminService.getCrawlJobs(),
          collegeAdminService.getCrawledPages(),
        ]);
        if (jobsRes.success && jobsRes.data) {
          setJobs(jobsRes.data);
          const current = jobsRes.data.find((j) => j.id === activeJob?.id) || jobsRes.data.find((j) => j.status === "RUNNING") || jobsRes.data[0];
          if (current) {
            setActiveJob(current);
            loadEvents(current.id);
          }
        }
        if (pagesRes.success && pagesRes.data) {
          setPages(pagesRes.data);
        }
      } catch (err) {
        console.error("Crawler telemetry poll error:", err);
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [hasLiveJobs, activeJob?.id]);

  const handleStartCrawl = async () => {
    if (!selectedSourceId) return;
    setIsStarting(true);
    try {
      const res = await collegeAdminService.startCrawl(selectedSourceId);
      if (res.success && res.data) {
        setActiveJob(res.data);
        fetchData();
      }
    } catch (err) {
      console.error("Failed to dispatch crawl:", err);
    } finally {
      setIsStarting(false);
    }
  };

  const handleControlJob = async (action: "PAUSE" | "RESUME" | "CANCEL") => {
    if (!activeJob) return;
    try {
      const res = await collegeAdminService.controlCrawl(activeJob.id, action);
      if (res.success && res.data) {
        setActiveJob(res.data);
        fetchData();
      }
    } catch (err) {
      console.error(`Failed to ${action} job:`, err);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <Activity className="h-5 w-5 text-[#10B981]" />
            Official Website Crawler Engine & Execution Console
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            SSRF-protected, tenant-scoped crawler with robots.txt adherence, structured table extraction, and content deduplication.
          </p>
        </div>

        <button
          onClick={fetchData}
          className="self-start sm:self-auto p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
          title="Refresh crawler state"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin text-[#10B981]" : ""}`} />
        </button>
      </div>

      {/* Crawl Trigger Control Bar */}
      <div className="p-5 rounded-2xl border border-[#2A2A30] bg-[#111114] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#10B981]/10 text-[#10B981]">
            <Globe className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-semibold text-[#F5F5F5] block">
              Select Official Target Website
            </span>
            <span className="text-[11px] text-[#A1A1AA]">
              Choose registered URL source to begin asynchronous discovery
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedSourceId}
            onChange={(e) => setSelectedSourceId(e.target.value)}
            className="flex-1 md:w-80 bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
          >
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.base_url} (Max {s.max_pages} pages, depth {s.max_depth})
              </option>
            ))}
          </select>

          <button
            onClick={handleStartCrawl}
            disabled={isStarting || !selectedSourceId}
            className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg text-xs font-medium transition flex items-center gap-2 shrink-0 shadow-md shadow-[#10B981]/20 disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{isStarting ? "Dispatching..." : "Start Crawl"}</span>
          </button>
        </div>
      </div>

      {/* Live crawl progress for every recent job */}
      <section className="p-5 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-4" aria-labelledby="crawl-progress-heading">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 id="crawl-progress-heading" className="text-sm font-semibold text-[#F5F5F5]">All Crawl Progress</h2>
            <p className="text-[11px] text-[#A1A1AA] mt-1">Live status for the latest {jobs.length} crawl jobs. Queued jobs begin progressing when a crawler worker picks them up.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] font-mono">
            {(["RUNNING", "PENDING", "COMPLETED", "FAILED"] as const).map((status) => (
              <span key={status} className="px-2 py-1 rounded-md bg-[#18181B] border border-[#2A2A30] text-[#A1A1AA]">
                {status} {jobs.filter((job) => job.status === status).length}
              </span>
            ))}
          </div>
        </div>

        {jobs.length > 0 ? (
          <div className="space-y-2">
            {jobs.map((job) => {
              const percent = getJobProgress(job);
              const isSelected = activeJob?.id === job.id;
              const isLive = job.status === "PENDING" || job.status === "RUNNING";
              return (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => { setActiveJob(job); loadEvents(job.id); }}
                  className={`w-full text-left p-3 rounded-xl border transition ${isSelected ? "border-[#10B981]/50 bg-[#10B981]/5" : "border-[#2A2A30] bg-[#18181B] hover:border-[#3F3F46]"}`}
                  aria-label={`View crawl job ${job.id}, ${job.status}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div className="min-w-0">
                      <span className="block text-xs font-semibold text-[#F5F5F5] truncate">{job.base_url || `Crawl job ${job.id.slice(0, 8)}`}</span>
                      <span className="text-[10px] text-[#71717A] font-mono">{job.id.slice(0, 8)} · {new Date(job.created_at).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={job.status} />
                      <span className="text-[10px] text-[#A1A1AA] font-mono min-w-10 text-right">{percent}%</span>
                    </div>
                  </div>
                  <div
                    className="h-2 w-full overflow-hidden rounded-full bg-[#2A2A30]"
                    role="progressbar"
                    aria-label={`Crawl progress ${job.id}`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percent}
                  >
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${job.status === "FAILED" ? "bg-[#EF4444]" : job.status === "COMPLETED" ? "bg-[#10B981]" : job.status === "PENDING" ? "bg-[#F59E0B]/70" : "bg-[#10B981]"} ${job.status === "RUNNING" && job.pages_discovered === 0 ? "w-1/3 animate-pulse" : ""}`}
                      style={job.status === "RUNNING" && job.pages_discovered === 0 ? undefined : { width: `${percent}%` }}
                    />
                  </div>
                  <div className="flex justify-between gap-2 mt-1.5 text-[10px] text-[#71717A] font-mono">
                    <span>{job.status === "PENDING" ? "Waiting for worker" : job.status === "RUNNING" && job.pages_discovered === 0 ? "Discovering pages…" : `${job.pages_crawled + job.pages_failed} / ${job.pages_discovered} pages processed`}</span>
                    <span>{job.pages_crawled} crawled · {job.pages_failed} failed</span>
                  </div>
                  {job.failure_reason && <p className="text-[10px] text-[#EF4444] mt-1 break-words">{job.failure_reason}</p>}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-xs text-[#71717A]">No crawl jobs yet. Start a crawl to see its progress here.</div>
        )}
      </section>

      {/* Active Job Telemetry Panel */}
      {activeJob && (
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] text-[#A1A1AA] font-mono">
                  Job ID: {activeJob.id}
                </span>
                <StatusBadge status={activeJob.status} />
              </div>
              <h3 className="text-base font-bold text-[#F5F5F5]">
                {activeJob.status === "RUNNING"
                  ? "Crawling Target Web Domain (Polite Throttling Active)..."
                  : activeJob.status === "COMPLETED"
                  ? "Crawl Execution Finished Successfully"
                  : activeJob.status === "PAUSED"
                  ? "Crawl Execution Suspended"
                  : `Crawl Job State: ${activeJob.status}`}
              </h3>
            </div>

            <div className="flex items-center gap-2">
              {activeJob.status === "RUNNING" && (
                <button
                  onClick={() => handleControlJob("PAUSE")}
                  className="px-3 py-1.5 rounded-lg border border-[#F59E0B]/30 bg-[#F59E0B]/10 hover:bg-[#F59E0B]/20 text-[#F59E0B] text-xs font-medium transition flex items-center gap-1.5"
                >
                  <Pause className="h-3.5 w-3.5" />
                  <span>Pause</span>
                </button>
              )}
              {activeJob.status === "PAUSED" && (
                <button
                  onClick={() => handleControlJob("RESUME")}
                  className="px-3 py-1.5 rounded-lg border border-[#10B981]/30 bg-[#10B981]/10 hover:bg-[#10B981]/20 text-[#10B981] text-xs font-medium transition flex items-center gap-1.5"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>Resume</span>
                </button>
              )}
              {(activeJob.status === "RUNNING" || activeJob.status === "PAUSED") && (
                <button
                  onClick={() => handleControlJob("CANCEL")}
                  className="px-3 py-1.5 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 hover:bg-[#EF4444]/20 text-[#EF4444] text-xs font-medium transition flex items-center gap-1.5"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  <span>Cancel</span>
                </button>
              )}
            </div>
          </div>

          {/* Progress Counters 3x Grid */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-xl bg-[#18181B] border border-[#2A2A30]">
              <span className="text-[10px] text-[#71717A] uppercase font-mono block">Discovered Links</span>
              <span className="text-xl font-bold text-[#F5F5F5] font-mono">{activeJob.pages_discovered}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#18181B] border border-[#2A2A30]">
              <span className="text-[10px] text-[#71717A] uppercase font-mono block">Pages Ingested</span>
              <span className="text-xl font-bold text-[#10B981] font-mono">{activeJob.pages_crawled}</span>
            </div>
            <div className="p-3 rounded-xl bg-[#18181B] border border-[#2A2A30]">
              <span className="text-[10px] text-[#71717A] uppercase font-mono block">Failed URLs</span>
              <span className="text-xl font-bold text-[#EF4444] font-mono">{activeJob.pages_failed}</span>
            </div>
          </div>
        </div>
      )}

      {/* Two Column Grid: Real-time Event Logs & Extracted Web Pages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Real-time Crawl Log Terminal */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-[#10B981]" />
              <h3 className="text-sm font-semibold text-[#F5F5F5]">Crawler Log Stream</h3>
            </div>
            <span className="text-[10px] text-[#71717A] font-mono">STDOUT / EVENTS</span>
          </div>

          <div
            ref={logContainerRef}
            className="h-80 overflow-y-auto p-4 rounded-xl bg-[#0B0B0D] border border-[#1F1F23] font-mono text-[11px] space-y-2 text-[#D4D4D8]"
          >
            {events.length > 0 ? (
              events.map((e) => (
                <div key={e.id} className="flex items-start gap-2">
                  <span className="text-[#71717A] shrink-0">
                    [{new Date(e.created_at).toLocaleTimeString()}]
                  </span>
                  <span
                    className={`font-semibold shrink-0 ${
                      e.log_level === "ERROR"
                        ? "text-[#EF4444]"
                        : e.log_level === "WARNING"
                        ? "text-[#F59E0B]"
                        : e.log_level === "SUCCESS"
                        ? "text-[#10B981]"
                        : "text-[#3B82F6]"
                    }`}
                  >
                    {e.log_level}
                  </span>
                  <span className="text-[#F5F5F5] break-words">{e.message}</span>
                </div>
              ))
            ) : (
              <div className="py-12 text-center text-[#71717A]">
                No crawler events emitted yet. Trigger a crawl to start execution logs.
              </div>
            )}
          </div>
        </div>

        {/* Extracted Web Pages Inspector */}
        <div className="p-6 rounded-2xl border border-[#2A2A30] bg-[#111114] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-[#3B82F6]" />
              <h3 className="text-sm font-semibold text-[#F5F5F5]">Extracted Web Pages</h3>
            </div>
            <span className="text-[10px] text-[#71717A] font-mono">{pages.length} Pages Parsed</span>
          </div>

          <div className="h-80 overflow-y-auto divide-y divide-[#1F1F23] pr-2">
            {pages.length > 0 ? (
              pages.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setSelectedPage(p)}
                  className="py-3 px-2 rounded-lg hover:bg-[#18181B] cursor-pointer transition space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#F5F5F5] truncate max-w-xs">
                      {p.title || "Untitled Institutional Page"}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] font-mono">
                      HTTP {p.http_status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-[#71717A] font-mono">
                    <span className="truncate max-w-[280px]">{p.url}</span>
                    <span className="text-[#10B981]">SHA: {p.content_hash.substring(0, 8)}</span>
                  </div>
                  <p className="text-[11px] text-[#A1A1AA] line-clamp-1 italic">
                    "{p.cleaned_text.substring(0, 100)}..."
                  </p>
                </div>
              ))
            ) : (
              <div className="py-12 text-center text-[#71717A] text-xs">
                No web pages parsed yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Crawled Page Inspection Modal */}
      {selectedPage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-3xl max-h-[85vh] bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative flex flex-col space-y-4">
            <button
              onClick={() => setSelectedPage(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-2 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] font-mono">
                  HTTP {selectedPage.http_status}
                </span>
                <span className="text-xs text-[#71717A] font-mono">
                  SHA-256: {selectedPage.content_hash}
                </span>
              </div>
              <h2 className="text-base font-bold text-[#F5F5F5]">{selectedPage.title}</h2>
              <a
                href={selectedPage.url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[#3B82F6] hover:underline font-mono flex items-center gap-1 mt-1"
              >
                {selectedPage.url}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>

            {selectedPage.meta_description && (
              <div className="p-3 rounded-lg bg-[#18181B] border border-[#2A2A30] text-xs text-[#A1A1AA]">
                <span className="text-[10px] text-[#71717A] uppercase font-mono block mb-1">Meta Description</span>
                {selectedPage.meta_description}
              </div>
            )}

            <div className="flex-1 overflow-y-auto space-y-2">
              <span className="text-[10px] text-[#71717A] uppercase font-mono block">Extracted Clean Content</span>
              <div className="p-4 rounded-xl bg-[#0B0B0D] border border-[#1F1F23] font-mono text-xs text-[#D4D4D8] whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                {selectedPage.cleaned_text}
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#1F1F23]">
              <button
                onClick={() => setSelectedPage(null)}
                className="px-4 py-2 bg-[#1F1F23] hover:bg-[#2A2A30] text-[#F5F5F5] rounded-lg text-xs font-medium transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
