# Production Readiness Checklist & Operational Manual

**Project:** CampusAI – AI FAQ College Chatbot SaaS Platform  
**Target Environment:** Production Cloud Cluster (Docker / Kubernetes / Supabase)  
**Revision:** 1.0.0 (Production Release)  

---

## 1. Infrastructure Architecture

```
[ Internet / Students & Admins ]
              │
              ▼
    [ Cloudflare / Reverse Proxy ]
              │
     ┌────────┴────────┐
     ▼                 ▼
[ User Frontend ]  [ Admin Frontend ]
(Port 3000)        (Port 3001)
     │                 │
     └────────┬────────┘
              │
              ▼
   [ FastAPI Backend Cluster ]
   (Port 8000, 4 Uvicorn Workers)
              │
    ┌─────────┼─────────────────┐
    ▼         ▼                 ▼
[ Supabase ] [ Redis Cluster ] [ Celery Workers ]
PostgreSQL   (Broker & Cache)  (Crawler, OCR, RAG)
+ pgvector
```

---

## 2. Infrastructure & Sizing Verification

| Component | Minimum Production Spec | Recommended Scaling Policy | Status |
| :--- | :--- | :--- | :---: |
| **FastAPI Backend** | 2 vCPU, 4GB RAM (2 instances) | Horizontal autoscaling at 70% CPU / 100 req/sec | Verified |
| **Celery Workers** | 2 vCPU, 4GB RAM (2 instances) | Scale by Celery queue depth ($> 50$ tasks pending) | Verified |
| **Redis Cache** | 1 vCPU, 1GB RAM (Persistent) | In-memory eviction: `volatile-lru` | Verified |
| **Next.js Frontends** | 1 vCPU, 1GB RAM (2 instances each)| CDN caching for static assets (`/_next/static/`) | Verified |
| **PostgreSQL Database** | Supabase Pro / Multi-AZ 4GB | pgBouncer connection pooling enabled | Verified |

---

## 3. Database Connection Pooling & Tuning

- [x] **Connection Pooler:** Use Supabase Transaction Pooler (port `6543`) with `pgBouncer` for short-lived HTTP API requests.
- [x] **Direct Connection:** Reserve direct PostgreSQL port `5432` for schema migrations and Alembic upgrades only.
- [x] **Pool Limits:** Configure SQLAlchemy async pool with `pool_size=20`, `max_overflow=10`, `pool_timeout=30`, `pool_recycle=1800` seconds.
- [x] **Vector Indexing:** pgvector `HNSW` or `IVFFlat` indexes verified on `knowledge_chunks.embedding` with cosine distance operator (`<=>`).

---

## 4. Background Workers & Queue Management

- [x] **Concurrency:** Production Celery worker launched with 4 concurrent worker processes:
  `celery -A app.workers.celery_app.celery worker --loglevel=info -c 4`
- [x] **Separation of Queues:**
  - `crawler_queue`: Website page fetching and DOM parsing.
  - `ocr_queue`: PyMuPDF and Tesseract image processing.
  - `rag_queue`: Embedding generation and chunk indexing.
- [x] **Scheduler:** Celery Beat daemon active for daily website incremental recrawling.
- [x] **Task Retries:** Exponential backoff configured on external API calls with maximum 3 retries.

---

## 5. Security & Network Hardening

- [x] **Non-Root Execution:** Backend Docker container runs strictly as unprivileged user `appuser` (UID 10001).
- [x] **Frontend Containers:** Next.js containers run as unprivileged user `nextjs` (UID 1001) using standalone output.
- [x] **Network Segmentation:** Docker Compose isolates Redis on internal private bridge `data-net`.
- [x] **OWASP Security Headers:** Enforced on every HTTP response:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- [x] **Payload Limits:** Maximum JSON payload 2MB; maximum file upload payload 55MB.
- [x] **Rate Limiting:** Sliding-window rate limiter active across authentication and query endpoints.

---

## 6. Health & Readiness Telemetry

- [x] **Liveness Probe:** `GET /api/v1/health`
  - Checks if FastAPI process is responsive.
  - Returns HTTP 200 with service name, environment, and version.
- [x] **Readiness Probe:** `GET /api/v1/health/ready`
  - Deep dependency check probing PostgreSQL, Redis broker, and Supabase Storage.
  - Returns HTTP 200 when ready; returns HTTP 503 if any core dependency fails.

---

## 7. Telemetry & Log Management

- [x] **PII Scrubbing:** Console and file logs automatically strip JWT tokens, passwords, and sensitive student emails.
- [x] **Structured JSON Logging:** Container log driver configured with `json-file`, `max-size: 10m`, `max-file: 5` to prevent disk saturation.
- [x] **Error Tracking:** Sentry SDK initialized with `before_send` scrubbing for unhandled exceptions.
- [x] **Correlation Tracking:** `X-Request-ID` attached to all request/response cycles for distributed tracing.

---

## 8. Deployment Sign-Off Procedure

1. Verify environment secrets populated in production vault (`.env` or Cloud Secrets Manager).
2. Apply database migrations: `alembic upgrade head` or execute `database/migrations/*.sql`.
3. Launch services: `docker compose -f docker-compose.prod.yml up -d`.
4. Validate readiness: `curl -f http://localhost:8000/api/v1/health/ready`.
5. Run automated end-to-end smoke tests.

