# Phase 8: PDF Upload, Document Processing & OCR Engine

## Overview

Phase 8 introduces the institutional PDF document ingestion and Optical Character Recognition (OCR) pipeline for the AI FAQ College Chatbot platform. It allows College Administrators to securely upload official prospectuses, fee circulars, syllabus booklets, and hostel guidelines in PDF format.

The engine deconstructs multi-page PDFs, formats structured tabular grids into Markdown, detects scanned/image-heavy pages, and extracts high-accuracy text using **PyMuPDF**, **pdfplumber**, and **Tesseract OCR**. All raw files are stored in private, college-scoped storage with time-limited signed access URLs.

---

## 1. Document Processing Architecture

```
┌────────────────────────────────────────────────────────┐
│             College Admin Dashboard                    │
│          (/college-admin/documents)                    │
└─────────────────────────┬──────────────────────────────┘
                          │ Multipart PDF Binary
                          ▼
┌────────────────────────────────────────────────────────┐
│             FastAPI Backend Engine                     │
│  - Magic Bytes Check (%PDF-)                           │
│  - MIME & Path Traversal Sanitization                  │
│  - Decompression Bomb Defense (Max 50MB, 200 Pages)    │
│  - SHA-256 Binary Checksum Generation                  │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            ▼                                ▼
┌───────────────────────┐        ┌───────────────────────┐
│ Private Storage       │        │ PostgreSQL DB         │
│ Bucket:               │        │ documents table       │
│ college-documents/    │        │ (status: QUEUED)      │
│ {college_id}/{doc_id} │        └───────────────────────┘
└───────────┬───────────┘
            │
            ▼
┌────────────────────────────────────────────────────────┐
│             Celery / Background Processing             │
│            (tasks.process_pdf_document_task)           │
├────────────────────────────────────────────────────────┤
│ 1. PyMuPDF (fitz) Text Flow Extraction                 │
│ 2. pdfplumber Tabular Grid Parsing -> Markdown         │
│ 3. Scanned Page Detection (< 50 characters)            │
│ 4. Tesseract OCR with Average Confidence Scoring       │
│ 5. Page-by-Page Database Recording (document_pages)    │
│ 6. Status Update -> PENDING_REVIEW                     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Security & Anti-Malware Safeguards

1. **Magic Byte Signature Verification:**
   - Evaluates the initial 1024 bytes of every uploaded file for the official `%PDF-` signature (`0x25 0x50 0x44 0x46 0x2D`).
   - Renamed executables (`.exe`), archives (`.zip`), HTML files, or scripts with `.pdf` extensions are blocked immediately.
2. **Decompression Bomb Defense:**
   - Strict 50 MB platform upload limit.
   - Enforces a 200-page threshold per document via PyMuPDF header inspection before executing full rasterization or OCR.
3. **Path Traversal Defense:**
   - Filenames are sanitized, stripping `../`, `..\`, null bytes, and operating-system-reserved characters.
4. **Encrypted / Password-Locked PDF Rejection:**
   - Checks `doc.is_encrypted` and rejects locked files with human-friendly guidance rather than crashing worker threads.
5. **Private Multi-Tenant Storage:**
   - Storage paths are strictly partitioned: `colleges/{college_id}/{document_id}.pdf`.
   - Files are never publicly exposed. Downloads and previews require short-lived cryptographic signed URLs (1-hour expiry).

---

## 3. Extraction & OCR Strategy

| Processing Stage | Tool / Library | Role & Functionality |
| :--- | :--- | :--- |
| **Header & Text Extraction** | **PyMuPDF (`fitz`)** | Fast C-based text extraction, document metadata parsing, and raster pixmap generation. |
| **Tabular Content** | **pdfplumber** | Deconstructs table grids (e.g. tuition fees, seat intake matrices) into structured Markdown tables. |
| **Scanned Page Detection** | Content Analyzer | Evaluates character density. Pages containing `< 50` characters of extractable text are flagged as scanned. |
| **Optical Character Recognition** | **Tesseract OCR (`pytesseract`)** | Renders 200 DPI image pixmaps of scanned pages and extracts text with per-word character confidence scoring. |

---

## 4. Document Processing Lifecycle State Machine

```
              ┌───────────┐
              │  UPLOADED │
              └─────┬─────┘
                    │ Validate Magic Bytes & Size
                    ▼
              ┌───────────┐
              │   QUEUED  │
              └─────┬─────┘
                    │ Dispatch Celery / Background Task
                    ▼
              ┌───────────┐
              │ PROCESSING│
              └─────┬─────┘
                    │ If Low-Text Page Detected (< 50 chars)
                    ▼
          ┌───────────────────┐
          │   OCR_PROCESSING  │
          └─────────┬─────────┘
                    │ Text & Table Deconstruction
                    ▼
          ┌───────────────────┐        If Corrupted / Timeout
          │   PENDING_REVIEW  ├──────────────────────────────► ┌─────────┐
          └─────────┬─────────┘                                │  FAILED │
                    │                                          └────┬────┘
                    ▼                                               │ Retry / Reprocess
          ┌───────────────────┐                                     │
          │     COMPLETED     │ ◄───────────────────────────────────┘
          └───────────────────┘
```

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/college-admin/documents` | Lists all uploaded documents for the authorized college with optional status filtering. |
| `POST` | `/api/v1/college-admin/documents/upload-file` | Multipart binary upload with magic byte verification, private storage persistence, and Celery dispatch. |
| `POST` | `/api/v1/college-admin/documents/upload` | JSON metadata registration endpoint (backward compatible). |
| `GET` | `/api/v1/college-admin/documents/{id}` | Fetches single document details, metadata, checksum, and signed download URL. |
| `GET` | `/api/v1/college-admin/documents/{id}/pages` | Returns page-by-page extracted text, tables, and OCR confidence. |
| `GET` | `/api/v1/college-admin/documents/{id}/status` | Lightweight polling endpoint for tracking processing progress and page counts. |
| `GET` | `/api/v1/college-admin/documents/{id}/download-url` | Generates a time-limited signed URL for viewing/downloading the raw PDF. |
| `POST` | `/api/v1/college-admin/documents/{id}/reprocess` | Re-queues the document for text extraction and OCR reprocessing. |
| `POST` | `/api/v1/college-admin/documents/{id}/retry` | Retries a previously failed document. |
| `DELETE` | `/api/v1/college-admin/documents/{id}` | Deletes the database record, cascaded page entries, and private storage binary. |

---

## 6. How to Install Tesseract OCR on Windows

1. Download the Windows installer from [UB Mannheim Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install to default location: `C:\Program Files\Tesseract-OCR`.
3. Add `C:\Program Files\Tesseract-OCR` to your Windows system `PATH` (optional; the platform automatically searches this directory).
4. For Hindi or Gujarati language data, download `hin.traineddata` or `guj.traineddata` from [Tesseract tessdata](https://github.com/tesseract-ocr/tessdata) and place into `C:\Program Files\Tesseract-OCR\tessdata\`.

---

## 7. Automated Test Execution

Execute the Phase 8 automated test suite:

```bash
node scripts/test_phase8_document_ocr.js
```

