# AI FAQ College Chat Bot

An enterprise-grade, multi-tenant AI-powered college information SaaS platform. Students and visitors can ask questions regarding courses, admissions, fees, hostel, faculty, and departments, receiving accurate answers grounded strictly in official college websites, verified PDF documents, and college-admin approved knowledge bases with source citations and verification badges.

---

## Quick Start (One Command / Start Button)

You can launch all applications concurrently (FastAPI backend on port 8000, Student portal on port 3000, and Admin portal on port 3001) using any of the following methods:

### Method 1: Standard `npm run dev`
From the project root directory, run:
```bash
npm run dev
```

### Method 2: Windows One-Click Start Button
Double-click `start.bat` in File Explorer, or run:
```cmd
start.bat
```

### Method 3: PowerShell Runner
```powershell
powershell scripts/run_dev.ps1
```

### Targeted Execution
- Run only Backend API: `npm run dev:backend`
- Run only Student Portal: `npm run dev:user`
- Run only Admin Portal: `npm run dev:admin`
- Install all dependencies: `npm run install:all`

---

## Port Allocation Matrix

| Application | Technology | URL | Description |
| :--- | :--- | :--- | :--- |
| **Backend API** | FastAPI / Python | [http://localhost:8000](http://localhost:8000) | REST API, Multi-tenant guard, pgvector search |
| **Swagger Docs** | OpenAPI | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API exploration |
| **Student Web** | Next.js 14+ | [http://localhost:3000](http://localhost:3000) | Public student chatbot & college selector |
| **Admin Web** | Next.js 14+ | [http://localhost:3001](http://localhost:3001) | College Admin & Super Admin governance |

---

## High-Level System Architecture

```
[ Student / User Browser ]           [ College Admin & Super Admin Browser ]
           │                                            │
           ▼                                            ▼
   apps/user-frontend                           apps/admin-frontend
 (Next.js 14+ App Router)                     (Next.js 14+ App Router)
           │                                            │
           └─────────────────────┬──────────────────────┘
                                 ▼
                     FastAPI Backend (REST API /v1)
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   Authentication          Multi-Tenant              RAG Engine
   & RBAC Guard           Enforcement Layer       (Hybrid Retrieval)
         │                       │                       │
         ├───────────────────────┴───────────────────────┤
         ▼                                               ▼
  Supabase PostgreSQL                           AI Providers Layer
  (pgvector + Tables + RLS)                     - Google Gemini API (Primary)
         ▲                                      - Backup Fallback Provider
         │
   Supabase Storage (Private PDFs)
         ▲
         │
  Celery Background Workers (Redis Broker)
  - Playwright & HTTPX Website Crawler
  - PyMuPDF, pdfplumber & Tesseract OCR
  - Chunking & Vector Embedding Pipeline
```

---

## Documentation Links

- [System Architecture Specification](docs/ARCHITECTURE.md)
- [Database Schema & ER Diagram](docs/DATABASE_SCHEMA.md)
- [Use Case Specifications](docs/USE_CASES.md)
- [Phase Implementation Roadmap](docs/ROADMAP.md)
