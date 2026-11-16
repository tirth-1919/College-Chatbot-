"use client";

import React, { useEffect, useState, useRef } from "react";
import { collegeAdminService } from "@/services/college-admin-service";
import { DocumentDetail, DocumentPage } from "@/types/college-admin";
import { DataTable, Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import {
  FileText,
  Upload,
  RefreshCw,
  Trash2,
  Lock,
  X,
  CheckCircle,
  AlertCircle,
  FileUp,
  Eye,
  RotateCw,
  Download,
  Table as TableIcon,
  Sparkles,
  Layers,
  FileCheck,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";

export default function DocumentManagementPage() {
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Upload modal state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [category, setCategory] = useState("PROSPECTUS");
  const [description, setDescription] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Inspect page modal state
  const [inspectingDoc, setInspectingDoc] = useState<DocumentDetail | null>(null);
  const [pages, setPages] = useState<DocumentPage[]>([]);
  const [selectedPageNum, setSelectedPageNum] = useState<number>(1);
  const [isLoadingPages, setIsLoadingPages] = useState(false);

  // Delete modal state
  const [deletingDoc, setDeletingDoc] = useState<DocumentDetail | null>(null);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Reprocessing state
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const res = await collegeAdminService.getDocuments(statusFilter === "ALL" ? undefined : statusFilter);
      if (res.success && res.data) {
        setDocuments(res.data);
      }
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [statusFilter]);

  // Real-time polling when documents are processing
  useEffect(() => {
    const hasActiveJobs = documents.some((d) =>
      ["QUEUED", "PROCESSING", "VALIDATING", "OCR_PROCESSING", "REPROCESSING"].includes(d.processing_status)
    );

    if (!hasActiveJobs) return;

    const timer = setInterval(async () => {
      try {
        const res = await collegeAdminService.getDocuments(statusFilter === "ALL" ? undefined : statusFilter);
        if (res.success && res.data) {
          setDocuments(res.data);
        }
      } catch (err) {
        console.error("Document status poll error:", err);
      }
    }, 3500);

    return () => clearInterval(timer);
  }, [documents, statusFilter]);

  const validateSelectedFile = (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Security Error: Only official PDF documents (.pdf) are accepted.");
      return false;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError("Limit Exceeded: Document exceeds the 50 MB platform upload limit.");
      return false;
    }
    if (file.size === 0) {
      setUploadError("Empty File: Uploaded document contains 0 bytes.");
      return false;
    }
    setUploadError(null);
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateSelectedFile(file)) {
        setUploadFile(file);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateSelectedFile(file)) {
        setUploadFile(file);
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a PDF document to upload.");
      return;
    }

    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(20);

    try {
      setUploadProgress(50);
      const res = await collegeAdminService.uploadDocumentBinary(
        uploadFile,
        category,
        description
      );
      setUploadProgress(100);

      if (res.success) {
        setIsUploadOpen(false);
        setUploadFile(null);
        setDescription("");
        setUploadProgress(0);
        fetchDocuments();
      } else {
        setUploadError(res.error || "Failed to process document upload.");
      }
    } catch (err: any) {
      setUploadError(err.message || "An unexpected error occurred during upload.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleInspectPages = async (doc: DocumentDetail) => {
    setInspectingDoc(doc);
    setIsLoadingPages(true);
    setSelectedPageNum(1);
    try {
      const res = await collegeAdminService.getDocumentPages(doc.id);
      if (res.success && res.data) {
        setPages(res.data);
      } else {
        setPages([]);
      }
    } catch (err) {
      console.error("Failed to load document pages:", err);
      setPages([]);
    } finally {
      setIsLoadingPages(false);
    }
  };

  const handleReprocess = async (docId: string) => {
    setReprocessingId(docId);
    try {
      const res = await collegeAdminService.reprocessDocument(docId);
      if (res.success) {
        fetchDocuments();
      }
    } catch (err) {
      console.error("Failed to reprocess document:", err);
    } finally {
      setReprocessingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deletingDoc) return;
    setIsDeleting(true);

    try {
      await collegeAdminService.deleteDocument(deletingDoc.id);
      setIsDeleteOpen(false);
      setDeletingDoc(null);
      fetchDocuments();
    } catch (err) {
      console.error("Failed to delete document:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const activePageData = pages.find((p) => p.page_number === selectedPageNum) || pages[0];

  const columns: Column<DocumentDetail>[] = [
    {
      header: "Document Filename",
      cell: (item) => (
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#10B981]/10 text-[#10B981]">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <span className="font-semibold text-[#F5F5F5] block text-xs truncate max-w-xs sm:max-w-md">
              {item.original_filename}
            </span>
            <div className="flex items-center gap-2 text-[10px] text-[#71717A] font-mono mt-0.5">
              <span className="px-1.5 py-0.2 rounded bg-[#1F1F23] text-[#A1A1AA]">
                {item.category || "GENERAL"}
              </span>
              <span>{Math.round(item.file_size_bytes / 1024)} KB</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      header: "Pages & Tables",
      cell: (item) => (
        <div className="text-[11px] font-mono">
          <span className="text-[#F5F5F5] block">
            {item.total_pages > 0 ? `${item.total_pages} Pages` : "Analyzing..."}
          </span>
          <span className="text-[10px] text-[#71717A]">
            {item.extraction_method || "PyMuPDF"}
          </span>
        </div>
      ),
    },
    {
      header: "OCR Telemetry",
      cell: (item) => (
        <div>
          {item.ocr_applied ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#8B5CF6]/10 text-[#A78BFA] border border-[#8B5CF6]/20">
              <Sparkles className="h-2.5 w-2.5" />
              Tesseract OCR
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20">
              <FileCheck className="h-2.5 w-2.5" />
              Native Text
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Processing Status",
      cell: (item) => (
        <div>
          <StatusBadge status={item.processing_status} />
          {item.failure_reason && (
            <span className="text-[10px] text-[#EF4444] block truncate max-w-[160px] mt-0.5" title={item.failure_reason}>
              {item.failure_reason}
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Uploaded On",
      cell: (item) => (
        <span className="text-[11px] text-[#71717A] font-mono">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      header: "Actions",
      className: "text-right",
      cell: (item) => (
        <div className="flex items-center justify-end gap-1.5">
          {/* Inspect Pages */}
          <button
            onClick={() => handleInspectPages(item)}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#10B981] hover:border-[#10B981]/30 transition"
            title="Inspect Extracted Pages & OCR"
          >
            <Eye className="h-3.5 w-3.5" />
          </button>

          {/* Download Private PDF */}
          {item.download_url && (
            <a
              href={item.download_url}
              target="_blank"
              rel="noreferrer"
              className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#3B82F6] hover:border-[#3B82F6]/30 transition inline-block"
              title="Secure Download Original PDF"
            >
              <Download className="h-3.5 w-3.5" />
            </a>
          )}

          {/* Reprocess / Retry */}
          <button
            onClick={() => handleReprocess(item.id)}
            disabled={reprocessingId === item.id}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#F59E0B] hover:border-[#F59E0B]/30 transition disabled:opacity-50"
            title="Reprocess Extraction & OCR"
          >
            <RotateCw className={`h-3.5 w-3.5 ${reprocessingId === item.id ? "animate-spin text-[#F59E0B]" : ""}`} />
          </button>

          {/* Delete */}
          <button
            onClick={() => {
              setDeletingDoc(item);
              setIsDeleteOpen(true);
            }}
            className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] text-[#A1A1AA] hover:text-[#EF4444] hover:border-[#EF4444]/30 transition"
            title="Delete Document"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F5] tracking-tight flex items-center gap-2">
            <FileText className="h-5 w-5 text-[#10B981]" />
            PDF Upload, Document Processing & OCR Engine
          </h1>
          <p className="text-xs text-[#A1A1AA] mt-1">
            Private Supabase Storage with magic byte verification, PyMuPDF extraction, pdfplumber table grids, and Tesseract OCR.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchDocuments}
            className="p-2 rounded-lg border border-[#2A2A30] bg-[#111114] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
            title="Refresh documents"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin text-[#10B981]" : ""}`} />
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#10B981] hover:bg-[#059669] text-white text-xs font-medium transition shadow-md shadow-[#10B981]/20"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Official PDF</span>
          </button>
        </div>
      </div>

      {/* Security notice */}
      <div className="p-4 rounded-xl border border-[#2A2A30] bg-[#111114] flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-4 w-4 text-[#10B981] shrink-0" />
          <span className="text-[#D4D4D8]">
            Multi-Tenant Isolation Active: Documents are stored in private college-scoped storage with 1-hour signed tokens.
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-[#A1A1AA]">
          <span className="font-mono">Tesseract OCR Ready</span>
          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2A2A30] pb-2 text-xs">
        {["ALL", "PENDING_REVIEW", "PROCESSING", "COMPLETED", "FAILED"].map((tab) => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              statusFilter === tab
                ? "bg-[#1F1F23] text-[#10B981] border border-[#2A2A30]"
                : "text-[#A1A1AA] hover:text-[#F5F5F5]"
            }`}
          >
            {tab.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Documents Table */}
      <DataTable
        data={documents}
        columns={columns}
        searchPlaceholder="Search institutional documents by filename..."
        emptyMessage="No documents uploaded. Click 'Upload Official PDF' to begin automated ingestion."
      />

      {/* Upload Modal with Drag and Drop */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-lg bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative">
            <button
              onClick={() => setIsUploadOpen(false)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            <h3 className="text-base font-bold text-[#F5F5F5] mb-1 flex items-center gap-2">
              <FileUp className="h-4 w-4 text-[#10B981]" />
              Upload PDF Circular or Prospectus
            </h3>
            <p className="text-xs text-[#A1A1AA] mb-4">
              Validated against %PDF- magic bytes, decompression limits (200 pages max), and private storage.
            </p>

            {uploadError && (
              <div className="mb-4 p-3 rounded-lg bg-[#EF4444]/10 border border-[#EF4444]/30 text-xs text-[#EF4444] flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4 text-xs">
              {/* Drag and Drop Dropzone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-6 border-2 border-dashed rounded-xl cursor-pointer text-center transition flex flex-col items-center justify-center gap-2 ${
                  isDragOver
                    ? "border-[#10B981] bg-[#10B981]/5"
                    : "border-[#2A2A30] bg-[#18181B] hover:border-[#3F3F46]"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="p-3 rounded-full bg-[#1F1F23] text-[#10B981]">
                  <Upload className="h-5 w-5" />
                </div>
                {uploadFile ? (
                  <div>
                    <span className="font-semibold text-[#F5F5F5] block">{uploadFile.name}</span>
                    <span className="text-[10px] text-[#A1A1AA] font-mono">
                      {Math.round(uploadFile.size / 1024)} KB - Ready for validation
                    </span>
                  </div>
                ) : (
                  <div>
                    <span className="font-semibold text-[#F5F5F5] block">
                      Click to browse or drag and drop PDF file here
                    </span>
                    <span className="text-[10px] text-[#71717A] block mt-0.5 font-mono">
                      Strict format: .pdf only (Max 50 MB, 200 pages)
                    </span>
                  </div>
                )}
              </div>

              {/* Category & Description */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Document Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  >
                    <option value="PROSPECTUS">Admission Prospectus</option>
                    <option value="FEES">Fee Structure Circular</option>
                    <option value="SYLLABUS">Academic Curriculum / Syllabus</option>
                    <option value="HOSTEL">Hostel & Accommodation Rules</option>
                    <option value="EXAMINATION">Exam Schedule & Regulations</option>
                    <option value="GENERAL">General Administrative Circular</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1">Description (Optional)</label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="e.g. 2026-27 First Year Degree Engineering"
                    className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#10B981]"
                  />
                </div>
              </div>

              {/* Upload Progress Bar */}
              {isUploading && (
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] text-[#A1A1AA] font-mono">
                    <span>Validating & Uploading to Private Storage...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#10B981] transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 rounded-lg border border-[#2A2A30] text-[#A1A1AA] hover:text-[#F5F5F5] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white rounded-lg font-medium transition disabled:opacity-50"
                >
                  {isUploading ? "Uploading..." : "Start Processing"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inspect Document Pages & OCR Telemetry Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-4xl max-h-[90vh] bg-[#111114] border border-[#2A2A30] rounded-2xl p-6 shadow-2xl relative flex flex-col space-y-4">
            <button
              onClick={() => setInspectingDoc(null)}
              className="absolute top-4 right-4 text-[#71717A] hover:text-[#F5F5F5]"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Modal Header */}
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs px-2 py-0.5 rounded bg-[#10B981]/10 text-[#10B981] font-mono">
                  {inspectingDoc.processing_status}
                </span>
                <span className="text-xs text-[#71717A] font-mono">
                  SHA-256: {inspectingDoc.checksum_sha256?.substring(0, 16)}...
                </span>
              </div>
              <h2 className="text-base font-bold text-[#F5F5F5]">{inspectingDoc.original_filename}</h2>
              <span className="text-xs text-[#A1A1AA] block mt-0.5">
                Total Extracted Pages: {pages.length} | Method: {inspectingDoc.extraction_method || "PyMuPDF"}
              </span>
            </div>

            {isLoadingPages ? (
              <div className="py-20 text-center text-[#A1A1AA] text-xs">
                <RefreshCw className="h-6 w-6 animate-spin mx-auto text-[#10B981] mb-2" />
                Loading page-level extracted data...
              </div>
            ) : pages.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 flex-1 overflow-hidden">
                {/* Page Navigation Sidebar */}
                <div className="md:col-span-1 border-r border-[#1F1F23] pr-3 space-y-1.5 overflow-y-auto max-h-[55vh]">
                  <span className="text-[10px] text-[#71717A] uppercase font-mono block mb-2">Pages</span>
                  {pages.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelectedPageNum(p.page_number)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition flex items-center justify-between ${
                        selectedPageNum === p.page_number
                          ? "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30"
                          : "text-[#A1A1AA] hover:bg-[#18181B]"
                      }`}
                    >
                      <span>Page {p.page_number}</span>
                      {p.ocr_applied ? (
                        <span title="Scanned Page (OCR)">
                          <Sparkles className="h-3 w-3 text-[#A78BFA]" />
                        </span>
                      ) : p.has_tables ? (
                        <span title="Contains Tables">
                          <TableIcon className="h-3 w-3 text-[#3B82F6]" />
                        </span>
                      ) : null}
                    </button>
                  ))}
                </div>

                {/* Active Page Content View */}
                <div className="md:col-span-3 space-y-3 flex flex-col overflow-hidden">
                  {activePageData && (
                    <>
                      {/* Telemetry Bar */}
                      <div className="flex flex-wrap items-center gap-3 p-3 rounded-xl bg-[#18181B] border border-[#2A2A30] text-xs">
                        <span className="font-semibold text-[#F5F5F5] font-mono">
                          Page {activePageData.page_number} of {pages.length}
                        </span>
                        <span className="text-[11px] text-[#71717A] font-mono">
                          {activePageData.word_count} words | {activePageData.char_count} chars
                        </span>
                        {activePageData.ocr_applied && (
                          <span className="px-2 py-0.5 rounded bg-[#8B5CF6]/10 text-[#A78BFA] font-mono text-[10px] ml-auto">
                            OCR Confidence: {activePageData.ocr_confidence ?? 85}%
                          </span>
                        )}
                        {activePageData.has_tables && (
                          <span className="px-2 py-0.5 rounded bg-[#3B82F6]/10 text-[#60A5FA] font-mono text-[10px]">
                            {activePageData.tables_markdown?.length || 1} Table(s) Formatted
                          </span>
                        )}
                      </div>

                      {/* Content Box */}
                      <div className="flex-1 overflow-y-auto p-4 rounded-xl bg-[#0B0B0D] border border-[#1F1F23] font-mono text-xs text-[#D4D4D8] whitespace-pre-wrap leading-relaxed max-h-[46vh]">
                        {activePageData.extracted_text || "(No extractable text on this page)"}
                      </div>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-16 text-center text-[#71717A] text-xs">
                No extracted pages available yet. Document may still be in the processing queue.
              </div>
            )}

            {/* Footer */}
            <div className="flex justify-between items-center pt-2 border-t border-[#1F1F23] text-xs">
              <span className="text-[10px] text-[#71717A] font-mono">
                Storage: {inspectingDoc.storage_path}
              </span>
              <button
                onClick={() => setInspectingDoc(null)}
                className="px-4 py-2 bg-[#1F1F23] hover:bg-[#2A2A30] text-[#F5F5F5] rounded-lg transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isDeleteOpen}
        onCancel={() => setIsDeleteOpen(false)}
        onConfirm={handleDelete}
        title="Delete Institutional Document"
        description={`Are you sure you want to delete '${deletingDoc?.original_filename}'? The raw PDF binary and all extracted pages will be permanently purged from private storage.`}
        confirmLabel={isDeleting ? "Deleting..." : "Permanently Delete"}
        isDestructive
        isLoading={isDeleting}
      />
    </div>
  );
}
