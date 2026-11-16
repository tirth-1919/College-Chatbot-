# Use Case Specifications

This document outlines the core functional interactions for each actor in the system:
1. **Regular User / Student**
2. **College Admin**
3. **Global Super Admin**
4. **Automated Celery Background Engine**

---

## 1. Actor-to-Use-Case Matrix

```mermaid
graph LR
    subgraph Student["Student / Public Visitor"]
        UC_S1["Register / Login / Verify Email"]
        UC_S2["Select College Tenant"]
        UC_S3["Ask Question (Text / Voice)"]
        UC_S4["View Verified Answers & Citations"]
        UC_S5["Manage Chat History (Rename/Delete)"]
        UC_S6["Provide Response Feedback (Thumbs/Rating)"]
        UC_S7["Switch Language (English / Hindi / Gujarati)"]
    end

    subgraph CollegeAdmin["College Admin"]
        UC_CA1["Log In to College Dashboard"]
        UC_CA2["Configure & Trigger Website Crawler"]
        UC_CA3["Upload PDF Documents & Trigger OCR"]
        UC_CA4["Review Extraction Queue (Pending Chunks)"]
        UC_CA5["Approve / Reject / Edit Extracted Facts"]
        UC_CA6["Publish / Unpublish Knowledge"]
        UC_CA7["Manage Structured College Entities\n(Courses, Fees, Faculty, Hostel)"]
        UC_CA8["Inspect Analytics & Unanswered Queries"]
    end

    subgraph SuperAdmin["Global Super Admin"]
        UC_SA1["Approve / Reject College Registrations"]
        UC_SA2["Manage Colleges & Tenants"]
        UC_SA3["Invite / Manage College Administrators"]
        UC_SA4["Manage Users & Revoke Sessions"]
        UC_SA5["Configure AI Providers (Gemini + Fallbacks)"]
        UC_SA6["Monitor Token Usage, Ingestion Jobs & Audit Logs"]
        UC_SA7["View Global Health & System Telemetry"]
    end

    subgraph Workers["Background Worker Engine"]
        UC_W1["Execute Playwright/HTTPX Crawler Jobs"]
        UC_W2["Process PDFs with PyMuPDF & pdfplumber"]
        UC_W3["Perform Tesseract OCR on Scanned Pages"]
        UC_W4["Generate Vector Embeddings via Gemini"]
        UC_W5["Run Scheduled Re-crawls & Health Probes"]
    end
```

---

## 2. Key Sequence Workflows

### 2.1. Student Chat Request & RAG Evaluation Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Student
    participant Frontend as apps/student-web
    participant API as FastAPI Backend
    participant TenantSec as Tenant Enforcement Guard
    participant DB as Supabase PostgreSQL (pgvector)
    participant Gemini as Google Gemini API
    participant Fallback as Secondary AI Fallback

    Student->>Frontend: Enters query: "What are the computer engineering fees?"
    Frontend->>API: POST /api/v1/chat/{session_id}/message {text, college_id}
    API->>TenantSec: Validate college_id & student session
    TenantSec->>DB: Query published knowledge chunks (WHERE college_id = X AND status = 'PUBLISHED')
    DB-->>API: Returns Top K matching chunks with similarity scores
    
    alt Sufficient Evidence Found (Similarity >= Threshold)
        API->>Gemini: Prompt with verified context + question
        Gemini-->>API: Grounded response with citations
        API->>DB: Save assistant response (verified=true, citations=[...])
        API-->>Frontend: Return response with green "Verified" badge and source links
    else Insufficient Evidence / Off-Topic
        API->>Gemini: Generate general guidance prompt (Label: General guidance)
        Gemini-->>API: Returns guidance
        API->>DB: Save assistant response (verified=false, label="GEMINI_UNVERIFIED")
        API-->>Frontend: Return response with amber "Unverified AI Guidance" badge
    else Gemini Outage / Rate Limit Exceeded
        API->>Fallback: Dispatch prompt to secondary provider
        Fallback-->>API: Response from backup model
        API->>DB: Save assistant response (verified=false, label="SECONDARY_AI_FALLBACK")
        API-->>Frontend: Return response with fallback notice
    end
```

### 2.2. PDF Upload, OCR & Knowledge Publishing Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Admin as College Admin
    participant AdminUI as apps/admin-web
    participant API as FastAPI Backend
    participant Storage as Supabase Storage
    participant Celery as Celery Worker Pool
    participant DB as Supabase PostgreSQL

    Admin->>AdminUI: Selects & uploads prospectus PDF
    AdminUI->>API: POST /api/v1/documents/upload (binary)
    API->>API: Validate MIME, magic bytes (%PDF-), virus check
    API->>Storage: Store file in private bucket (college-id/documents/...)
    API->>DB: Insert record into `documents` table (status: 'PROCESSING')
    API->>Celery: Enqueue `process_document_task(document_id)`
    API-->>AdminUI: 202 Accepted (processing in background)

    Celery->>Storage: Fetch PDF binary stream
    Celery->>Celery: Extract pages with PyMuPDF
    opt Page contains scanned image with low text density
        Celery->>Celery: Run Tesseract OCR on page raster
    end
    Celery->>Celery: Chunk paragraphs & extract facts
    Celery->>DB: Save document_pages, paragraphs & knowledge_chunks (status: 'PENDING_REVIEW')
    Celery->>DB: Update documents status: 'PENDING_REVIEW'

    Admin->>AdminUI: Views Knowledge Review Queue
    AdminUI->>API: GET /api/v1/knowledge/review-queue
    API-->>AdminUI: List of unreviewed chunks
    Admin->>AdminUI: Edits or clicks "Approve"
    AdminUI->>API: POST /api/v1/knowledge/{chunk_id}/approve
    API->>DB: Update chunk status: 'APPROVED'
    
    Admin->>AdminUI: Clicks "Publish Knowledge"
    AdminUI->>API: POST /api/v1/knowledge/{chunk_id}/publish
    API->>Celery: Trigger embedding generation task
    Celery->>DB: Save embedding vector, mark status = 'PUBLISHED'
    API-->>AdminUI: Knowledge is now live for student chat retrieval!
```

